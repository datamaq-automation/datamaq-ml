"""src/application/cargas/use_cases/identificar_cargas.py — Caso de uso: qué cargas hay detrás del consumo total."""

from src.application.cargas.dtos.identificar_cargas import (
    AgrupamientoResponse,
    BarraHistogramaResponse,
    CargaResponse,
    EventoResponse,
    IdentificarCargasRequest,
    IdentificarCargasResponse,
    ModoResponse,
    PuntoResponse,
    SaltosBajoUmbralResponse,
    UmbralResponse,
)
from src.domain.cargas.entities import Carga, EstimacionUmbral, EventoCarga, Medicion
from src.domain.cargas.regimenes import Modo, etiquetar_por_modos, hallar_regimen
from src.domain.cargas.repositories import AgrupadorEventos, Bitacora, MedicionRepository
from src.domain.cargas.services import (
    detectar_eventos,
    estimar_min_eventos,
    estimar_radio,
    estimar_umbral,
    histograma,
    nivel_de_ruido,
    resumir_cargas,
    saltos_bajo_umbral,
    saltos_kw,
)

REGIMEN_OTSU = "otsu"
REGIMEN_VALLE = "valle_claro"
REGIMEN_SIN_MODOS = "sin_modos_separables"


def _cargas_respuesta(
    cargas: list[Carga], dias: float, balance_minimo: float
) -> list[CargaResponse]:
    return [
        CargaResponse(
            potencia_tipica_kw=c.potencia_tipica_kw,
            encendidos=c.encendidos,
            apagados=c.apagados,
            ciclos=c.ciclos,
            ciclos_por_dia=round(c.ciclos / dias, 1) if dias >= 1 else None,
            on_off=c.es_on_off(balance_minimo),
            dispersion_kw=c.dispersion_kw,
            reactiva_tipica_kvar=c.reactiva_tipica_kvar,
            cos_phi_estimado=c.cos_phi_estimado,
            ratio_qp_mediana=c.ratio_qp_mediana,
        )
        for c in cargas
    ]


