"""src/infrastructure/cli/exportar_repo_educativo.py — Extracción determinista de repositorio educativo sanitizado."""

import argparse
import json
import os
import re
import shutil
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from src.infrastructure.settings.logger import logger

CODIGO_OK = 0
CODIGO_ERROR_PARAMETROS = 2
CODIGO_VIOLACION_PRIVACIDAD = 3

DIRECTORIOS_EXCLUIDOS: set[str] = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov",
    "tmp",
    "prod-cache",
}

ARCHIVOS_EXCLUIDOS: set[str] = {
    ".env",
    ".env.local",
    "*.log",
    "diagnostico_privado_1.sh",
    "diagnostico_privado_2.sh",
    "validacion_privada.sh",
}

# Rutas relativas que deben excluirse por ser adaptadores privados a servidores o datos reales
RUTAS_EXCLUIDAS_PREFIJO: tuple[str, ...] = (
    "src/infrastructure/ssh",
    "src/infrastructure/cli/exportar_dias_ssh.py",
    "src/infrastructure/cli/exportar_repo_educativo.py",
    "scripts/exportar_repo_educativo.py",
    "tests/integration/test_ssh_medicion_repository.py",
    "tests/unit/test_exportar_dias_ssh.py",
    "tests/unit/test_exportar_repo_educativo.py",
    "tests/unit/test_mediciones_factory.py",
    "data/verdad",
    "data/prod-cache",
    "config/clientes_privados.json",
)

# Nombres privados a tapar: se leen de un archivo local no versionado (ver .gitignore). El ejemplo
# versionado, con nombres ficticios, está en config/clientes_privados.example.json.
RUTA_CLIENTES_POR_DEFECTO = Path("config/clientes_privados.json")

