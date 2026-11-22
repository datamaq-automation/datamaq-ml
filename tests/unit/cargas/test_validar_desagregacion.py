"""tests/unit/cargas/test_validar_desagregacion.py — Métricas de validación de un día, con datos sintéticos."""

from datetime import datetime, timedelta

import pytest

from src.application.cargas.dtos.desagregar_cargas import FirmaConfirmadaDTO
from src.application.cargas.use_cases.validar_desagregacion import (
    ValidarDesagregacionDiaUseCase,
)
from src.domain.cargas.entities import Medicion

DESDE = datetime(2026, 9, 20, 0, 0)
HASTA = datetime(2026, 9, 21, 0, 0)
PASO = timedelta(minutes=5)
MOTOR_50 = FirmaConfirmadaDTO(
    machine_id="m50", nombre="Motor 50", potencia_nominal_kw=50.0, tolerancia_kw=5.0
)
MOTOR_30 = FirmaConfirmadaDTO(
    machine_id="m30", nombre="Motor 30", potencia_nominal_kw=30.0, tolerancia_kw=3.0
)


def dia_con_base(base_kw: float = 10.0, reactiva: float | None = None) -> list[Medicion]:
    """Un día de muestras cada 5 min con una carga base constante."""
    return [
        Medicion(instante=DESDE + PASO * i, potencia_kw=base_kw, reactiva_kvar=reactiva)
        for i in range(288)
    ]


def sumar_carga(
    mediciones: list[Medicion], inicio: datetime, fin: datetime, kw: float
) -> list[Medicion]:
    """Suma `kw` a las muestras de [inicio, fin): la carga queda encendida entre esos instantes."""
    return [
        Medicion(
            instante=m.instante,
            potencia_kw=m.potencia_kw + (kw if inicio <= m.instante < fin else 0.0),
            reactiva_kvar=m.reactiva_kvar,
        )
        for m in mediciones
    ]


def ejecutar(mediciones: list[Medicion], firmas: list[FirmaConfirmadaDTO]):
    return ValidarDesagregacionDiaUseCase().ejecutar(mediciones, firmas, DESDE, HASTA)


def test_dia_vacio_no_tiene_eventos_ni_energia() -> None:
    m = ejecutar([], [MOTOR_50])
    assert m.mediciones == 0
    assert m.eventos == 0
    assert m.energia_medida_kwh == 0.0
    assert m.pct_energia_atribuida == 0.0
    assert m.intervalos_cerrados == 0


def test_carga_limpia_se_atribuye_completa_y_cerrada() -> None:
    mediciones = sumar_carga(
        dia_con_base(), datetime(2026, 9, 20, 10, 0), datetime(2026, 9, 20, 11, 0), 50.0
    )
    m = ejecutar(mediciones, [MOTOR_50])
    assert m.eventos == 2
    assert m.encendidos == 1 and m.apagados == 1
    assert m.intervalos_cerrados == 1
    assert m.intervalos_abiertos == 0
    assert m.eventos_sin_atribuir == 0
    assert not m.energia_atribuida_excede_medida
    assert 0 < m.pct_energia_atribuida <= 100


def test_carga_que_sigue_encendida_al_final_del_dia_queda_abierta() -> None:
    mediciones = sumar_carga(dia_con_base(), datetime(2026, 9, 20, 22, 0), HASTA, 50.0)
    m = ejecutar(mediciones, [MOTOR_50])
    assert m.intervalos_abiertos == 1
    assert m.intervalos_cerrados == 0
    assert m.eventos_sin_atribuir == 0


def test_escalon_sin_firma_queda_sin_atribuir_y_el_invariante_se_cumple() -> None:
    """Un salto de 60 kW supera el umbral (45 kW) pero cae fuera de la tolerancia de 50 ± 5: sin atribuir."""
    mediciones = sumar_carga(
        dia_con_base(), datetime(2026, 9, 20, 10, 0), datetime(2026, 9, 20, 11, 0), 60.0
    )
    m = ejecutar(mediciones, [MOTOR_50])
    assert m.eventos == 2
    assert m.eventos_sin_atribuir == 2
    assert m.eventos_atribuidos + m.eventos_sin_atribuir == m.eventos


def test_dos_cargas_que_se_superponen_se_cuentan_como_solapamiento() -> None:
    """Motor de 50 kW de 10 a 12 y motor de 30 kW de 11 a 13: se superponen una hora."""
    mediciones = dia_con_base()
    mediciones = sumar_carga(
        mediciones, datetime(2026, 9, 20, 10, 0), datetime(2026, 9, 20, 12, 0), 50.0
    )
    mediciones = sumar_carga(
        mediciones, datetime(2026, 9, 20, 11, 0), datetime(2026, 9, 20, 13, 0), 30.0
    )
    m = ejecutar(mediciones, [MOTOR_50, MOTOR_30])
    assert m.intervalos_cerrados == 2
    assert m.solapamientos == 1
    assert m.horas_solapadas == pytest.approx(1.0, abs=0.01)


def test_hueco_de_muestreo_mayor_a_5_minutos_se_cuenta() -> None:
    mediciones = [
        m
        for m in dia_con_base()
        if not (datetime(2026, 9, 20, 3, 0) <= m.instante < datetime(2026, 9, 20, 3, 15))
    ]
    m = ejecutar(mediciones, [MOTOR_50])
    assert m.huecos_mayores_a_5_min == 1


def test_muestras_fuera_de_la_ventana_no_cuentan() -> None:
    fuera = [Medicion(instante=HASTA + PASO, potencia_kw=500.0)]
    m = ejecutar(dia_con_base() + fuera, [MOTOR_50])
    assert m.mediciones == 288
    assert m.eventos == 0
