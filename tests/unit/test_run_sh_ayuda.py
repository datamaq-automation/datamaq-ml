"""tests/unit/test_run_sh_ayuda.py — Menú y ayuda por comando de run.sh (#29).

Se prueban con NO_COLOR=1 y COLUMNS=80, como en la terminal del estudiante.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ANSI = "\x1b["


def _run_sh(*args: str) -> subprocess.CompletedProcess[str]:
    entorno = {**os.environ, "NO_COLOR": "1", "COLUMNS": "80"}
    return subprocess.run(
        ["bash", str(RAIZ / "run.sh"), *args],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        env=entorno,
        check=False,
    )


def test_run_sh_sin_argumentos_muestra_menu_agrupado() -> None:
    resultado = _run_sh()
    assert resultado.returncode == 0
    for seccion in ("DATOS", "APRENDIZAJE", "EVALUACIÓN"):
        assert seccion in resultado.stdout
    assert all(len(linea) <= 80 for linea in resultado.stdout.splitlines())
    assert ANSI not in resultado.stdout


def test_run_sh_ayuda_de_un_comando_muestra_ejemplo_y_ejercicio() -> None:
    resultado = _run_sh("ayuda", "train")
    assert resultado.returncode == 0
    assert "Ejercicio: E6" in resultado.stdout
    assert "./run.sh train sintetico" in resultado.stdout


def test_run_sh_ayuda_de_comando_desconocido_explica_y_falla() -> None:
    resultado = _run_sh("ayuda", "nope")
    assert resultado.returncode == 1
    assert "No conozco el comando «nope»" in resultado.stderr
    assert "Por qué:" in resultado.stderr
