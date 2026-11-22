"""src/infrastructure/cli/presentacion.py — Presentación de la terminal: tablas, veredictos y errores que enseñan. Solo biblioteca estándar.

Este módulo solo da forma al texto. No decide nada y no cambia ningún resultado: los CSV y los
JSON que escriben los comandos son los mismos. Respeta NO_COLOR (sin colores ANSI) y COLUMNS (ancho
de la terminal), y usa símbolos ASCII si la salida no es UTF-8.
"""

from __future__ import annotations

import os
import sys

from src.application.cargas.dtos.identificar_cargas import IdentificarCargasResponse
from src.infrastructure.settings.logger import canal_terminal

ANCHO_POR_DEFECTO = 80
ANCHO_MINIMO = 40

_UNICODE = {"ok": "✔ OK", "aviso": "⚠ AVISO", "error": "✘ ERROR"}
_ASCII = {"ok": "[OK]", "aviso": "[AVISO]", "error": "[ERROR]"}


def ancho_terminal() -> int:
    """Ancho de la terminal según COLUMNS; si no es un número válido, 80."""
    try:
        return max(ANCHO_MINIMO, int(os.environ.get("COLUMNS", ANCHO_POR_DEFECTO)))
    except ValueError:
        return ANCHO_POR_DEFECTO


def usa_unicode(flujo=None) -> bool:
    codificacion = (getattr(flujo or sys.stdout, "encoding", None) or "").lower()
    return "utf" in codificacion


def numero(valor: float, decimales: int = 1) -> str:
    """Formato en español: coma decimal y punto como separador de miles (48,9 · 4.031)."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def veredicto(nivel: str, texto: str, unicode: bool | None = None) -> str:
    """Una línea con símbolo y palabra: nunca depende solo del color."""
    usar = usa_unicode() if unicode is None else unicode
    etiqueta = _UNICODE[nivel] if usar else _ASCII[nivel]
    return f"{etiqueta}  {texto}" if usar else f"{etiqueta} {texto}"


def tabla(encabezados: list[str], filas: list[list[str]]) -> list[str]:
    """Tabla alineada a la izquierda; cada columna mide lo que mide su celda más larga."""
    todas = [encabezados, *filas]
    anchos = [max(len(str(fila[i])) for fila in todas) for i in range(len(encabezados))]

    def linea(celdas: list[str]) -> str:
        return "  ".join(str(v).ljust(a) for v, a in zip(celdas, anchos, strict=True)).rstrip()

    separador = "  ".join("-" * a for a in anchos)
    return [linea(encabezados), separador, *(linea(fila) for fila in filas)]


def error_que_ensena(que: str, porque: str, como: str, guia: str | None = None) -> list[str]:
    """Error con tres partes: qué pasó, por qué y cómo se arregla (y dónde leer más)."""
    lineas = [veredicto("error", que), f"  Por qué:  {porque}", f"  Cómo:     {como}"]
    if guia:
        lineas.append(f"  Guía:     {guia}")
    return lineas


def mostrar(lineas: list[str]) -> None:
    """Resultados para el usuario, por stdout y con el logger de terminal."""
    canal = canal_terminal("datamaq.terminal.salida", sys.stdout)
    for linea in lineas:
        canal.info(linea)


def imprimir_error(lineas: list[str]) -> None:
    """Errores para el usuario, por stderr y con el logger de terminal, sin traza de Python."""
    canal = canal_terminal("datamaq.terminal.error", sys.stderr)
    for linea in lineas:
        canal.error(linea)


def _cargas_como_filas(r: IdentificarCargasResponse) -> list[list[str]]:
    return [
        [
            f"carga {i}",
            f"{numero(c.potencia_tipica_kw)} kW",
            str(c.encendidos),
            str(c.apagados),
            str(c.ciclos),
        ]
        for i, c in enumerate(r.cargas, start=1)
    ]


def veredicto_entrenamiento(r: IdentificarCargasResponse) -> tuple[str, str]:
    """Nivel y texto del veredicto de un entrenamiento. Reglas fijas, sin azar."""
    if r.sin_modos_separables:
        return "aviso", "no hay escalones separables: no se agrupan cargas, no se inventan."
    if not r.cargas:
        return "aviso", "no se encontró ninguna carga con estos eventos."
    if r.eventos_sin_grupo > 0:
        return "aviso", (
            f"{r.eventos_sin_grupo} de {r.eventos} eventos sin grupo (ruido): "
            f"no cuentan como carga."
        )
    return "ok", f"se identificaron {len(r.cargas)} cargas con todos sus eventos agrupados."


def siguiente_paso_entrenamiento(r: IdentificarCargasResponse) -> str:
    """El comando que conviene correr después, según el veredicto. Solo comandos que existen."""
    nivel, _ = veredicto_entrenamiento(r)
    if nivel == "ok":
        return "./run.sh supervise   (aprender con la verdad simulada)"
    return "./run.sh ayuda train   (cómo cambiar el umbral)"


def lineas_resumen_entrenamiento(r: IdentificarCargasResponse, medidor: str) -> list[str]:
    """Resumen final de `train`: tabla de cargas, umbral, veredicto y siguiente paso."""
    nivel, texto = veredicto_entrenamiento(r)
    umbral = "sin umbral" if r.umbral.kw is None else f"{numero(r.umbral.kw)} kW"
    lineas = [
        "",
        f"Resumen de «{medidor}» ({r.mediciones} mediciones, {numero(r.dias)} días)",
    ]
    if r.cargas:
        filas = _cargas_como_filas(r)
        lineas += tabla(["Carga", "Potencia", "Encendidos", "Apagados", "Ciclos"], filas)
    lineas += [
        f"Umbral · radio · mínimo: {umbral} · {_radio(r)} · {r.agrupamiento.min_eventos} eventos",
        veredicto(nivel, texto),
        f"Siguiente paso: {siguiente_paso_entrenamiento(r)}",
    ]
    return lineas


def _radio(r: IdentificarCargasResponse) -> str:
    return (
        "sin radio" if r.agrupamiento.radio_kw is None else f"{numero(r.agrupamiento.radio_kw)} kW"
    )