class IdentificarCargasUseCase:
    def __init__(
        self,
        mediciones: MedicionRepository,
        agrupador: AgrupadorEventos,
        umbral_kw: float | None,
        logger: Bitacora,
        balance_minimo: float = 0.5,
        separacion_minima: float = 0.8,
        radio_kw: float | None = None,
        min_eventos: int | None = None,
    ) -> None:
        self._min_eventos = min_eventos
        self._radio_kw = radio_kw
        self._separacion_minima = separacion_minima
        self._balance_minimo = balance_minimo
        self._logger = logger
        self._mediciones = mediciones
        self._agrupador = agrupador
        self._umbral_kw = umbral_kw

    def execute(self, request: IdentificarCargasRequest) -> IdentificarCargasResponse:
        serie = self._leer(request)
        umbral = self._elegir_umbral(serie)
        eventos = self._detectar(serie, umbral.kw)
        agrupamiento, etiquetas, modos = self._agrupar(serie, eventos, umbral)
        cargas = self._resumir(serie, eventos, etiquetas)
        return self._responder(
            request.medidor, serie, eventos, etiquetas, cargas, umbral, agrupamiento, modos
        )

    def _agrupar(
        self, serie: list[Medicion], eventos: list[EventoCarga], umbral: UmbralResponse
    ) -> tuple[AgrupamientoResponse, list[int], list[Modo]]:
        """Agrupa los eventos según el régimen: DBSCAN (Otsu), modos del valle, o nada si no hay modos."""
        if umbral.regimen == REGIMEN_SIN_MODOS:
            self._logger.warning(
                "Sin modos separables: no se agrupan cargas (hace falta una firma confirmada)"
            )
            return _agrupamiento_sin_grupos(), [-1] * len(eventos), []
        if umbral.regimen == REGIMEN_VALLE:
            return _agrupar_por_modos(serie, eventos, self._logger)
        agrupamiento = self._elegir_agrupamiento(serie, eventos, umbral.kw)
        etiquetas = (
            self._agrupador.agrupar(eventos, agrupamiento.radio_kw, agrupamiento.min_eventos)
            if eventos and agrupamiento.radio_kw
            else [-1] * len(eventos)
        )
        return agrupamiento, etiquetas, []

    def _responder(
        self,
        medidor: str,
        serie: list[Medicion],
        eventos: list[EventoCarga],
        etiquetas: list[int],
        cargas: list[Carga],
        umbral: UmbralResponse,
        agrupamiento: AgrupamientoResponse,
        modos: list[Modo],
    ) -> IdentificarCargasResponse:
        dias = _dias(serie)
        encendidos = sum(e.es_encendido for e in eventos)
        cant_bajo, energia_bajo = (
            saltos_bajo_umbral(serie, umbral.kw) if umbral.kw is not None else (0, 0.0)
        )
        return IdentificarCargasResponse(
            medidor=medidor,
            mediciones=len(serie),
            eventos=len(eventos),
            encendidos=encendidos,
            apagados=len(eventos) - encendidos,
            eventos_sin_grupo=etiquetas.count(-1),
            dias=round(dias, 1),
            potencia_media_kw=round(sum(m.potencia_kw for m in serie) / len(serie), 1)
            if serie
            else 0.0,
            cargas=_cargas_respuesta(cargas, dias, self._balance_minimo),
            umbral=umbral,
            agrupamiento=agrupamiento,
            saltos_bajo_umbral=SaltosBajoUmbralResponse(
                cantidad=cant_bajo, energia_kwh=round(energia_bajo, 1)
            ),
            sin_modos_separables=umbral.regimen == REGIMEN_SIN_MODOS,
            modos=_modos_respuesta(modos),
            serie=[
                PuntoResponse(instante=m.instante, potencia_kw=m.potencia_kw)
                for m in sorted(serie, key=lambda m: m.instante)
            ],
            detalle_eventos=_detalle_eventos(eventos, etiquetas),
            histograma=[
                BarraHistogramaResponse(
                    desde_kw=b.desde_kw, hasta_kw=b.hasta_kw, cantidad=b.cantidad
                )
                for b in histograma(saltos_kw(serie))
            ],
        )

    def _leer(self, request: IdentificarCargasRequest) -> list[Medicion]:
        self._logger.info(
            "Paso 1/4 · Leyendo mediciones de %s (%s → %s)",
            request.medidor,
            request.desde,
            request.hasta,
        )
        serie = self._mediciones.listar(request.medidor, request.desde, request.hasta)
        if serie:
            media = sum(m.potencia_kw for m in serie) / len(serie)
            self._logger.info(
                "Potencia media del medidor: %.0f kW (para comparar con las cargas)", media
            )
        else:
            self._logger.warning("%s no tiene mediciones en el rango pedido", request.medidor)
        return serie

    def _elegir_umbral(self, serie: list[Medicion]) -> UmbralResponse:
        self._logger.info("Paso 2/4 · Detectando saltos de potencia |ΔP|")
        if self._umbral_kw is not None:
            self._logger.info("Umbral fijo por configuración: %s kW", self._umbral_kw)
            return UmbralResponse(kw=self._umbral_kw, automatico=False)
        estimacion = estimar_umbral(serie)
        if estimacion is None:
            self._logger.warning("No hay suficientes mediciones para estimar el umbral automático")
            return UmbralResponse(kw=None, automatico=True)
        self._logger.info(
            "Umbral automático: %s kW (Otsu, separación ruido/eventos η=%.2f)",
            estimacion.umbral_kw, estimacion.separacion,
        )  # fmt: skip
        if estimacion.es_confiable(self._separacion_minima):
            return UmbralResponse(
                kw=estimacion.umbral_kw, automatico=True, separacion=estimacion.separacion,
                confiable=True, regimen=REGIMEN_OTSU,
            )  # fmt: skip
        return _umbral_de_valle(serie, estimacion, self._logger, self._separacion_minima)

    def _elegir_agrupamiento(
        self, serie: list[Medicion], eventos: list[EventoCarga], umbral_kw: float | None
    ) -> AgrupamientoResponse:
        self._logger.info("Paso 3/4 · Agrupando eventos por magnitud (DBSCAN)")
        radio, radio_automatico = self._radio_kw, self._radio_kw is None
        if radio_automatico:
            ruido = nivel_de_ruido(serie, umbral_kw) if umbral_kw else 0.0
            radio = estimar_radio(eventos, ruido)
            if radio is not None:
                self._logger.info(
                    "Radio automático: %s kW (mayor entre Freedman–Diaconis y 2 × ruido de la señal, ruido = %.1f kW)",
                    radio, ruido,
                )  # fmt: skip
        else:
            self._logger.info("Radio fijo por configuración: %s kW", radio)
        minimo, minimo_automatico = self._min_eventos, self._min_eventos is None
        if minimo is None:
            minimo = estimar_min_eventos(_dias(serie))
            self._logger.info(
                "Mínimo automático: %d eventos por carga (uno por día analizado, al menos 3)",
                minimo,
            )
        else:
            self._logger.info("Mínimo fijo por configuración: %d eventos por carga", minimo)
        return AgrupamientoResponse(
            radio_kw=radio,
            radio_automatico=radio_automatico,
            min_eventos=minimo,
            min_eventos_automatico=minimo_automatico,
        )

    def _detectar(self, serie: list[Medicion], umbral: float | None) -> list[EventoCarga]:
        if umbral is None:
            return []
        eventos = detectar_eventos(serie, umbral)
        encendidos = sum(e.es_encendido for e in eventos)
        self._logger.info(
            "%d eventos detectados en %d mediciones (%d ↑ encendidos, %d ↓ apagados)",
            len(eventos), len(serie), encendidos, len(eventos) - encendidos,
        )  # fmt: skip
        if serie and not eventos:
            self._logger.warning("Ningún salto supera %s kW: probá con un umbral más bajo", umbral)
        return eventos

    def _resumir(
        self, serie: list[Medicion], eventos: list[EventoCarga], etiquetas: list[int]
    ) -> list[Carga]:
        self._logger.info("Paso 4/4 · Resumiendo cargas")
        cargas = resumir_cargas(eventos, etiquetas)
        dias = _dias(serie)
        for c in cargas:
            por_dia = ""
            if dias >= 1:
                frecuencia = c.ciclos / dias
                por_dia = (
                    f" (≈{frecuencia:.0f}/día)"
                    if frecuencia >= 1
                    else f" (≈{frecuencia * 7:.1f}/semana)"
                )
            self._logger.info(
                "Carga de ~%s kW: %d ↑ encendidos, %d ↓ apagados, %d ciclos%s",
                c.potencia_tipica_kw, c.encendidos, c.apagados, c.ciclos, por_dia,
            )  # fmt: skip
            if not c.es_on_off(self._balance_minimo):
                self._logger.warning(
                    "~%s kW tiene %d ↑ y %d ↓: probablemente no es una sola carga ON/OFF",
                    c.potencia_tipica_kw, c.encendidos, c.apagados,
                )  # fmt: skip
        if eventos and not cargas:
            self._logger.warning(
                "Hubo eventos pero ningún grupo alcanzó el mínimo para ser una carga"
            )
        return cargas


