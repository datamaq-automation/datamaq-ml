"""src/domain/cargas/pronostico_demanda.py — Modelos de regresión y pronóstico de series temporales de energía.

Implementa métricas de error continuo (MAE, RMSE), partición temporal determinista (sin fugas de datos),
modelos de línea de base (promedio histórico, último valor/persistencia), modelo de tendencia lineal,
árbol de regresión continuo univariado basado en minimización de varianza cuadrática, y
comparación del sesgo de optimismo artificial por partición aleatoria frente a temporal.
Cero dependencias externas (Clean Architecture).
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass


def calcular_mae(reales: Sequence[float], previstos: Sequence[float]) -> float:
    """Calcula el Error Absoluto Medio (MAE)."""
    if not reales or len(reales) != len(previstos):
        raise ValueError("Las series reales y previstas deben ser no vacías y de igual longitud.")
    return sum(abs(r - p) for r, p in zip(reales, previstos, strict=True)) / len(reales)


def calcular_rmse(reales: Sequence[float], previstos: Sequence[float]) -> float:
    """Calcula la Raíz del Error Cuadrático Medio (RMSE)."""
    if not reales or len(reales) != len(previstos):
        raise ValueError("Las series reales y previstas deben ser no vacías y de igual longitud.")
    mse = sum((r - p) ** 2 for r, p in zip(reales, previstos, strict=True)) / len(reales)
    return math.sqrt(mse)


@dataclass(frozen=True)
class ParticionTemporal:
    """Partición estricta de series de tiempo para evitar filtración de información del futuro."""

    corte_entrenamiento: float = 0.7

    def partir(self, serie: Sequence[float]) -> tuple[list[float], list[float]]:
        """Divide la serie preservando el orden cronológico."""
        n = len(serie)
        if n < 2:
            raise ValueError("La serie temporal debe contener al menos 2 observaciones.")
        indice_corte = int(n * self.corte_entrenamiento)
        indice_corte = max(1, min(n - 1, indice_corte))
        return list(serie[:indice_corte]), list(serie[indice_corte:])


class ModeloPromedio:
    """Línea de base de pronóstico: media histórica de entrenamiento."""

    def __init__(self) -> None:
        self._media: float = 0.0

    def ajustar(self, serie_entrenamiento: Sequence[float]) -> None:
        if not serie_entrenamiento:
            raise ValueError("Serie de entrenamiento vacía.")
        self._media = sum(serie_entrenamiento) / len(serie_entrenamiento)

    def predecir(self, horizonte: int) -> list[float]:
        return [self._media] * horizonte


class ModeloUltimoValor:
    """Línea de base de pronóstico: persistencia / martingala (último valor observado)."""

    def __init__(self) -> None:
        self._ultimo: float = 0.0

    def ajustar(self, serie_entrenamiento: Sequence[float]) -> None:
        if not serie_entrenamiento:
            raise ValueError("Serie de entrenamiento vacía.")
        self._ultimo = float(serie_entrenamiento[-1])

    def predecir(self, horizonte: int) -> list[float]:
        return [self._ultimo] * horizonte


class ModeloTendenciaLineal:
    """Pronóstico paramétrico extrapolando la recta de mínimos cuadrados en el tiempo."""

    def __init__(self) -> None:
        self._pendiente: float = 0.0
        self._ordenada: float = 0.0
        self._n: int = 0

    def ajustar(self, serie_entrenamiento: Sequence[float]) -> None:
        n = len(serie_entrenamiento)
        if n < 2:
            raise ValueError("Se requieren al menos 2 puntos para estimar tendencia.")
        self._n = n
        t_medio = (n - 1) / 2.0
        y_medio = sum(serie_entrenamiento) / n

        denom = sum((t - t_medio) ** 2 for t in range(n))
        if denom == 0:
            self._pendiente = 0.0
        else:
            numer = sum((t - t_medio) * (y - y_medio) for t, y in enumerate(serie_entrenamiento))
            self._pendiente = numer / denom

        self._ordenada = y_medio - self._pendiente * t_medio

    def predecir(self, horizonte: int) -> list[float]:
        return [self._ordenada + self._pendiente * t for t in range(self._n, self._n + horizonte)]


class ArbolRegresionContinuo:
    """Árbol de regresión 1D recursivo que minimiza la varianza (reducción de MSE)."""

    def __init__(self, max_profundidad: int = 2) -> None:
        self.max_profundidad = max_profundidad
        self._pred_der: float = 0.0

    def ajustar(self, serie_entrenamiento: Sequence[float]) -> None:
        n = len(serie_entrenamiento)
        if not serie_entrenamiento:
            raise ValueError("Serie de entrenamiento vacía.")
        if n < 3 or self.max_profundidad < 1:
            self._pred_der = sum(serie_entrenamiento) / n
            return

        mejor_mse = float("inf")
        mejor_corte: int | None = None

        for corte in range(1, n):
            izq = serie_entrenamiento[:corte]
            der = serie_entrenamiento[corte:]
            m_izq = sum(izq) / len(izq)
            m_der = sum(der) / len(der)
            mse_izq = sum((x - m_izq) ** 2 for x in izq)
            mse_der = sum((x - m_der) ** 2 for x in der)
            total_mse = mse_izq + mse_der
            if total_mse < mejor_mse:
                mejor_mse = total_mse
                mejor_corte = corte

        if mejor_corte is not None:
            der = serie_entrenamiento[mejor_corte:]
            self._pred_der = sum(der) / len(der)
        else:
            self._pred_der = sum(serie_entrenamiento) / n

    def predecir(self, horizonte: int) -> list[float]:
        return [self._pred_der] * horizonte


def comparar_particion_temporal_vs_aleatoria(
    serie: Sequence[float],
    fraccion: float = 0.7,
    seed: int = 42,
) -> dict[str, float]:
    """Demuestra empíricamente el sesgo optimista de la partición aleatoria en series de demanda.

    Cuando los datos presentan estacionalidad cíclica combinada con tendencia de crecimiento,
    una partición aleatoria permite que el modelo observe ejemplos futuros en cada fase del ciclo,
    reduciendo artificialmente el error de prueba (fuga temporal o data leakage).
    """
    n = len(serie)
    corte = int(n * fraccion)

    # Construir observaciones con rasgo estacional y tendencia
    datos: list[tuple[int, float]] = []
    for d, val in enumerate(serie):
        fase_ciclo = d % 7
        datos.append((fase_ciclo, float(val)))

    def _evaluar_modelo_estacional(
        entrena: list[tuple[int, float]], prueba: list[tuple[int, float]]
    ) -> tuple[float, float]:
        proms = defaultdict(list)
        for fase, y in entrena:
            proms[fase].append(y)
        media_global = sum(y for _, y in entrena) / len(entrena) if entrena else 0.0
        modelo = {fase: sum(ys) / len(ys) for fase, ys in proms.items() if ys}

        reales = [y for _, y in prueba]
        previstos = [modelo.get(fase, media_global) for fase, _ in prueba]
        return calcular_mae(reales, previstos), calcular_rmse(reales, previstos)

    # 1. Partición Temporal estricta
    datos_entrena_temp = datos[:corte]
    datos_prueba_temp = datos[corte:]
    mae_temp, rmse_temp = _evaluar_modelo_estacional(datos_entrena_temp, datos_prueba_temp)

    # 2. Partición Aleatoria (filtración de puntos del futuro)
    rnd = random.Random(seed)
    datos_shuffled = list(datos)
    rnd.shuffle(datos_shuffled)
    datos_entrena_aleat = datos_shuffled[:corte]
    datos_prueba_aleat = datos_shuffled[corte:]
    mae_aleat, rmse_aleat = _evaluar_modelo_estacional(datos_entrena_aleat, datos_prueba_aleat)

    return {
        "mae_temporal": mae_temp,
        "rmse_temporal": rmse_temp,
        "mae_aleatoria": mae_aleat,
        "rmse_aleatoria": rmse_aleat,
    }


def evaluar_pronostico(
    serie: Sequence[float],
    corte_entrenamiento: float = 0.7,
) -> dict[str, dict[str, float | list[float]]]:
    """Evalúa múltiples modelos de regresión y líneas de base sobre la serie temporal."""
    particion = ParticionTemporal(corte_entrenamiento)
    entrena, prueba = particion.partir(serie)
    horizonte = len(prueba)

    modelos = [
        ("promedio", ModeloPromedio()),
        ("ultimo_valor", ModeloUltimoValor()),
        ("tendencia", ModeloTendenciaLineal()),
        ("arbol_regresion", ArbolRegresionContinuo()),
    ]

    resultados: dict[str, dict[str, float | list[float]]] = {}
    for nombre, mod in modelos:
        mod.ajustar(entrena)
        prev = mod.predecir(horizonte)
        resultados[nombre] = {
            "mae": calcular_mae(prueba, prev),
            "rmse": calcular_rmse(prueba, prev),
            "predicciones": prev,
        }

    return resultados
