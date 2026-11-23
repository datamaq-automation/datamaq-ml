"""tests/unit/test_descargar_datos_estudiantes.py — Pruebas unitarias de descarga de datasets didácticos."""

import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.infrastructure.cli.descargar_datos_estudiantes import (
    CODIGO_ERROR_RED,
    CODIGO_OK,
    descargar_archivo,
    main,
    sincronizar_datasets,
)

CSV_VALIDO = (
    "instante,potencia_kw,reactiva_kvar,energia_kwh\n2026-09-12T03:00:01,4.21,-40.6,1000.0\n"
)


def test_descargar_archivo_exitoso(tmp_path: Path) -> None:
    destino = tmp_path / "t1.csv"

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = CSV_VALIDO.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        exito = descargar_archivo("https://example.com/t1.csv", destino)

    assert exito is True
    assert destino.exists()
    assert destino.read_text(encoding="utf-8") == CSV_VALIDO


def test_descargar_archivo_error_http(tmp_path: Path) -> None:
    destino = tmp_path / "t1.csv"

    mock_resp = MagicMock()
    mock_resp.status = 404
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        exito = descargar_archivo("https://example.com/t1.csv", destino)

    assert exito is False
    assert not destino.exists()


def test_descargar_archivo_formato_invalido(tmp_path: Path) -> None:
    destino = tmp_path / "t1.csv"

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"<html><head><title>Error</title></head></html>"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        exito = descargar_archivo("https://example.com/t1.csv", destino)

    assert exito is False
    assert not destino.exists()


def test_descargar_archivo_error_red(tmp_path: Path) -> None:
    destino = tmp_path / "t1.csv"

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Timeout")):
        exito = descargar_archivo("https://example.com/t1.csv", destino)

    assert exito is False
    assert not destino.exists()


def test_sincronizar_datasets_completo(tmp_path: Path) -> None:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = CSV_VALIDO.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        exitos = sincronizar_datasets("https://example.com", tmp_path)

    assert exitos == 2
    assert (tmp_path / "t1.csv").exists()
    assert (tmp_path / "t2.csv").exists()


def test_main_cli(tmp_path: Path) -> None:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = CSV_VALIDO.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        codigo = main(["--destino", str(tmp_path)])

    assert codigo == CODIGO_OK
    assert (tmp_path / "t1.csv").exists()
    assert (tmp_path / "t2.csv").exists()


def test_main_cli_fallo_red(tmp_path: Path) -> None:
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network unreachable")):
        codigo = main(["--destino", str(tmp_path)])

    assert codigo == CODIGO_ERROR_RED
