"""src/application/cargas/use_cases/atribuir_cargas_batch.py — Caso de uso: desagregación batch diaria de cargas NILM."""

import math
from bisect import bisect_left
from datetime import UTC, datetime

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    AtribuirCargasBatchResponseDTO,
    CargaDTO,
    FirmaConfirmadaDTO,
    IntervaloMarchaDTO,
    MedidorDTO,
    ParametrosBancoDTO,
    ParametrosMotorDTO,
    VentanaUtcDTO,
)
from src.domain.cargas.banco_capacitores import (
    ConmutacionBanco,
    coincide_con_banco,
    detectar_conmutaciones,
    es_evento_de_banco,
)
from src.domain.cargas.entities import EventoCarga, Medicion
from src.domain.cargas.services import detectar_eventos, integrar_trapecios


def _utc(instante: datetime) -> datetime:
    """Instante interno (UTC sin zona) → instante con zona UTC, para la salida."""
    return instante.replace(tzinfo=UTC)


def umbral_minimo_kw(firmas: list[FirmaConfirmadaDTO]) -> float:
    """Umbral |ΔP| mínimo para detectar escalones: el más bajo que alguna firma puede necesitar."""
    return min(
        max(f.umbral_marcha_kw, f.potencia_nominal_kw - f.tolerancia_kw, 0.1) for f in firmas
    )


def _cae_bajo_base(
    mediciones: list[Medicion], indice_inicio: int, indice_evento: int, tolerancia_kw: float
) -> bool:
    """¿La potencia en el evento quedó por debajo de la base previa al encendido, menos la tolerancia?

    Si pasa, el escalón no es de esta máquina: se apagó otra carga (no catalogada) que formaba parte
    de la base. El intervalo no puede seguir atribuyéndose a la máquina después de ese escalón.
    """
    base = mediciones[indice_inicio - 1].potencia_kw
    return mediciones[indice_evento].potencia_kw < base - tolerancia_kw


def buscar_firma_compatible(
    evento: EventoCarga,
    firmas: list[FirmaConfirmadaDTO],
    params: ParametrosBancoDTO,
    usar_q: bool = True,
) -> tuple[FirmaConfirmadaDTO, float] | None:
    """Firma más parecida al salto y la distancia en P, o None si ninguna encaja.

    ΔP es el criterio principal: solo entran firmas cuya potencia nominal cae dentro de su tolerancia.
    La ΔQ suma con su peso, pero solo si `usar_q` es True (si el escalón tiene la ΔQ contaminada por
    una conmutación de banco, no se usa). Con pesos iguales (el default) la distancia es la euclídea en P-Q.
    """
    delta_p = abs(evento.delta_kw)
    delta_q = abs(evento.delta_kvar)
    candidatas: list[tuple[float, float, FirmaConfirmadaDTO]] = []
    for firma in firmas:
        dist_p = abs(delta_p - firma.potencia_nominal_kw)
        if dist_p <= firma.tolerancia_kw:
            dist_q = abs(delta_q - firma.reactiva_tipica_kvar) if usar_q else 0.0
            distancia = math.sqrt((params.peso_p * dist_p) ** 2 + (params.peso_q * dist_q) ** 2)
            candidatas.append((distancia, dist_p, firma))
    if not candidatas:
        return None
    _, dist_p, firma = min(candidatas, key=lambda t: t[0])
    return firma, dist_p


def tolerancia_efectiva(firma: FirmaConfirmadaDTO, params: ParametrosMotorDTO) -> float:
    """Tolerancia que usa el motor para la firma.

    Por defecto, la tolerancia explícita de la firma. Con `tolerancia_por_dispersion`, la dispersión medida del
    grupo (si la firma la trae) por `factor_dispersion`, acotada entre `tolerancia_min_kw` y `tolerancia_max_kw`.
    Una tolerancia ancha confunde cargas de potencia parecida; el tope la evita.
    """
    if not params.tolerancia_por_dispersion or firma.dispersion_kw is None:
        return firma.tolerancia_kw
    estimada = params.factor_dispersion * firma.dispersion_kw
    return min(max(estimada, params.tolerancia_min_kw), params.tolerancia_max_kw)


def _con_tolerancias_efectivas(
    request: AtribuirCargasBatchRequestDTO,
) -> AtribuirCargasBatchRequestDTO:
    """Copia de la petición con la tolerancia efectiva de cada firma. Sin cambios con el default."""
    params = request.parametros_motor
    if not params.tolerancia_por_dispersion:
        return request
    firmas = [
        f.model_copy(update={"tolerancia_kw": tolerancia_efectiva(f, params)})
        for f in request.firmas
    ]
    return request.model_copy(update={"firmas": firmas})


