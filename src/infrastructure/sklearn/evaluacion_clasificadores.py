"""src/infrastructure/sklearn/evaluacion_clasificadores.py — Evaluación y validación cruzada de clasificadores."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import clone
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import KFold


def evaluar_clasificador_cv(
    clasificador: Any,
    X: list[list[float]] | np.ndarray,
    y: list[Any] | np.ndarray,
    k: int = 5,
    shuffle: bool = True,
    random_state: int = 42,
) -> dict[str, Any]:
    """Evalúa un clasificador supervisado mediante validación cruzada de k particiones (k-fold).

    Funciona de manera polimórfica sobre cualquier estimador compatible con scikit-learn
    (DecisionTreeClassifier, KNeighborsClassifier, GaussianNB, etc.).
    """
    if len(X) != len(y):
        raise ValueError("X e y deben contener la misma cantidad de ejemplos.")
    if k < 2:
        raise ValueError("El número de folds (k) debe ser al menos 2.")

    X_arr = np.asarray(X)
    y_arr = np.asarray(y)

    kf = KFold(n_splits=k, shuffle=shuffle, random_state=random_state)
    scores_entrenamiento: list[float] = []
    scores_validacion: list[float] = []
    y_reales_total: list[Any] = []
    y_predichos_total: list[Any] = []

    for train_idx, val_idx in kf.split(X_arr, y_arr):
        X_train, X_val = X_arr[train_idx], X_arr[val_idx]
        y_train, y_val = y_arr[train_idx], y_arr[val_idx]

        modelo = clone(clasificador)
        modelo.fit(X_train, y_train)

        score_train = float(modelo.score(X_train, y_train))
        score_val = float(modelo.score(X_val, y_val))
        scores_entrenamiento.append(score_train)
        scores_validacion.append(score_val)

        preds_val = modelo.predict(X_val)
        y_reales_total.extend(y_val)
        y_predichos_total.extend(preds_val)

    clases = sorted(set(y_arr))
    matriz = confusion_matrix(y_reales_total, y_predichos_total, labels=clases)

    return {
        "k_folds": k,
        "clases": [str(c) for c in clases],
        "scores_entrenamiento": scores_entrenamiento,
        "scores_validacion": scores_validacion,
        "exactitud_entrenamiento_media": float(np.mean(scores_entrenamiento)),
        "exactitud_validacion_media": float(np.mean(scores_validacion)),
        "desvio_estandar_validacion": float(np.std(scores_validacion)),
        "matriz_confusion": matriz.tolist(),
    }
