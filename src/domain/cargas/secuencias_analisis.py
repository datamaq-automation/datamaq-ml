"""src/domain/cargas/secuencias_analisis.py — Secuencias de análisis y contratos fuertemente tipados.

Implementa la arquitectura en pipeline de cuatro etapas para procesamiento NILM:
1. Diferencias temporales (DiferenciasContrato).
2. Detección de eventos por umbral (DeteccionEventosContrato).
3. Agrupamiento por magnitud (AgrupamientoContrato).
4. Resumen y métricas de carga (ResumenContrato).
Garantiza validación estricta de contratos entre componentes propios, de pares y externos.
Cero dependencias externas (Clean Architecture).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


class ContratoVioladoError(TypeError):
    """Excepción emitida cuando una etapa de análisis recibe o produce datos fuera de contrato."""


@dataclass(frozen=True)
class EventoDetectadoDTO:
    """Contrato formal de un evento de conmutación de carga en la serie temporal."""

    indice: int
    delta_kw: float

    def __post_init__(self) -> None:
        if self.indice < 1:
            raise ValueError("indice debe ser mayor o igual a 1.")
        if not math.isfinite(self.delta_kw):
            raise ValueError("delta_kw debe ser un número finito.")

    @property
    def magnitud(self) -> float:
        return abs(self.delta_kw)

    @property
    def es_arranque(self) -> bool:
        return self.delta_kw > 0.0


@dataclass(frozen=True)
class ResumenCargasDTO:
    """Contrato de salida de la etapa de resumen estadístico de cargas."""

    conteo_por_magnitud: dict[float, int]
    total_eventos: int
    magnitudes_detectadas: list[float]


class DiferenciasContrato:
    """Etapa 1: Calcula el gradiente de potencia discreto entre minutos adyacentes."""

    def ejecutar(self, serie: Sequence[float]) -> list[float]:
        if not isinstance(serie, (list, tuple)):
            raise ContratoVioladoError("La serie debe ser una secuencia (list o tuple).")
        if len(serie) < 2:
            raise ContratoVioladoError(
                "La serie debe contener al menos 2 observaciones para calcular diferencias."
            )
        for i, val in enumerate(serie):
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise ContratoVioladoError(
                    f"Elemento en índice {i} ({val}) no es un valor numérico finito."
                )

        return [float(b - a) for a, b in zip(serie, serie[1:], strict=False)]


class DeteccionEventosContrato:
    """Etapa 2: Aísla transitorios de potencia que superan el umbral establecido."""

    def __init__(self, umbral_kw: float = 20.0) -> None:
        if umbral_kw <= 0.0 or not math.isfinite(umbral_kw):
            raise ContratoVioladoError("El umbral debe ser positivo y finito.")
        self.umbral_kw = umbral_kw

    def ejecutar(self, deltas: Sequence[float]) -> list[EventoDetectadoDTO]:
        if not isinstance(deltas, (list, tuple)):
            raise ContratoVioladoError("deltas debe ser una secuencia.")

        eventos: list[EventoDetectadoDTO] = []
        for i, d in enumerate(deltas):
            if not isinstance(d, (int, float)) or not math.isfinite(d):
                raise ContratoVioladoError(f"Delta en índice {i} no es un número finito.")
            if abs(d) >= self.umbral_kw:
                eventos.append(EventoDetectadoDTO(indice=i + 1, delta_kw=float(d)))

        return eventos


class AgrupamientoContrato:
    """Etapa 3: Agrupa eventos por magnitud de escalón nominal."""

    def ejecutar(
        self, eventos: Sequence[EventoDetectadoDTO]
    ) -> dict[float, list[EventoDetectadoDTO]]:
        if not isinstance(eventos, (list, tuple)):
            raise ContratoVioladoError("eventos debe ser una secuencia.")

        grupos: dict[float, list[EventoDetectadoDTO]] = {}
        for ev in eventos:
            if not isinstance(ev, EventoDetectadoDTO):
                raise ContratoVioladoError(
                    f"Cada evento debe ser instancia de EventoDetectadoDTO, recibido: {type(ev)}"
                )
            mag = round(ev.magnitud, 2)
            grupos.setdefault(mag, []).append(ev)

        return grupos


class ResumenContrato:
    """Etapa 4: Consolida métricas finales por clase de carga."""

    def ejecutar(self, grupos: dict[float, list[EventoDetectadoDTO]]) -> ResumenCargasDTO:
        if not isinstance(grupos, dict):
            raise ContratoVioladoError("grupos debe ser un diccionario.")

        conteo: dict[float, int] = {}
        total = 0
        for mag, evs in sorted(grupos.items(), reverse=True):
            if not isinstance(evs, list):
                raise ContratoVioladoError(f"Lista de eventos para {mag} inválida.")
            conteo[mag] = len(evs)
            total += len(evs)

        return ResumenCargasDTO(
            conteo_por_magnitud=conteo,
            total_eventos=total,
            magnitudes_detectadas=list(conteo.keys()),
        )


class CadenaAnalisisNILM:
    """Orquestador de la secuencia de análisis completa con contratos inter-etapas."""

    def __init__(self, umbral_kw: float = 20.0) -> None:
        self.etapa1 = DiferenciasContrato()
        self.etapa2 = DeteccionEventosContrato(umbral_kw=umbral_kw)
        self.etapa3 = AgrupamientoContrato()
        self.etapa4 = ResumenContrato()
        self._ultimos_eventos: list[EventoDetectadoDTO] = []

    def procesar(self, serie_kw: Sequence[float]) -> ResumenCargasDTO:
        """Ejecuta la tubería completa de análisis."""
        deltas = self.etapa1.ejecutar(serie_kw)
        self._ultimos_eventos = self.etapa2.ejecutar(deltas)
        grupos = self.etapa3.ejecutar(self._ultimos_eventos)
        return self.etapa4.ejecutar(grupos)

    def obtener_eventos_detectados(self) -> list[EventoDetectadoDTO]:
        return list(self._ultimos_eventos)
