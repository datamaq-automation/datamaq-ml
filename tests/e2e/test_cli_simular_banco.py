"""tests/e2e/test_cli_simular_banco.py — simulate con banco fijo o automático escribe reactiva (datos sintéticos)."""

from datetime import datetime
from pathlib import Path

import pytest

from src.domain.cargas.banco_capacitores import detectar_conmutaciones
from src.infrastructure.cli.simular_tablero import main as simular
from src.infrastructure.csv.medicion_repository import CsvMedicionRepository
from src.infrastructure.settings.config import get_settings


def _simular(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, banco: str) -> CsvMedicionRepository:
    monkeypatch.setenv("MEDICIONES_CSV_DIR", str(tmp_path / "input"))
    monkeypatch.setenv("VERDAD_DIR", str(tmp_path / "verdad"))
    monkeypatch.setattr(
        "sys.argv",
        [
            "simulate",
            "--nombre",
            banco,
            "--dias",
            "3",
            "--banco",
            banco,
            "--ruido",
            "0.1",
            "--ruido-q",
            "0.1",
        ],
    )
    get_settings.cache_clear()
    try:
        simular()
    finally:
        get_settings.cache_clear()
    return CsvMedicionRepository(tmp_path / "input")


def test_banco_fijo_escribe_reactiva_y_no_tiene_conmutaciones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _simular(tmp_path, monkeypatch, "fijo")
    mediciones = repo.listar("fijo", datetime.min, datetime.max)
    assert all(m.reactiva_kvar is not None for m in mediciones)
    assert detectar_conmutaciones(mediciones) == []


def test_banco_automatico_tiene_conmutaciones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _simular(tmp_path, monkeypatch, "automatico")
    mediciones = repo.listar("automatico", datetime.min, datetime.max)
    assert len(detectar_conmutaciones(mediciones)) >= 1


def test_simulate_sin_banco_no_escribe_reactiva(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MEDICIONES_CSV_DIR", str(tmp_path / "input"))
    monkeypatch.setenv("VERDAD_DIR", str(tmp_path / "verdad"))
    monkeypatch.setattr("sys.argv", ["simulate", "--nombre", "plano", "--dias", "1"])
    get_settings.cache_clear()
    try:
        simular()
    finally:
        get_settings.cache_clear()
    cabecera = (tmp_path / "input" / "plano.csv").read_text(encoding="utf-8").splitlines()[0]
    assert cabecera == "instante,potencia_kw"
