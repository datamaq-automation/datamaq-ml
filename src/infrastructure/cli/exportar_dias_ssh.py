"""src/infrastructure/cli/exportar_dias_ssh.py — Exporta días de medidores desde la base del VPS, solo lectura.

Uso (lo ejecuta el dueño en su terminal; este comando no se corre contra producción desde el repo):
    ./.venv/bin/python scripts/exportar_dias_ssh.py \\
        --device-id <uuid-del-medidor> [--device-id <uuid-2>] \\
        --desde 2026-09-11 --hasta 2026-11-21 \\
        --salida-dir /ruta/fuera/de/git --tope-filas-dia 5000

Qué escribe: un archivo por medidor y día argentino, `<device-id>_<AAAA-MM-DD>.csv`, con las columnas
`instante,potencia_kw,reactiva_kvar,energia_kwh` (instantes UTC sin zona; potencias en kW y kVAr; energía
acumulada en kWh, vacía si el medidor no la tiene). Un día sin filas se escribe con solo la cabecera.

Garantías:
- Solo lectura: la consulta es un único SELECT (lo verifica el adaptador antes de conectarse).
- Solo datos confiables: `es_dato_confiable = 1` (el flag hoy casi siempre es verdadero; ver la adenda de telemetry).
- Ventana UTC del día argentino: [D 03:00Z, D+1 03:00Z).
- Tope de filas por día: si un día supera el tope, no se escribe y el comando sale con código 3.
- El directorio de salida debe estar fuera de todo repositorio git y tener permisos 700. Los archivos se crean con 600.
- Imprime solo conteos. No imprime valores ni instantes.

Códigos de salida: 0 ok; 2 argumentos o directorio inválidos; 3 algún día superó el tope o no se pudo parsear;
4 error de conexión o de la consulta.
"""

import argparse
import os
import re
import stat
from datetime import date, datetime, timedelta
from pathlib import Path

from src.infrastructure.cli.desagregar_cargas import ventana_utc_del_dia
from src.infrastructure.cli.seudonimizar_mediciones import esta_dentro_de_repo_git
from src.infrastructure.settings.logger import logger
from src.infrastructure.ssh.medicion_repository import (
    FilaDia,
    SshMedicionRepository,
    ejecutar_consulta_de_lectura,
    parsear_filas_dia,
)

CODIGO_OK = 0
CODIGO_ARGUMENTOS = 2
CODIGO_TOPE = 3
CODIGO_CONEXION = 4
PERMISOS_DIRECTORIO = 0o700
PERMISOS_ARCHIVO = 0o600
PATRON_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
CABECERA_CON_ENERGIA = "instante,potencia_kw,reactiva_kvar,energia_kwh"
CABECERA_SIN_ENERGIA = "instante,potencia_kw,reactiva_kvar"


class ErrorExportacion(Exception):
    def __init__(self, codigo: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo


def consulta_dia(
    device_id: str, desde_utc: datetime, hasta_utc: datetime, tope: int, con_energia: bool
) -> str:
    """SELECT de un medidor en la ventana [desde, hasta). Valida el uuid y el tope antes de armar el texto."""
    if not PATRON_UUID.match(device_id):
        raise ErrorExportacion(CODIGO_ARGUMENTOS, "El device-id no tiene formato uuid canónico.")
    if tope < 1:
        raise ErrorExportacion(CODIGO_ARGUMENTOS, "El tope de filas por día debe ser positivo.")
    columnas = "t.recorded_at, t.total_active_power, t.total_reactive_power"
    join = ""
    if con_energia:
        columnas += ", e.net_active_energy_kwh"
        join = (
            "LEFT JOIN datamaq_telemetry.telemetry_energy e "
            "ON e.device_id = t.device_id AND e.recorded_at = t.recorded_at"
        )
    desde_s = desde_utc.strftime("%Y-%m-%d %H:%M:%S")
    hasta_s = hasta_utc.strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"SELECT {columnas} "
        "FROM datamaq_telemetry.telemetry_instantaneous t "
        f"{join} "
        f"WHERE t.device_id = '{device_id}' "
        f"AND t.recorded_at >= '{desde_s}' AND t.recorded_at < '{hasta_s}' "
        "AND t.es_dato_confiable = 1 AND t.total_active_power IS NOT NULL "
        f"ORDER BY t.recorded_at LIMIT {tope + 1}"
    )


def preparar_salida(directorio: Path) -> None:
    """Crea o verifica el directorio: fuera de git y con permisos 700."""
    if esta_dentro_de_repo_git(directorio):
        raise ErrorExportacion(
            CODIGO_ARGUMENTOS, "El directorio de salida está dentro de un repositorio git."
        )
    if directorio.exists():
        modo = stat.S_IMODE(directorio.stat().st_mode)
        if modo != PERMISOS_DIRECTORIO:
            raise ErrorExportacion(
                CODIGO_ARGUMENTOS, "El directorio de salida debe tener permisos 700."
            )
    else:
        directorio.mkdir(mode=PERMISOS_DIRECTORIO, parents=True)
        os.chmod(directorio, PERMISOS_DIRECTORIO)


