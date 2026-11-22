"""tests/unit/cargas/test_simular_contactores.py — Contactores simulados: verdad por intervalos y desfase (datos sintéticos)."""

from datetime import datetime, timedelta

from src.domain.cargas.entities import CargaSimulada
from src.domain.cargas.simulacion import simular_contactores, simular_tablero

INICIO = datetime(2026, 9, 1)
CARGAS = [
    CargaSimulada(potencia_kw=90, ciclos_por_dia=18, duracion_min=25),
    CargaSimulada(potencia_kw=40, ciclos_por_dia=6, duracion_min=60),
]


def test_los_arranques_de_los_contactores_son_los_eventos_de_la_simulacion() -> None:
    _, verdad = simular_tablero(CARGAS, dias=2, ruido_kw=3.0, semilla=5, inicio=INICIO)
    intervalos = simular_contactores(CARGAS, dias=2, semilla=5, inicio=INICIO)
    for carga, tramos in zip(CARGAS, intervalos, strict=True):
        arranques = sorted(
            e.instante for e in verdad if e.carga_kw == carga.potencia_kw and e.delta_kw > 0
        )
        assert [a for a, _ in tramos] == arranques


def test_cada_intervalo_empieza_antes_de_terminar_y_no_se_solapa() -> None:
    for tramos in simular_contactores(CARGAS, dias=3, semilla=9, inicio=INICIO):
        for (_, fin), (inicio_siguiente, _) in zip(tramos, tramos[1:], strict=False):
            assert fin <= inicio_siguiente
        assert all(inicio < fin for inicio, fin in tramos)


def test_el_desfase_corre_todos_los_tiempos_del_automata() -> None:
    sin = simular_contactores(CARGAS, dias=1, semilla=3, inicio=INICIO, desfase_s=0)
    con = simular_contactores(CARGAS, dias=1, semilla=3, inicio=INICIO, desfase_s=7.5)
    for tramos_sin, tramos_con in zip(sin, con, strict=True):
        assert len(tramos_sin) == len(tramos_con)
        for (a0, b0), (a1, b1) in zip(tramos_sin, tramos_con, strict=True):
            assert a1 - a0 == timedelta(seconds=7.5)
            assert b1 - b0 == timedelta(seconds=7.5)
