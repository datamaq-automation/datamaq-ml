"""src/infrastructure/cli/comparar_placas.py — Compara el catálogo por placa con los modos que descubrió train.

Uso:
    python -m src.infrastructure.cli.comparar_placas --placas <catalogo_placas.csv> \\
        --cargas <cargas_<medidor>.csv> [--tolerancia-kw 5] [--salida-json <ruta.json>]

Por motor dice si train encontró un modo en su potencia (o en sus escalones de arranque), y si la relación
ΔQ/ΔP del modo coincide con la que esperan su cos φ y su forma de arranque. Los logs dan solo conteos; el
detalle por motor va al JSON de salida.

Códigos de salida: 0 ok; 2 archivos ausentes o inválidos.
"""

import argparse
import csv
import dataclasses
import json
from collections import Counter
from pathlib import Path

from src.application.cargas.use_cases.sembrar_firmas import sembrar_firmas
from src.domain.cargas.catalogo_placa import (
    TOLERANCIA_POTENCIA_KW,
    ModoObservado,
    comparar_con_modos,
    firma_esperada,
)
from src.infrastructure.csv.catalogo_placa_repository import leer_catalogo_placa
from src.infrastructure.settings.logger import logger

CODIGO_OK = 0
CODIGO_ARGUMENTOS = 2


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compara el catálogo por placa con los modos de train."
    )
    parser.add_argument("--placas", type=Path, required=True, help="catálogo por placa (CSV)")
    parser.add_argument("--cargas", type=Path, required=True, help="cargas_<medidor>.csv de train")
    parser.add_argument("--tolerancia-kw", type=float, default=TOLERANCIA_POTENCIA_KW)
    parser.add_argument("--salida-json", type=Path, default=None)
    parser.add_argument(
        "--salida-firmas",
        type=Path,
        default=None,
        help="siembra las firmas candidatas (catálogo para el batch, sin confirmar)",
    )
    return parser


def _modos(ruta: Path) -> list[ModoObservado]:
    if not ruta.exists():
        raise ValueError(f"no existe: {ruta}")
    with ruta.open(encoding="utf-8", newline="") as archivo:
        return [
            ModoObservado(
                centro_kw=float(fila["potencia_tipica_kw"]),
                ratio_qp=float(fila["ratio_qp_mediana"]) if fila.get("ratio_qp_mediana") else None,
            )
            for fila in csv.DictReader(archivo)
        ]


def main(args: list[str] | None = None) -> int:
    parsed = _construir_parser().parse_args(args)
    try:
        placas = leer_catalogo_placa(parsed.placas)
        modos = _modos(parsed.cargas)
    except (OSError, ValueError, KeyError) as error:
        logger.error("No se pudo comparar: %s", error)
        return CODIGO_ARGUMENTOS
    firmas = [firma_esperada(p) for p in placas]
    comparaciones = comparar_con_modos(firmas, modos, tolerancia_kw=parsed.tolerancia_kw)
    conteo = Counter(c.estado for c in comparaciones)
    logger.info(
        "Motores: %d · coinciden %d · forma distinta %d · sin modo %d · sin escalón %d",
        len(comparaciones), conteo["coincide"], conteo["coincide_forma_distinta"],
        conteo["sin_modo"], conteo["sin_escalon"],
    )  # fmt: skip
    if parsed.salida_firmas is not None:
        sembradas = sembrar_firmas(placas)
        parsed.salida_firmas.parent.mkdir(parents=True, exist_ok=True)
        datos = [f.model_dump(mode="json") for f in sembradas]
        parsed.salida_firmas.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        logger.info("Firmas sembradas: %d (las formas sin escalón no se siembran)", len(sembradas))
    if parsed.salida_json is not None:
        parsed.salida_json.parent.mkdir(parents=True, exist_ok=True)
        detalle = [
            {**dataclasses.asdict(c), "nota": f.nota, "forma_arranque": p.forma_arranque}
            for c, f, p in zip(comparaciones, firmas, placas, strict=True)
        ]
        parsed.salida_json.write_text(
            json.dumps(detalle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return CODIGO_OK


if __name__ == "__main__":
    import sys

    sys.exit(main())
