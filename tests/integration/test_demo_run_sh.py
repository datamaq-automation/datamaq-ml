"""tests/integration/test_demo_run_sh.py — ./run.sh demo --rapido recorre los cuatro pasos (#29).

Usa carpetas temporales para no tocar data/ del repo. Solo datos sintéticos.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def test_demo_rapido_recorre_los_cuatro_pasos(tmp_path: Path) -> None:
    entorno = {
        **os.environ,
        "NO_COLOR": "1",
        "COLUMNS": "80",
        "MEDICIONES_CSV_DIR": str(tmp_path / "in"),
        "VERDAD_DIR": str(tmp_path / "verdad"),
        "RESULTADOS_DIR": str(tmp_path / "out"),
    }
    resultado = subprocess.run(
        ["bash", str(RAIZ / "run.sh"), "demo", "--rapido"],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        env=entorno,
        check=False,
        timeout=900,
    )
    assert resultado.returncode == 0, resultado.stderr[-2000:]
    for paso in ("Paso 1/4", "Paso 2/4", "Paso 3/4", "Paso 4/4"):
        assert paso in resultado.stdout
    assert "Distribución de saltos" in resultado.stdout
    assert "Recorrido completo" in resultado.stdout
