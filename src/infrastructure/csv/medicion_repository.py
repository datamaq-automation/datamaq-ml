"""src/infrastructure/csv/medicion_repository.py — Lectura de mediciones desde CSV.

Formato (columnas en este orden; reactiva y energía son opcionales):
    instante,potencia_kw[,reactiva_kvar[,energia_kwh]]
- instante: ISO 8601. Si trae zona, se convierte a UTC; si no trae, se asume UTC.
- potencia_kw: potencia activa en kW.
- reactiva_kvar: potencia reactiva en kVAr. Vacía o ausente → None.
- energia_kwh: contador acumulado de energía activa en kWh. Vacío o ausente → None.
"""

import csv
from datetime import UTC, datetime
from pathlib import Path

from src.domain.cargas.entities import Medicion
from src.infrastructure.settings.logger import logger


def _leer_opcional(fila: dict[str, str], columna: str) -> float | None:
    """Valor float de una columna opcional: ausente o vacía es None."""
    valor = fila.get(columna) or ""
    return float(valor) if valor.strip() else None


def leer_reactiva_kvar(fila: dict[str, str]) -> float | None:
    """Reactiva (kVAr) de una fila CSV; la columna reactiva_kvar es opcional."""
    return _leer_opcional(fila, "reactiva_kvar")


def leer_energia_kwh(fila: dict[str, str]) -> float | None:
    """Contador de energía activa (kWh) de una fila CSV; la columna energia_kwh es opcional."""
    return _leer_opcional(fila, "energia_kwh")


def _instante_utc(texto: str) -> datetime:
    """Instante en UTC sin zona. Un texto sin zona se toma como UTC."""
    instante = datetime.fromisoformat(texto)
    if instante.tzinfo is None:
        return instante
    return instante.astimezone(UTC).replace(tzinfo=None)


class CsvMedicionRepository:
    """Lee mediciones de CSV: un medidor por archivo (`listar`) o un archivo cualquiera (`leer_archivo`)."""

    def __init__(self, carpeta: Path) -> None:
        self._carpeta = carpeta

    def medidores(self) -> list[str]:
        return sorted(p.stem for p in self._carpeta.glob("*.csv"))

    def listar(self, medidor: str, desde: datetime, hasta: datetime) -> list[Medicion]:
        # Solo nombres de archivos existentes: evita leer rutas arbitrarias ("../.env").
        if medidor not in self.medidores():
            logger.error(
                "Medidor desconocido: %s (disponibles: %s)", medidor, ", ".join(self.medidores())
            )
            raise LookupError(f"Medidor desconocido: {medidor}")
        return self.leer_archivo(self._carpeta / f"{medidor}.csv", desde, hasta)

    def leer_archivo(self, ruta: Path, desde: datetime, hasta: datetime) -> list[Medicion]:
        """Mediciones de `ruta` con desde <= instante < hasta (ventana semiabierta, en UTC)."""
        logger.info("Leyendo %s", ruta)
        with ruta.open(encoding="utf-8") as archivo:
            filas = (
                Medicion(
                    instante=_instante_utc(f["instante"]),
                    potencia_kw=float(f["potencia_kw"]),
                    reactiva_kvar=leer_reactiva_kvar(f),
                    energia_acumulada_kwh=leer_energia_kwh(f),
                )
                for f in csv.DictReader(archivo)
            )
            mediciones = [m for m in filas if desde <= m.instante < hasta]
        logger.info("%d mediciones dentro del rango", len(mediciones))
        return mediciones

    def guardar(self, medidor: str, mediciones: list[Medicion]) -> None:
        """Escribe <medidor>.csv con el mismo formato que lee listar (lo usa el simulador)."""
        self._carpeta.mkdir(parents=True, exist_ok=True)
        destino = self._carpeta / f"{medidor}.csv"
        con_reactiva = any(m.reactiva_kvar is not None for m in mediciones)
        with destino.open("w", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            if con_reactiva:
                escritor.writerow(["instante", "potencia_kw", "reactiva_kvar"])
                escritor.writerows(
                    (
                        m.instante.isoformat(),
                        m.potencia_kw,
                        "" if m.reactiva_kvar is None else m.reactiva_kvar,
                    )
                    for m in mediciones
                )
            else:
                escritor.writerow(["instante", "potencia_kw"])
                escritor.writerows((m.instante.isoformat(), m.potencia_kw) for m in mediciones)
        logger.info("%d mediciones guardadas en %s", len(mediciones), destino)
