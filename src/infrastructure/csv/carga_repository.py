"""src/infrastructure/csv/carga_repository.py — Cargas identificadas (cargas_<medidor>.csv) y su régimen (entrenamiento_<medidor>.json)."""

import csv
import json
from pathlib import Path
from typing import Any

from src.domain.cargas.entities import Carga
from src.infrastructure.settings.logger import logger

COLUMNAS = [
    "potencia_tipica_kw",
    "encendidos",
    "apagados",
    "ciclos",
    "dispersion_kw",
    "reactiva_tipica_kvar",
    "ratio_qp_mediana",
]


class CsvCargaRepository:
    """Implementa CargaRepository: un CSV por medidor, una fila por carga."""

    def __init__(self, carpeta: Path) -> None:
        self._carpeta = carpeta

    def guardar(self, medidor: str, cargas: list[Carga]) -> None:
        self._carpeta.mkdir(parents=True, exist_ok=True)
        destino = self._carpeta / f"cargas_{medidor}.csv"
        with destino.open("w", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(COLUMNAS)
            escritor.writerows(_fila(c) for c in cargas)
        logger.info("%s: %d cargas guardadas en %s", medidor, len(cargas), destino)

    def guardar_entrenamiento(self, medidor: str, resumen: dict[str, Any]) -> None:
        """Umbral, régimen y modos con los que se formaron las cargas: lo lee la validación."""
        self._carpeta.mkdir(parents=True, exist_ok=True)
        destino = self._carpeta / f"entrenamiento_{medidor}.json"
        destino.write_text(
            json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        logger.info("%s: régimen de entrenamiento guardado en %s", medidor, destino)


def _fila(carga: Carga) -> tuple[str, ...]:
    """Una fila de cargas_<medidor>.csv. Los valores sin dato quedan vacíos."""
    valores = (
        carga.potencia_tipica_kw,
        carga.encendidos,
        carga.apagados,
        carga.ciclos,
        carga.dispersion_kw,
        carga.reactiva_tipica_kvar,
        carga.ratio_qp_mediana,
    )
    return tuple("" if v is None else str(v) for v in valores)
