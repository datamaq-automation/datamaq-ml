"""scripts/validar_dia_real.py — Envoltorio de src.infrastructure.cli.validar_dia_real.

Ejecutar desde la raíz del repo, con el Python del venv:
    ./.venv/bin/python scripts/validar_dia_real.py --archivo <CSV> --firmas <JSON> \\
        --fecha AAAA-MM-DD --salida-json <ruta.json>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.cli.validar_dia_real import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
