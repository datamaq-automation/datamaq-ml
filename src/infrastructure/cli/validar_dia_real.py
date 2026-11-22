"""src/infrastructure/cli/validar_dia_real.py — Valida la desagregación de un día sin verdad de terreno.

Uso:
    python -m src.infrastructure.cli.validar_dia_real --archivo <CSV diario> --firmas <catálogo.json> \\
        --fecha 2026-09-20 --salida-json <ruta.json> [--entrenamiento <entrenamiento.json>] \\
        [--tolerancia-por-dispersion [--tolerancia-max-kw 25]]

Escribe solo agregados (conteos, energías, porcentajes y horas por carga). No escribe filas de
mediciones: la salida es segura para compartir si el CSV de entrada no lo es.

Día: --fecha es un día de Argentina (America/Argentina/Buenos_Aires), con la misma ventana UTC que
el batch. Formato del CSV y del catálogo: ver el README (desagregación batch).

Con --entrenamiento (el JSON que escribe `train`), la validación usa el mismo umbral de detección que
el entrenamiento y respeta el régimen: si el entrenamiento marcó «sin modos separables», no hay firmas
que usar y el día se mide sin atribuir. Sin esa opción, el umbral es el mínimo del catálogo (como antes).

Códigos de salida: 0 ok; 2 argumentos, catálogo o entrenamiento inválidos; 3 CSV ausente o inválido.
"""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from src.application.cargas.dtos.desagregar_cargas import FirmaConfirmadaDTO, ParametrosMotorDTO
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
        "--entrenamiento",
        type=Path,
        default=None,
        help="entrenamiento_<medidor>.json de train: fija el umbral y el régimen",
    )
    parser.add_argument(
        "--umbral-huecos",
        type=int,
        default=UMBRAL_HUECOS_CALIDAD,
        help="huecos de muestreo (>5 min) por día a partir de los que el día es de calidad baja",
    )
    parser.add_argument(
        "--tolerancia-por-dispersion",
        action="store_true",
        help="la tolerancia de cada firma sale de su dispersión (factor × σ, acotada)",
    )
    parser.add_argument("--factor-dispersion", type=float, default=2.0)
    parser.add_argument("--tolerancia-min-kw", type=float, default=2.0)
    parser.add_argument(
        "--tolerancia-max-kw",
        type=float,
        default=8.0,
        help="tope de la tolerancia por dispersión (un modo ancho, como 77 a 110 kW, necesita más)",
    )
    return parser


def _cargar_entrenamiento(ruta: Path) -> dict[str, Any]:
    if not ruta.exists():
        raise ValueError(f"El entrenamiento no existe: {ruta}")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ValueError("El entrenamiento debe ser un objeto JSON.")
    return datos


def _cargar_firmas(ruta: Path, permitir_vacio: bool) -> list[FirmaConfirmadaDTO]:
    if not ruta.exists():
        raise ValueError(f"El catálogo de firmas no existe: {ruta}")
    firmas = [FirmaConfirmadaDTO(**item) for item in json.loads(ruta.read_text(encoding="utf-8"))]
    if not firmas and not permitir_vacio:
        raise ValueError("El catálogo de firmas está vacío.")
    return firmas


def _umbral_y_regimen(entrenamiento: dict[str, Any] | None) -> tuple[float | None, bool]:
    if entrenamiento is None:
        return None, False
    umbral = entrenamiento.get("umbral_kw")
    return (float(umbral) if umbral is not None else None), bool(
        entrenamiento.get("sin_modos_separables")
    )


def main(args: list[str] | None = None) -> int:
    parsed = _construir_parser().parse_args(args)
    try:
        entrenamiento = (
            _cargar_entrenamiento(parsed.entrenamiento) if parsed.entrenamiento else None
        )
        umbral_kw, sin_modos = _umbral_y_regimen(entrenamiento)
        firmas = _cargar_firmas(parsed.firmas, permitir_vacio=sin_modos)
    except (ValueError, TypeError) as error:
        logger.error("Catálogo o entrenamiento inválido: %s", error)
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

    motor = ParametrosMotorDTO(
        tolerancia_por_dispersion=parsed.tolerancia_por_dispersion,
        factor_dispersion=parsed.factor_dispersion,
        tolerancia_min_kw=parsed.tolerancia_min_kw,
        tolerancia_max_kw=parsed.tolerancia_max_kw,
    )
    metricas = ValidarDesagregacionDiaUseCase(umbral_huecos_calidad=parsed.umbral_huecos).ejecutar(
        mediciones, firmas, desde, hasta, umbral_kw=umbral_kw, motor=motor, sin_modos=sin_modos
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
