"""Issue #17 (agrupamiento aglomerativo): fusiones y cortes con 4 criterios de enlace. Datos sintéticos.

Demuestra la formación del dendrograma jerárquico y cómo los diferentes métodos de enlace
(single, complete, average, ward) producen agrupamientos distintos según encadenamiento o compacidad.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_17.py
"""

from __future__ import annotations

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

METODOS = ("single", "complete", "average", "ward")
PUNTOS = np.array([[1.0], [2.0], [3.5], [5.0], [9.0], [10.0], [12.5]])


def matriz_enlaces(
    puntos: list[float] | list[list[float]] | np.ndarray,
    metodo: str = "complete",
) -> np.ndarray:
    """Calcula la matriz de enlaces jerárquicos (dendrograma) con scipy.linkage."""
    arr = np.asarray(puntos, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    return linkage(arr, method=metodo)


def cortar_dendrograma(
    z: np.ndarray,
    n_clusters: int | None = None,
    distancia_corte: float | None = None,
) -> list[int]:
    """Corta el dendrograma por cantidad de clusters o por umbral de distancia."""
    if n_clusters is not None:
        etiquetas = fcluster(z, t=n_clusters, criterion="maxclust")
    elif distancia_corte is not None:
        etiquetas = fcluster(z, t=distancia_corte, criterion="distance")
    else:
        raise ValueError("Debe especificar n_clusters o distancia_corte.")
    return [int(e) for e in etiquetas]


if __name__ == "__main__":
    print("alturas de fusión (7 puntos):")
    for m in METODOS:
        z = matriz_enlaces(PUNTOS, metodo=m)
        alturas = [round(float(h), 3) for h in z[:, 2]]
        print(f"  {m:>8}: {alturas}")

    esperado = {
        "single": [1, 1, 1, 1, 2, 2, 3],
        "complete": [2, 2, 3, 3, 1, 1, 1],
        "average": [1, 1, 1, 1, 2, 2, 3],
        "ward": [2, 2, 3, 3, 1, 1, 1],
    }
    print("\ngrupos al cortar en 3 (etiqueta por punto 1, 2, 3.5, 5, 9, 10, 12.5):")
    for m in METODOS:
        z = matriz_enlaces(PUNTOS, metodo=m)
        etiquetas = cortar_dendrograma(z, n_clusters=3)
        print(f"  {m:>8}: {etiquetas}")
        assert etiquetas == esperado[m], m

    seis = np.array([[1.0], [2.0], [4.0], [10.0], [11.0], [13.0]])
    for m in METODOS:
        z = matriz_enlaces(seis, metodo=m)
        etiquetas_seis = cortar_dendrograma(z, n_clusters=2)
        assert etiquetas_seis in ([1, 1, 1, 2, 2, 2], [2, 2, 2, 1, 1, 1])
    print("\ncortando en 2 grupos, los cuatro criterios dan {1,2,4} y {10,11,13} sobre 6 puntos.")
