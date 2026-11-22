"""src/infrastructure/cli/entrenar_cargas.py — Identifica las cargas de data/input/*.csv y las guarda en data/output/.

Uso:
    ./run.sh train                                   # todos los medidores, todos los datos
    ./run.sh train planta_2_a                        # un medidor
    ./run.sh train planta_2_a --desde 2026-09-15 --hasta 2026-09-22
    ./run.sh train planta_2_b --umbral 60                # fija un parámetro (el resto sigue automático)
    ./run.sh train --help                                # todas las opciones
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.application.cargas.dtos.identificar_cargas import (
    CargaResponse,
    IdentificarCargasRequest,
    IdentificarCargasResponse,
)
from src.application.cargas.use_cases.identificar_cargas import IdentificarCargasUseCase
from src.domain.cargas.entities import Carga
from src.infrastructure.cli.presentacion import (
    error_que_ensena,
    imprimir_error,
    lineas_resumen_entrenamiento,
    mostrar,
)
from src.infrastructure.csv.carga_repository import CsvCargaRepository
from src.infrastructure.mediciones_factory import get_mediciones
from src.infrastructure.settings.config import describir_nilm, get_settings
from src.infrastructure.settings.logger import logger
from src.infrastructure.sklearn.dbscan_agrupador import DbscanAgrupador

TODO_EL_RANGO = (datetime(2000, 1, 1), datetime(2100, 1, 1))

# Códigos de salida, los mismos que validar_dia_real: 0 = terminó (incluso con advertencias),
# 2 = argumentos inválidos o medidor desconocido, 3 = datos faltantes o ilegibles.
CODIGO_OK = 0
CODIGO_ARGUMENTOS = 2
CODIGO_DATOS = 3

# Opción de la CLI → variable de Settings. Lo que se pasa por argumento tiene prioridad.
PARAMETROS_NILM = {
    "umbral": "NILM_UMBRAL_KW",
    "radio": "NILM_EPS_KW",
    "min_eventos": "NILM_MIN_EVENTOS",
    "separacion_minima": "NILM_SEPARACION_MINIMA",
    "balance_minimo": "NILM_BALANCE_MINIMO",
}


def _positivo(texto: str) -> float:
    valor = float(texto)
    if valor <= 0:
        raise argparse.ArgumentTypeError(f"tiene que ser mayor que 0 (recibido {texto})")
    return valor


def _entero_positivo(texto: str) -> int:
    valor = int(texto)
    if valor < 1:
        raise argparse.ArgumentTypeError(f"tiene que ser al menos 1 (recibido {texto})")
    return valor


def _proporcion(texto: str) -> float:
    valor = float(texto)
    if not 0 <= valor <= 1:
        raise argparse.ArgumentTypeError(f"tiene que estar entre 0 y 1 (recibido {texto})")
    return valor


def agregar_parametros_nilm(parser: argparse.ArgumentParser) -> None:
    """Opciones para fijar los parámetros NILM (las comparten train y evaluate)."""
    nilm = parser.add_argument_group(
        "parámetros NILM",
        "Sin estas opciones se usa config.py (umbral, radio y mínimo son automáticos). Criterios para elegirlos: docs/guia-docente.md, §6 y §7.",
    )
    nilm.add_argument(
        "--umbral", type=_positivo, metavar="KW", help="umbral |ΔP| fijo (por defecto: Otsu)"
    )
    nilm.add_argument(
        "--radio",
        type=_positivo,
        metavar="KW",
        help="radio de DBSCAN fijo (por defecto: F–D / 2 × ruido)",
    )
    nilm.add_argument(
        "--min-eventos",
        type=_entero_positivo,
        metavar="N",
        help="eventos mínimos por carga (por defecto: uno por día)",
    )
    nilm.add_argument(
        "--separacion-minima",
        type=_proporcion,
        metavar="η",
        help="η mínimo para confiar en el umbral (0 a 1)",
    )
    nilm.add_argument(
        "--balance-minimo",
        type=_proporcion,
        metavar="P",
        help="proporción ciclos/mayor para ser ON/OFF (0 a 1)",
    )


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Identifica cargas (NILM) en los CSV de data/input/."
    )
    parser.add_argument(
        "medidores", nargs="*", help="nombres de CSV sin extensión (por defecto: todos)"
    )
    parser.add_argument(
        "--desde", type=datetime.fromisoformat, default=TODO_EL_RANGO[0], help="ej. 2026-09-15"
    )
    parser.add_argument(
        "--hasta", type=datetime.fromisoformat, default=TODO_EL_RANGO[1], help="ej. 2026-09-22"
    )
    agregar_parametros_nilm(parser)
    return parser.parse_args()


def _carga(c: CargaResponse) -> Carga:
    return Carga(
        potencia_tipica_kw=c.potencia_tipica_kw,
        encendidos=c.encendidos,
        apagados=c.apagados,
        dispersion_kw=c.dispersion_kw,
        reactiva_tipica_kvar=c.reactiva_tipica_kvar,
        ratio_qp_mediana=c.ratio_qp_mediana,
    )


def _resumen_entrenamiento(r: IdentificarCargasResponse) -> dict[str, Any]:
    """Lo que la validación necesita para usar el mismo umbral y el mismo régimen."""
    return {
        "umbral_kw": r.umbral.kw,
        "separacion": r.umbral.separacion,
        "regimen": r.umbral.regimen,
        "sin_modos_separables": r.sin_modos_separables,
        "eventos": r.eventos,
        "radio_kw": r.agrupamiento.radio_kw,
        "modos": [m.model_dump() for m in r.modos],
    }


def _error_de_rango(args: argparse.Namespace) -> list[str] | None:
    if args.hasta <= args.desde:
        return error_que_ensena(
            "El rango de fechas está al revés.",
            f"--hasta ({args.hasta:%Y-%m-%d}) no es posterior a --desde ({args.desde:%Y-%m-%d}).",
            "poné --hasta después de --desde, por ejemplo --desde 2026-09-15 --hasta 2026-09-22.",
        )
    return None


def _error_de_medidores(
    args: argparse.Namespace, disponibles: list[str], entrada: Path
) -> int | None:
    """Código de salida si no hay mediciones o si piden un medidor que no existe; None si todo está bien."""
    if not disponibles:
        imprimir_error(
            error_que_ensena(
                f"No encuentro mediciones en {entrada}.",
                "el CLI lee un CSV por medidor en esa carpeta y no hay ninguno.",
                "generá datos de prueba con ./run.sh simulate, o copiá el CSV del medidor a esa "
                "carpeta.",
                "README.md, sección de datos",
            )
        )
        return CODIGO_DATOS
    desconocidos = [m for m in args.medidores if m not in disponibles]
    if desconocidos:
        imprimir_error(
            error_que_ensena(
                f"Medidor desconocido: {', '.join(desconocidos)}.",
                "el nombre tiene que coincidir con un CSV de la carpeta, sin la extensión .csv.",
                f"usá uno de estos: {', '.join(disponibles)}.",
            )
        )
        return CODIGO_ARGUMENTOS
    return None


def _entrenar_medidores(
    caso_de_uso: IdentificarCargasUseCase,
    resultados: CsvCargaRepository,
    medidores: list[str],
    args: argparse.Namespace,
) -> int:
    """Entrena cada medidor. Un CSV ilegible (valor no numérico, columna que falta) es un error de datos."""
    try:
        for medidor in medidores:
            r = caso_de_uso.execute(
                IdentificarCargasRequest(medidor=medidor, desde=args.desde, hasta=args.hasta)
            )
            resultados.guardar(medidor, [_carga(c) for c in r.cargas])
            resultados.guardar_entrenamiento(medidor, _resumen_entrenamiento(r))
            mostrar(lineas_resumen_entrenamiento(r, medidor))
    except (ValueError, KeyError) as error:
        imprimir_error(
            error_que_ensena(
                "No pude leer las mediciones.",
                f"el CSV tiene un dato que no se puede interpretar ({error}).",
                "revisá que las columnas sean instante y potencia_kw, y que la potencia sea un "
                "número.",
                "README.md, sección de datos",
            )
        )
        return CODIGO_DATOS
    return CODIGO_OK


def main() -> int:
    args = leer_argumentos()
    if (error := _error_de_rango(args)) is not None:
        imprimir_error(error)
        return CODIGO_ARGUMENTOS
    cambios = {
        var: getattr(args, opcion)
        for opcion, var in PARAMETROS_NILM.items()
        if getattr(args, opcion) is not None
    }
    settings = get_settings().model_copy(update=cambios)
    entrada, salida = Path(settings.MEDICIONES_CSV_DIR), Path(settings.RESULTADOS_DIR)
    repositorio = get_mediciones(settings)
    resultados = CsvCargaRepository(salida)
    caso_de_uso = IdentificarCargasUseCase(
        mediciones=repositorio,
        agrupador=DbscanAgrupador(),
        umbral_kw=settings.NILM_UMBRAL_KW,
        logger=logger,
        balance_minimo=settings.NILM_BALANCE_MINIMO,
        separacion_minima=settings.NILM_SEPARACION_MINIMA,
        radio_kw=settings.NILM_EPS_KW,
        min_eventos=settings.NILM_MIN_EVENTOS,
    )
    disponibles = repositorio.medidores()
    if (error := _error_de_medidores(args, disponibles, entrada)) is not None:
        return error
    medidores = args.medidores or disponibles

    logger.info(describir_nilm(settings))
    logger.info(
        "Entrenando con %d de %d medidores de %s",
        len(medidores),
        len(disponibles),
        entrada,
    )
    return _entrenar_medidores(caso_de_uso, resultados, medidores, args)


if __name__ == "__main__":
    sys.exit(main())
