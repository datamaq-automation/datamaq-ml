"""tests/unit/test_comparacion_agrupadores.py — k-medias frente a DBSCAN sobre valores con resultado conocido."""

import random

from src.infrastructure.sklearn.comparacion_agrupadores import (
    RUIDO,
    agrupar_dbscan,
    agrupar_kmeans,
)


def _tres_grupos(semilla: int = 1) -> list[float]:
    """Escalones alrededor de 10, 50 y 90 kW, con ±1 kW de ruido. Sin valores aislados."""
    rng = random.Random(semilla)
    return [c + rng.uniform(-1.0, 1.0) for c in (10.0, 50.0, 90.0) for _ in range(30)]


def test_kmedias_con_k_3_encuentra_los_tres_grupos() -> None:
    res = agrupar_kmeans(_tres_grupos(), k=3)
    assert res.grupos == 3
    assert res.ruido == 0
    assert res.silueta is not None and res.silueta > 0.9


def test_dbscan_encuentra_los_mismos_tres_grupos_sin_fijar_k() -> None:
    res = agrupar_dbscan(_tres_grupos(), eps_kw=5.0, min_samples=5)
    assert res.grupos == 3
    assert res.ruido == 0


def test_un_valor_aislado_es_ruido_para_dbscan_pero_kmedias_lo_asigna_a_un_grupo() -> None:
    valores = _tres_grupos() + [300.0]
    dbscan = agrupar_dbscan(valores, eps_kw=5.0, min_samples=5)
    kmedias = agrupar_kmeans(valores, k=3)
    assert dbscan.etiquetas[-1] == RUIDO
    assert dbscan.ruido == 1
    assert kmedias.ruido == 0
    assert kmedias.etiquetas[-1] != RUIDO


def test_con_k_2_kmedias_une_dos_grupos_reales_y_la_silueta_baja() -> None:
    """Forzar k=2 con tres grupos reales obliga a mezclar dos: la silueta baja frente a k=3."""
    valores = _tres_grupos()
    con_tres = agrupar_kmeans(valores, k=3)
    con_dos = agrupar_kmeans(valores, k=2)
    assert con_dos.grupos == 2
    assert con_dos.silueta is not None and con_tres.silueta is not None
    assert con_dos.silueta < con_tres.silueta


def test_dbscan_sin_densidad_suficiente_da_un_solo_resultado_de_ruido() -> None:
    res = agrupar_dbscan([1.0, 50.0, 100.0], eps_kw=1.0, min_samples=2)
    assert res.grupos == 0
    assert res.ruido == 3
    assert res.silueta is None
