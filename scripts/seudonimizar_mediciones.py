"""scripts/seudonimizar_mediciones.py — Envoltorio de src.infrastructure.cli.seudonimizar_mediciones.

Ejecutar desde la raíz del repo, con el Python del venv:
    ./.venv/bin/python scripts/seudonimizar_mediciones.py <entrada> --salida <carpeta fuera de git> \\
        --config <config.json fuera del repo>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.cli.seudonimizar_mediciones import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
