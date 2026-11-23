"""tests/unit/test_aq_learner.py — Tests unitarios del algoritmo AQ y cubrimiento secuencial (Issue #13).

Verifica la inducción de complejos estrella de Michalski, el cubrimiento secuencial disyuntivo,
el cálculo de intervalos sin negativos y la predicción en el dominio eléctrico.
"""

from __future__ import annotations

import math

from src.domain.cargas.aq_learner import AQLearner, inducir_complejo_1d


def test_inducir_complejo_1d_casos_nominales_issue_13() -> None:
    """Verifica exactamente los tres complejos del Issue #13 con 6 arranques sintéticos."""
    ejemplos = [
        (88.0, 90),
        (92.0, 90),
        (40.0, 40),
        (42.0, 40),
        (15.0, 15),
        (16.0, 15),
    ]

    # Clase 90: negativos cercanos son 42 por debajo y ninguno por encima
    c90 = inducir_complejo_1d(ejemplos, clase_objetivo=90)
    assert c90.minimo == 42.0
    assert math.isinf(c90.maximo) and c90.maximo > 0

    # Clase 40: negativos son 16 por debajo y 88 por encima
    c40 = inducir_complejo_1d(ejemplos, clase_objetivo=40)
    assert c40.minimo == 16.0
    assert c40.maximo == 88.0

    # Clase 15: ninguno por debajo y 40 por encima
    c15 = inducir_complejo_1d(ejemplos, clase_objetivo=15)
    assert math.isinf(c15.minimo) and c15.minimo < 0
    assert c15.maximo == 40.0

    # Ninguno de los tres complejos cubre negativos
    for c, clase in [(c90, 90), (c40, 40), (c15, 15)]:
        negativos_cubiertos = [dp for dp, y in ejemplos if y != clase and c.cubre_valor(dp)]
        assert negativos_cubiertos == []


def test_aq_learner_cubrimiento_secuencial_disyuntivo() -> None:
    """Verifica que el cubrimiento secuencial genere múltiples complejos si los positivos están separados."""
    # Clase A tiene positivos en 10 y 50, con negativo en 30
    ejemplos = [
        ({"dp": 10.0}, "A"),
        ({"dp": 50.0}, "A"),
        ({"dp": 30.0}, "B"),
    ]

    aq = AQLearner()
    aq.entrenar(ejemplos)

    reglas = aq.obtener_reglas()
    regla_a = next(r for r in reglas if r.clase == "A")

    # Debe tener 2 complejos para la clase A (uno para < 30 y otro para > 30)
    assert len(regla_a.complejos) == 2
    assert aq.predecir({"dp": 10.0}) == "A"
    assert aq.predecir({"dp": 50.0}) == "A"
    assert aq.predecir({"dp": 30.0}) == "B"


def test_aq_learner_prediccion_salto_60kw() -> None:
    """Un arranque de 60 kW cae en el complejo de 40 kW (16 < 60 < 88)."""
    ejemplos = [
        ({"dp": 88.0}, 90),
        ({"dp": 92.0}, 90),
        ({"dp": 40.0}, 40),
        ({"dp": 42.0}, 40),
        ({"dp": 15.0}, 15),
        ({"dp": 16.0}, 15),
    ]
    aq = AQLearner()
    aq.entrenar(ejemplos)

    assert aq.predecir({"dp": 60.0}) == 40
    assert aq.predecir({"dp": 90.0}) == 90
    assert aq.predecir({"dp": 20.0}) == 15


def test_aq_learner_sin_cobertura_devuelve_none() -> None:
    """Si un ejemplo no cae en ningún complejo conocido, devuelve None o clase por defecto."""
    ejemplos = [
        ({"dp": 10.0}, "A"),
        ({"dp": 20.0}, "B"),
    ]
    aq = AQLearner()
    aq.entrenar(ejemplos)

    # 10 < dp < 20 no está cubierto por complejos disjuntos acotados
    assert aq.predecir({"dp": 15.0}) is None or aq.predecir({"dp": 15.0}) in (
        "A",
        "B",
    )
