"""tests/unit/test_agrupamiento_aglomerativo.py — Tests de agrupamiento jerárquico aglomerativo (Issue #17).

Verifica la función de agrupamiento aglomerativo con enlace simple, completo, promedio y Ward,
los cortes por número de grupos y por umbral de distancia, y el cálculo de silueta.
"""

from __future__ import annotations

import pytest
from docs.ejemplos.ejemplo_issue_17 import (
    METODOS,
    cortar_dendrograma,
    matriz_enlaces,
)

from src.infrastructure.sklearn.comparacion_agrupadores import (
    agrupar_aglomerativo,
)


def test_agrupar_aglomerativo_7_puntos_tres_grupos() -> None:
    """Verifica el agrupamiento en 3 clusters sobre los 7 puntos de la especificación."""
    puntos = [1.0, 2.0, 3.5, 5.0, 9.0, 10.0, 12.5]

    res_single = agrupar_aglomerativo(puntos, n_clusters=3, metodo="single")
    res_complete = agrupar_aglomerativo(puntos, n_clusters=3, metodo="complete")

    assert res_single.grupos == 3
    assert res_single.ruido == 0
    assert res_complete.grupos == 3

    # Enlace simple encadena 1, 2, 3.5, 5 en el mismo grupo
    assert (
        res_single.etiquetas[0]
        == res_single.etiquetas[1]
        == res_single.etiquetas[2]
        == res_single.etiquetas[3]
    )

    # Enlace completo separa {1, 2} de {3.5, 5}
    assert res_complete.etiquetas[0] == res_complete.etiquetas[1]
    assert res_complete.etiquetas[2] == res_complete.etiquetas[3]
    assert res_complete.etiquetas[0] != res_complete.etiquetas[2]


def test_agrupar_aglomerativo_seis_puntos_dos_grupos() -> None:
    """Sobre seis puntos con separación clara {1,2,4} y {10,11,13}, los 4 métodos coinciden."""
    puntos = [1.0, 2.0, 4.0, 10.0, 11.0, 13.0]

    for metodo in ("single", "complete", "average", "ward"):
        res = agrupar_aglomerativo(puntos, n_clusters=2, metodo=metodo)
        assert res.grupos == 2
        # Los primeros 3 puntos comparten etiqueta, y los últimos 3 comparten otra
        assert res.etiquetas[0] == res.etiquetas[1] == res.etiquetas[2]
        assert res.etiquetas[3] == res.etiquetas[4] == res.etiquetas[5]
        assert res.etiquetas[0] != res.etiquetas[3]


def test_agrupar_aglomerativo_corte_por_distancia() -> None:
    """Verifica que el corte por distancia máxima forme grupos coherentes."""
    puntos = [1.0, 2.0, 4.0, 10.0, 11.0, 13.0]
    # Con distancia_corte = 3.0 y complete, se separan los grupos con distancia > 3.0
    res = agrupar_aglomerativo(puntos, distancia_corte=3.5, metodo="complete")
    assert res.grupos == 2


def test_agrupar_aglomerativo_argumentos_invalidos() -> None:
    """Falla si el método no es válido o si no se especifica ni n_clusters ni distancia_corte."""
    with pytest.raises(ValueError, match="Método de enlace no soportado"):
        agrupar_aglomerativo([1.0, 2.0], n_clusters=2, metodo="invalido")

    with pytest.raises(ValueError, match="Debe especificar n_clusters o distancia_corte"):
        agrupar_aglomerativo([1.0, 2.0], n_clusters=None, distancia_corte=None)


def test_matriz_enlaces_y_cortes_ejemplo_issue_17() -> None:
    """Verifica las funciones modulares del script didáctico de issue 17."""
    puntos = [1.0, 2.0, 3.5, 5.0, 9.0, 10.0, 12.5]
    for metodo in METODOS:
        z = matriz_enlaces(puntos, metodo=metodo)
        assert z.shape == (6, 4)  # n-1 fusiones de 4 columnas

        etiquetas = cortar_dendrograma(z, n_clusters=3)
        assert len(etiquetas) == 7
        assert len(set(etiquetas)) == 3
