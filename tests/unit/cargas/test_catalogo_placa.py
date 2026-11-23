"""tests/unit/cargas/test_catalogo_placa.py — Firma esperada por placa y forma de arranque (datos sintéticos)."""

from pathlib import Path

import pytest

from src.domain.cargas.catalogo_placa import (
    ModoObservado,
    PlacaMotor,
    comparar_con_modos,
    firma_esperada,
    ratio_qp,
)


def _placa(forma: str, potencia: float = 90.0, cos_phi: float = 0.85) -> PlacaMotor:
    return PlacaMotor("Motor X", potencia, "T1", "bombeo", forma, cos_phi)


def test_la_reactiva_esperada_sale_de_cos_phi() -> None:
    f = firma_esperada(_placa("directo", 90.0, 0.85))
    assert f.ratio_qp_esperado == pytest.approx(0.62, abs=0.01)  # tan(arccos 0,85)
    assert f.reactiva_esperada_kvar == pytest.approx(90.0 * ratio_qp(0.85), abs=0.01)


def test_el_arranque_directo_deja_un_escalon_de_la_potencia_nominal() -> None:
    f = firma_esperada(_placa("directo"))
    assert f.pasos_kw == (90.0,) and f.detectable_como_escalon


def test_el_estrella_triangulo_deja_dos_escalones_y_no_uno_de_la_potencia() -> None:
    f = firma_esperada(_placa("estrella_triangulo", 90.0))
    assert f.pasos_kw == (30.0, 60.0)
    assert 90.0 not in f.pasos_kw


@pytest.mark.parametrize("forma", ["variador", "arranque_suave"])
def test_variador_y_arranque_suave_no_dejan_escalon(forma: str) -> None:
    f = firma_esperada(_placa(forma))
    assert f.pasos_kw == () and not f.detectable_como_escalon


def test_una_forma_desconocida_es_error() -> None:
    with pytest.raises(ValueError):
        firma_esperada(_placa("a-mano"))


def test_un_modo_en_la_potencia_con_la_relacion_esperada_coincide() -> None:
    (c,) = comparar_con_modos([firma_esperada(_placa("directo"))], [ModoObservado(91.0, 0.60)])
    assert c.estado == "coincide"


def test_un_modo_en_la_potencia_con_otra_relacion_marca_forma_distinta() -> None:
    (c,) = comparar_con_modos([firma_esperada(_placa("directo"))], [ModoObservado(91.0, 0.95)])
    assert c.estado == "coincide_forma_distinta"


def test_sin_modo_cerca_no_hay_coincidencia() -> None:
    (c,) = comparar_con_modos([firma_esperada(_placa("directo"))], [ModoObservado(40.0, 0.6)])
    assert c.estado == "sin_modo"


def test_el_estrella_triangulo_coincide_con_su_primer_escalon() -> None:
    (c,) = comparar_con_modos(
        [firma_esperada(_placa("estrella_triangulo"))], [ModoObservado(31.0, None)]
    )
    assert c.estado == "coincide"


def test_una_rampa_no_se_compara_como_escalon() -> None:
    (c,) = comparar_con_modos([firma_esperada(_placa("variador"))], [ModoObservado(90.0, 0.6)])
    assert c.estado == "sin_escalon"


def test_el_csv_de_ejemplo_se_lee_con_sus_cuatro_motores() -> None:
    from src.infrastructure.csv.catalogo_placa_repository import leer_catalogo_placa

    placas = leer_catalogo_placa(Path("docs/ejemplos/placas_sinteticas.csv"))
    assert [p.forma_arranque for p in placas] == [
        "directo",
        "estrella_triangulo",
        "variador",
        "arranque_suave",
    ]
    assert placas[3].cos_phi == 0.85  # sin cos_phi en la fila: el típico
