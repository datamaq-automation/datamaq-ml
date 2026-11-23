"""tests/unit/test_run_sh_glosario.py — ./run.sh glosario con un glosario temporal (#29).

El glosario real llega con el PR #32; para no depender de él, el test usa GLOSARIO_PATH.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture
def glosario(tmp_path: Path) -> Path:
    archivo = tmp_path / "glosario.md"
    archivo.write_text(
        "# Glosario\n\n"
        "**Otsu.** Método que elige el umbral que separa dos grupos. Ejemplo: 48,9 kW.\n\n"
        "**DBSCAN.** Agrupa por densidad. Ejemplo: eps de 8 kW.\n",
        encoding="utf-8",
    )
    return archivo


def _glosario(glosario: Path, *args: str) -> subprocess.CompletedProcess[str]:
    entorno = {**os.environ, "NO_COLOR": "1", "COLUMNS": "80", "GLOSARIO_PATH": str(glosario)}
    return subprocess.run(
        ["bash", str(RAIZ / "run.sh"), "glosario", *args],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        env=entorno,
        check=False,
    )


def test_glosario_sin_termino_lista_los_terminos(glosario: Path) -> None:
    resultado = _glosario(glosario)
    assert resultado.returncode == 0
    assert "Otsu." in resultado.stdout and "DBSCAN." in resultado.stdout


def test_glosario_con_termino_muestra_definicion_y_ejemplo(glosario: Path) -> None:
    resultado = _glosario(glosario, "otsu")  # sin distinguir mayúsculas
    assert resultado.returncode == 0
    assert "Método que elige el umbral" in resultado.stdout
    assert "Ejemplo: 48,9 kW." in resultado.stdout
    assert "**" not in resultado.stdout


def test_glosario_con_termino_desconocido_explica_y_falla(glosario: Path) -> None:
    resultado = _glosario(glosario, "inexistente")
    assert resultado.returncode == 1
    assert "No tengo el término «inexistente»" in resultado.stderr
    assert "Cómo:" in resultado.stderr


def test_glosario_sin_archivo_dice_donde_buscarlo(tmp_path: Path) -> None:
    resultado = _glosario(tmp_path / "no_existe.md")
    assert resultado.returncode == 1
    assert "No encuentro el glosario" in resultado.stderr
