"""tests/unit/test_debounce.py — Debounce: un pico de una muestra no es un evento (datos sintéticos)."""

from datetime import datetime, timedelta

import pytest

from src.domain.cargas.entities import Medicion
from src.domain.cargas.services import detectar_eventos

T0 = datetime(2026, 9, 20, 10, 0)
CINCO = timedelta(minutes=5)


def _serie(niveles: list[float]) -> list[Medicion]:
    return [Medicion(instante=T0 + i * CINCO, potencia_kw=p) for i, p in enumerate(niveles)]


def test_un_pico_de_una_muestra_genera_eventos_sin_debounce_pero_no_con_dos() -> None:
    """10 kW, un pico de 70 kW de una sola muestra, y vuelta a 10 kW."""
    pico = _serie([10.0, 10.0, 70.0, 10.0, 10.0, 10.0])
    assert len(detectar_eventos(pico, umbral_kw=45.0)) == 2  # encendido y apagado espurios
    assert detectar_eventos(pico, umbral_kw=45.0, muestras_persistencia=2) == []


def test_un_escalon_real_que_se_sostiene_se_conserva_con_debounce_dos() -> None:
    escalon = _serie([10.0, 10.0, 60.0, 61.0, 60.0, 59.0, 60.0])
    eventos = detectar_eventos(escalon, umbral_kw=45.0, muestras_persistencia=2)
    assert len(eventos) == 1
    assert eventos[0].delta_kw == pytest.approx(50.0)


def test_el_default_no_cambia_el_resultado() -> None:
    serie = _serie([10.0, 10.0, 70.0, 10.0, 60.0, 60.0])
    assert detectar_eventos(serie, umbral_kw=45.0) == detectar_eventos(
        serie, 45.0, muestras_persistencia=1
    )


def test_al_final_de_la_serie_no_hay_muestras_para_confirmar_y_el_salto_se_conserva() -> None:
    final = _serie([10.0, 10.0, 60.0])
    assert len(detectar_eventos(final, umbral_kw=45.0, muestras_persistencia=2)) == 1


def test_persistencia_menor_a_uno_es_error() -> None:
    with pytest.raises(ValueError):
        detectar_eventos(_serie([1.0, 2.0]), umbral_kw=1.0, muestras_persistencia=0)
