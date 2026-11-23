"""tests/unit/test_algoritmo_genetico.py — Tests del optimizador genético de horarios de demanda (Issue #19).

Verifica:
1. Cálculo determinista de la demanda horaria acumulada y pico máximo.
2. Búsqueda exhaustiva por fuerza bruta como cota inferior óptima de referencia (110 kW).
3. Algoritmo genético con elitismo, selección por torneo, cruza en un punto y mutación.
4. Coincidencia determinista entre la solución heurística del genético y la fuerza bruta.
"""

from __future__ import annotations

from src.domain.cargas.algoritmo_genetico import (
    OptimizadorHorariosGenetico,
    calcular_demanda_maxima,
    resolver_fuerza_bruta,
)

CARGAS_ISSUE_19 = (90.0, 40.0, 25.0, 15.0)  # horno, compresor, luz, bomba (kW)
BASE_ISSUE_19 = (20.0, 30.0, 50.0, 40.0)  # demanda base por hora (kW)


def test_demanda_maxima_sin_optimizar() -> None:
    """Si todas las cargas arrancan en la hora 0, la demanda pico es 20 + 90 + 40 + 25 + 15 = 190 kW."""
    pico_hora_cero = calcular_demanda_maxima(
        horarios=(0, 0, 0, 0),
        cargas=CARGAS_ISSUE_19,
        base=BASE_ISSUE_19,
    )
    assert pico_hora_cero == 190.0


def test_demanda_maxima_individuo_especifico_110kw() -> None:
    """El horario (0, 1, 1, 1) arroja exactamente 110 kW de demanda máxima."""
    pico = calcular_demanda_maxima(
        horarios=(0, 1, 1, 1),
        cargas=CARGAS_ISSUE_19,
        base=BASE_ISSUE_19,
    )
    # Hora 0: 20 + 90 = 110 kW
    # Hora 1: 30 + 40 + 25 + 15 = 110 kW
    # Hora 2: 50 + 0 = 50 kW
    # Hora 3: 40 + 0 = 40 kW
    assert pico == 110.0


def test_fuerza_bruta_encuentra_optimo_110kw() -> None:
    """La búsqueda exhaustiva sobre 4^4 = 256 combinaciones halla el mínimo absoluto de 110 kW."""
    mejor_horario, mejor_pico = resolver_fuerza_bruta(
        cargas=CARGAS_ISSUE_19,
        base=BASE_ISSUE_19,
    )
    assert mejor_pico == 110.0
    assert len(mejor_horario) == len(CARGAS_ISSUE_19)


def test_algoritmo_genetico_alcanza_optimo_global() -> None:
    """El algoritmo genético determinista con semilla fija converge al óptimo global de 110 kW."""
    opt = OptimizadorHorariosGenetico(
        cargas=CARGAS_ISSUE_19,
        base=BASE_ISSUE_19,
        tam_poblacion=12,
        generaciones=40,
        tasa_mutacion=0.1,
        elitismo=2,
        semilla=1,
    )
    resultado = opt.optimizar()

    assert resultado.demanda_pico == 110.0
    assert len(resultado.horarios) == 4
    # La aptitud por generación debe no empeorar gracias al elitismo
    historico = resultado.historial_mejor_pico
    assert len(historico) == 40
    for i in range(1, len(historico)):
        assert historico[i] <= historico[i - 1]
