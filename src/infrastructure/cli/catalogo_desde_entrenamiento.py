"""src/infrastructure/cli/catalogo_desde_entrenamiento.py — Catálogo de firmas a partir de lo que entrenó `train`.

Uso:
    python -m src.infrastructure.cli.catalogo_desde_entrenamiento \\
        --cargas <cargas_<medidor>.csv> --entrenamiento <entrenamiento_<medidor>.json> \\
        --salida <catalogo.json> [--tolerancia-kw 5.0]

Cada clúster del entrenamiento es una firma candidata: la potencia nominal es la típica del clúster, la
reactiva típica sale de la mediana de |ΔQ|/|ΔP| (la forma del equipo) por la potencia nominal, y la
dispersión es la del clúster. Si el entrenamiento marcó «sin modos separables», el catálogo queda vacío:
no hay cargas que atribuir y la validación lo mide así (no se inventan firmas).

Son candidatas, no firmas confirmadas: el catálogo de producción lo confirma el dueño.

Códigos de salida: 0 ok; 2 archivos ausentes o inválidos.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from src.infrastructure.settings.logger import logger

CODIGO_OK = 0
CODIGO_ARGUMENTOS = 2


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Catálogo de firmas candidatas a partir del entrenamiento (sin confirmar)."
    )
    parser.add_argument("--cargas", type=Path, required=True, help="cargas_<medidor>.csv de train")
    parser.add_argument(
        "--entrenamiento", type=Path, required=True, help="entrenamiento_<medidor>.json de train"
    )
    parser.add_argument("--salida", type=Path, required=True, help="Catálogo JSON a escribir")
    parser.add_argument(
        "--tolerancia-kw",
        type=float,
        default=5.0,
        help="tolerancia base de cada firma; la validación puede usar la de dispersión",
    )
    return parser


def _leer_json(ruta: Path) -> dict[str, Any]:
    if not ruta.exists():
        raise ValueError(f"No existe: {ruta}")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ValueError(f"Se esperaba un objeto JSON en {ruta}")
    return datos


def _firmas(cargas: Path, tolerancia_kw: float) -> list[dict[str, Any]]:
    if not cargas.exists():
        raise ValueError(f"No existe: {cargas}")
    with cargas.open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    etiqueta = cargas.stem.removeprefix("cargas_")
    firmas = []
    for i, fila in enumerate(filas, start=1):
        potencia = float(fila["potencia_tipica_kw"])
        ratio = fila.get("ratio_qp_mediana") or ""
        reactiva = round(float(ratio) * potencia, 2) if ratio else 0.0
        dispersion = fila.get("dispersion_kw") or ""
        firmas.append(
            {
                "machine_id": f"{etiqueta}-{i}",
                "nombre": f"{etiqueta} carga {i}",
                "potencia_nominal_kw": potencia,
                "reactiva_tipica_kvar": reactiva,
                "tolerancia_kw": tolerancia_kw,
                "umbral_marcha_kw": 1.0,
                "dispersion_kw": float(dispersion) if dispersion else None,
            }
        )
    return firmas


def main(args: list[str] | None = None) -> int:
    parsed = _construir_parser().parse_args(args)
    try:
        entrenamiento = _leer_json(parsed.entrenamiento)
        firmas = (
            []
            if entrenamiento.get("sin_modos_separables")
            else _firmas(parsed.cargas, parsed.tolerancia_kw)
        )
    except (ValueError, KeyError, TypeError) as error:
        logger.error("No se pudo armar el catálogo: %s", error)
        return CODIGO_ARGUMENTOS
    parsed.salida.parent.mkdir(parents=True, exist_ok=True)
    parsed.salida.write_text(
        json.dumps(firmas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not firmas:
        logger.info("Régimen sin modos separables: catálogo vacío (no hay cargas que atribuir)")
    else:
        logger.info("Catálogo con %d firmas candidatas", len(firmas))
    return CODIGO_OK


if __name__ == "__main__":
    import sys

    sys.exit(main())