PATRON_IP_TAILSCALE = re.compile(r"\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def cargar_reemplazos(ruta: Path) -> dict[str, str]:
    """Lee el mapa {nombre privado: nombre genérico} del archivo de configuración local."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    reemplazos = datos.get("reemplazos") if isinstance(datos, dict) else None
    if not isinstance(reemplazos, dict) or not all(
        isinstance(k, str) and k.strip() and isinstance(v, str) for k, v in reemplazos.items()
    ):
        raise ValueError(f'{ruta}: se esperaba {{"reemplazos": {{"nombre": "genérico"}}}}')
    return dict(reemplazos)


def _patron_nombre(nombre: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(nombre)}\b", re.IGNORECASE)


def _es_directorio_excluido(partes: set[str]) -> bool:
    return bool(partes & DIRECTORIOS_EXCLUIDOS)


def _es_prefijo_excluido(ruta_rel: Path) -> bool:
    ruta_str = str(ruta_rel).replace(os.sep, "/")
    return any(ruta_str.startswith(prefijo) for prefijo in RUTAS_EXCLUIDAS_PREFIJO)


def _es_dataset_excluido(ruta_rel: Path) -> bool:
    if len(ruta_rel.parts) >= 2 and ruta_rel.parts[0] == "data" and ruta_rel.parts[1] == "input":
        nombre = ruta_rel.name
        return nombre.endswith(".csv") and nombre != "sintetico.csv"
    return False


def es_archivo_permitido(ruta_rel: Path) -> bool:
    """Determina si un archivo debe ser incluido en la extracción educativa."""
    if _es_directorio_excluido(set(ruta_rel.parts)):
        return False
    if _es_prefijo_excluido(ruta_rel):
        return False
    if _es_dataset_excluido(ruta_rel):
        return False
    if ruta_rel.name in ARCHIVOS_EXCLUIDOS or ruta_rel.name.endswith(".log"):
        return False
    return True


def escanear_patrones_prohibidos(contenido: str, reemplazos: Mapping[str, str]) -> list[str]:
    """Retorna las coincidencias de patrones prohibidos (nombres de cliente, IPs privadas)."""
    hallazgos: list[str] = []
    patrones = [_patron_nombre(nombre) for nombre in reemplazos] + [PATRON_IP_TAILSCALE]
    for patron in patrones:
        coincidencias = patron.findall(contenido)
        if coincidencias:
            hallazgos.extend(coincidencias)
    return hallazgos


def sanitizar_texto(texto: str, reemplazos: Mapping[str, str]) -> str:
    """Reemplaza identificadores privados conocidos por nombres genéricos de aula."""
    reemplazado = texto
    # Los nombres más largos primero, para que uno contenido en otro no lo corte a medias.
    for nombre in sorted(reemplazos, key=len, reverse=True):
        reemplazado = _patron_nombre(nombre).sub(reemplazos[nombre], reemplazado)
    return reemplazado


def exportar_arbol(
    origen: Path,
    destino: Path,
    reemplazos: Mapping[str, str],
    sobreescribir: bool = False,
) -> tuple[int, list[str]]:
    """Copia los archivos permitidos y sanitiza textos hacia el repositorio educativo."""
    if destino.exists():
        if not sobreescribir:
            raise FileExistsError(f"El directorio destino ya existe: {destino}")
        shutil.rmtree(destino)

    destino.mkdir(parents=True, exist_ok=True)
    copiados = 0
    advertencias_privacidad: list[str] = []

    for raiz, _, archivos in os.walk(origen):
        raiz_path = Path(raiz)
        for archivo in archivos:
            origen_archivo = raiz_path / archivo
            rel = origen_archivo.relative_to(origen)

            if not es_archivo_permitido(rel):
                continue

            destino_archivo = destino / rel
            destino_archivo.parent.mkdir(parents=True, exist_ok=True)

            # Para archivos de texto, sanitizar y auditar patrones
            es_texto = rel.suffix.lower() in {
                ".py",
                ".md",
                ".json",
                ".txt",
                ".sh",
                ".toml",
                ".yaml",
                ".yml",
            }
            if es_texto:
                try:
                    contenido = origen_archivo.read_text(encoding="utf-8")
                    contenido_limpio = sanitizar_texto(contenido, reemplazos)
                    restos = escanear_patrones_prohibidos(contenido_limpio, reemplazos)
                    if restos:
                        advertencias_privacidad.append(f"{rel}: patrones encontrados {set(restos)}")
                    destino_archivo.write_text(contenido_limpio, encoding="utf-8")
                except UnicodeDecodeError:
                    shutil.copy2(origen_archivo, destino_archivo)
            else:
                shutil.copy2(origen_archivo, destino_archivo)

            copiados += 1

    return copiados, advertencias_privacidad


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exporta una versión limpia del repositorio para uso educativo en ISFT 199."
    )
    parser.add_argument(
        "--origen",
        type=Path,
        default=Path("."),
        help="Directorio raíz del repositorio comercial (por defecto: actual)",
    )
    parser.add_argument(
        "--destino",
        type=Path,
        required=True,
        help="Directorio destino para el repositorio educativo limpio",
    )
    parser.add_argument(
        "--sobreescribir",
        action="store_true",
        help="Sobreescribe el directorio destino si ya existe",
    )
    parser.add_argument(
        "--clientes",
        type=Path,
        default=None,
        help=(
            "Archivo JSON local, no versionado, con los nombres privados a tapar "
            f"(por defecto: <origen>/{RUTA_CLIENTES_POR_DEFECTO})"
        ),
    )
    return parser


def main(args: Sequence[str] | None = None) -> int:
    parser = _construir_parser()
    parsed = parser.parse_args(args)

    origen = parsed.origen.resolve()
    destino = parsed.destino.resolve()

    if not origen.exists() or not origen.is_dir():
        logger.error("El directorio de origen no existe: %s", origen)
        return CODIGO_ERROR_PARAMETROS

    ruta_clientes = (parsed.clientes or origen / RUTA_CLIENTES_POR_DEFECTO).resolve()
    if not ruta_clientes.is_file():
        # Sin la lista no se puede tapar nada: exportar igual podría filtrar nombres de clientes.
        logger.error(
            "No existe el archivo de nombres privados: %s (copiar config/clientes_privados.example.json)",
            ruta_clientes,
        )
        return CODIGO_ERROR_PARAMETROS
    try:
        reemplazos = cargar_reemplazos(ruta_clientes)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("Archivo de nombres privados inválido: %s", exc)
        return CODIGO_ERROR_PARAMETROS

    logger.info("Iniciando exportación educativa desde %s hacia %s", origen, destino)
    try:
        copiados, advertencias = exportar_arbol(
            origen, destino, reemplazos, sobreescribir=parsed.sobreescribir
        )
        logger.info("Exportación completada con éxito. Archivos copiados: %d", copiados)
        if advertencias:
            for adv in advertencias:
                logger.warning("Auditoría de privacidad: %s", adv)
            return CODIGO_VIOLACION_PRIVACIDAD
        return CODIGO_OK
    except Exception as exc:
        logger.error("Error durante la exportación educativa: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
