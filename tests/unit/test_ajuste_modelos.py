"""tests/unit/test_ajuste_modelos.py — Tests de ajuste de modelos, validación cruzada y sobreajuste (Issue #16).

Verifica la función reutilizable de evaluación con validación cruzada sobre k-NN, Naive Bayes y
árboles CART, así como la curva de sobreajuste por profundidad con datos sintéticos.
"""

from __future__ import annotations

import pytest
from docs.ejemplos.ejemplo_issue_16 import (
    Xe,
    Xp,
    cambiadas,
    generar_curva_profundidad,
    ruidosa,
    ye,
    yp,
)
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier

from src.infrastructure.sklearn.evaluacion_clasificadores import (
    evaluar_clasificador_cv,
)


def test_evaluar_clasificador_cv_con_arbol() -> None:
    """Verifica validación cruzada con un árbol de decisión."""
    clf = DecisionTreeClassifier(max_depth=3, random_state=42)
    resultado = evaluar_clasificador_cv(clf, Xe, ye, k=3, random_state=42)

    assert resultado["k_folds"] == 3
    assert len(resultado["scores_validacion"]) == 3
    assert 0.0 <= resultado["exactitud_validacion_media"] <= 1.0
    assert 0.0 <= resultado["exactitud_entrenamiento_media"] <= 1.0
    assert "matriz_confusion" in resultado


def test_evaluar_clasificador_cv_con_knn() -> None:
    """Verifica la función reutilizable con k-NN."""
    clf = KNeighborsClassifier(n_neighbors=3)
    resultado = evaluar_clasificador_cv(clf, Xe, ye, k=3, random_state=42)

    assert resultado["k_folds"] == 3
    assert len(resultado["scores_validacion"]) == 3
    assert 0.0 <= resultado["exactitud_validacion_media"] <= 1.0


def test_evaluar_clasificador_cv_con_bayes() -> None:
    """Verifica la función reutilizable con Naive Bayes gaussiano."""
    clf = GaussianNB()
    resultado = evaluar_clasificador_cv(clf, Xe, ye, k=3, random_state=42)

    assert resultado["k_folds"] == 3
    assert len(resultado["scores_validacion"]) == 3
    assert 0.0 <= resultado["exactitud_validacion_media"] <= 1.0


def test_evaluar_clasificador_cv_dimensiones_invalidas() -> None:
    """Falla si X e y tienen diferente longitud o k < 2."""
    clf = DecisionTreeClassifier()
    with pytest.raises(ValueError, match="misma cantidad"):
        evaluar_clasificador_cv(clf, [[1.0], [2.0]], [1])

    with pytest.raises(ValueError, match="al menos 2"):
        evaluar_clasificador_cv(clf, [[1.0], [2.0]], [1, 2], k=1)


def test_curva_sobreajuste_valores_nominales_issue_16() -> None:
    """Verifica exactamente los valores nominales y el sobreajuste reportado en el Issue #16."""
    assert cambiadas == 19

    curva = generar_curva_profundidad(Xe, ruidosa, Xp, yp, profundidades=(2, 4, None))

    scores_entrena = [round(curva[p]["score_entrenamiento"], 3) for p in (2, 4, None)]
    scores_prueba = [round(curva[p]["score_prueba"], 3) for p in (2, 4, None)]
    hojas = [curva[p]["hojas"] for p in (2, 4, None)]

    # Coincidencia con la especificación del Issue #16
    assert scores_entrena == [0.717, 0.800, 0.983]
    assert scores_prueba == [0.780, 0.650, 0.575]
    assert hojas == [4, 11, 25]

    # Demostración del sobreajuste: a mayor profundidad, mayor score en entrenamiento pero menor en prueba
    assert scores_entrena[2] > scores_entrena[0]
    assert scores_prueba[2] < scores_prueba[0]