def escribir_csv(ruta: Path, filas: list[FilaDia], con_energia: bool) -> None:
    """Escribe el CSV del día con permisos 600. Un valor NULL queda como celda vacía."""
    cabecera = CABECERA_CON_ENERGIA if con_energia else CABECERA_SIN_ENERGIA
    lineas = [cabecera]
    for f in filas:
        partes = [f.instante, _formatear(f.potencia_kw), _formatear(f.reactiva_kvar)]
        if con_energia:
            partes.append(_formatear(f.energia_kwh))
        lineas.append(",".join(partes))
    descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, PERMISOS_ARCHIVO)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as archivo:
        archivo.write("\n".join(lineas) + "\n")


def _formatear(valor: float | None) -> str:
    return "" if valor is None else repr(valor)


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exporta días de medidores desde el VPS (solo lectura)."
    )
    parser.add_argument(
        "--device-id", action="append", required=True, help="uuid del medidor (repetible)"
    )
    parser.add_argument(
        "--desde", type=date.fromisoformat, required=True, help="primer día local (AAAA-MM-DD)"
    )
    parser.add_argument(
        "--hasta", type=date.fromisoformat, required=True, help="último día local, inclusive"
    )
    parser.add_argument(
        "--salida-dir", type=Path, required=True, help="directorio fuera de git, permisos 700"
    )
    parser.add_argument(
        "--tope-filas-dia",
        type=int,
        default=5000,
        help="máximo de filas por día (por defecto 5000)",
    )
    parser.add_argument(
        "--sin-energia",
        action="store_true",
        help="no leer la energía acumulada (si la tabla no existe)",
    )
    return parser


def _dias(desde: date, hasta: date) -> list[date]:
    if hasta < desde:
        raise ErrorExportacion(CODIGO_ARGUMENTOS, "--hasta es anterior a --desde.")
    return [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]


def _exportar_uno(
    repo: SshMedicionRepository,
    device_id: str,
    dia: date,
    salida: Path,
    tope: int,
    con_energia: bool,
) -> int:
    desde_utc, hasta_utc = ventana_utc_del_dia(dia)
    consulta = consulta_dia(device_id, desde_utc, hasta_utc, tope, con_energia)
    filas = parsear_filas_dia(ejecutar_consulta_de_lectura(repo, consulta), con_energia)
    if len(filas) > tope:
        raise ErrorExportacion(CODIGO_TOPE, "Un día superó el tope de filas: no se escribió.")
    escribir_csv(salida / f"{device_id}_{dia.isoformat()}.csv", filas, con_energia)
    return len(filas)


def main(args: list[str] | None = None) -> int:
    parsed = _construir_parser().parse_args(args)
    con_energia = not parsed.sin_energia
    codigo = CODIGO_OK
    try:
        preparar_salida(parsed.salida_dir)
        dias = _dias(parsed.desde, parsed.hasta)
        for indice, device_id in enumerate(parsed.device_id, start=1):
            if not PATRON_UUID.match(device_id):
                raise ErrorExportacion(
                    CODIGO_ARGUMENTOS, f"device-id {indice} con formato inválido."
                )
        # El adaptador solo ejecuta consultas aquí; no sincroniza ni escribe caché.
        repo = SshMedicionRepository(cache_dir=parsed.salida_dir)
        for indice, device_id in enumerate(parsed.device_id, start=1):
            for dia in dias:
                codigo = max(
                    codigo, _exportar_dia_medidor(repo, device_id, indice, dia, parsed, con_energia)
                )
    except ErrorExportacion as error:
        logger.error("%s", error)
        return error.codigo
    return codigo


def _exportar_dia_medidor(
    repo: SshMedicionRepository,
    device_id: str,
    indice: int,
    dia: date,
    parsed: argparse.Namespace,
    con_energia: bool,
) -> int:
    try:
        filas = _exportar_uno(
            repo, device_id, dia, parsed.salida_dir, parsed.tope_filas_dia, con_energia
        )
    except ErrorExportacion as error:
        logger.error("medidor %d, día %s: %s", indice, dia.isoformat(), error)
        return error.codigo
    except (RuntimeError, ValueError) as error:
        logger.error(
            "medidor %d, día %s: error de conexión o de datos (%s)",
            indice,
            dia.isoformat(),
            type(error).__name__,
        )
        return CODIGO_CONEXION
    logger.info("medidor %d, día %s: %d filas exportadas", indice, dia.isoformat(), filas)
    return CODIGO_OK
