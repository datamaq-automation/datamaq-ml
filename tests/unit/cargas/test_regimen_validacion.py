"""tests/unit/cargas/test_regimen_validacion.py — Validación con el umbral del valle y la tolerancia por dispersión.

Datos sintéticos: un día con una carga de 77 a 110 kW (un modo ancho, como el del trafo bimodal) y ruido
chico. Se compara la energía atribuida con el comportamiento anterior (umbral = nominal − tolerancia y
tolerancia fija de 5 kW) y con el nuevo (umbral del valle y tolerancia por dispersión acotada).
"""

import random
from datetime import date, timedelta

from src.application.cargas.dtos.desagregar_cargas import FirmaConfirmadaDTO, ParametrosMotorDTO
from src.application.cargas.use_cases.validar_desagregacion import ValidarDesagregacionDiaUseCase
from src.domain.cargas.entities import Medicion
from src.domain.cargas.regimenes import hallar_regimen
from src.domain.cargas.services import saltos_kw
from src.infrastructure.cli.desagregar_cargas import ventana_utc_del_dia

DESDE, HASTA = ventana_utc_del_dia(date(2026, 9, 20))
FIRMA = FirmaConfirmadaDTO(
    machine_id="m1",
    nombre="Carga",
    potencia_nominal_kw=91.4,
    reactiva_tipica_kvar=0.0,
    tolerancia_kw=5.0,
    umbral_marcha_kw=1.0,
    dispersion_kw=9.5,
)


def _dia(semilla: int, n_eventos: int = 20) -> list[Medicion]:
    """Línea base de 20 kW; cada evento sube entre 77 y 110 kW durante 20 min, y después baja.

    20 eventos de 11 muestras entran en el día (288 muestras de 5 min).
    """
    r = random.Random(semilla)
    mediciones: list[Medicion] = []
    instante = DESDE

    def emitir(valor: float) -> None:
        nonlocal instante
        mediciones.append(Medicion(instante=instante, potencia_kw=valor))
        instante += timedelta(minutes=5)

    emitir(20.0)
    for _ in range(n_eventos):
        m = r.uniform(77.0, 110.0)
        for _ in range(4):
            emitir(20.0 + m + r.gauss(0, 0.3))
        for _ in range(4):
            emitir(20.0 + r.gauss(0, 0.3))
        for _ in range(3):
            emitir(20.0 + r.uniform(0.0, 12.0))  # ruido chico: no debe contar como evento
    return mediciones


def test_el_valle_y_la_tolerancia_por_dispersion_atribuyen_mas_energia() -> None:
    mediciones = _dia(21)
    caso = ValidarDesagregacionDiaUseCase()
    anterior = caso.ejecutar(mediciones, [FIRMA], DESDE, HASTA)

    umbral = hallar_regimen(saltos_kw(mediciones)).umbral_kw
    assert umbral is not None
    nuevo = caso.ejecutar(
        mediciones,
        [FIRMA],
        DESDE,
        HASTA,
        umbral_kw=umbral,
        motor=ParametrosMotorDTO(tolerancia_por_dispersion=True, tolerancia_max_kw=25.0),
    )
    assert nuevo.eventos > anterior.eventos  # el umbral anterior ignoraba los saltos de 77 a 86 kW
    # La línea base de 20 kW pesa en el total: la energía de los eventos es ~56 % de lo medido.
    assert nuevo.energia_atribuida_kwh > anterior.energia_atribuida_kwh
    assert nuevo.pct_energia_atribuida > 2 * anterior.pct_energia_atribuida
    # Los pocos que quedan fuera son los saltos de borde del modo (110 kW con el ruido del generador).
    assert nuevo.eventos_sin_atribuir <= 0.1 * nuevo.eventos


def test_la_tolerancia_por_dispersion_cubre_el_ancho_del_modo() -> None:
    """Con el tope de 8 kW (el de antes) el modo de 77 a 110 kW no entra en una sola firma; con 25 sí."""
    mediciones = _dia(22)
    caso = ValidarDesagregacionDiaUseCase()
    umbral = hallar_regimen(saltos_kw(mediciones)).umbral_kw
    assert umbral is not None
    con_tope_chico = caso.ejecutar(
        mediciones,
        [FIRMA],
        DESDE,
        HASTA,
        umbral_kw=umbral,
        motor=ParametrosMotorDTO(tolerancia_por_dispersion=True, tolerancia_max_kw=8.0),
    )
    con_tope_amplio = caso.ejecutar(
        mediciones,
        [FIRMA],
        DESDE,
        HASTA,
        umbral_kw=umbral,
        motor=ParametrosMotorDTO(tolerancia_por_dispersion=True, tolerancia_max_kw=25.0),
    )
    assert con_tope_amplio.energia_atribuida_kwh > con_tope_chico.energia_atribuida_kwh


def test_sin_modos_separables_no_atribuye_nada_pero_cuenta_los_eventos() -> None:
    mediciones = _dia(23)
    metricas = ValidarDesagregacionDiaUseCase().ejecutar(
        mediciones, [], DESDE, HASTA, umbral_kw=40.0, sin_modos=True
    )
    assert metricas.sin_modos_separables
    assert metricas.eventos > 0
    assert metricas.eventos_sin_atribuir == metricas.eventos
    assert metricas.energia_atribuida_kwh == 0.0
