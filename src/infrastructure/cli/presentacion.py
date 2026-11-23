"""src/infrastructure/cli/presentacion.py — Presentación de la terminal: tablas, veredictos y errores que enseñan. Solo biblioteca estándar.

Este módulo solo da forma al texto. No decide nada y no cambia ningún resultado: los CSV y los
JSON que escriben los comandos son los mismos. Respeta NO_COLOR (sin colores ANSI) y COLUMNS (ancho
de la terminal), y usa símbolos ASCII si la salida no es UTF-8.
"""

from __future__ import annotations

import os
import sys

from src.application.cargas.dtos.identificar_cargas import (
    BarraHistogramaResponse,
    IdentificarCargasResponse,
)
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


def siguiente_paso_entrenamiento(r: IdentificarCargasResponse, medidor: str) -> str:
    """El comando que conviene correr después, según el veredicto. Solo comandos que existen."""
    if r.umbral.kw is not None and r.saltos_bajo_umbral.cantidad > 0:
        umbral_bajo = max(1.0, round(r.umbral.kw / 2, 1))
        return (
            f"./run.sh train {medidor} --umbral {numero(umbral_bajo)}   "
            f"(probá con --umbral más bajo para ver cargas chicas)"
        )
    nivel, _ = veredicto_entrenamiento(r)
    if nivel == "ok":
        return "./run.sh supervise   (aprender con la verdad simulada)"
    return f"./run.sh train {medidor} --grafico   (ver dónde caen los saltos)"


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
    lineas.append(
        f"Umbral · radio · mínimo: {umbral} · {_radio(r)} · {r.agrupamiento.min_eventos} eventos"
    )
    if r.umbral.kw is not None and r.saltos_bajo_umbral.cantidad > 0:
        lineas.append(
            f"{numero(r.saltos_bajo_umbral.cantidad, 0)} saltos quedaron bajo el umbral de "
            f"{numero(r.umbral.kw)} kW y no se analizaron ({numero(r.saltos_bajo_umbral.energia_kwh)} kWh estimados)."
        )
    lineas += [
        veredicto(nivel, texto),
        f"Siguiente paso: {siguiente_paso_entrenamiento(r, medidor)}",
    ]
    return lineas


def _radio(r: IdentificarCargasResponse) -> str:
    return (
        "sin radio" if r.agrupamiento.radio_kw is None else f"{numero(r.agrupamiento.radio_kw)} kW"
    )


def lineas_explicacion(r: IdentificarCargasResponse) -> list[str]:
    """Narra los pasos del entrenamiento con sus valores. Solo lee el resultado: no cambia nada.

    ADVERTENCIA: esta narración describe lo que hace IdentificarCargasUseCase hoy. Si ese caso de
    uso cambia (pasos, umbral, agrupamiento), hay que actualizar esta narración. El test
    tests/unit/test_presentacion_explica.py vigila que cada número salga del resultado, pero no que
    el texto siga siendo verdadero.
    """
    umbral = "sin umbral" if r.umbral.kw is None else f"{numero(r.umbral.kw)} kW"
    confianza = "confiable" if r.umbral.confiable else "no confiable"
    return [
        "",
        "Cómo llegué a este resultado (--explica)",
        f"Paso 1 · Saltos: hay {numero(r.mediciones, 0)} mediciones y {r.eventos} eventos",
        "  (|ΔP|: cambio de potencia entre dos mediciones seguidas).",
        f"Paso 2 · Umbral: {umbral}, con el método de Otsu (η = {_eta(r)}, {confianza}).",
        "  Otsu elige el corte que mejor separa ruido y eventos. η mide esa separación.",
        f"Paso 3 · Agrupamiento: eventos de magnitud parecida (a menos de {_radio(r)}) se",
        f"  juntan. Un grupo con al menos {r.agrupamiento.min_eventos} eventos es una carga.",
        f"  Quedan {r.eventos_sin_grupo} eventos sin grupo (ruido).",
        f"Paso 4 · Resumen: {_plural(len(r.cargas), 'carga', 'cargas')}. Glosario: docs/glosario.md.",
    ]


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _eta(r: IdentificarCargasResponse) -> str:
    return "—" if r.umbral.separacion is None else numero(r.umbral.separacion, 2)


def lineas_histograma(
    barras: list[BarraHistogramaResponse],
    umbral_kw: float | None,
    unicode: bool | None = None,
) -> list[str]:
    """Histograma horizontal de |ΔP| en texto. La marca indica el corte que usó el entrenamiento."""
    if not barras:
        return ["No hay saltos para graficar."]
    usar = usa_unicode() if unicode is None else unicode
    bloque, marca = ("█", "←") if usar else ("#", "<")
    ancho = max(10, min(40, ancho_terminal() - 36))
    maximo = max(b.cantidad for b in barras) or 1
    lineas = ["Distribución de saltos |ΔP| (cada fila es un tramo; los tramos no son iguales)"]
    for b in barras:
        etiqueta = f"{numero(b.desde_kw, 0)}–{numero(b.hasta_kw, 0)} kW".rjust(14)
        largo = round(ancho * b.cantidad / maximo)
        corte = ""
        if umbral_kw is not None and b.desde_kw <= umbral_kw < b.hasta_kw:
            corte = f"  {marca} corte {numero(umbral_kw)} kW"
        lineas.append(f"{etiqueta} │{bloque * largo:<{ancho}} {numero(b.cantidad, 0)}{corte}")
    if umbral_kw is not None:
        bajo = sum(b.cantidad for b in barras if b.hasta_kw <= umbral_kw)
        lineas.append(f"{numero(bajo, 0)} saltos quedan bajo el corte y no cuentan como eventos.")
    return lineas
