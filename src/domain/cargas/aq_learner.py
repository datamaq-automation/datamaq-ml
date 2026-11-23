"""src/domain/cargas/aq_learner.py — Algoritmo AQ de Michalski para inducción de reglas conjuntivas."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

INF = float("inf")


@dataclass(frozen=True)
class ComplejoAQ:
    """Complejo AQ: conjunción de intervalos por rasgo que excluyen negativos."""

    clase: Any
    rasgo: str = "dp"
    minimo: float = -INF
    maximo: float = INF

    def cubre_valor(self, valor: float) -> bool:
        """Determina si un valor numérico cae en el intervalo abierto (minimo, maximo)."""
        return self.minimo < valor < self.maximo

    def cubre_ejemplo(self, rasgos: dict[str, float]) -> bool:
        """Determina si los rasgos del ejemplo satisfacen el complejo."""
        if self.rasgo not in rasgos:
            return False
        return self.cubre_valor(rasgos[self.rasgo])


@dataclass
class ReglaAQ:
    """Regla disyuntiva de una clase: cubierta si AL MENOS UN complejo la satisface."""

    clase: Any
    complejos: list[ComplejoAQ] = field(default_factory=list)

    def cubre(self, rasgos: dict[str, float]) -> bool:
        """Determina si algún complejo de la regla cubre el ejemplo."""
        return any(c.cubre_ejemplo(rasgos) for c in self.complejos)


def inducir_complejo_1d(
    ejemplos: list[tuple[float, Any]],
    clase_objetivo: Any,
    rasgo: str = "dp",
) -> ComplejoAQ:
    """Induce el complejo más general (estrella) para la clase sobre un atributo 1D."""
    pos = [dp for dp, c in ejemplos if c == clase_objetivo]
    neg = [dp for dp, c in ejemplos if c != clase_objetivo]

    if not pos:
        return ComplejoAQ(clase=clase_objetivo, rasgo=rasgo, minimo=INF, maximo=-INF)

    min_pos = min(pos)
    max_pos = max(pos)

    lo = max((n for n in neg if n < min_pos), default=-INF)
    hi = min((n for n in neg if n > max_pos), default=INF)

    return ComplejoAQ(clase=clase_objetivo, rasgo=rasgo, minimo=lo, maximo=hi)


class AQLearner:
    """Implementación de aprendizaje por cubrimiento secuencial (Algoritmo AQ de Michalski)."""

    def __init__(self, rasgo_principal: str = "dp") -> None:
        self._rasgo = rasgo_principal
        self._reglas: list[ReglaAQ] = []

    def entrenar(self, ejemplos: list[tuple[dict[str, float], Any]]) -> None:
        """Entrena el clasificador aprendiendo una regla disyuntiva por cada clase."""
        self._reglas.clear()
        clases = sorted({c for _, c in ejemplos}, key=str)

        for clase in clases:
            positivos = [d[self._rasgo] for d, c in ejemplos if c == clase and self._rasgo in d]
            negativos = [d[self._rasgo] for d, c in ejemplos if c != clase and self._rasgo in d]

            regla = ReglaAQ(clase=clase)
            por_cubrir = list(positivos)

            # Cubrimiento secuencial: selecciona semilla y expande el complejo estrella
            while por_cubrir:
                semilla = por_cubrir[0]
                lo = max((n for n in negativos if n < semilla), default=-INF)
                hi = min((n for n in negativos if n > semilla), default=INF)

                complejo = ComplejoAQ(clase=clase, rasgo=self._rasgo, minimo=lo, maximo=hi)
                regla.complejos.append(complejo)

                # Elimina positivos cubiertos por este complejo
                por_cubrir = [p for p in por_cubrir if not (lo < p < hi)]

            self._reglas.append(regla)

    def predecir(self, rasgos: dict[str, float]) -> Any | None:
        """Clasifica un ejemplo buscando qué regla lo cubre."""
        candidatos: list[Any] = []
        for regla in self._reglas:
            if regla.cubre(rasgos):
                candidatos.append(regla.clase)

        if len(candidatos) == 1:
            return candidatos[0]
        if len(candidatos) > 1:
            # En caso de solapamiento entre complejos, prioriza el que tenga centro más cercano
            if self._rasgo in rasgos:
                val = rasgos[self._rasgo]
                return min(
                    candidatos,
                    key=lambda c: self._distancia_centro(c, val),
                )
            return candidatos[0]
        return None

    def _distancia_centro(self, clase: Any, val: float) -> float:
        for regla in self._reglas:
            if regla.clase == clase:
                distancias = []
                for c in regla.complejos:
                    centro = (
                        (c.minimo + c.maximo) / 2
                        if not math.isinf(c.minimo) and not math.isinf(c.maximo)
                        else (c.minimo if not math.isinf(c.minimo) else c.maximo)
                    )
                    distancias.append(abs(val - centro))
                return min(distancias) if distancias else INF
        return INF

    def obtener_reglas(self) -> list[ReglaAQ]:
        """Devuelve las reglas inducidas."""
        return list(self._reglas)
