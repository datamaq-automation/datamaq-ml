"""scripts/descargar_datos_estudiantes.py — Envoltorio de descarga de datasets didácticos para ISFT 199.

Uso:
    ./.venv/bin/python scripts/descargar_datos_estudiantes.py [--destino data/input]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.cli.descargar_datos_estudiantes import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
