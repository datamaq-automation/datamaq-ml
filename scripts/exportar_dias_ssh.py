"""scripts/exportar_dias_ssh.py — Envoltorio de src.infrastructure.cli.exportar_dias_ssh (solo lectura).

Ejecutar desde la raíz del repo, con el Python del venv. Ver el docstring del módulo para opciones y garantías:
    ./.venv/bin/python scripts/exportar_dias_ssh.py --device-id <uuid> --desde AAAA-MM-DD --hasta AAAA-MM-DD \\
        --salida-dir <carpeta fuera de git, permisos 700>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.cli.exportar_dias_ssh import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
