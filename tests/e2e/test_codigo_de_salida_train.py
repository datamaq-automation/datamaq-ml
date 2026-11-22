"""tests/e2e/test_codigo_de_salida_train.py — Códigos de salida de train (#29, fix de códigos).

0 = terminó (también con advertencias), 2 = argumentos o medidor inválido, 3 = datos faltantes.
Mismos códigos que validar_dia_real. Solo datos sintéticos.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.infrastructure.cli.entrenar_cargas import (
    CODIGO_ARGUMENTOS,
    CODIGO_DATOS,
    CODIGO_OK,
    main,
)
from src.infrastructure.settings.config import get_settings

RAIZ = Path(__file__).resolve().parents[2]


def _serie(valores: list[int]) -> str:
    filas = [f"2026-09-20T{i // 12:02d}:{5 * (i % 12):02d}:00,{kw}" for i, kw in enumerate(valores)]
    return "instante,potencia_kw\n" + "\n".join(filas) + "\n"


@pytest.fixture
def entorno(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    entrada, salida = tmp_path / "input", tmp_path / "output"
    entrada.mkdir()
    monkeypatch.setenv("MEDICIONES_CSV_DIR", str(entrada))
    monkeypatch.setenv("RESULTADOS_DIR", str(salida))
    get_settings.cache_clear()
    yield entrada
    get_settings.cache_clear()


def _argv(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr("sys.argv", ["train", *args])


def test_terminar_con_normalidad_devuelve_cero(
    entorno: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    valores = [120 + (0, 1, 2, 1)[j % 4] + (90 if (j // 3) % 2 else 0) for j in range(72)]
    (entorno / "planta.csv").write_text(_serie(valores), encoding="utf-8")
    _argv(monkeypatch, "planta")
    assert main() == CODIGO_OK


def test_advertencia_sin_cargas_sigue_siendo_cero(
    entorno: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Serie plana: no hay saltos, no hay cargas. Es una advertencia, no un error.
    (entorno / "plana.csv").write_text(_serie([120] * 72), encoding="utf-8")
    _argv(monkeypatch, "plana")
    assert main() == CODIGO_OK


def test_sin_csv_devuelve_datos_faltantes(entorno: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _argv(monkeypatch)
    assert main() == CODIGO_DATOS


def test_medidor_desconocido_devuelve_argumentos_invalidos(
    entorno: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (entorno / "planta.csv").write_text(_serie([120] * 72), encoding="utf-8")
    _argv(monkeypatch, "nada")
    assert main() == CODIGO_ARGUMENTOS


def test_rango_de_fechas_invertido_devuelve_argumentos_invalidos(
    entorno: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (entorno / "planta.csv").write_text(_serie([120] * 72), encoding="utf-8")
    _argv(monkeypatch, "planta", "--desde", "2026-09-22", "--hasta", "2026-09-15")
    assert main() == CODIGO_ARGUMENTOS


def test_run_sh_propaga_el_codigo_al_shell(tmp_path: Path) -> None:
    (tmp_path / "planta.csv").write_text(_serie([120] * 72), encoding="utf-8")
    entorno_proceso = {
        **os.environ,
        "MEDICIONES_CSV_DIR": str(tmp_path),
        "RESULTADOS_DIR": str(tmp_path / "out"),
        "NO_COLOR": "1",
        "COLUMNS": "80",
    }
    resultado = subprocess.run(
        [sys.executable, "-m", "src.infrastructure.cli.entrenar_cargas", "nada"],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        env=entorno_proceso,
        check=False,
    )
    assert resultado.returncode == CODIGO_ARGUMENTOS
    assert "Medidor desconocido" in resultado.stderr


def test_csv_ilegible_devuelve_datos_invalidos(
    entorno: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    # Una potencia que no es número: antes salía con traza y código 1.
    (entorno / "rota.csv").write_text(
        "instante,potencia_kw\n2026-09-20T00:00:00,abc\n2026-09-20T00:05:00,120\n", encoding="utf-8"
    )
    _argv(monkeypatch, "rota")
    assert main() == CODIGO_DATOS
