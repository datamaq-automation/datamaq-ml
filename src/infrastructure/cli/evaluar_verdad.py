"""src/infrastructure/cli/evaluar_verdad.py — Evalúa la salida inferida contra la verdad de terreno, por máquina.

Uso:
    python -m src.infrastructure.cli.evaluar_verdad --inferido <nilm.intervalos.v1.json> \\
        --verdad <nilm.verdad.v1.json> [--tolerancia-s 300] [--salida-json <ruta.json>]

Por máquina: precisión y sensibilidad por tiempo (minutos en marcha) y por eventos (arranques y paradas
emparejados a ±tolerancia), y el error de energía si la verdad trae energía. Las máquinas se emparejan por
nombre. Los logs dan solo conteos; el detalle va al JSON de salida.

Calidad del día (bloque `calidad` de la verdad, opcional; sin él el día es OK):
- OK: se evalúa y cuenta en el resumen.
- DUDOSA: se evalúa y queda marcada; no cuenta en el resumen salvo `--incluir-dudosos`.
- NO_UTILIZABLE: se rechaza y no se evalúa, salvo `--incluir-no-utilizables`.
Los días excluidos se reportan con su motivo en el log.

Códigos de salida: 0 ok (también con días excluidos); 2 archivos ausentes o inválidos (no cumplen el contrato).
"""

import argparse
import dataclasses
import json
from pathlib import Path

from src.application.cargas.dtos.desagregar_cargas import AtribuirCargasBatchResponseDTO
from src.application.cargas.dtos.verdad_intervalos import VerdadIntervalosDTO
from src.application.cargas.use_cases.evaluar_contra_verdad import (
    EvaluacionDia,
    evaluar_dia,
    resumen_exclusiones,
)
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
    parser.add_argument(
        "--incluir-dudosos",
        action="store_true",
        help="cuenta los días DUDOSA en el resumen (por defecto quedan marcados y fuera)",
    )
    parser.add_argument(
        "--incluir-no-utilizables",
        action="store_true",
        help="evalúa los días NO_UTILIZABLE (por defecto se rechazan)",
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
    evaluacion = evaluar_dia(
        inferido,
        verdad,
        parsed.tolerancia_s,
        incluir_dudosos=parsed.incluir_dudosos,
        incluir_no_utilizables=parsed.incluir_no_utilizables,
    )
    _reportar_calidad(evaluacion)
    for r in evaluacion.resultados:
        logger.info(
            "Máquina %s: tiempo precisión %.2f sensibilidad %.2f; arranques %d de %d; paradas %d de %d",
            r.maquina, r.tiempo.precision, r.tiempo.sensibilidad,
            r.arranques.emparejados, r.arranques.verdaderos,
            r.paradas.emparejados, r.paradas.verdaderos,
        )  # fmt: skip
    if parsed.salida_json is not None:
        parsed.salida_json.parent.mkdir(parents=True, exist_ok=True)
        detalle = [_fila(r, evaluacion) for r in evaluacion.resultados]
        parsed.salida_json.write_text(
            json.dumps(detalle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return CODIGO_OK


def _reportar_calidad(evaluacion: EvaluacionDia) -> None:
    motivos = ", ".join(evaluacion.motivos)
    if not evaluacion.evaluado:
        logger.warning(
            "Día %s rechazado (%s). Para evaluarlo igual: --incluir-no-utilizables",
            evaluacion.estado,
            motivos,
        )
    elif evaluacion.estado == "DUDOSA":
        logger.warning(
            "Día DUDOSO (%s): evaluado y marcado. %s",
            motivos,
            "Cuenta en el resumen (--incluir-dudosos)."
            if evaluacion.en_resumen
            else "Fuera del resumen; --incluir-dudosos para contarlo.",
        )
    resumen = resumen_exclusiones([evaluacion])
    logger.info(
        "Días: %d; excluidos: %d; motivos de exclusión: %s",
        resumen["dias"],
        resumen["excluidos"],
        resumen["por_motivo"] or "ninguno",
    )


def _fila(resultado, evaluacion: EvaluacionDia) -> dict[str, object]:
    """Una fila del detalle: los campos de siempre más el estado de calidad del día (aditivo)."""
    return {
        **dataclasses.asdict(resultado),
        "calidad_dia": evaluacion.estado,
        "en_resumen": evaluacion.en_resumen,
    }


if __name__ == "__main__":
    import sys

    sys.exit(main())
