"""tests/unit/cargas/test_regimenes.py — Valle del histograma de |ΔP| y modos por régimen (datos sintéticos)."""

import random

from src.domain.cargas.regimenes import etiquetar_por_modos, hallar_regimen


def _bimodal(semilla: int) -> list[float]:
    """Ruido de 0 a 20 kW, valle casi vacío entre 20 y 75 kW, y un modo ancho de 77 a 110 kW (una carga)."""
    r = random.Random(semilla)
    ruido = [min(abs(r.gauss(0, 4.0)), 19.9) for _ in range(4000)]
    eventos = [r.uniform(77.0, 110.0) for _ in range(350)]
    return ruido + eventos


def _continuo(semilla: int) -> list[float]:
    """Ruido de 0 a 13 kW y después una población uniforme de 15 a 150 kW sin ningún valle."""
    r = random.Random(semilla)
    ruido = [min(abs(r.gauss(0, 4.0)), 12.9) for _ in range(4000)]
    cuerpo = [r.uniform(15.0, 150.0) for _ in range(3000)]
    return ruido + cuerpo


def test_bimodal_tiene_valle_claro_y_un_modo_con_su_dispersion() -> None:
    regimen = hallar_regimen(_bimodal(1))
    assert regimen.hay_modos
    assert regimen.profundidad_valle is not None and regimen.profundidad_valle < 0.2
    assert regimen.umbral_kw is not None
    # El umbral cae en el valle, no en el ruido ni en el modo.
    assert 20.0 <= regimen.umbral_kw <= 77.0
    assert len(regimen.modos) == 1
    modo = regimen.modos[0]
    assert 85.0 <= modo.centro_kw <= 102.0
    # Uniforme en 77-110: σ = 33/√12 ≈ 9,5 kW; el radio es 2σ, no el IQR de todo el conjunto.
    assert 7.0 <= modo.dispersion_kw <= 11.0
    assert abs(modo.radio_kw - 2 * modo.dispersion_kw) < 0.05


def test_continuo_sin_valle_no_tiene_modos_separables() -> None:
    regimen = hallar_regimen(_continuo(2))
    assert not regimen.hay_modos
    assert regimen.modos == []


def test_pocos_saltos_no_producen_regimen() -> None:
    regimen = hallar_regimen([1.0, 2.0, 80.0])
    assert regimen.umbral_kw is None
    assert not regimen.hay_modos


def test_etiquetar_asigna_cada_salto_a_su_modo_o_a_ninguno() -> None:
    regimen = hallar_regimen(_bimodal(3))
    etiquetas = etiquetar_por_modos([3.0, 90.0, 60.0, 105.0], regimen.modos)
    assert etiquetas == [-1, 0, -1, 0]


def test_la_seleccion_es_reproducible_con_la_misma_semilla() -> None:
    assert hallar_regimen(_bimodal(7)) == hallar_regimen(_bimodal(7))
