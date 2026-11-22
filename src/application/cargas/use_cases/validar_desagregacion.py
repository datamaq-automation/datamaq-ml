"""src/application/cargas/use_cases/validar_desagregacion.py — Validación de la desagregación de un día sin verdad de terreno.

No compara contra nada externo: mide cuánto del consumo queda atribuido, qué tan consistentes son
los intervalos y cuántos escalones quedan sin explicar. Sirve para decidir si un catálogo de firmas
y sus tolerancias son plausibles antes de confiar en el batch.
"""

from datetime import datetime

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    AtribuirCargasBatchResponseDTO,
    FirmaConfirmadaDTO,
    IntervaloMarchaDTO,
    ParametrosBancoDTO,
)
from src.application.cargas.dtos.validar_desagregacion import (
    CargaValidacionDTO,
    MetricasDiaDTO,
)
from src.application.cargas.use_cases.atribuir_cargas_batch import (
    AtribuirCargasBatchUseCase,
    umbral_minimo_kw,
)
from src.domain.cargas.banco_capacitores import (
    coincide_con_banco,
    detectar_conmutaciones,
)
from src.domain.cargas.entities import EventoCarga, Medicion
from src.domain.cargas.services import detectar_eventos, integrar_trapecios

HUECO_MAXIMO_MIN = 5.0
UMBRAL_HUECOS_CALIDAD = (
    10  # huecos mayores a 5 min por día a partir de los cuales el día es de calidad baja
)
CERRADO = "cerrado"  # termina en un apagado que es de la misma firma: consume 2 eventos
ABIERTO = "abierto"  # termina en la última medición del día, sin apagado: consume 1 evento
CORTADO = "cortado"  # termina en un escalón que no es de la firma (otra carga se apagó): consume 1

Clasificado = tuple[str, IntervaloMarchaDTO, str]


def _sin_zona(instante: datetime) -> datetime:
    """Los intervalos de salida llevan zona UTC; el análisis trabaja con instantes UTC sin zona."""
    return instante.replace(tzinfo=None)


def _ventana(mediciones: list[Medicion], desde: datetime, hasta: datetime) -> list[Medicion]:
    return sorted((m for m in mediciones if desde <= m.instante < hasta), key=lambda m: m.instante)


def _eventos(ventana: list[Medicion], firmas: list[FirmaConfirmadaDTO]) -> list[EventoCarga]:
    if len(ventana) < 2:
        return []
    return detectar_eventos(ventana, umbral_kw=umbral_minimo_kw(firmas) if firmas else 0.1)


def _atribuir(
    ventana: list[Medicion],
    firmas: list[FirmaConfirmadaDTO],
    desde: datetime,
    hasta: datetime,
    parametros: ParametrosBancoDTO | None = None,
) -> AtribuirCargasBatchResponseDTO:
    return AtribuirCargasBatchUseCase().ejecutar(
        AtribuirCargasBatchRequestDTO(
            device_id="validacion",
            etiqueta_ml="validacion",
            fecha_local=desde.date(),
            ventana_desde_utc=desde,
            ventana_hasta_utc=hasta,
            generado_en_utc=desde,
            mediciones=ventana,
            firmas=firmas,
            parametros_banco=parametros or ParametrosBancoDTO(),
        )
    )


def _es_de_firma(evento: EventoCarga, firma: FirmaConfirmadaDTO) -> bool:
    return abs(abs(evento.delta_kw) - firma.potencia_nominal_kw) <= firma.tolerancia_kw


def _tipo(
    intervalo: IntervaloMarchaDTO,
    evento_de_fin: EventoCarga | None,
    firma: FirmaConfirmadaDTO,
    ultimo: datetime | None,
) -> str:
    if _sin_zona(intervalo.fin_utc) == ultimo:
        return ABIERTO
    if evento_de_fin is not None and _es_de_firma(evento_de_fin, firma):
        return CERRADO
    return CORTADO


def _clasificar(
    respuesta: AtribuirCargasBatchResponseDTO,
    eventos: list[EventoCarga],
    firmas: list[FirmaConfirmadaDTO],
    ultimo: datetime | None,
) -> list[Clasificado]:
    apagados = {e.instante: e for e in eventos if not e.es_encendido}
    firma_por_nombre = {f.nombre: f for f in firmas}
    return [
        (
            carga.nombre,
            it,
            _tipo(it, apagados.get(_sin_zona(it.fin_utc)), firma_por_nombre[carga.nombre], ultimo),
        )
        for carga in respuesta.cargas
        for it in carga.intervalos
    ]


