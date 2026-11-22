"""Issue #17 (agrupamiento aglomerativo): fusiones y cortes con 4 criterios de enlace. Datos sintéticos.

Solo usa scipy. Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_17.py
"""

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

METODOS = ("single", "complete", "average", "ward")
PUNTOS = np.array([[1.0], [2.0], [3.5], [5.0], [9.0], [10.0], [12.5]])

if __name__ == "__main__":
    print("alturas de fusión (7 puntos):")
    for m in METODOS:
        print(f"  {m:>8}: {[round(float(h), 3) for h in linkage(PUNTOS, method=m)[:, 2]]}")
    esperado = {
        "single": [1, 1, 1, 1, 2, 2, 3],
        "complete": [2, 2, 3, 3, 1, 1, 1],
        "average": [1, 1, 1, 1, 2, 2, 3],
        "ward": [2, 2, 3, 3, 1, 1, 1],
    }
    print("grupos al cortar en 3 (etiqueta por punto 1, 2, 3.5, 5, 9, 10, 12.5):")
    for m in METODOS:
        etiquetas = fcluster(linkage(PUNTOS, method=m), t=3, criterion="maxclust").tolist()
        print(f"  {m:>8}: {etiquetas}")
        assert etiquetas == esperado[m], m
    seis = np.array([[1.0], [2.0], [4.0], [10.0], [11.0], [13.0]])
    for m in METODOS:
        assert fcluster(linkage(seis, method=m), t=2, criterion="maxclust").tolist() in (
            [1, 1, 1, 2, 2, 2],
            [2, 2, 2, 1, 1, 1],
        )
    print("cortando en 2 grupos, los cuatro criterios dan {1,2,4} y {10,11,13} sobre 6 puntos")
