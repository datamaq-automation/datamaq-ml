"""docs/material-ensenanza/practicas/practica_supervisado_arranques.py — Práctica: clasificar arranques con verdad conocida.

Datos sintéticos del simulador: cada arranque tiene su carga verdadera (la etiqueta). Se compara k-NN, Bayes
(gaussiano) y el árbol del repo sobre los mismos rasgos: ΔP del arranque y los saltos vecinos. Se parte en el
tiempo: primero se entrena con la parte antigua del día y se evalúa con la reciente, para no mirar el futuro.

Uso (desde la raíz del repo):
    ./.venv/bin/python docs/material-ensenanza/practicas/practica_supervisado_arranques.py
"""

import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sklearn.naive_bayes import GaussianNB  # noqa: E402
from sklearn.neighbors import KNeighborsClassifier  # noqa: E402

from src.domain.cargas.entities import CargaSimulada, Salto  # noqa: E402
from src.domain.cargas.simulacion import simular_tablero  # noqa: E402
from src.infrastructure.sklearn.arbol_clasificador import ArbolClasificador  # noqa: E402

INICIO = datetime(2026, 9, 1)
CARGAS = [
    CargaSimulada(potencia_kw=90, ciclos_por_dia=18, duracion_min=25),
    CargaSimulada(potencia_kw=40, ciclos_por_dia=6, duracion_min=60),
    CargaSimulada(potencia_kw=15, ciclos_por_dia=30, duracion_min=10),
]
FRACCION_ENTRENAMIENTO = 0.7


def ejemplos(dias: int = 14, semilla: int = 3) -> list[tuple[Salto, str]]:
    """Un ejemplo por arranque: el salto y sus dos vecinos, con la carga verdadera como etiqueta."""
    mediciones, verdad = simular_tablero(CARGAS, dias, ruido_kw=3.0, semilla=semilla, inicio=INICIO)
    deltas = [0.0] + [
        b.potencia_kw - a.potencia_kw for a, b in zip(mediciones, mediciones[1:], strict=False)
    ]
    indice = {m.instante: i for i, m in enumerate(mediciones)}
    salidas = []
    for evento in verdad:
        if evento.delta_kw <= 0:
            continue
        i = indice[evento.instante]
        previo = deltas[i - 1] if i >= 1 else 0.0
        siguiente = deltas[i + 1] if i + 1 < len(deltas) else 0.0
        salto = Salto(evento.instante, deltas[i], previo, siguiente)
        salidas.append((salto, f"{evento.carga_kw:g} kW"))
    return salidas


def evaluar(ejemplos_: list[tuple[Salto, str]]) -> dict[str, float]:
    corte = int(len(ejemplos_) * FRACCION_ENTRENAMIENTO)
    entrena, prueba = ejemplos_[:corte], ejemplos_[corte:]
    X = [s.rasgos for s, _ in entrena]
    y = [e for _, e in entrena]
    X_prueba = [s.rasgos for s, _ in prueba]
    y_prueba = [e for _, e in prueba]

    knn = KNeighborsClassifier(n_neighbors=5).fit(X, y)
    bayes = GaussianNB().fit(X, y)
    arbol = ArbolClasificador(profundidad=4)
    arbol.entrenar([s for s, _ in entrena], y)
    predicciones = {
        "k-NN (k=5)": list(knn.predict(X_prueba)),
        "Bayes gaussiano": list(bayes.predict(X_prueba)),
        "árbol de decisión": arbol.predecir([s for s, _ in prueba]),
    }
    return {
        nombre: sum(p == v for p, v in zip(pred, y_prueba, strict=True)) / len(y_prueba)
        for nombre, pred in predicciones.items()
    }


def main() -> None:
    datos = ejemplos()
    resultados = evaluar(datos)
    print(f"Arranques etiquetados: {len(datos)} (datos sintéticos, verdad conocida)")
    for nombre, exactitud in resultados.items():
        print(f"  {nombre}: exactitud {exactitud:.2f} sobre la parte reciente")


if __name__ == "__main__":
    main()
