"""scripts/exportar_repo_educativo.py — Envoltorio de exportación de repositorio educativo.

Uso:
    ./.venv/bin/python scripts/exportar_repo_educativo.py --destino /ruta/datamaq-ml-edu [--sobreescribir]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.cli.exportar_repo_educativo import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
