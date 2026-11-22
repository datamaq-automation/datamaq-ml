"""src/infrastructure/cli/desagregar_cargas.py — Desagregación batch diaria (contrato nilm.intervalos.v1).

Uso (el nombre del medidor es una etiqueta; la clave es --device-id, uuid de devices.id en telemetry):
    ./run.sh disaggregate "Trafo arriba" --device-id a01b1642-ed29-4c3e-a793-f57de09504f8 \\
        --fecha 2026-11-21 --firmas config/firmas.json --salida-json salida/nilm_2026-11-21.json
    ./run.sh disaggregate "Trafo arriba" --device-id a01b1642-ed29-4c3e-a793-f57de09504f8 \\
        --potencia 91.0 --nombre "Compresor 1"

Día y zona: --fecha es un día de Argentina (America/Argentina/Buenos_Aires, UTC-3 sin horario de
verano). Si se omite, es el día anterior (D-1) en esa zona: el timer de las 03:30 UTC procesa
el día que ya cerró. El día D es la ventana UTC semiabierta [D 00:00 ART, D+1 00:00 ART), es decir
[D 03:00Z, D+1 03:00Z).

Entrada: un CSV por medidor y día con instante,potencia_kw,reactiva_kvar[,energia_kwh]. Por
defecto es <MEDICIONES_CSV_DIR>/<device-id>_<fecha>.csv; --archivo lo reemplaza. Este comando no
se conecta a MySQL ni al VPS.

Códigos de salida: 0 ok; 2 argumentos o catálogo de firmas inválidos; 3 archivo de mediciones
ausente o inválido.
"""

import argparse
import json
import uuid
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.application.cargas.dtos.desagregar_cargas import (
    ZONA_HORARIA_DIA,
    AtribuirCargasBatchRequestDTO,
    AtribuirCargasBatchResponseDTO,
    FirmaConfirmadaDTO,
)
from src.application.cargas.use_cases.atribuir_cargas_batch import (
    AtribuirCargasBatchUseCase,
)
from src.domain.cargas.entities import Medicion
from src.infrastructure.csv.medicion_repository import CsvMedicionRepository
from src.infrastructure.settings.config import get_settings
from src.infrastructure.settings.logger import logger

ZONA = ZoneInfo(ZONA_HORARIA_DIA)
CODIGO_OK = 0
CODIGO_ARGUMENTOS = 2
CODIGO_DATOS = 3


class ErrorCli(Exception):
    """Falla de uso o de datos: lleva el código de salida y el mensaje para el log."""

    def __init__(self, codigo: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def dia_local_anterior(ahora: datetime) -> date:
    """D-1 en la zona del día: el día anterior al que es en Argentina en el instante `ahora`.

    Un `ahora` sin zona se toma como UTC.
    """
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=UTC)
    return ahora.astimezone(ZONA).date() - timedelta(days=1)


def ventana_utc_del_dia(fecha_local: date) -> tuple[datetime, datetime]:
    """Ventana [desde, hasta) del día local en UTC, sin zona (el interno del batch es UTC)."""
    desde = datetime.combine(fecha_local, time.min, tzinfo=ZONA)
    hasta = datetime.combine(fecha_local + timedelta(days=1), time.min, tzinfo=ZONA)
    return (
        desde.astimezone(UTC).replace(tzinfo=None),
        hasta.astimezone(UTC).replace(tzinfo=None),
    )


def ruta_mediciones_por_defecto(carpeta: Path, device_id: str, fecha: date) -> Path:
    """Archivo diario de un medidor: <carpeta>/<device-id>_<YYYY-MM-DD>.csv."""
    return carpeta / f"{device_id}_{fecha.isoformat()}.csv"


def _fecha_local(texto: str) -> date:
    return datetime.strptime(texto, "%Y-%m-%d").date()


def _cargar_firmas(parsed: argparse.Namespace) -> list[FirmaConfirmadaDTO]:
    """Firmas del catálogo (--firmas) o la firma rápida (--potencia). Errores de uso son ErrorCli."""
    firmas: list[FirmaConfirmadaDTO] = []
    if parsed.firmas is not None:
        if not parsed.firmas.exists():
            raise ErrorCli(CODIGO_ARGUMENTOS, f"El catálogo de firmas no existe: {parsed.firmas}")
        try:
            for item in json.loads(parsed.firmas.read_text(encoding="utf-8")):
                firmas.append(FirmaConfirmadaDTO(**item))
        except (ValueError, TypeError) as error:
            raise ErrorCli(CODIGO_ARGUMENTOS, f"Catálogo de firmas inválido: {error}") from error
    elif parsed.potencia is not None:
        firmas.append(
            FirmaConfirmadaDTO(
                machine_id=parsed.machine_id or "m-1",
                nombre=parsed.nombre or f"Carga {parsed.potencia} kW",
                potencia_nominal_kw=parsed.potencia,
                reactiva_tipica_kvar=parsed.reactiva or 0.0,
            )
        )
    if not firmas:
        raise ErrorCli(
            CODIGO_ARGUMENTOS,
            "Indicá --firmas o --potencia: sin firmas no hay cargas que atribuir.",
        )
    return firmas


