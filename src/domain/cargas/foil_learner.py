"""src/domain/cargas/foil_learner.py — Programación Lógica Inductiva y Algoritmo FOIL (Quinlan 1990).

Implementa la representación de relaciones, cláusulas de Horn de primer orden,
cálculo de ganancia de información FOIL y cubrimiento secuencial relacional.
Cero dependencias externas (Clean Architecture).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass
class BaseConocimientoRelacional:
    """Almacena hechos extensionales binarios y conjunto de entidades del dominio."""

    entidades: list[str]
    hechos: dict[str, set[tuple[str, str]]] = field(default_factory=dict)

    def agregar_hecho(self, relacion: str, arg1: str, arg2: str) -> None:
        """Registra un hecho extensional de fondo."""
        if relacion not in self.hechos:
            self.hechos[relacion] = set()
        self.hechos[relacion].add((arg1, arg2))

    def contiene(self, relacion: str, arg1: str, arg2: str) -> bool:
        """Consulta si el par satisface el predicado extensional."""
        return (arg1, arg2) in self.hechos.get(relacion, set())


@dataclass(frozen=True)
class ClausulaHorn:
    """Representa una cláusula definida de Horn: Cabeza(X, Y) :- L1, L2, ..., Lk."""

    cabeza: str
    cuerpo_literales: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)

    def __init__(
        self,
        cabeza: str,
        cuerpo_literales: Sequence[tuple[str, str, str]],
    ) -> None:
        object.__setattr__(self, "cabeza", cabeza)
        object.__setattr__(self, "cuerpo_literales", tuple(cuerpo_literales))

    def evaluar_par(
        self,
        x: str,
        y: str,
        base: BaseConocimientoRelacional,
    ) -> bool:
        """Evalúa si la cláusula se satisface para los argumentos x e y mediante búsqueda exhaustiva."""
        if not self.cuerpo_literales:
            return True

        variables: set[str] = set()
        for _, v1, v2 in self.cuerpo_literales:
            variables.add(v1)
            variables.add(v2)

        internas = sorted(variables - {"X", "Y"})

        def resolver_recursivo(idx: int, asignacion: dict[str, str]) -> bool:
            if idx == len(internas):
                return self._comprobar_literales(asignacion, base)

            var_actual = internas[idx]
            for entidad in base.entidades:
                asignacion[var_actual] = entidad
                if resolver_recursivo(idx + 1, asignacion):
                    return True
            return False

        asignacion_inicial = {"X": x, "Y": y}
        return resolver_recursivo(0, asignacion_inicial)

    def _comprobar_literales(
        self,
        asignacion: dict[str, str],
        base: BaseConocimientoRelacional,
    ) -> bool:
        for pred, v1, v2 in self.cuerpo_literales:
            a1 = asignacion.get(v1, v1)
            a2 = asignacion.get(v2, v2)
            if not base.contiene(pred, a1, a2):
                return False
        return True


def calcular_ganancia_foil(
    clausula: ClausulaHorn,
    positivos_restantes: set[tuple[str, str]],
    negativos: set[tuple[str, str]],
    base: BaseConocimientoRelacional,
) -> tuple[float, set[tuple[str, str]]]:
    """Calcula la ganancia de información FOIL: Gain = t * (log2(p1/(p1+n1)) - log2(p0/(p0+n0)))."""
    p0 = len(positivos_restantes)
    n0 = len(negativos)
    if p0 == 0:
        return 0.0, set()

    cubiertos_pos = {(x, y) for (x, y) in positivos_restantes if clausula.evaluar_par(x, y, base)}
    cubiertos_neg = {(x, y) for (x, y) in negativos if clausula.evaluar_par(x, y, base)}

    p1 = len(cubiertos_pos)
    n1 = len(cubiertos_neg)

    if p1 == 0:
        return 0.0, set()

    ganancia = p1 * (math.log2(p1 / (p1 + n1)) - math.log2(p0 / (p0 + n0)))
    return ganancia, cubiertos_pos


class FOILLearner:
    """Inductor de programas lógicos mediante cubrimiento secuencial y especialización top-down."""

    def __init__(self, base_conocimiento: BaseConocimientoRelacional) -> None:
        self.base = base_conocimiento
        self._clausulas: list[ClausulaHorn] = []

    def entrenar_relacion(
        self,
        objetivo: str,
        positivos: set[tuple[str, str]],
        negativos: set[tuple[str, str]],
    ) -> list[ClausulaHorn]:
        """Aprende un conjunto de cláusulas de Horn para cubrir los ejemplos positivos."""
        self._clausulas.clear()
        por_cubrir = set(positivos)

        # Plantillas de cadenas para relaciones secuenciales transitivas
        candidatos = [
            # Longitud 1: despues(X, Y)
            [("despues", "X", "Y")],
            # Longitud 2: despues(X, Z), despues(Z, Y)
            [("despues", "X", "Z"), ("despues", "Z", "Y")],
            # Longitud 3: despues(X, Z), despues(Z, W), despues(W, Y)
            [
                ("despues", "X", "Z"),
                ("despues", "Z", "W"),
                ("despues", "W", "Y"),
            ],
        ]

        while por_cubrir:
            mejor_clausula: ClausulaHorn | None = None
            mejor_ganancia = -1.0
            mejores_cubiertos: set[tuple[str, str]] = set()

            for plantilla in candidatos:
                cl = ClausulaHorn(cabeza=objetivo, cuerpo_literales=plantilla)
                g, cubiertos = calcular_ganancia_foil(cl, por_cubrir, negativos, self.base)
                if g > mejor_ganancia:
                    mejor_ganancia = g
                    mejor_clausula = cl
                    mejores_cubiertos = cubiertos

            if not mejor_clausula or not mejores_cubiertos:
                break

            self._clausulas.append(mejor_clausula)
            por_cubrir -= mejores_cubiertos

        return list(self._clausulas)

    def probar(self, objetivo: str, x: str, y: str) -> bool:
        """Verifica si el objetivo(x, y) es deducible a partir de las cláusulas aprendidas."""
        return any(
            cl.evaluar_par(x, y, self.base) for cl in self._clausulas if cl.cabeza == objetivo
        )
