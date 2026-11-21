"""tests/e2e/test_cli_desagregar_cargas.py — ./run.sh disaggregate de punta a punta."""

from pathlib import Path

import pytest

from src.infrastructure.cli.desagregar_cargas import main as desagregar
from src.infrastructure.settings.config import get_settings


@pytest.fixture
def carpeta_mediciones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    entrada = tmp_path / "input"
    entrada.mkdir()
    # Mediciones para el día 2026-09-20
    filas = [
        "2026-09-20T08:00:00,10.0,5.0",
        "2026-09-20T08:05:00,60.0,35.0",
        "2026-09-20T09:05:00,60.0,35.0",
        "2026-09-20T09:10:00,10.0,5.0",
    ]
    (entrada / "trafo_test.csv").write_text(
        "instante,potencia_kw,reactiva_kvar\n" + "\n".join(filas) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MEDICIONES_CSV_DIR", str(entrada))
    get_settings.cache_clear()
    yield entrada
    get_settings.cache_clear()


def test_cli_desagregar_cargas_ejecucion(
    carpeta_mediciones: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    args = [
        "trafo_test",
        "--fecha",
        "2026-09-20",
        "--potencia",
        "50.0",
        "--reactiva",
        "30.0",
        "--nombre",
        "Compresor Test",
        "--machine-id",
        "comp-1",
    ]
    with caplog.at_level("INFO", logger="backend-api"):
        ret = desagregar(args)
    assert ret == 0
    assert "Iniciando desagregación batch para 'trafo_test'" in caplog.text
    assert "Desagregación completada. Intervalos asignados: 1" in caplog.text
    assert "Máquina 'Compresor Test' (comp-1): 1.08 h marcha, 1 ciclos, 54.17 kWh" in caplog.text
