"""src/infrastructure/cli/validar_dia_real.py — Valida la desagregación de un día sin verdad de terreno.

Uso:
    python scripts/validar_dia_real.py --archivo <CSV diario> --firmas <catálogo.json> \\
        --fecha 2026-09-20 --salida-json <ruta.json>

Escribe solo agregados (conteos, energías, porcentajes y horas por carga). No escribe filas de
mediciones: la salida es segura para compartir si el CSV de entrada no lo es.

Día: --fecha es un día de Argentina (America/Argentina/Buenos_Aires), con la misma ventana UTC que
el batch. Formato del CSV y del catálogo: ver el README (desagregación batch).

Códigos de salida: 0 ok; 2 argumentos o catálogo inválidos; 3 CSV ausente o inválido.
"""

import argparse
import json
from datetime import date
from pathlib import Path

from src.application.cargas.dtos.desagregar_cargas import FirmaConfirmadaDTO
from src.application.cargas.use_cases.validar_desagregacion import (
    UMBRAL_HUECOS_CALIDAD,
    ValidarDesagregacionDiaUseCase,
)
from src.infrastructure.cli.desagregar_cargas import ventana_utc_del_dia
from src.infrastructure.csv.medicion_repository import CsvMedicionRepository
from src.infrastructure.settings.logger import logger

CODIGO_OK = 0
CODIGO_ARGUMENTOS = 2
CODIGO_DATOS = 3


def _fecha_local(texto: str) -> date:
    return date.fromisoformat(texto)


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Métricas de la desagregación de un día, sin verdad de terreno (solo agregados)."
    )
    parser.add_argument("--archivo", type=Path, required=True, help="CSV diario del medidor")
    parser.add_argument("--firmas", type=Path, required=True, help="Catálogo JSON de firmas")
    parser.add_argument("--fecha", type=_fecha_local, required=True, help="Día local (YYYY-MM-DD)")
    parser.add_argument(
        "--salida-json", type=Path, required=True, help="Dónde escribir las métricas"
    )
    parser.add_argument(
        "--umbral-huecos",
        type=int,
        default=UMBRAL_HUECOS_CALIDAD,
        help="huecos de muestreo (>5 min) por día a partir de los que el día es de calidad baja",
    )
    return parser


def _cargar_firmas(ruta: Path) -> list[FirmaConfirmadaDTO]:
    if not ruta.exists():
        raise ValueError(f"El catálogo de firmas no existe: {ruta}")
    firmas = [FirmaConfirmadaDTO(**item) for item in json.loads(ruta.read_text(encoding="utf-8"))]
    if not firmas:
        raise ValueError("El catálogo de firmas está vacío.")
    return firmas


def main(args: list[str] | None = None) -> int:
    parsed = _construir_parser().parse_args(args)
    try:
        firmas = _cargar_firmas(parsed.firmas)
    except (ValueError, TypeError) as error:
        logger.error("Catálogo de firmas inválido: %s", error)
        return CODIGO_ARGUMENTOS

    if not parsed.archivo.exists():
        logger.error("No existe el CSV del día: %s", parsed.archivo)
        return CODIGO_DATOS
    desde, hasta = ventana_utc_del_dia(parsed.fecha)
    try:
        mediciones = CsvMedicionRepository(parsed.archivo.parent).leer_archivo(
            parsed.archivo, desde, hasta
        )
    except (ValueError, KeyError) as error:
        logger.error("CSV inválido (%s): %s", parsed.archivo, error)
        return CODIGO_DATOS

    metricas = ValidarDesagregacionDiaUseCase(umbral_huecos_calidad=parsed.umbral_huecos).ejecutar(
        mediciones, firmas, desde, hasta
    )
    parsed.salida_json.parent.mkdir(parents=True, exist_ok=True)
    parsed.salida_json.write_text(metricas.model_dump_json(indent=2) + "\n", encoding="utf-8")
    logger.info(
        "Validación del día %s: %d eventos, %d sin atribuir, %.1f %% de energía atribuida",
        parsed.fecha,
        metricas.eventos,
        metricas.eventos_sin_atribuir,
        metricas.pct_energia_atribuida,
    )
    return CODIGO_OK


if __name__ == "__main__":
    import sys

    sys.exit(main())
