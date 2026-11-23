"""src/infrastructure/sklearn/comparacion_agrupadores.py — k-medias y DBSCAN sobre los mismos escalones.

Sirve para la práctica del módulo de aprendizaje no supervisado: los dos algoritmos reciben los mismos
valores de |ΔP| y se comparan por cantidad de grupos, ruido y silueta. Ver docs/material-ensenanza/ejercicios.md.
"""

from dataclasses import dataclass

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score

SEMILLA = 0
RUIDO = -1


@dataclass(frozen=True)
class ResultadoAgrupamiento:
    algoritmo: str
    etiquetas: list[int]
    grupos: int
    ruido: int
    silueta: float | None  # None si hay menos de 2 grupos (la silueta no está definida)


def _silueta(valores: np.ndarray, etiquetas: np.ndarray) -> float | None:
    """Silueta sobre los puntos que no son ruido. None si quedan menos de 2 grupos."""
    mascara = etiquetas != RUIDO
    grupos = set(etiquetas[mascara].tolist())
    if len(grupos) < 2:
        return None
    return float(silhouette_score(valores[mascara].reshape(-1, 1), etiquetas[mascara]))


def agrupar_kmeans(valores_kw: list[float], k: int) -> ResultadoAgrupamiento:
    """k-medias: divide los valores en exactamente k grupos. No tiene noción de ruido."""
    valores = np.asarray(valores_kw, dtype=float)
    etiquetas = KMeans(n_clusters=k, n_init=10, random_state=SEMILLA).fit_predict(
        valores.reshape(-1, 1)
    )
    return ResultadoAgrupamiento(
        algoritmo="k-medias",
        etiquetas=[int(e) for e in etiquetas],
        grupos=len(set(etiquetas.tolist())),
        ruido=0,
        silueta=_silueta(valores, etiquetas),
    )


def agrupar_dbscan(
    valores_kw: list[float], eps_kw: float, min_samples: int
) -> ResultadoAgrupamiento:
    """DBSCAN: agrupa por densidad; los valores aislados quedan como ruido (-1) y el número de grupos no se fija."""
    valores = np.asarray(valores_kw, dtype=float)
    etiquetas = DBSCAN(eps=eps_kw, min_samples=min_samples).fit_predict(valores.reshape(-1, 1))
    return ResultadoAgrupamiento(
        algoritmo="DBSCAN",
        etiquetas=[int(e) for e in etiquetas],
        grupos=len(set(etiquetas.tolist()) - {RUIDO}),
        ruido=int(np.sum(etiquetas == RUIDO)),
        silueta=_silueta(valores, etiquetas),
    )


METODOS_ENLACE = ("single", "complete", "average", "ward")


def agrupar_aglomerativo(
    valores_kw: list[float],
    n_clusters: int | None = None,
    distancia_corte: float | None = None,
    metodo: str = "complete",
) -> ResultadoAgrupamiento:
    """Agrupamiento jerárquico aglomerativo con dendrograma.

    Permite cortar por número de clusters (n_clusters) o por distancia de unión (distancia_corte).
    Soporta métodos de enlace: 'single', 'complete', 'average', 'ward'.
    """
    if metodo not in METODOS_ENLACE:
        raise ValueError(f"Método de enlace no soportado: '{metodo}'. Opciones: {METODOS_ENLACE}")
    if n_clusters is None and distancia_corte is None:
        raise ValueError("Debe especificar n_clusters o distancia_corte.")

    valores = np.asarray(valores_kw, dtype=float)
    if len(valores) < 2:
        return ResultadoAgrupamiento(
            algoritmo=f"Aglomerativo ({metodo})",
            etiquetas=[0] * len(valores),
            grupos=len(valores),
            ruido=0,
            silueta=None,
        )

    z = linkage(valores.reshape(-1, 1), method=metodo)

    if n_clusters is not None:
        etiquetas_raw = fcluster(z, t=n_clusters, criterion="maxclust")
    else:
        etiquetas_raw = fcluster(z, t=distancia_corte, criterion="distance")

    etiquetas = [int(e) for e in etiquetas_raw]
    grupos_unicos = set(etiquetas)

    return ResultadoAgrupamiento(
        algoritmo=f"Aglomerativo ({metodo})",
        etiquetas=etiquetas,
        grupos=len(grupos_unicos),
        ruido=0,
        silueta=_silueta(valores, np.asarray(etiquetas)),
    )