def _resumen_cargas(
    respuesta: AtribuirCargasBatchResponseDTO, clasificados: list[Clasificado]
) -> list[CargaValidacionDTO]:
    resumen = []
    for carga in respuesta.cargas:
        tipos = [t for nombre, _, t in clasificados if nombre == carga.nombre]
        resumen.append(
            CargaValidacionDTO(
                nombre=carga.nombre,
                intervalos=len(carga.intervalos),
                cerrados=tipos.count(CERRADO),
                abiertos=tipos.count(ABIERTO),
                cortados=tipos.count(CORTADO),
                horas=round(sum(it.horas for it in carga.intervalos), 4),
                energia_kwh=round(sum(it.energia_kwh_medida for it in carga.intervalos), 3),
            )
        )
    return resumen


def _energia_medida(ventana: list[Medicion]) -> float:
    """Energía medida del día (integral trapezoidal de la potencia de la ventana), en kWh."""
    return integrar_trapecios([(m.instante, m.potencia_kw) for m in ventana]) if ventana else 0.0


def _huecos(ventana: list[Medicion]) -> int:
    return sum(
        1
        for a, b in zip(ventana, ventana[1:], strict=False)
        if (b.instante - a.instante).total_seconds() > HUECO_MAXIMO_MIN * 60
    )


def candidatos_a_fusion(
    clasificados: list[Clasificado], umbral: float = 0.5
) -> set[frozenset[str]]:
    """Pares de grupos que son, muy probablemente, la misma máquina.

    Criterio explícito: dos grupos son candidatos si, para CADA uno, al menos `umbral` (por defecto la mitad)
    de sus intervalos se superpone con algún intervalo del otro. Así un grupo que solo toca a otro de vez
    en cuando no se fusiona; uno que coincide casi siempre con otro, sí. Es una evaluación: no cambia la energía.
    """
    por_grupo: dict[str, list[tuple[datetime, datetime]]] = {}
    for nombre, it, _ in clasificados:
        por_grupo.setdefault(nombre, []).append((it.inicio_utc, it.fin_utc))
    candidatos: set[frozenset[str]] = set()
    nombres = sorted(por_grupo)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1 :]:
            fa = _fraccion_superpuesta(por_grupo[a], por_grupo[b])
            fb = _fraccion_superpuesta(por_grupo[b], por_grupo[a])
            if min(fa, fb) >= umbral:
                candidatos.add(frozenset({a, b}))
    return candidatos


def _fusion(clasificados: list[Clasificado]) -> tuple[int, int]:
    """(pares candidatos a fusión, solapamientos que quedan después de fusionarlos)."""
    candidatos = candidatos_a_fusion(clasificados)
    return len(candidatos), _solapamientos(clasificados, candidatos)[0]


def _fraccion_superpuesta(
    propios: list[tuple[datetime, datetime]], otros: list[tuple[datetime, datetime]]
) -> float:
    """Fracción de los intervalos propios que se superponen con algún intervalo de los otros."""
    if not propios:
        return 0.0
    coinciden = sum(
        1 for ini, fin in propios if any(ini < fin2 and ini2 < fin for ini2, fin2 in otros)
    )
    return coinciden / len(propios)


def _solapamientos(
    clasificados: list[Clasificado], fusionados: set[frozenset[str]] | None = None
) -> tuple[int, float]:
    """Pares de intervalos de grupos distintos que se superponen, y las horas solapadas.

    Los pares de grupos que se fusionan (`fusionados`) son la misma máquina: sus superposiciones no cuentan.
    """
    excluir = fusionados or set()
    pares = 0
    horas = 0.0
    for i, (nombre_a, a, _) in enumerate(clasificados):
        for nombre_b, b, _ in clasificados[i + 1 :]:
            if nombre_a == nombre_b or frozenset({nombre_a, nombre_b}) in excluir:
                continue
            inicio = max(a.inicio_utc, b.inicio_utc)
            fin = min(a.fin_utc, b.fin_utc)
            if fin > inicio:
                pares += 1
                horas += (fin - inicio).total_seconds() / 3600.0
    return pares, horas


