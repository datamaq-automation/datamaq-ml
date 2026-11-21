"""src/infrastructure/cli/desagregar_cargas.py — Ejecución batch de desagregación de cargas y cálculo de horómetros.

Uso (el nombre del medidor es exacto, con espacio: "Trafo arriba"):
    ./run.sh disaggregate "Trafo arriba" --fecha 2026-09-20 --firmas config/firmas.json
    ./run.sh disaggregate "Trafo arriba" --fecha 2026-09-20 --potencia 91.0 --nombre "Compresor 1"
"""

import argparse
import json
from datetime import date, datetime, time
from pathlib import Path

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    FirmaConfirmadaDTO,
)
from src.application.cargas.use_cases.atribuir_cargas_batch import (
    AtribuirCargasBatchUseCase,
)
from src.infrastructure.mediciones_factory import get_mediciones
from src.infrastructure.settings.config import get_settings
from src.infrastructure.settings.logger import logger


def _cargar_firmas(
    archivo_firmas: Path | None,
    potencia: float | None,
    reactiva: float | None,
    nombre: str | None,
    machine_id: str | None,
) -> list[FirmaConfirmadaDTO]:
    firmas: list[FirmaConfirmadaDTO] = []
    if archivo_firmas and archivo_firmas.exists():
        contenido = json.loads(archivo_firmas.read_text(encoding="utf-8"))
        for item in contenido:
            firmas.append(FirmaConfirmadaDTO(**item))
    elif potencia is not None:
        firmas.append(
            FirmaConfirmadaDTO(
                machine_id=machine_id or "m-1",
                nombre=nombre or f"Carga {potencia} kW",
                potencia_nominal_kw=potencia,
                reactiva_tipica_kvar=reactiva or 0.0,
            )
        )
    return firmas


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Desagrega eventos y calcula horas de marcha efectivas por máquina para un día cerrado."
    )
    parser.add_argument("medidor", help="Nombre o identificador del medidor/dispositivo")
    parser.add_argument(
        "--fecha",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=date.today(),
        help="Fecha del día cerrado a desagregar (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--firmas",
        type=Path,
        default=None,
        help="Archivo JSON con catálogo de firmas confirmadas",
    )
    parser.add_argument(
        "--potencia",
        type=float,
        default=None,
        help="Potencia nominal (kW) para firma rápida por CLI",
    )
    parser.add_argument(
        "--reactiva",
        type=float,
        default=0.0,
        help="Potencia reactiva típica (kvar) para firma rápida por CLI",
    )
    parser.add_argument(
        "--nombre",
        type=str,
        default=None,
        help="Nombre de la máquina para firma rápida por CLI",
    )
    parser.add_argument(
        "--machine-id",
        type=str,
        default=None,
        help="ID de la máquina para firma rápida por CLI",
    )
    return parser


def main(args: list[str] | None = None) -> int:
    parser = _construir_parser()
    parsed = parser.parse_args(args)
    settings = get_settings()
    repo = get_mediciones(settings)

    desde = datetime.combine(parsed.fecha, time.min)
    hasta = datetime.combine(parsed.fecha, time.max)

    logger.info(
        "Iniciando desagregación batch para '%s' en fecha %s",
        parsed.medidor,
        parsed.fecha,
    )
    mediciones = repo.listar(parsed.medidor, desde=desde, hasta=hasta)
    logger.info("Mediciones leídas: %d", len(mediciones))

    firmas = _cargar_firmas(
        parsed.firmas,
        parsed.potencia,
        parsed.reactiva,
        parsed.nombre,
        parsed.machine_id,
    )

    resultado = AtribuirCargasBatchUseCase().ejecutar(
        AtribuirCargasBatchRequestDTO(
            dispositivo_id=parsed.medidor,
            fecha=parsed.fecha,
            mediciones=mediciones,
            firmas=firmas,
        )
    )

    logger.info("Desagregación completada. Intervalos asignados: %d", len(resultado.intervalos))
    for res in resultado.resumen_maquinas:
        logger.info(
            "Máquina '%s' (%s): %.2f h marcha, %d ciclos, %.2f kWh",
            res.nombre,
            res.machine_id,
            res.horas_marcha,
            res.ciclos,
            res.energia_kwh,
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