def _confianza(distancia_kw: float, tolerancia_kw: float) -> float:
    """1 si el salto coincide exacto con la potencia nominal; 0 si cae en el borde de la tolerancia."""
    if tolerancia_kw <= 0:
        return 1.0 if distancia_kw == 0 else 0.0
    return round(min(1.0, max(0.0, 1.0 - distancia_kw / tolerancia_kw)), 2)


class AtribuirCargasBatchUseCase:
    """Desagrega un día cerrado de un medidor y atribuye intervalos de marcha a las cargas confirmadas.

    Magnitudes medidas, no nominales:
    - Energía: si la fuente trae el contador acumulado en los bordes del intervalo, es su diferencia
      menos la carga base por el tiempo. Si no, es la integral por trapecios de (P - P_base).
      P_base es la potencia de la medición anterior al encendido: así no se atribuye a la máquina
      la carga permanente del tablero.
    - Un intervalo sin apagado dentro del día se cierra en la última medición real de ese día.
      Nunca se extiende a una hora inventada (ni a 23:59:59).
    - Mediciones fuera de la ventana del día se descartan: un intervalo no cruza hacia otro día.
    """

    def ejecutar(self, request: AtribuirCargasBatchRequestDTO) -> AtribuirCargasBatchResponseDTO:
        request = _con_tolerancias_efectivas(request)
        mediciones = sorted(
            (
                m
                for m in request.mediciones
                if request.ventana_desde_utc <= m.instante < request.ventana_hasta_utc
            ),
            key=lambda m: m.instante,
        )
        intervalos_por_firma: dict[str, list[IntervaloMarchaDTO]] = {
            f.machine_id: [] for f in request.firmas
        }

        if request.firmas and len(mediciones) >= 2:
            params = request.parametros_banco
            conmutaciones = detectar_conmutaciones(
                mediciones, params.umbral_p_kw, params.umbral_q_kvar
            )
            # Las conmutaciones de banco no son cargas: no entran en la atribución.
            eventos = [
                e
                for e in detectar_eventos(
                    mediciones,
                    umbral_kw=umbral_minimo_kw(request.firmas),
                    muestras_persistencia=request.parametros_motor.muestras_debounce,
                )
                if not es_evento_de_banco(e, params.umbral_p_kw, params.umbral_q_kvar)
            ]
            for machine_id, intervalo in self._emparejar_eventos(
                request, mediciones, eventos, conmutaciones
            ):
                intervalos_por_firma[machine_id].append(intervalo)

        return AtribuirCargasBatchResponseDTO(
            generado_en_utc=request.generado_en_utc.replace(tzinfo=UTC),
            fecha_local=request.fecha_local,
            ventana_utc=VentanaUtcDTO(
                desde=_utc(request.ventana_desde_utc),
                hasta=_utc(request.ventana_hasta_utc),
            ),
            medidor=MedidorDTO(
                device_id=request.device_id,
                etiqueta_ml=request.etiqueta_ml,
                ultima_lectura_utc=_utc(mediciones[-1].instante) if mediciones else None,
            ),
            cargas=[
                CargaDTO(
                    load_id=f.load_id,
                    nombre=f.nombre,
                    intervalos=sorted(
                        intervalos_por_firma[f.machine_id], key=lambda it: it.inicio_utc
                    ),
                )
                for f in request.firmas
            ],
        )

    def _emparejar_eventos(
        self,
        request: AtribuirCargasBatchRequestDTO,
        mediciones: list[Medicion],
        eventos: list[EventoCarga],
        conmutaciones: list[ConmutacionBanco],
    ) -> list[tuple[str, IntervaloMarchaDTO]]:
        params = request.parametros_banco
        instantes = [m.instante for m in mediciones]
        firmas_por_id = {f.machine_id: f for f in request.firmas}
        cerrados: list[tuple[str, IntervaloMarchaDTO]] = []
        # machine_id → (índice de la primera medición en marcha, confianza del encendido)
        encendidos_activos: dict[str, tuple[int, float]] = {}

        for ev in eventos:
            indice = bisect_left(instantes, ev.instante)
            # Si un banco conmutó en la misma ventana, la ΔQ de este escalón no es confiable: se empareja solo con P.
            contaminado = coincide_con_banco(ev.instante, conmutaciones, params.tolerancia)
            encontrada = buscar_firma_compatible(ev, request.firmas, params, usar_q=not contaminado)
            if encontrada is None:
                if not ev.es_encendido:
                    cerrados.extend(
                        self._cortar_por_escalon_ajeno(
                            mediciones, indice, firmas_por_id, encendidos_activos
                        )
                    )
                continue
            firma, distancia = encontrada
            confianza = _confianza(distancia, firma.tolerancia_kw)
            if ev.es_encendido:
                if firma.machine_id not in encendidos_activos:
                    encendidos_activos[firma.machine_id] = (indice, confianza)
            elif firma.machine_id in encendidos_activos:
                inicio, conf_on = encendidos_activos.pop(firma.machine_id)
                intervalo = self._crear_intervalo(
                    firma, mediciones, inicio, indice, (conf_on + confianza) / 2
                )
                cerrados.append((firma.machine_id, intervalo))

        # Sin apagado dentro del día: el intervalo termina en la última medición real.
        ultimo = len(mediciones) - 1
        for machine_id, (inicio, conf_on) in encendidos_activos.items():
            intervalo = self._crear_intervalo(
                firmas_por_id[machine_id], mediciones, inicio, ultimo, conf_on
            )
            cerrados.append((machine_id, intervalo))

        return cerrados

    def _cortar_por_escalon_ajeno(
        self,
        mediciones: list[Medicion],
        indice: int,
        firmas_por_id: dict[str, FirmaConfirmadaDTO],
        encendidos_activos: dict[str, tuple[int, float]],
    ) -> list[tuple[str, IntervaloMarchaDTO]]:
        """Cierra en `indice` las máquinas en marcha cuya base cayó por un apagado que no es de ninguna firma.

        Un apagado no catalogado que deja la potencia bajo la base de una máquina en marcha significa que
        se apagó otra carga que formaba parte de esa base. La máquina no puede seguir acumulando energía
        más allá de ese escalón. Se quita de `encendidos_activos` para que su apagado posterior no la cierre.
        """
        cortados: list[tuple[str, IntervaloMarchaDTO]] = []
        for machine_id, (inicio, conf_on) in list(encendidos_activos.items()):
            firma = firmas_por_id[machine_id]
            if _cae_bajo_base(mediciones, inicio, indice, firma.tolerancia_kw):
                del encendidos_activos[machine_id]
                cortados.append(
                    (machine_id, self._crear_intervalo(firma, mediciones, inicio, indice, conf_on))
                )
        return cortados

    def _crear_intervalo(
        self,
        firma: FirmaConfirmadaDTO,
        mediciones: list[Medicion],
        indice_inicio: int,
        indice_fin: int,
        confianza: float,
    ) -> IntervaloMarchaDTO:
        """Arma el intervalo entre dos mediciones, con energía, potencia y reactiva medidas."""
        base = mediciones[indice_inicio - 1]
        tramo = mediciones[indice_inicio : indice_fin + 1]
        inicio = mediciones[indice_inicio].instante
        fin = mediciones[indice_fin].instante

        horas = max(0.0, (fin - inicio).total_seconds()) / 3600.0
        energia = self._energia_kwh(base, tramo, horas)
        potencia_media = (
            energia / horas
            if horas > 0
            else mediciones[indice_inicio].potencia_kw - base.potencia_kw
        )

        delta_reactiva: float | None = None
        if base.reactiva_kvar is not None and all(m.reactiva_kvar is not None for m in tramo):
            delta_reactiva = self._reactiva_media(base, tramo, horas)

        return IntervaloMarchaDTO(
            inicio_utc=_utc(inicio),
            fin_utc=_utc(fin),
            horas=round(horas, 4),
            energia_kwh_medida=round(energia, 3),
            potencia_media_kw=round(potencia_media, 3),
            delta_reactiva_kvar=round(delta_reactiva, 3) if delta_reactiva is not None else None,
            confianza=confianza,
        )

    @staticmethod
    def _energia_kwh(base: Medicion, tramo: list[Medicion], horas: float) -> float:
        """Energía de la máquina en el tramo, sin la carga base."""
        inicial, final = tramo[0], tramo[-1]
        if inicial.energia_acumulada_kwh is not None and final.energia_acumulada_kwh is not None:
            # Diferencia de contadores del medidor, menos la base integrada en el mismo tiempo.
            return (
                final.energia_acumulada_kwh - inicial.energia_acumulada_kwh
            ) - base.potencia_kw * horas
        return integrar_trapecios([(m.instante, m.potencia_kw - base.potencia_kw) for m in tramo])

    @staticmethod
    def _reactiva_media(base: Medicion, tramo: list[Medicion], horas: float) -> float:
        """Reactiva media del tramo menos la base, en kVAr."""
        base_q = base.reactiva_kvar or 0.0
        if horas > 0:
            energia_q = integrar_trapecios(
                [(m.instante, (m.reactiva_kvar or 0.0) - base_q) for m in tramo]
            )
            return energia_q / horas
        return (tramo[0].reactiva_kvar or 0.0) - base_q
