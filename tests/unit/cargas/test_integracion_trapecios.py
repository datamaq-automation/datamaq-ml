"""tests/unit/cargas/test_integracion_trapecios.py — Integral por trapecios (energía desde potencia medida)."""

from datetime import datetime, timedelta

import pytest

from src.domain.cargas.services import integrar_trapecios

T0 = datetime(2026, 9, 20, 8, 0, 0)


def test_sin_puntos_o_con_uno_la_integral_es_cero() -> None:
    assert integrar_trapecios([]) == 0.0
    assert integrar_trapecios([(T0, 50.0)]) == 0.0


def test_potencia_constante_integra_potencia_por_horas() -> None:
    """10 kW durante 2 horas son 20 kWh."""
    puntos = [(T0, 10.0), (T0 + timedelta(hours=1), 10.0), (T0 + timedelta(hours=2), 10.0)]
    assert integrar_trapecios(puntos) == pytest.approx(20.0)


def test_rampa_lineal_integra_el_promedio() -> None:
    """Una rampa de 0 a 10 kW en 1 hora integra el promedio, 5 kWh."""
    puntos = [(T0, 0.0), (T0 + timedelta(hours=1), 10.0)]
    assert integrar_trapecios(puntos) == pytest.approx(5.0)


def test_muestras_con_espaciado_irregular() -> None:
    """Cada tramo usa su propio Δt: 10 kW por 30 min y luego una caída a 0 en 90 min."""
    puntos = [
        (T0, 10.0),
        (T0 + timedelta(minutes=30), 10.0),
        (T0 + timedelta(minutes=120), 0.0),
    ]
    # Tramo 1: 10 kW · 0,5 h = 5 kWh. Tramo 2: (10 + 0)/2 · 1,5 h = 7,5 kWh.
    assert integrar_trapecios(puntos) == pytest.approx(12.5)


def test_reactiva_integra_kvarh_con_la_misma_regla() -> None:
    """La misma integral sirve para la reactiva: 30 kVAr durante 5 min son 2,5 kVArh."""
    puntos = [(T0, 30.0), (T0 + timedelta(minutes=5), 30.0)]
    assert integrar_trapecios(puntos) == pytest.approx(2.5)
