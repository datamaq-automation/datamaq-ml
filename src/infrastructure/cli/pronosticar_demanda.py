"""src/infrastructure/cli/pronosticar_demanda.py — CLI de pronóstico de demanda con partición temporal.

Uso:
    ./run.sh forecast                       # usa serie sintética por defecto
    ./run.sh forecast --corte 0.8           # 80 % para entrenamiento temporal
"""

import argparse
from pathlib import Path

from src.application.cargas.use_cases.pronosticar_demanda import (
    PronosticarDemandaUseCase,
    ResultadoPronosticoDTO,
)
from src.infrastructure.settings.logger import logger

SERIE_DEFECTO = [100.0, 104.0, 99.0, 105.0, 101.0, 107.0, 102.0, 108.0, 104.0, 110.0]


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Entrena y evalúa pronósticos de demanda eléctrica con partición temporal estricta."
    )
    parser.add_argument(
        "--corte",
        type=float,
        default=0.7,
        help="Fracción de la serie para entrenamiento (por defecto: 0.7)",
    )
    parser.add_argument(
        "--archivo",
        type=Path,
        default=None,
        help="Ruta a CSV de telemetría o serie numérica (opcional)",
    )
    return parser.parse_args()


def cargar_serie(archivo: Path | None) -> list[float]:
    """Carga serie numérica desde archivo o retorna serie sintética por defecto."""
    if not archivo or not archivo.exists():
        return list(SERIE_DEFECTO)
    try:
        lineas = archivo.read_text(encoding="utf-8").strip().splitlines()
        valores: list[float] = []
        for lin in lineas:
            for p in lin.split(","):
                try:
                    valores.append(float(p.strip()))
                except ValueError:
                    continue
        if len(valores) >= 3:
            return valores
    except Exception as e:
        logger.warning("Error leyendo %s: %s. Usando serie por defecto.", archivo, e)
    return list(SERIE_DEFECTO)


def reportar_metricas(resultado: ResultadoPronosticoDTO, n: int, corte: float) -> None:
    """Emite por logger el reporte estructurado de pronóstico y evaluación de sesgo."""
    n_train = max(1, min(n - 1, int(n * corte)))
    n_test = n - n_train
    logger.info("Total obs: %d | Train: %d | Test: %d", n, n_train, n_test)
    for clave, met in resultado.modelos.items():
        logger.info(
            "Modelo %-15s | MAE: %6.2f kWh | RMSE: %6.2f kWh",
            clave,
            float(met["mae"]),
            float(met["rmse"]),
        )
    sesgo = resultado.comparacion_sesgo
    logger.info(
        "Sesgo data leakage: MAE temporal = %.2f kWh vs MAE aleatorio = %.2f kWh",
        sesgo["mae_temporal"],
        sesgo["mae_aleatoria"],
    )


def main() -> None:
    args = leer_argumentos()
    serie = cargar_serie(args.archivo)
    caso_uso = PronosticarDemandaUseCase(corte_entrenamiento=args.corte)
    resultado = caso_uso.ejecutar(serie)
    reportar_metricas(resultado, len(serie), args.corte)


if __name__ == "__main__":
    main()
