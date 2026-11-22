"""tests/integration/test_csv_carga_repository.py — Escritura de cargas en CSV."""

import json
from pathlib import Path

from src.domain.cargas.entities import Carga
from src.domain.cargas.repositories import CargaRepository
from src.infrastructure.csv.carga_repository import CsvCargaRepository


def test_guardar_escribe_un_csv_por_medidor(tmp_path: Path) -> None:
    repo: CargaRepository = CsvCargaRepository(tmp_path / "output")
    repo.guardar("planta", [Carga(potencia_tipica_kw=92.1, encendidos=411, apagados=378)])
    lineas = (tmp_path / "output" / "cargas_planta.csv").read_text(encoding="utf-8").splitlines()
    assert lineas == [
        "potencia_tipica_kw,encendidos,apagados,ciclos,dispersion_kw,reactiva_tipica_kvar,ratio_qp_mediana",
        "92.1,411,378,378,0.0,0.0,",
    ]


def test_guardar_entrenamiento_escribe_el_regimen_en_json(tmp_path: Path) -> None:
    repo = CsvCargaRepository(tmp_path / "output")
    repo.guardar_entrenamiento("planta", {"umbral_kw": 44.5, "regimen": "valle_claro"})
    datos = json.loads(
        (tmp_path / "output" / "entrenamiento_planta.json").read_text(encoding="utf-8")
    )
    assert datos == {"umbral_kw": 44.5, "regimen": "valle_claro"}
