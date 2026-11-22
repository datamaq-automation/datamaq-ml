"""tests/unit/cargas/test_simulacion_banco.py — Tablero sintético con banco fijo o automático (datos sintéticos)."""

import statistics
from datetime import datetime

import pytest

from src.domain.cargas.banco_capacitores import detectar_conmutaciones
from src.domain.cargas.entities import CargaSimulada, Medicion
from src.domain.cargas.simulacion import simular_tablero_con_reactiva

INICIO = datetime(2026, 9, 1, 0, 0)
CARGAS = [
    CargaSimulada(potencia_kw=50.0, ciclos_por_dia=8.0, duracion_min=45.0),
    CargaSimulada(potencia_kw=30.0, ciclos_por_dia=12.0, duracion_min=20.0),
]
FACTOR = 1.2  # ΔQ / ΔP de un motor en el sintético


def _generar(banco: str, semilla: int = 3) -> tuple[list[Medicion], list]:
    return simular_tablero_con_reactiva(
        CARGAS,
        dias=3,
        ruido_kw=0.1,
        ruido_kvar=0.1,
        semilla=semilla,
        inicio=INICIO,
        banco=banco,
        factor_reactiva=FACTOR,
    )


def test_banco_fijo_no_produce_conmutaciones() -> None:
    mediciones, _ = _generar("fijo")
    assert detectar_conmutaciones(mediciones) == []


def test_banco_automatico_produce_conmutaciones() -> None:
    mediciones, _ = _generar("automatico")
    assert len(detectar_conmutaciones(mediciones)) >= 1


def test_con_banco_fijo_la_delta_q_de_un_arranque_es_limpia() -> None:
    """Con Q constante, ΔQ / ΔP en un arranque de motor vale el factor del motor (sin contaminación)."""
    mediciones, verdad = _generar("fijo")
    por_instante = {m.instante: i for i, m in enumerate(mediciones)}
    ratios = []
    for ev in verdad:
        if ev.delta_kw <= 0:
            continue
        i = por_instante[ev.instante]
        dp = mediciones[i].potencia_kw - mediciones[i - 1].potencia_kw
        dq = (mediciones[i].reactiva_kvar or 0.0) - (mediciones[i - 1].reactiva_kvar or 0.0)
        ratios.append(dq / dp)
    assert ratios
    assert statistics.median(ratios) == pytest.approx(FACTOR, abs=0.05)


def test_la_misma_semilla_da_el_mismo_tablero() -> None:
    a, _ = _generar("automatico", semilla=7)
    b, _ = _generar("automatico", semilla=7)
    assert a == b


def test_tipo_de_banco_desconocido_falla() -> None:
    with pytest.raises(ValueError):
        _generar("variable")
