"""src/domain/cargas/algoritmo_genetico.py — Optimización heurística de horarios de demanda con algoritmos genéticos.

Implementa la función de aptitud (minimización de demanda pico horaria), búsqueda exhaustiva
por fuerza bruta como baseline comparativo, y el algoritmo genético con elitismo, selección por
torneo, cruza en un punto y mutación aleatoria. Cero dependencias externas (Clean Architecture).
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Sequence
from dataclasses import dataclass


def calcular_demanda_horaria(
    horarios: Sequence[int],
    cargas: Sequence[float],
    base: Sequence[float],
) -> list[float]:
    """Calcula la demanda total resultante para cada hora."""
    demanda = list(base)
    n_horas = len(base)
    for carga, h in zip(cargas, horarios, strict=False):
        if 0 <= h < n_horas:
            demanda[h] += carga
    return demanda


def calcular_demanda_maxima(
    horarios: Sequence[int],
    cargas: Sequence[float],
    base: Sequence[float],
) -> float:
    """Calcula el pico máximo de demanda resultante de la asignación horaria."""
    demanda = calcular_demanda_horaria(horarios, cargas, base)
    return max(demanda) if demanda else 0.0


def resolver_fuerza_bruta(
    cargas: Sequence[float],
    base: Sequence[float],
) -> tuple[tuple[int, ...], float]:
    """Encuentra la asignación óptima evaluando todas las combinaciones posibles (H^C)."""
    n_horas = len(base)
    n_cargas = len(cargas)
    combinaciones = itertools.product(range(n_horas), repeat=n_cargas)
    mejor_horario = min(
        combinaciones,
        key=lambda h: calcular_demanda_maxima(h, cargas, base),
    )
    mejor_pico = calcular_demanda_maxima(mejor_horario, cargas, base)
    return mejor_horario, mejor_pico


@dataclass(frozen=True)
class ResultadoOptimizacionGenetica:
    """Resultado de la ejecución del algoritmo genético."""

    horarios: tuple[int, ...]
    demanda_pico: float
    curva_demanda: list[float]
    historial_mejor_pico: list[float]


class OptimizadorHorariosGenetico:
    """Optimizador poblacional para aplanamiento de curva de carga (peak shaving)."""

    def __init__(
        self,
        cargas: Sequence[float],
        base: Sequence[float],
        tam_poblacion: int = 12,
        generaciones: int = 40,
        tasa_mutacion: float = 0.1,
        elitismo: int = 2,
        tam_torneo: int = 2,
        semilla: int = 1,
    ) -> None:
        self.cargas = list(cargas)
        self.base = list(base)
        self.n_horas = len(base)
        self.n_cargas = len(cargas)
        self.tam_poblacion = tam_poblacion
        self.generaciones = generaciones
        self.tasa_mutacion = tasa_mutacion
        self.elitismo = elitismo
        self.tam_torneo = tam_torneo
        self.semilla = semilla

    def optimizar(self) -> ResultadoOptimizacionGenetica:
        """Ejecuta el ciclo generativo con elitismo y operadores genéticos."""
        rng = random.Random(self.semilla)
        # Inicialización aleatoria uniforme
        poblacion = [
            [rng.randrange(self.n_horas) for _ in range(self.n_cargas)]
            for _ in range(self.tam_poblacion)
        ]

        historial: list[float] = []

        for _ in range(self.generaciones):
            # Evaluación y ordenamiento por aptitud (menor demanda máxima)
            poblacion.sort(key=lambda ind: calcular_demanda_maxima(ind, self.cargas, self.base))
            mejor_actual = calcular_demanda_maxima(poblacion[0], self.cargas, self.base)
            historial.append(mejor_actual)

            # Elitismo: conservar los mejores individuos intactos
            nueva_poblacion = [list(ind) for ind in poblacion[: self.elitismo]]

            # Reproducción hasta completar la población
            while len(nueva_poblacion) < self.tam_poblacion:
                padre = self._seleccion_torneo(poblacion, rng)
                madre = self._seleccion_torneo(poblacion, rng)

                # Cruza en un punto
                if self.n_cargas > 1:
                    punto_corte = rng.randrange(1, self.n_cargas)
                    hijo = padre[:punto_corte] + madre[punto_corte:]
                else:
                    hijo = list(padre)

                # Mutación aleatoria uniforme
                for i in range(self.n_cargas):
                    if rng.random() < self.tasa_mutacion:
                        hijo[i] = rng.randrange(self.n_horas)

                nueva_poblacion.append(hijo)

            poblacion = nueva_poblacion

        poblacion.sort(key=lambda ind: calcular_demanda_maxima(ind, self.cargas, self.base))
        mejor_ind = tuple(poblacion[0])
        mejor_pico = calcular_demanda_maxima(mejor_ind, self.cargas, self.base)
        curva = calcular_demanda_horaria(mejor_ind, self.cargas, self.base)

        return ResultadoOptimizacionGenetica(
            horarios=mejor_ind,
            demanda_pico=mejor_pico,
            curva_demanda=curva,
            historial_mejor_pico=historial,
        )

    def _seleccion_torneo(self, poblacion: list[list[int]], rng: random.Random) -> list[int]:
        candidatos = rng.sample(poblacion, min(self.tam_torneo, len(poblacion)))
        return min(
            candidatos,
            key=lambda ind: calcular_demanda_maxima(ind, self.cargas, self.base),
        )
