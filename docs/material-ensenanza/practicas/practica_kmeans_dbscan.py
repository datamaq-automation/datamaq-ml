"""Práctica: k-medias frente a DBSCAN sobre los mismos escalones de potencia.

Uso (desde la raíz del repo, con el Python del venv; por defecto usa el tablero sintético):
    ./.venv/bin/python docs/material-ensenanza/practicas/practica_kmeans_dbscan.py
    ./.venv/bin/python docs/material-ensenanza/practicas/practica_kmeans_dbscan.py \\
        --csv data/input/sintetico.csv --k 4 --eps 8 --min-muestras 5

Qué hace:
1. Lee las mediciones del CSV y detecta los escalones |ΔP| con el umbral de Otsu.
2. Agrupa esos mismos valores con k-medias (k fijo) y con DBSCAN (radio y mínimo).
3. Muestra, para cada algoritmo: cuántos grupos encontró, cuántos valores quedaron sin grupo y la silueta.

Preguntas para pensar después de correrla: en la pregunta 1 del ejercicio E7 de `ejercicios.md`.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from src.domain.cargas.services import detectar_eventos, estimar_radio, estimar_umbral  # noqa: E402
from src.infrastructure.csv.medicion_repository import CsvMedicionRepository  # noqa: E402
from src.infrastructure.sklearn.comparacion_agrupadores import (  # noqa: E402
    ResultadoAgrupamiento,
    agrupar_dbscan,
    agrupar_kmeans,
)


def _mostrar(res: ResultadoAgrupamiento, total: int) -> None:
    silueta = "no definida (menos de 2 grupos)" if res.silueta is None else f"{res.silueta:.3f}"
    print(
        f"  {res.algoritmo:9s}: grupos={res.grupos:2d}  sin grupo={res.ruido:4d} de {total}  silueta={silueta}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="k-medias frente a DBSCAN sobre los mismos escalones."
    )
    parser.add_argument("--csv", type=Path, default=RAIZ / "data" / "input" / "sintetico.csv")
    parser.add_argument("--k", type=int, default=3, help="Grupos para k-medias")
    parser.add_argument(
        "--eps", type=float, default=None, help="Radio de DBSCAN (kW); por defecto, automático"
    )
    parser.add_argument(
        "--min-muestras", type=int, default=5, help="Mínimo de escalones por grupo en DBSCAN"
    )
    args = parser.parse_args()

    repo = CsvMedicionRepository(args.csv.parent)
    mediciones = repo.leer_archivo(args.csv, datetime.min, datetime.max)
    estimacion = estimar_umbral(mediciones)
    if estimacion is None:
        print("No hay suficientes escalones para estimar un umbral.")
        return 1
    eventos = detectar_eventos(mediciones, umbral_kw=estimacion.umbral_kw)
    valores = [abs(e.delta_kw) for e in eventos]
    if len(valores) < args.k:
        print(f"Hay {len(valores)} escalones; no alcanzan para {args.k} grupos.")
        return 1

    eps = args.eps if args.eps is not None else estimar_radio(eventos)
    if eps is None:
        print("No hay escalones para estimar el radio de DBSCAN.")
        return 1
    print(
        f"Umbral de Otsu: {estimacion.umbral_kw} kW · escalones: {len(valores)} · radio DBSCAN: {eps:.2f} kW"
    )
    _mostrar(agrupar_kmeans(valores, k=args.k), len(valores))
    _mostrar(agrupar_dbscan(valores, eps_kw=eps, min_samples=args.min_muestras), len(valores))
    return 0


if __name__ == "__main__":
    sys.exit(main())
