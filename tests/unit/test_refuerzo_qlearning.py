"""tests/unit/test_refuerzo_qlearning.py — Tests de Aprendizaje por Refuerzo y Q-learning tabular (Issue #18).

Verifica:
1. Simulación determinista del entorno de tarifa eléctrica (valle / pico).
2. Convergencia del agente Q-learning a los valores analíticos de Bellman (10.53 y 15.26).
3. Transición de política óptima inducida según la recompensa de pico (esperar vs arrancar).
4. Independencia arquitectónica y cero dependencias externas.
"""

from __future__ import annotations

import pytest

from src.domain.cargas.refuerzo_qlearning import (
    AgenteQLearningTabular,
    EntornoTarifaHoraria,
    calcular_valor_analitico_valle,
)


def test_entorno_tarifa_transiciones_y_recompensas() -> None:
    """Verifica las transiciones de estado deterministas y la función de recompensa."""
    env = EntornoTarifaHoraria(r_pico=-5.0, recompensa_valle=2.0)
    assert env.estado_actual == "valle"

    # Acción esperar en valle: recompensa 0, pasa a pico
    r1, s1 = env.paso("esperar")
    assert r1 == 0.0
    assert s1 == "pico"
    assert env.estado_actual == "pico"

    # Acción arrancar en pico: recompensa -5, pasa a valle
    r2, s2 = env.paso("arrancar")
    assert r2 == -5.0
    assert s2 == "valle"

    # Acción arrancar en valle: recompensa 2, pasa a pico
    r3, s3 = env.paso("arrancar")
    assert r3 == 2.0
    assert s3 == "pico"


def test_valor_analitico_valle_bellman() -> None:
    """Verifica la fórmula cerrada geométrica de Bellman V(valle) = (r_valle + gamma * r_pico) / (1 - gamma^2)."""
    # Con r_pico = -5, la política óptima es arrancar en valle (+2) y esperar en pico (0)
    # V = 2 / (1 - 0.9^2) = 2 / 0.19 = 10.5263...
    v_penalizado = calcular_valor_analitico_valle(r_valle=2.0, r_pico=0.0, gamma=0.9)
    assert pytest.approx(v_penalizado, abs=0.01) == 10.53

    # Con r_pico = +1, la política óptima es arrancar en ambos estados (+2 en valle, +1 en pico)
    # V = (2 + 0.9 * 1) / (1 - 0.9^2) = 2.9 / 0.19 = 15.2631...
    v_favorable = calcular_valor_analitico_valle(r_valle=2.0, r_pico=1.0, gamma=0.9)
    assert pytest.approx(v_favorable, abs=0.01) == 15.26


def test_qlearning_convergencia_r_pico_negativo() -> None:
    """Con r_pico = -5.0, Q(valle, arrancar) converge a ~10.53 y la política es {valle: arrancar, pico: esperar}."""
    env = EntornoTarifaHoraria(r_pico=-5.0, recompensa_valle=2.0)
    agente = AgenteQLearningTabular(
        alfa=0.1,
        gamma=0.9,
        epsilon=0.2,
        semilla=0,
    )
    agente.entrenar(env, pasos=20000)

    politica = agente.obtener_politica()
    tabla_q = agente.obtener_tabla_q()

    assert politica == {"valle": "arrancar", "pico": "esperar"}
    assert pytest.approx(tabla_q[("valle", "arrancar")], abs=0.5) == 10.526


def test_qlearning_convergencia_r_pico_positivo() -> None:
    """Con r_pico = +1.0, Q(valle, arrancar) converge a ~15.26 y la política es {valle: arrancar, pico: arrancar}."""
    env = EntornoTarifaHoraria(r_pico=1.0, recompensa_valle=2.0)
    agente = AgenteQLearningTabular(
        alfa=0.1,
        gamma=0.9,
        epsilon=0.2,
        semilla=0,
    )
    agente.entrenar(env, pasos=20000)

    politica = agente.obtener_politica()
    tabla_q = agente.obtener_tabla_q()

    assert politica == {"valle": "arrancar", "pico": "arrancar"}
    assert pytest.approx(tabla_q[("valle", "arrancar")], abs=0.5) == 15.263
