"""tests/unit/test_evaluar_verdad_calidad_cli.py — La CLI de evaluar_verdad reporta la calidad del día (datos sintéticos)."""

import json
from pathlib import Path

import pytest

from src.infrastructure.cli.evaluar_verdad import CODIGO_OK, main

from .test_evaluar_dia_calidad import EJEMPLO, _inferido, _verdad


def _escribir(
    tmp_path: Path, estado: str | None, motivos: list[str] | None = None
) -> tuple[Path, Path]:
    inferido = tmp_path / "inferido.json"
    inferido.write_text(_inferido().model_dump_json(), encoding="utf-8")
    verdad = tmp_path / "verdad.json"
    verdad.write_text(_verdad(estado, motivos).model_dump_json(), encoding="utf-8")
    return inferido, verdad


@pytest.fixture
def logs(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level("INFO", logger="backend-api")
    return caplog


def test_no_utilizable_se_rechaza_y_el_log_dice_por_que(tmp_path: Path, logs) -> None:
    inferido, verdad = _escribir(tmp_path, "NO_UTILIZABLE", ["desvio_reloj"])
    salida = tmp_path / "detalle.json"
    assert (
        main(["--inferido", str(inferido), "--verdad", str(verdad), "--salida-json", str(salida)])
        == CODIGO_OK
    )
    assert json.loads(salida.read_text(encoding="utf-8")) == []
    assert "Día NO_UTILIZABLE rechazado (desvio_reloj)" in logs.text
    assert "motivos de exclusión: {'desvio_reloj': 1}" in logs.text


def test_no_utilizable_con_bandera_se_evalua_y_se_marca(tmp_path: Path, logs) -> None:
    inferido, verdad = _escribir(tmp_path, "NO_UTILIZABLE", ["desvio_reloj"])
    salida = tmp_path / "detalle.json"
    assert main(
        ["--inferido", str(inferido), "--verdad", str(verdad), "--salida-json", str(salida),
         "--incluir-no-utilizables"]
    ) == CODIGO_OK  # fmt: skip
    filas = json.loads(salida.read_text(encoding="utf-8"))
    assert len(filas) == 2 and all(f["calidad_dia"] == "NO_UTILIZABLE" for f in filas)


def test_dudosa_se_evalua_marcada_y_fuera_del_resumen(tmp_path: Path, logs) -> None:
    inferido, verdad = _escribir(tmp_path, "DUDOSA", ["huecos_seq"])
    salida = tmp_path / "detalle.json"
    assert (
        main(["--inferido", str(inferido), "--verdad", str(verdad), "--salida-json", str(salida)])
        == CODIGO_OK
    )
    filas = json.loads(salida.read_text(encoding="utf-8"))
    assert len(filas) == 2 and all(
        f["calidad_dia"] == "DUDOSA" and not f["en_resumen"] for f in filas
    )
    assert "Día DUDOSO (huecos_seq)" in logs.text
    assert "excluidos: 0" in logs.text


def test_dia_ok_sin_bloque_no_cambia_el_detalle_y_no_avisa(tmp_path: Path, logs) -> None:
    inferido, verdad = _escribir(tmp_path, None)
    salida = tmp_path / "detalle.json"
    assert (
        main(["--inferido", str(inferido), "--verdad", str(verdad), "--salida-json", str(salida)])
        == CODIGO_OK
    )
    filas = json.loads(salida.read_text(encoding="utf-8"))
    assert len(filas) == 2 and all(f["calidad_dia"] == "OK" and f["en_resumen"] for f in filas)
    assert "DUDOSO" not in logs.text and "rechazado" not in logs.text


def test_el_ejemplo_documentado_sigue_evaluandose_igual(tmp_path: Path) -> None:
    verdad = tmp_path / "verdad.json"
    verdad.write_text(EJEMPLO.read_text(encoding="utf-8"), encoding="utf-8")
    inferido, _ = _escribir(tmp_path, None)
    assert main(["--inferido", str(inferido), "--verdad", str(verdad)]) == CODIGO_OK
