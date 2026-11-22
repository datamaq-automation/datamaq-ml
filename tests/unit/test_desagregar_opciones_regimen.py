"""tests/unit/test_desagregar_opciones_regimen.py — Opciones de umbral y tolerancia del batch (sin datos reales)."""

from src.infrastructure.cli.desagregar_cargas import _construir_parser

BASE = ["Trafo 1", "--device-id", "00000000-0000-4000-8000-000000000001"]


def test_por_defecto_no_hay_umbral_compartido_ni_dispersion() -> None:
    parsed = _construir_parser().parse_args(BASE)
    assert parsed.umbral_kw is None
    assert parsed.tolerancia_por_dispersion is False
    assert parsed.tolerancia_max_kw == 8.0


def test_las_opciones_de_umbral_y_dispersion_se_leen() -> None:
    parsed = _construir_parser().parse_args(
        [*BASE, "--umbral-kw", "41.5", "--tolerancia-por-dispersion", "--tolerancia-max-kw", "25"]
    )
    assert parsed.umbral_kw == 41.5
    assert parsed.tolerancia_por_dispersion is True
    assert parsed.tolerancia_max_kw == 25.0
