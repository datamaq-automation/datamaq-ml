"""src/infrastructure/csv/catalogo_placa_repository.py — Lector del catálogo por placa (CSV).

Columnas obligatorias: etiqueta, potencia_nominal_kw, trafo, tipo_proceso, forma_arranque.
Opcional: cos_phi (si falta, el cos φ típico). Cualquier fila inválida es error, con su número de línea.
El archivo real de motores no entra al repo: este lector se prueba con ejemplos sintéticos.
"""

import csv
from pathlib import Path

from src.domain.cargas.catalogo_placa import COS_PHI_TIPICO, FORMAS_ARRANQUE, PlacaMotor

COLUMNAS_OBLIGATORIAS = (
    "etiqueta",
    "potencia_nominal_kw",
    "trafo",
    "tipo_proceso",
    "forma_arranque",
)


def leer_catalogo_placa(ruta: Path) -> list[PlacaMotor]:
    with ruta.open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in (lector.fieldnames or [])]
        if faltantes:
            raise ValueError(f"faltan columnas: {', '.join(faltantes)}")
        placas: list[PlacaMotor] = []
        vistas: set[str] = set()
        for numero, fila in enumerate(lector, start=2):
            placa = _placa(fila, numero)
            if placa.etiqueta in vistas:
                raise ValueError(f"línea {numero}: etiqueta repetida {placa.etiqueta!r}")
            vistas.add(placa.etiqueta)
            placas.append(placa)
    return placas


def _placa(fila: dict[str, str], numero: int) -> PlacaMotor:
    etiqueta = (fila.get("etiqueta") or "").strip()
    if not etiqueta:
        raise ValueError(f"línea {numero}: etiqueta vacía")
    try:
        potencia = float(fila["potencia_nominal_kw"])
    except ValueError as error:
        raise ValueError(f"línea {numero}: potencia_nominal_kw no es un número") from error
    if potencia <= 0:
        raise ValueError(f"línea {numero}: potencia_nominal_kw debe ser mayor que cero")
    forma = (fila["forma_arranque"] or "").strip()
    if forma not in FORMAS_ARRANQUE:
        raise ValueError(f"línea {numero}: forma_arranque desconocida {forma!r}")
    cos_phi = _cos_phi(fila.get("cos_phi"), numero)
    return PlacaMotor(
        etiqueta=etiqueta,
        potencia_nominal_kw=potencia,
        trafo=(fila["trafo"] or "").strip(),
        tipo_proceso=(fila["tipo_proceso"] or "").strip(),
        forma_arranque=forma,
        cos_phi=cos_phi,
    )


def _cos_phi(texto: str | None, numero: int) -> float:
    if texto is None or not texto.strip():
        return COS_PHI_TIPICO
    try:
        valor = float(texto)
    except ValueError as error:
        raise ValueError(f"línea {numero}: cos_phi no es un número") from error
    if not 0 < valor <= 1:
        raise ValueError(f"línea {numero}: cos_phi debe estar en (0, 1]")
    return valor
