"""tests/unit/test_aprendizaje_inductivo_deductivo.py — Tests de contraste inductivo vs. deductivo (Issue #12).

Verifica el cálculo de cortes a mitad de camino, las funciones de clasificación experta e inducida,
las matrices de confusión 3x3 y la divergencia en los casos de fallo (ΔP=26 kW vs. ΔP=62 kW).
"""

from __future__ import annotations

from docs.ejemplos.ejemplo_issue_12 import (
    ENTRENA,
    PRUEBA,
    cortes_inducidos,
    evaluar_clasificador,
    experto,
    inducida,
    matriz_confusion_3x3,
)


def test_cortes_inducidos_calcula_puntos_medios() -> None:
    """Los cortes inducidos deben situarse a mitad de camino entre valores vecinos de entrenamiento."""
    c1, c2 = cortes_inducidos(ENTRENA)
    assert c1 == 27.5  # (15 + 40) / 2
    assert c2 == 65.0  # (40 + 90) / 2


def test_exactitud_identica_con_fallos_distintos() -> None:
    """Ambos clasificadores obtienen 5/6 aciertos pero divergen en los casos puntuales."""
    c1, c2 = cortes_inducidos(ENTRENA)
    res_exp = evaluar_clasificador(PRUEBA, experto)
    res_ind = evaluar_clasificador(PRUEBA, lambda dp: inducida(dp, c1, c2))

    assert res_exp["aciertos"] == 5
    assert res_exp["total"] == 6
    assert round(res_exp["exactitud"], 4) == round(5 / 6, 4)

    assert res_ind["aciertos"] == 5
    assert res_ind["total"] == 6
    assert round(res_ind["exactitud"], 4) == round(5 / 6, 4)

    # El experto falla exclusivamente en ΔP=26 (clasifica 40 en lugar de 15)
    assert res_exp["fallos"] == [(26, 40, 15)]

    # El modelo inducido falla exclusivamente en ΔP=62 (clasifica 40 en lugar de 90)
    assert res_ind["fallos"] == [(62, 40, 90)]


def test_matriz_confusion_3x3() -> None:
    """Verifica que la matriz de confusión 3x3 refleje exactamente los aciertos y las confusiones."""
    c1, c2 = cortes_inducidos(ENTRENA)
    clases = [15, 40, 90]

    matriz_exp = matriz_confusion_3x3(PRUEBA, experto, clases)
    matriz_ind = matriz_confusion_3x3(PRUEBA, lambda dp: inducida(dp, c1, c2), clases)

    # Experto:
    # 15 kW: 1 acierto (20), 1 confusión con 40 (26)
    assert matriz_exp[(15, 15)] == 1
    assert matriz_exp[(15, 40)] == 1
    # 40 kW: 2 aciertos (55, 30)
    assert matriz_exp[(40, 40)] == 2
    # 90 kW: 2 aciertos (70, 62)
    assert matriz_exp[(90, 90)] == 2

    # Inducido:
    # 15 kW: 2 aciertos (20, 26)
    assert matriz_ind[(15, 15)] == 2
    # 40 kW: 2 aciertos (55, 30)
    assert matriz_ind[(40, 40)] == 2
    # 90 kW: 1 acierto (70), 1 confusión con 40 (62)
    assert matriz_ind[(90, 90)] == 1
    assert matriz_ind[(90, 40)] == 1


def test_casos_de_borde_en_umbrales() -> None:
    """Verifica el comportamiento exacto en los límites de decisión."""
    c1, c2 = cortes_inducidos(ENTRENA)

    # Experto: cortes en 25 y 60
    assert experto(24.9) == 15
    assert experto(25.0) == 40
    assert experto(59.9) == 40
    assert experto(60.0) == 90

    # Inducido: cortes en 27.5 y 65.0
    assert inducida(27.4, c1, c2) == 15
    assert inducida(27.5, c1, c2) == 40
    assert inducida(64.9, c1, c2) == 40
    assert inducida(65.0, c1, c2) == 90
