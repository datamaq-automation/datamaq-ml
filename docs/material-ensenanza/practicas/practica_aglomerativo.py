"""docs/material-ensenanza/practicas/practica_aglomerativo.py — Práctica: Agrupamiento aglomerativo jerárquico.

Compara métodos de enlace (single, complete, average, ward) sobre escalones de potencia |ΔP|
y evalúa el corte del dendrograma por número de clusters (k) o por umbral de distancia.

Uso:
    ./.venv/bin/python docs/material-ensenanza/practicas/practica_aglomerativo.py
    ./.venv/bin/python docs/material-ensenanza/practicas/practica_aglomerativo.py --k 3 --metodo complete
    ./.venv/bin/python docs/material-ensenanza/practicas/practica_aglomerativo.py --distancia 15.0 --metodo ward
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.domain.cargas.services import (  # noqa: E402
    detectar_eventos,
    estimar_umbral,
)
from src.infrastructure.csv.medicion_repository import (  # noqa: E402
    CsvMedicionRepository,
)
from src.infrastructure.sklearn.comparacion_agrupadores import (  # noqa: E402
    METODOS_ENLACE,
    ResultadoAgrupamiento,
    agrupar_aglomerativo,
)


def _mostrar(res: ResultadoAgrupamiento, total: int) -> None:
    silueta = "no definida (menos de 2 grupos)" if res.silueta is None else f"{res.silueta:.3f}"
    print(
        f"  {res.algoritmo:20s}: grupos={res.grupos:2d}  ruido={res.ruido:2d} de {total}  silueta={silueta}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agrupamiento aglomerativo jerárquico sobre escalones |ΔP|."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=RAIZ / "data" / "input" / "sintetico.csv",
        help="CSV con mediciones",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Número de grupos (corte por cantidad)",
    )
    parser.add_argument(
        "--distancia",
        type=float,
        default=None,
        help="Umbral de distancia para corte de dendrograma",
    )
    parser.add_argument(
        "--metodo",
        type=str,
        default="complete",
        choices=METODOS_ENLACE,
        help="Método de enlace (single, complete, average, ward)",
    )
    parser.add_argument(
        "--comparar-todos",
        action="store_true",
        help="Compara los 4 métodos de enlace simultáneamente",
    )
    args = parser.parse_args()

    repo = CsvMedicionRepository(args.csv.parent)
    mediciones = repo.leer_archivo(args.csv, datetime.min, datetime.max)
    estimacion = estimar_umbral(mediciones)
    if estimacion is None:
        print("No hay suficientes escalones para estimar umbral.")
        return 1

    eventos = detectar_eventos(mediciones, umbral_kw=estimacion.umbral_kw)
    valores = [abs(e.delta_kw) for e in eventos]
    if len(valores) < 3:
        print(f"Hay {len(valores)} escalones; no alcanzan para agrupar.")
        return 1

    print(
        f"Mediciones analizadas: {len(mediciones)} · Escalones detectados: {len(valores)} (umbral {estimacion.umbral_kw} kW)"
    )

    if args.comparar_todos:
        print(f"\nComparación de los 4 métodos de enlace cortando en k={args.k}:")
        for m in METODOS_ENLACE:
            res = agrupar_aglomerativo(valores, n_clusters=args.k, metodo=m)
            _mostrar(res, len(valores))
    else:
        criterio = f"k={args.k}" if args.distancia is None else f"distancia={args.distancia}"
        print(f"\nAgrupamiento aglomerativo con método '{args.metodo}' ({criterio}):")
        res = agrupar_aglomerativo(
            valores,
            n_clusters=args.k if args.distancia is None else None,
            distancia_corte=args.distancia,
            metodo=args.metodo,
        )
        _mostrar(res, len(valores))

    return 0


if __name__ == "__main__":
    sys.exit(main())