def _agrupar_por_modos(
    serie: list[Medicion], eventos: list[EventoCarga], logger: Bitacora
) -> tuple[AgrupamientoResponse, list[int], list[Modo]]:
    """Régimen de valle claro: cada modo de eventos es una carga; el radio es el de cada modo."""
    modos = hallar_regimen(saltos_kw(serie)).modos
    etiquetas = etiquetar_por_modos([abs(e.delta_kw) for e in eventos], modos)
    radios = [m.radio_kw for m in modos]
    logger.info(
        "Modos separables por valle: %d (radio por modo: %s kW)",
        len(modos), ", ".join(f"{r:.1f}" for r in radios) or "—",
    )  # fmt: skip
    return _agrupamiento_sin_grupos(radio_kw=max(radios, default=None)), etiquetas, modos


def _umbral_de_valle(
    serie: list[Medicion], estimacion: EstimacionUmbral, logger: Bitacora, separacion_minima: float
) -> UmbralResponse:
    """Con η bajo, Otsu no separa: el umbral es el valle del histograma de |ΔP|, si lo hay.

    Sin valle no hay ningún umbral que separe nada: se conserva el de Otsu para contar eventos, y el
    régimen queda en «sin modos separables» (no se agrupa).
    """
    logger.warning(
        "η=%.2f < %.2f: Otsu no separa ruido y eventos; se busca el valle del histograma de |ΔP|",
        estimacion.separacion, separacion_minima,
    )  # fmt: skip
    regimen = hallar_regimen(saltos_kw(serie))
    if regimen.umbral_kw is None:
        logger.warning("Sin valle en el histograma: se usa el umbral de Otsu, sin modos separables")
        return UmbralResponse(
            kw=estimacion.umbral_kw, automatico=True, separacion=estimacion.separacion,
            confiable=False, regimen=REGIMEN_SIN_MODOS,
        )  # fmt: skip
    return UmbralResponse(
        kw=regimen.umbral_kw,
        automatico=True,
        separacion=estimacion.separacion,
        confiable=False,
        regimen=REGIMEN_VALLE if regimen.hay_modos else REGIMEN_SIN_MODOS,
    )


def _modos_respuesta(modos: list[Modo]) -> list[ModoResponse]:
    return [
        ModoResponse(
            desde_kw=m.desde_kw,
            hasta_kw=m.hasta_kw,
            cantidad=m.cantidad,
            centro_kw=m.centro_kw,
            dispersion_kw=m.dispersion_kw,
            radio_kw=m.radio_kw,
        )
        for m in modos
    ]


def _agrupamiento_sin_grupos(radio_kw: float | None = None) -> AgrupamientoResponse:
    return AgrupamientoResponse(
        radio_kw=radio_kw,
        radio_automatico=True,
        min_eventos=0,
        min_eventos_automatico=True,
    )


def _dias(serie: list[Medicion]) -> float:
    if not serie:
        return 0.0
    return (max(m.instante for m in serie) - min(m.instante for m in serie)).total_seconds() / 86400


def _detalle_eventos(eventos: list[EventoCarga], etiquetas: list[int]) -> list[EventoResponse]:
    """Cada evento con la potencia típica de su grupo (la misma que calcula resumir_cargas)."""
    por_grupo: dict[int, list[float]] = {}
    for evento, etiqueta in zip(eventos, etiquetas, strict=False):
        if etiqueta >= 0:
            por_grupo.setdefault(etiqueta, []).append(abs(evento.delta_kw))
    potencia = {g: round(sum(v) / len(v), 1) for g, v in por_grupo.items()}
    etiquetas_completas = etiquetas or [-1] * len(eventos)
    return [
        EventoResponse(instante=e.instante, delta_kw=round(e.delta_kw, 1), carga_kw=potencia.get(g))
        for e, g in zip(eventos, etiquetas_completas, strict=True)
    ]
