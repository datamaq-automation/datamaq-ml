"""src/infrastructure/cli/simular_tablero.py — Genera un tablero simulado con cargas conocidas.

Uso:
    ./run.sh simulate                         # data/input/sintetico.csv + data/verdad/sintetico.csv
    ./run.sh simulate --semilla 7 --nombre otro
"""

import argparse
from datetime import datetime
from pathlib import Path

from src.application.cargas.use_cases.construir_verdad import construir_verdad_simulada
from src.domain.cargas.entities import CargaSimulada
from src.domain.cargas.simulacion import (
    BANCO_AUTOMATICO,
    BANCO_FIJO,
    simular_contactores,
    simular_tablero,
    simular_tablero_con_reactiva,
)
from src.infrastructure.csv.medicion_repository import CsvMedicionRepository
from src.infrastructure.csv.verdad_repository import CsvVerdadRepository
from src.infrastructure.settings.config import get_settings
from src.infrastructure.settings.logger import logger

# Tres equipos elegidos para enseñar: uno fácil (90 kW), uno más chico que el umbral típico (40 kW)
# y uno al nivel del ruido (15 kW = 5 veces el ruido de 3 kW).
CARGAS = [
    CargaSimulada(potencia_kw=90, ciclos_por_dia=18, duracion_min=25),
    CargaSimulada(potencia_kw=40, ciclos_por_dia=6, duracion_min=60),
    CargaSimulada(potencia_kw=15, ciclos_por_dia=30, duracion_min=10),
]
NOMBRES_MAQUINAS = ["Carga 90 kW", "Carga 40 kW", "Carga 15 kW"]
INICIO = datetime(2026, 9, 1)


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera un tablero simulado con cargas conocidas.")
    parser.add_argument(
        "--nombre", default="sintetico", help="nombre del medidor simulado (por defecto: sintetico)"
    )
    parser.add_argument("--dias", type=int, default=21, help="días a simular (por defecto: 21)")
    parser.add_argument(
        "--ruido",
        type=float,
        default=3.0,
        metavar="KW",
        help="desvío del ruido (por defecto: 3 kW)",
    )
    parser.add_argument(
        "--semilla", type=int, default=1, help="misma semilla, mismos datos (por defecto: 1)"
    )
    parser.add_argument(
        "--banco",
        choices=["ninguno", BANCO_FIJO, BANCO_AUTOMATICO],
        default="ninguno",
        help="banco de capacitores en paralelo: fijo, automático o ninguno (por defecto: ninguno, sin reactiva)",
    )
    parser.add_argument(
        "--verdad-json",
        default=None,
        help="escribe la verdad por intervalos de contactores (nilm.verdad.v1) en este archivo",
    )
    parser.add_argument(
        "--desfase-s",
        type=float,
        default=0.0,
        metavar="S",
        help="desfase de reloj del autómata respecto del medidor, en segundos (por defecto: 0)",
    )
    parser.add_argument(
        "--ruido-q",
        type=float,
        default=0.3,
        metavar="KVAR",
        help="desvío del ruido de reactiva, solo con --banco (por defecto: 0,3 kVAr)",
    )
    return parser.parse_args()


def main() -> None:
    args = leer_argumentos()
    settings = get_settings()
    descripcion = ", ".join(f"{c.potencia_kw:g} kW ({c.ciclos_por_dia:g}/día)" for c in CARGAS)
    logger.info(
        "Simulando %d días de %s con ruido de %s kW: %s",
        args.dias,
        args.nombre,
        args.ruido,
        descripcion,
    )
    if args.banco == "ninguno":
        mediciones, verdad = simular_tablero(CARGAS, args.dias, args.ruido, args.semilla, INICIO)
    else:
        mediciones, verdad = simular_tablero_con_reactiva(
            CARGAS, args.dias, args.ruido, args.ruido_q, args.semilla, INICIO, banco=args.banco
        )
    CsvMedicionRepository(Path(settings.MEDICIONES_CSV_DIR)).guardar(args.nombre, mediciones)
    CsvVerdadRepository(Path(settings.VERDAD_DIR)).guardar(args.nombre, verdad)
    if args.verdad_json:
        _escribir_verdad(args)


def _escribir_verdad(args: argparse.Namespace) -> None:
    tramos = simular_contactores(CARGAS, args.dias, args.semilla, INICIO, args.desfase_s)
    maquinas = [(n, c.potencia_kw) for n, c in zip(NOMBRES_MAQUINAS, CARGAS, strict=True)]
    verdad = construir_verdad_simulada(
        maquinas,
        tramos,
        INICIO,
        args.dias,
        args.desfase_s,
        etiqueta=args.nombre,
        device_id="simulado",
    )
    ruta = Path(args.verdad_json)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(verdad.model_dump_json(indent=2) + "\n", encoding="utf-8")
    logger.info(
        "Verdad por intervalos escrita: %d máquinas, desfase %s s", len(maquinas), args.desfase_s
    )


if __name__ == "__main__":
    main()
