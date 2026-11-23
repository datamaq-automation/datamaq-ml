"""tests/unit/test_sembrar_firmas.py — Siembra de firmas desde el catálogo por placa (datos sintéticos)."""

import json
from pathlib import Path

from src.application.cargas.dtos.desagregar_cargas import FirmaConfirmadaDTO
from src.application.cargas.use_cases.sembrar_firmas import sembrar_firmas
from src.domain.cargas.catalogo_placa import PlacaMotor
from src.infrastructure.cli.comparar_placas import main as comparar
from src.infrastructure.csv.catalogo_placa_repository import leer_catalogo_placa

EJEMPLO = Path(__file__).resolve().parents[2] / "docs" / "ejemplos" / "placas_sinteticas.csv"


def _placa(forma: str, potencia: float = 90.0) -> PlacaMotor:
    return PlacaMotor("Motor X", potencia, "T1", "bombeo", forma, 0.85)


def test_la_firma_sembrada_lleva_potencia_de_placa_y_reactiva_por_cos_phi() -> None:
    (firma,) = sembrar_firmas([_placa("directo", 90.0)])
    assert isinstance(firma, FirmaConfirmadaDTO)
    assert firma.potencia_nominal_kw == 90.0
    assert firma.reactiva_tipica_kvar == 55.78  # 90 · tan(arccos 0,85)


def test_las_rampas_no_se_siembran() -> None:
    assert sembrar_firmas([_placa("variador"), _placa("arranque_suave")]) == []


def test_la_cli_escribe_las_firmas_sembradas_que_el_batch_acepta(tmp_path: Path) -> None:
    cargas = tmp_path / "cargas_T1.csv"
    cargas.write_text(
        "potencia_tipica_kw,encendidos,apagados,ciclos,dispersion_kw,reactiva_tipica_kvar,ratio_qp_mediana\n"
        "90.0,40,40,40,9.5,50.0,0.6\n",
        encoding="utf-8",
    )
    salida = tmp_path / "firmas.json"
    assert (
        comparar(
            ["--placas", str(EJEMPLO), "--cargas", str(cargas), "--salida-firmas", str(salida)]
        )
        == 0
    )
    firmas = [FirmaConfirmadaDTO(**f) for f in json.loads(salida.read_text(encoding="utf-8"))]
    assert len(firmas) == 2  # directo y estrella-triángulo; las rampas no
    assert {f.potencia_nominal_kw for f in firmas} == {90.0, 45.0}
    assert len(leer_catalogo_placa(EJEMPLO)) == 4
