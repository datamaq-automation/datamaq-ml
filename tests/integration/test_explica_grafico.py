"""tests/integration/test_explica_grafico.py — --explica y --grafico no cambian los archivos (#29).

Se entrena dos veces el mismo tablero: una sin banderas y otra con --explica --grafico. Los CSV y los
JSON que escribe train tienen que ser idénticos byte a byte. Solo datos sintéticos.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _correr(modulo: str, entorno: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", modulo, *args],
        capture_output=True,
        text=True,
        cwd=RAIZ,
        env={**os.environ, **entorno, "NO_COLOR": "1", "COLUMNS": "80"},
        check=False,
    )


def test_explica_y_grafico_dejan_los_archivos_de_train_identicos(tmp_path: Path) -> None:
    entrada, verdad = tmp_path / "in", tmp_path / "verdad"
    base = {"MEDICIONES_CSV_DIR": str(entrada), "VERDAD_DIR": str(verdad)}
    simulado = _correr("src.infrastructure.cli.simular_tablero", base, "--dias", "3")
    assert simulado.returncode == 0, simulado.stderr

    solo, con_banderas = tmp_path / "solo", tmp_path / "banderas"
    primero = _correr(
        "src.infrastructure.cli.entrenar_cargas", {**base, "RESULTADOS_DIR": str(solo)}, "sintetico"
    )
    segundo = _correr(
        "src.infrastructure.cli.entrenar_cargas",
        {**base, "RESULTADOS_DIR": str(con_banderas)},
        "sintetico",
        "--explica",
        "--grafico",
    )
    assert primero.returncode == 0 and segundo.returncode == 0

    archivos = sorted(p.name for p in solo.iterdir())
    assert archivos == sorted(p.name for p in con_banderas.iterdir()) and archivos
    for nombre in archivos:
        assert (solo / nombre).read_bytes() == (con_banderas / nombre).read_bytes(), nombre

    assert "Cómo llegué a este resultado (--explica)" in segundo.stdout
    assert "Distribución de saltos" in segundo.stdout
    assert "Cómo llegué" not in primero.stdout
