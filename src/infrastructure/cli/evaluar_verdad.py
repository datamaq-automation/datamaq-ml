"""src/infrastructure/cli/evaluar_verdad.py — Evalúa la salida inferida contra la verdad de terreno, por máquina.

Uso:
    python -m src.infrastructure.cli.evaluar_verdad --inferido <nilm.intervalos.v1.json> \\
        --verdad <nilm.verdad.v1.json> [--tolerancia-s 300] [--salida-json <ruta.json>]

Por máquina: precisión y sensibilidad por tiempo (minutos en marcha) y por eventos (arranques y paradas
emparejados a ±tolerancia), y el error de energía si la verdad trae energía. Las máquinas se emparejan por
nombre. Los logs dan solo conteos; el detalle va al JSON de salida.

Códigos de salida: 0 ok; 2 archivos ausentes o inválidos (no cumplen el contrato).
"""

import argparse
import dataclasses
import json
from pathlib import Path

from src.application.cargas.dtos.desagregar_cargas import AtribuirCargasBatchResponseDTO
from src.application.cargas.dtos.verdad_intervalos import VerdadIntervalosDTO
from src.application.cargas.use_cases.evaluar_contra_verdad import evaluar_contra_verdad
from src.domain.cargas.evaluacion_verdad import TOLERANCIA_EVENTO_S
from src.infrastructure.settings.logger import logger

CODIGO_OK = 0
CODIGO_ARGUMENTOS = 2


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evalúa la inferencia contra la verdad de terreno."
    )
    parser.add_argument(
        "--inferido", type=Path, required=True, help="salida del batch (nilm.intervalos.v1)"
    )
    parser.add_argument(
        "--verdad", type=Path, required=True, help="verdad por intervalos (nilm.verdad.v1)"
    )
    parser.add_argument(
        "--tolerancia-s",
        type=float,
        default=TOLERANCIA_EVENTO_S,
        help="tolerancia de emparejamiento de arranques y paradas, en segundos (por defecto: 300)",
    )
    parser.add_argument(
        "--salida-json", type=Path, default=None, help="escribe el detalle por máquina"
    )
    return parser


def main(args: list[str] | None = None) -> int:
    parsed = _construir_parser().parse_args(args)
    try:
        inferido = AtribuirCargasBatchResponseDTO.model_validate_json(
            parsed.inferido.read_text(encoding="utf-8")
        )
        verdad = VerdadIntervalosDTO.model_validate_json(parsed.verdad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        logger.error("No se pudo leer el contrato: %s", error)
        return CODIGO_ARGUMENTOS
    resultados = evaluar_contra_verdad(inferido, verdad, parsed.tolerancia_s)
    for r in resultados:
        logger.info(
            "Máquina %s: tiempo precisión %.2f sensibilidad %.2f; arranques %d de %d; paradas %d de %d",
            r.maquina, r.tiempo.precision, r.tiempo.sensibilidad,
            r.arranques.emparejados, r.arranques.verdaderos,
            r.paradas.emparejados, r.paradas.verdaderos,
        )  # fmt: skip
    if parsed.salida_json is not None:
        parsed.salida_json.parent.mkdir(parents=True, exist_ok=True)
        detalle = [dataclasses.asdict(r) for r in resultados]
        parsed.salida_json.write_text(
            json.dumps(detalle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return CODIGO_OK


if __name__ == "__main__":
    import sys

    sys.exit(main())