def _banco(
    ventana: list[Medicion],
    eventos: list[EventoCarga],
    respuesta_solo_p: AtribuirCargasBatchResponseDTO,
    energia_atribuida: float,
) -> tuple[int, int, float, float]:
    """(conmutaciones de banco, escalones de carga contaminados, energía solo con P, % de diferencia P vs P y Q)."""
    params = ParametrosBancoDTO()
    conmutaciones = detectar_conmutaciones(ventana, params.umbral_p_kw, params.umbral_q_kvar)
    contaminados = sum(
        1 for e in eventos if coincide_con_banco(e.instante, conmutaciones, params.tolerancia)
    )
    energia_solo_p = sum(
        it.energia_kwh_medida for c in respuesta_solo_p.cargas for it in c.intervalos
    )
    diferencia = (
        100.0 * (energia_atribuida - energia_solo_p) / energia_solo_p if energia_solo_p else 0.0
    )
    return len(conmutaciones), contaminados, round(energia_solo_p, 3), round(diferencia, 1)


class ValidarDesagregacionDiaUseCase:
    """Calcula las métricas de un día: eventos, atribución, energía, solapamientos, huecos y banco.

    `umbral_huecos_calidad`: un día con más huecos de muestreo mayores a 5 minutos que este umbral se marca
    como de calidad baja (la integral y el conteo de eventos son menos confiables).
    """

    def __init__(self, umbral_huecos_calidad: int = UMBRAL_HUECOS_CALIDAD) -> None:
        if umbral_huecos_calidad < 0:
            raise ValueError("El umbral de huecos no puede ser negativo.")
        self._umbral_huecos = umbral_huecos_calidad

    def ejecutar(
        self,
        mediciones: list[Medicion],
        firmas: list[FirmaConfirmadaDTO],
        desde: datetime,
        hasta: datetime,
    ) -> MetricasDiaDTO:
        ventana = _ventana(mediciones, desde, hasta)
        eventos = _eventos(ventana, firmas)
        respuesta = _atribuir(ventana, firmas, desde, hasta)
        respuesta_solo_p = _atribuir(ventana, firmas, desde, hasta, ParametrosBancoDTO(peso_q=0.0))
        ultimo = ventana[-1].instante if ventana else None
        clasificados = _clasificar(respuesta, eventos, firmas, ultimo)

        tipos = [t for _, _, t in clasificados]
        cerrados, abiertos, cortados = (
            tipos.count(CERRADO),
            tipos.count(ABIERTO),
            tipos.count(CORTADO),
        )
        atribuidos = 2 * cerrados + abiertos + cortados
        energia_medida = _energia_medida(ventana)
        energia_atribuida = sum(it.energia_kwh_medida for _, it, _ in clasificados)
        solapamientos, horas_solapadas = _solapamientos(clasificados)
        pares_fusion, solapamientos_tras = _fusion(clasificados)
        umbral = umbral_minimo_kw(firmas) if firmas else 0.1
        banco_conmutaciones, banco_contaminados, energia_solo_p, diferencia = _banco(
            ventana, eventos, respuesta_solo_p, energia_atribuida
        )

        return MetricasDiaDTO(
            mediciones=len(ventana),
            huecos_mayores_a_5_min=_huecos(ventana),
            calidad_baja=_huecos(ventana) > self._umbral_huecos,
            umbral_kw=round(umbral, 3),
            energia_medida_kwh=round(energia_medida, 3),
            eventos=len(eventos),
            encendidos=sum(e.es_encendido for e in eventos),
            apagados=sum(not e.es_encendido for e in eventos),
            eventos_atribuidos=atribuidos,
            eventos_sin_atribuir=len(eventos) - atribuidos,
            intervalos_cerrados=cerrados,
            intervalos_abiertos=abiertos,
            intervalos_cortados_por_caida=cortados,
            energia_atribuida_kwh=round(energia_atribuida, 3),
            pct_energia_atribuida=round(100.0 * energia_atribuida / energia_medida, 1)
            if energia_medida > 0
            else 0.0,
            energia_atribuida_excede_medida=energia_atribuida > energia_medida,
            eventos_banco_dp_bajo_dq_alto=banco_conmutaciones,
            eventos_carga_con_banco=banco_contaminados,
            energia_atribuida_solo_p_kwh=energia_solo_p,
            diferencia_pct_p_vs_pq=diferencia,
            solapamientos=solapamientos,
            pares_candidatos_fusion=pares_fusion,
            solapamientos_tras_fusion=solapamientos_tras,
            horas_solapadas=round(horas_solapadas, 4),
            cargas=_resumen_cargas(respuesta, clasificados),
        )
