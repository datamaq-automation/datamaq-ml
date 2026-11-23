"""src/application/cargas/use_cases/pronosticar_demanda.py — Caso de uso de pronóstico de demanda con partición temporal.

Entrena modelos de regresión y líneas de base comparativas (promedio, persistencia, tendencia lineal,
árbol de regresión continuo) y calcula métricas de desempeño honestas (MAE, RMSE).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from src.domain.cargas.pronostico_demanda import (
    comparar_particion_temporal_vs_aleatoria,
    evaluar_pronostico,
)


@dataclass(frozen=True)
class ResultadoPronosticoDTO:
    """Métricas y estimaciones de los modelos de regresión."""

    modelos: dict[str, dict[str, float | list[float]]]
    comparacion_sesgo: dict[str, float]


class PronosticarDemandaUseCase:
    """Orquesta la evaluación de pronóstico con series de energía."""

    def __init__(self, corte_entrenamiento: float = 0.7) -> None:
        self.corte_entrenamiento = corte_entrenamiento

    def ejecutar(
        self,
        serie_energia: Sequence[float],
    ) -> ResultadoPronosticoDTO:
        """Calcula pronósticos sobre partición temporal y evalúa el sesgo aleatorio."""
        metricas_modelos = evaluar_pronostico(
            serie_energia,
            corte_entrenamiento=self.corte_entrenamiento,
        )
        sesgo = comparar_particion_temporal_vs_aleatoria(
            serie_energia,
            fraccion=self.corte_entrenamiento,
        )
        return ResultadoPronosticoDTO(
            modelos=metricas_modelos,
            comparacion_sesgo=sesgo,
        )
