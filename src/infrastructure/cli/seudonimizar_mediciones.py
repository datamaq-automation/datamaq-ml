"""src/infrastructure/cli/seudonimizar_mediciones.py — Seudonimiza el nombre de la empresa y los identificadores de medidor.

Qué hace, y qué NO hace:
- Reemplaza en archivos de texto la mención del nombre de la empresa por un texto configurable.
- Renombra medidores (nombres de archivo y contenido): identificadores técnicos y nombres internos → etiquetas.
- NO toca instantes ni valores de potencia: las columnas numéricas y de fecha salen idénticas. Se verifica
  al final, fila por fila, y el comando falla si algo cambió.
- NO desplaza fechas y NO escala potencias.
- Escribe solo fuera de un repositorio git (el destino no puede estar dentro de un working tree).

La configuración (nombres reales, identificadores y el nombre de la empresa) se lee de un archivo JSON
que vive FUERA del repo. El comando nunca imprime esos valores: solo conteos.

Formato de la configuración:
    {
      "medidores": {"<nombre o uuid real>": "Trafo 1", "<otro>": "Trafo 2"},
      "empresa": {"patron": "<nombre de la empresa>", "reemplazo": "una papelera"}
    }

Códigos de salida: 0 ok; 2 argumentos, configuración o destino inválidos; 3 verificación fallida.
"""

import argparse
import csv
import json
from pathlib import Path

from src.infrastructure.settings.logger import logger

CODIGO_OK = 0
CODIGO_ARGUMENTOS = 2
CODIGO_VERIFICACION = 3
COLUMNAS_NUMERICAS = ("instante", "potencia_kw", "reactiva_kvar", "energia_kwh")
EXTENSIONES_TEXTO = {".csv", ".json", ".md", ".txt"}


class ErrorSeudonimizacion(Exception):
    def __init__(self, codigo: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo


def esta_dentro_de_repo_git(ruta: Path) -> bool:
    """¿La ruta está dentro de un working tree de git? Busca un `.git` en la ruta o en sus ancestros."""
    actual = ruta.resolve()
    for candidato in [actual, *actual.parents]:
        if (candidato / ".git").exists():
            return True
    return False


def cargar_configuracion(ruta: Path) -> tuple[dict[str, str], str, str]:
    """(mapa de medidores, patrón de la empresa, reemplazo). Falla si falta algo o está vacío."""
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        medidores = {str(k): str(v) for k, v in datos["medidores"].items()}
        patron = str(datos["empresa"]["patron"])
        reemplazo = str(datos["empresa"]["reemplazo"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise ErrorSeudonimizacion(CODIGO_ARGUMENTOS, f"Configuración inválida: {error}") from error
    if not patron or not reemplazo:
        raise ErrorSeudonimizacion(
            CODIGO_ARGUMENTOS, "La configuración de la empresa no puede estar vacía."
        )
    return medidores, patron, reemplazo


def _reemplazar(texto: str, reemplazos: list[tuple[str, str]]) -> str:
    for original, nuevo in reemplazos:
        texto = texto.replace(original, nuevo)
    return texto


def _nombre_destino(nombre: str, reemplazos: list[tuple[str, str]]) -> str:
    return _reemplazar(nombre, reemplazos)


def seudonimizar_archivo(
    origen: Path, destino_dir: Path, reemplazos: list[tuple[str, str]]
) -> Path:
    """Escribe en `destino_dir` una copia del archivo con el texto y el nombre reemplazados."""
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / _nombre_destino(origen.name, reemplazos)
    texto = origen.read_text(encoding="utf-8")
    destino.write_text(_reemplazar(texto, reemplazos), encoding="utf-8", newline="")
    return destino


def _filas_numericas(ruta: Path) -> list[tuple[str, ...]]:
    """Valores de las columnas de medición de un CSV, tal como están escritos (sin convertir)."""
    with ruta.open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        columnas = [c for c in COLUMNAS_NUMERICAS if c in (lector.fieldnames or [])]
        return [tuple(fila[c] for c in columnas) for fila in lector]


def verificar_mediciones(origen: Path, destino: Path) -> bool:
    """True si las columnas de medición (instante, potencias, energía) son idénticas fila por fila."""
    return _filas_numericas(origen) == _filas_numericas(destino)


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seudonimiza el nombre de la empresa y los medidores. No toca instantes ni potencias."
    )
    parser.add_argument("entrada", type=Path, help="Un archivo o una carpeta con archivos de texto")
    parser.add_argument(
        "--salida", type=Path, required=True, help="Carpeta de salida (fuera de git)"
    )
    parser.add_argument(
        "--config", type=Path, required=True, help="JSON con medidores y empresa (fuera del repo)"
    )
    return parser


def _archivos(entrada: Path) -> list[Path]:
    if entrada.is_file():
        return [entrada]
    return sorted(
        p for p in entrada.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONES_TEXTO
    )


def ejecutar(parsed: argparse.Namespace) -> int:
    if not parsed.entrada.exists():
        raise ErrorSeudonimizacion(CODIGO_ARGUMENTOS, "La entrada no existe.")
    if esta_dentro_de_repo_git(parsed.salida):
        raise ErrorSeudonimizacion(
            CODIGO_ARGUMENTOS, "La salida está dentro de un repositorio git: no se escribe ahí."
        )
    if parsed.salida.resolve() == parsed.entrada.resolve():
        raise ErrorSeudonimizacion(CODIGO_ARGUMENTOS, "La salida no puede ser la entrada.")

    medidores, patron, reemplazo = cargar_configuracion(parsed.config)
    reemplazos = [(original, nuevo) for original, nuevo in medidores.items()] + [
        (patron, reemplazo)
    ]
    archivos = _archivos(parsed.entrada)
    if not archivos:
        raise ErrorSeudonimizacion(CODIGO_ARGUMENTOS, "No hay archivos de texto para seudonimizar.")

    escritos = [seudonimizar_archivo(a, parsed.salida, reemplazos) for a in archivos]
    csv_pares = [
        (origen, destino)
        for origen, destino in zip(archivos, escritos, strict=True)
        if origen.suffix.lower() == ".csv"
    ]
    if not all(verificar_mediciones(o, d) for o, d in csv_pares):
        raise ErrorSeudonimizacion(
            CODIGO_VERIFICACION, "La verificación falló: cambiaron instantes o potencias."
        )
    logger.info(
        "Seudonimizados %d archivos; %d CSV verificados (instantes y potencias idénticos).",
        len(escritos),
        len(csv_pares),
    )
    return CODIGO_OK


def main(args: list[str] | None = None) -> int:
    parsed = _construir_parser().parse_args(args)
    try:
        return ejecutar(parsed)
    except ErrorSeudonimizacion as error:
        logger.error("%s", error)
        return error.codigo