def _leer_mediciones(
    parsed: argparse.Namespace, fecha: date, desde: datetime, hasta: datetime
) -> list[Medicion]:
    """Mediciones del día desde el CSV diario del medidor (o --archivo). Errores de datos son ErrorCli."""
    archivo = parsed.archivo or ruta_mediciones_por_defecto(
        Path(get_settings().MEDICIONES_CSV_DIR), parsed.device_id, fecha
    )
    if not archivo.exists():
        raise ErrorCli(CODIGO_DATOS, f"No hay archivo de mediciones para el día {fecha}: {archivo}")
    try:
        return CsvMedicionRepository(archivo.parent).leer_archivo(archivo, desde, hasta)
    except (ValueError, KeyError) as error:
        raise ErrorCli(
            CODIGO_DATOS, f"Archivo de mediciones inválido ({archivo}): {error}"
        ) from error


def _registrar(resultado: AtribuirCargasBatchResponseDTO) -> None:
    intervalos = sum(len(c.intervalos) for c in resultado.cargas)
    logger.info("Desagregación completada. Intervalos asignados: %d", intervalos)
    for carga in resultado.cargas:
        logger.info(
            "Máquina '%s' (%s): %.2f h marcha, %d ciclos, %.2f kWh",
            carga.nombre,
            carga.load_id or "sin load_id",
            sum(it.horas for it in carga.intervalos),
            len(carga.intervalos),
            sum(it.energia_kwh_medida for it in carga.intervalos),
        )


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Desagrega cargas de un día cerrado y emite el contrato nilm.intervalos.v1."
    )
    parser.add_argument("medidor", help="Etiqueta humana del medidor (no identifica el medidor)")
    parser.add_argument(
        "--device-id",
        required=True,
        help="Clave del medidor: uuid de devices.id en telemetry",
    )
    parser.add_argument(
        "--fecha",
        type=_fecha_local,
        default=None,
        help="Día local a procesar (YYYY-MM-DD, Argentina). Por defecto: D-1",
    )
    parser.add_argument(
        "--archivo",
        type=Path,
        default=None,
        help="CSV diario del medidor. Por defecto: <MEDICIONES_CSV_DIR>/<device-id>_<fecha>.csv",
    )
    parser.add_argument(
        "--firmas",
        type=Path,
        default=None,
        help="Archivo JSON con el catálogo de firmas confirmadas",
    )
    parser.add_argument(
        "--potencia", type=float, default=None, help="Potencia nominal (kW) de una firma rápida"
    )
    parser.add_argument(
        "--reactiva", type=float, default=0.0, help="Reactiva típica (kVAr) de la firma rápida"
    )
    parser.add_argument("--nombre", type=str, default=None, help="Nombre de la firma rápida")
    parser.add_argument(
        "--machine-id", type=str, default=None, help="ID interno de la firma rápida"
    )
    parser.add_argument(
        "--salida-json",
        type=Path,
        default=None,
        help="Escribe el contrato nilm.intervalos.v1 en este archivo",
    )
    return parser


def _ejecutar(parsed: argparse.Namespace) -> int:
    try:
        uuid.UUID(parsed.device_id)
    except ValueError as error:
        raise ErrorCli(
            CODIGO_ARGUMENTOS, f"--device-id no es un uuid válido: {parsed.device_id}"
        ) from error

    firmas = _cargar_firmas(parsed)
    fecha = parsed.fecha or dia_local_anterior(datetime.now(UTC))
    desde, hasta = ventana_utc_del_dia(fecha)
    mediciones = _leer_mediciones(parsed, fecha, desde, hasta)

    logger.info(
        "Iniciando desagregación batch para '%s' (device %s) el día %s (UTC %s a %s)",
        parsed.medidor,
        parsed.device_id,
        fecha,
        desde,
        hasta,
    )
    logger.info("Mediciones leídas: %d", len(mediciones))

    resultado = AtribuirCargasBatchUseCase().ejecutar(
        AtribuirCargasBatchRequestDTO(
            device_id=parsed.device_id,
            etiqueta_ml=parsed.medidor,
            fecha_local=fecha,
            ventana_desde_utc=desde,
            ventana_hasta_utc=hasta,
            generado_en_utc=datetime.now(UTC).replace(tzinfo=None, microsecond=0),
            mediciones=mediciones,
            firmas=firmas,
        )
    )
    _registrar(resultado)

    if parsed.salida_json is not None:
        parsed.salida_json.parent.mkdir(parents=True, exist_ok=True)
        parsed.salida_json.write_text(resultado.model_dump_json(indent=2) + "\n", encoding="utf-8")
        logger.info("Salida nilm.intervalos.v1 escrita en %s", parsed.salida_json)
    return CODIGO_OK


def main(args: list[str] | None = None) -> int:
    parsed = _construir_parser().parse_args(args)
    try:
        return _ejecutar(parsed)
    except ErrorCli as error:
        logger.error("%s", error.mensaje)
        return error.codigo


if __name__ == "__main__":
    import sys

    sys.exit(main())
