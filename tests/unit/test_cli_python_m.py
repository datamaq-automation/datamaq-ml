"""tests/unit/test_cli_python_m.py — Cada CLI corre con `python -m` y propaga su código de salida."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_CLI = RAIZ / "src" / "infrastructure" / "cli"


def _modulos_con_main() -> list[str]:
    nombres: list[str] = []
    for ruta in sorted(CARPETA_CLI.glob("*.py")):
        if ruta.name == "__init__.py":
            continue
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        if any(isinstance(nodo, ast.FunctionDef) and nodo.name == "main" for nodo in arbol.body):
            nombres.append(ruta.stem)
    return nombres


def _tiene_guarda_que_llama_main(ruta: Path) -> bool:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if not isinstance(nodo, ast.If):
            continue
        es_guarda = (
            isinstance(nodo.test, ast.Compare)
            and isinstance(nodo.test.left, ast.Name)
            and nodo.test.left.id == "__name__"
        )
        if es_guarda and any(
            isinstance(llamada, ast.Call)
            and isinstance(llamada.func, ast.Name)
            and llamada.func.id == "main"
            for llamada in ast.walk(nodo)
        ):
            return True
    return False


def _correr_modulo(modulo: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", f"src.infrastructure.cli.{modulo}", *args],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("modulo", _modulos_con_main())
def test_cada_cli_tiene_guarda_que_llama_main(modulo: str) -> None:
    assert _tiene_guarda_que_llama_main(CARPETA_CLI / f"{modulo}.py"), (
        f'{modulo}.py define main() pero no tiene `if __name__ == "__main__":` que lo llame: '
        "con `python -m` no hace nada."
    )


def test_exportar_dias_ssh_con_python_m_propaga_el_codigo_de_argumentos(tmp_path: Path) -> None:
    """Un device-id que no es uuid sale con código 2 antes de cualquier conexión por SSH."""
    resultado = _correr_modulo(
        "exportar_dias_ssh",
        "--device-id",
        "no-es-un-uuid",
        "--desde",
        "2026-09-12",
        "--hasta",
        "2026-09-12",
        "--salida-dir",
        str(tmp_path / "salida"),
    )
    assert resultado.returncode == 2, resultado.stderr


def test_seudonimizar_con_python_m_propaga_el_codigo_de_argumentos(tmp_path: Path) -> None:
    """Una entrada que no existe sale con código 2 (ruta de error, sin argparse)."""
    resultado = _correr_modulo(
        "seudonimizar_mediciones",
        str(tmp_path / "no-existe"),
        "--salida",
        str(tmp_path / "salida"),
        "--config",
        str(tmp_path / "config.json"),
    )
    assert resultado.returncode == 2, resultado.stderr
