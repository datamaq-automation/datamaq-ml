"""Issue #16 (sobreajuste y validación): profundidad del árbol con 20 % de etiquetas cambiadas. Datos sintéticos.

Demuestra el efecto de sobreajuste: a mayor profundidad, el modelo memoriza el ruido
de entrenamiento (sube el score de entrenamiento) y empeora su capacidad de generalizar
en datos de prueba no vistos.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_16.py
"""

from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sklearn.tree import DecisionTreeClassifier  # noqa: E402

from src.infrastructure.sklearn.evaluacion_clasificadores import (  # noqa: E402
    evaluar_clasificador_cv,
)

spec = importlib.util.spec_from_file_location(
    "p", "docs/material-ensenanza/practicas/practica_supervisado_arranques.py"
)
if spec is None or spec.loader is None:
    raise ImportError("No se pudo cargar practica_supervisado_arranques.py")
practica = importlib.util.module_from_spec(spec)
spec.loader.exec_module(practica)

datos = practica.ejemplos(dias=14, semilla=3)
Xe = [s.rasgos for s, _ in datos[:60]]
ye = [e for _, e in datos[:60]]
Xp = [s.rasgos for s, _ in datos[60:260]]
yp = [e for _, e in datos[60:260]]

r = random.Random(7)
clases = sorted(set(ye))
ruidosa = [y if r.random() > 0.2 else r.choice([c for c in clases if c != y]) for y in ye]
cambiadas = sum(a != b for a, b in zip(ye, ruidosa, strict=False))


def generar_curva_profundidad(
    X_train: list[list[float]],
    y_train: list[str],
    X_test: list[list[float]],
    y_test: list[str],
    profundidades: tuple[int | None, ...] = (2, 4, None),
) -> dict[int | None, dict[str, Any]]:
    """Ajusta árboles con distintas profundidades y compara scores en train y test."""
    curva: dict[int | None, dict[str, Any]] = {}
    for prof in profundidades:
        arbol = DecisionTreeClassifier(max_depth=prof, random_state=0).fit(X_train, y_train)
        curva[prof] = {
            "score_entrenamiento": float(arbol.score(X_train, y_train)),
            "score_prueba": float(arbol.score(X_test, y_test)),
            "hojas": arbol.get_n_leaves(),
        }
    return curva


def evaluar_con_cv(
    clasificador: Any,
    X: list[list[float]],
    y: list[str],
    k: int = 5,
) -> dict[str, Any]:
    """Evalúa un clasificador mediante validación cruzada usando la utilidad del repo."""
    return evaluar_clasificador_cv(clasificador, X, y, k=k)


if __name__ == "__main__":
    print(f"entrenamiento de 60 con {cambiadas} etiquetas cambiadas; prueba limpia de 200")
    curva = generar_curva_profundidad(Xe, ruidosa, Xp, yp)
    for prof, res in curva.items():
        print(
            f"profundidad {str(prof):>4}: entrenamiento {res['score_entrenamiento']:.3f}  "
            f"prueba {res['score_prueba']:.3f}  hojas {res['hojas']}"
        )

    assert cambiadas == 19
    assert [round(curva[p]["score_prueba"], 3) for p in (2, 4, None)] == [
        0.780,
        0.650,
        0.575,
    ]
    assert [round(curva[p]["score_entrenamiento"], 3) for p in (2, 4, None)] == [
        0.717,
        0.800,
        0.983,
    ]
    print(
        "Sobreajuste comprobado: al aumentar la profundidad, la exactitud en prueba cae de 78.0 % a 57.5 %."
    )
