"""src/infrastructure/cli/descargar_datos_estudiantes.py — Descarga de datasets didácticos para ISFT 199."""

import argparse
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from src.infrastructure.settings.logger import logger

CODIGO_OK = 0
CODIGO_ERROR_PARAMETROS = 2
CODIGO_ERROR_RED = 3

BASE_URL_DEFAULT = "https://api.datamaq.com.ar/static/isft199"
ARCHIVOS_DATASET: tuple[str, ...] = ("t1.csv", "t2.csv")


def descargar_archivo(url: str, destino: Path, timeout: float = 15.0) -> bool:
    """Descarga un archivo remoto y lo persiste en destino."""
    logger.info("Descargando %s...", url)
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "DataMaq-ISFT199-Fetcher/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as respuesta:
            if respuesta.status != 200:
                logger.error("Error HTTP %d al descargar %s", respuesta.status, url)
                return False
            contenido = respuesta.read().decode("utf-8")

        # Validación mínima de cabecera tabular
        primera_linea = contenido.splitlines()[0] if contenido else ""
        if "instante" not in primera_linea or "potencia_kw" not in primera_linea:
            logger.error("El contenido descargado de %s no tiene formato tabular válido", url)
            return False

        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
        logger.info("Archivo guardado en %s (%d bytes)", destino, len(contenido.encode("utf-8")))
        return True
    except urllib.error.URLError as err:
        logger.error("Fallo de conexión al descargar %s: %s", url, err)
        return False
    except Exception as exc:
        logger.error("Error inesperado al guardar %s: %s", destino, exc)
        return False


def sincronizar_datasets(base_url: str, carpeta_destino: Path, timeout: float = 15.0) -> int:
    """Descarga todos los datasets didácticos a la carpeta de destino."""
    exitos = 0
    base = base_url.rstrip("/")

    for nombre in ARCHIVOS_DATASET:
        url = f"{base}/{nombre}"
        destino = carpeta_destino / nombre
        if descargar_archivo(url, destino, timeout=timeout):
            exitos += 1

    return exitos


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Descarga los datasets didácticos anonimizados (t1.csv y t2.csv) para ISFT 199."
    )
    parser.add_argument(
        "--destino",
        type=Path,
        default=Path("data/input"),
        help="Carpeta destino para los archivos CSV (por defecto: data/input)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=BASE_URL_DEFAULT,
        help=f"URL base de distribución estática (por defecto: {BASE_URL_DEFAULT})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Tiempo de espera en segundos para la descarga (por defecto: 15s)",
    )
    return parser


def main(args: Sequence[str] | None = None) -> int:
    parser = _construir_parser()
    parsed = parser.parse_args(args)

    destino = parsed.destino.resolve()
    logger.info("Iniciando sincronización de datasets hacia %s", destino)

    exitos = sincronizar_datasets(parsed.base_url, destino, timeout=parsed.timeout)
    if exitos == len(ARCHIVOS_DATASET):
        logger.info(
            "Todos los datasets (%d/%d) fueron descargados con éxito.",
            exitos,
            len(ARCHIVOS_DATASET),
        )
        return CODIGO_OK

    logger.error("Solo se pudieron descargar %d de %d datasets.", exitos, len(ARCHIVOS_DATASET))
    return CODIGO_ERROR_RED


if __name__ == "__main__":
    sys.exit(main())
