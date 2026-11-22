"""tests/unit/cargas/test_banco_capacitores.py — Detección de conmutaciones de banco (datos sintéticos)."""

from datetime import datetime, timedelta

from src.domain.cargas.banco_capacitores import (
    coincide_con_banco,
    detectar_conmutaciones,
    es_conmutacion,
    es_evento_de_banco,
)
from src.domain.cargas.entities import EventoCarga, Medicion

T0 = datetime(2026, 9, 20, 10, 0)
CINCO = timedelta(minutes=5)


def test_un_paso_de_reactiva_sin_potencia_activa_es_conmutacion() -> None:
    assert es_conmutacion(delta_kw=0.4, delta_kvar=-20.0, umbral_p_kw=1.5, umbral_q_kvar=10.0)


def test_un_arranque_de_motor_con_potencia_activa_no_es_conmutacion() -> None:
    assert not es_conmutacion(delta_kw=50.0, delta_kvar=40.0, umbral_p_kw=1.5, umbral_q_kvar=10.0)


def test_un_cambio_chico_de_reactiva_no_es_conmutacion() -> None:
    assert not es_conmutacion(delta_kw=0.2, delta_kvar=4.0, umbral_p_kw=1.5, umbral_q_kvar=10.0)


def test_detecta_solo_los_pares_de_banco() -> None:
    mediciones = [
        Medicion(instante=T0, potencia_kw=100.0, reactiva_kvar=50.0),
        Medicion(instante=T0 + CINCO, potencia_kw=100.2, reactiva_kvar=30.0),  # banco: -20 kvar
        Medicion(instante=T0 + 2 * CINCO, potencia_kw=150.0, reactiva_kvar=70.0),  # motor: +50 kW
        Medicion(instante=T0 + 3 * CINCO, potencia_kw=150.1, reactiva_kvar=85.0),  # banco: +15 kvar
    ]
    conmutaciones = detectar_conmutaciones(mediciones)
    assert [c.instante for c in conmutaciones] == [T0 + CINCO, T0 + 3 * CINCO]
    assert [c.delta_kvar for c in conmutaciones] == [-20.0, 15.0]


def test_sin_reactiva_no_hay_conmutaciones() -> None:
    mediciones = [Medicion(instante=T0 + i * CINCO, potencia_kw=100.0) for i in range(5)]
    assert detectar_conmutaciones(mediciones) == []


def test_un_evento_de_carga_puede_clasificarse_como_evento_de_banco() -> None:
    banco = EventoCarga(instante=T0, delta_kw=0.3, delta_kvar=-25.0)
    motor = EventoCarga(instante=T0, delta_kw=50.0, delta_kvar=40.0)
    assert es_evento_de_banco(banco, umbral_p_kw=1.5, umbral_q_kvar=10.0)
    assert not es_evento_de_banco(motor, umbral_p_kw=1.5, umbral_q_kvar=10.0)


def test_coincidencia_dentro_de_la_tolerancia_de_una_muestra() -> None:
    conmutaciones = detectar_conmutaciones(
        [
            Medicion(instante=T0, potencia_kw=100.0, reactiva_kvar=50.0),
            Medicion(instante=T0 + CINCO, potencia_kw=100.0, reactiva_kvar=30.0),
        ]
    )
    assert coincide_con_banco(T0 + CINCO, conmutaciones)  # misma muestra
    assert coincide_con_banco(T0 + 2 * CINCO, conmutaciones)  # una muestra después
    assert not coincide_con_banco(T0 + 4 * CINCO, conmutaciones)  # lejos
