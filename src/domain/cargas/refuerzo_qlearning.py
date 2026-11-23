"""src/domain/cargas/refuerzo_qlearning.py — Aprendizaje por Refuerzo: entorno mínimo y Q-learning tabular.

Implementa un proceso de decisión de Markov (MDP) discreto para despacho horario de cargas bajo tarifas
diferenciales (valle y pico), actualización analítica de Bellman y agente Q-learning con política épsilon-voraz.
Cero dependencias externas (Clean Architecture).
"""

from __future__ import annotations

import random
from typing import Literal

EstadoTarifa = Literal["valle", "pico"]
AccionCarga = Literal["arrancar", "esperar"]

ESTADOS_TARIFA: tuple[EstadoTarifa, ...] = ("valle", "pico")
ACCIONES_CARGA: tuple[AccionCarga, ...] = ("arrancar", "esperar")


def calcular_valor_analitico_valle(r_valle: float, r_pico: float, gamma: float = 0.9) -> float:
    """Calcula el valor esperado óptimo de Bellman en estado valle para un ciclo de 2 pasos."""
    denom = 1.0 - (gamma**2)
    if denom == 0.0:
        return 0.0
    return (r_valle + gamma * r_pico) / denom


class EntornoTarifaHoraria:
    """Entorno determinista de dos estados horarios: valle (tarifa baja) y pico (tarifa alta)."""

    def __init__(self, r_pico: float = -5.0, recompensa_valle: float = 2.0) -> None:
        self.r_pico = r_pico
        self.recompensa_valle = recompensa_valle
        self.estado_actual: EstadoTarifa = "valle"

    def reiniciar(self) -> EstadoTarifa:
        self.estado_actual = "valle"
        return self.estado_actual

    def paso(self, accion: AccionCarga) -> tuple[float, EstadoTarifa]:
        """Ejecuta una acción, computa la recompensa inmediata y transiciona al siguiente estado."""
        if accion == "esperar":
            recompensa = 0.0
        else:
            recompensa = self.recompensa_valle if self.estado_actual == "valle" else self.r_pico

        # Alternancia determinista de franjas horarias
        siguiente: EstadoTarifa = "pico" if self.estado_actual == "valle" else "valle"
        self.estado_actual = siguiente
        return recompensa, siguiente


class AgenteQLearningTabular:
    """Agente que aprende una política óptima mediante la regla de actualización temporal de Bellman."""

    def __init__(
        self,
        alfa: float = 0.1,
        gamma: float = 0.9,
        epsilon: float = 0.2,
        semilla: int = 0,
    ) -> None:
        self.alfa = alfa
        self.gamma = gamma
        self.epsilon = epsilon
        self.semilla = semilla
        self._q: dict[tuple[EstadoTarifa, AccionCarga], float] = {
            (e, a): 0.0 for e in ESTADOS_TARIFA for a in ACCIONES_CARGA
        }

    def entrenar(self, entorno: EntornoTarifaHoraria, pasos: int = 20000) -> None:
        """Itera el bucle de interacción agente-entorno actualizando la tabla Q."""
        rng = random.Random(self.semilla)
        estado = entorno.reiniciar()

        for _ in range(pasos):
            # Exploración vs explotación épsilon-voraz
            if rng.random() < self.epsilon:
                accion = rng.choice(ACCIONES_CARGA)
            else:
                accion = max(
                    ACCIONES_CARGA,
                    key=lambda a: self._q[(estado, a)],
                )

            recompensa, s_siguiente = entorno.paso(accion)

            # Regla de actualización Q-learning de Bellman:
            # Q(s, a) <- Q(s, a) + alfa * [r + gamma * max_b Q(s', b) - Q(s, a)]
            q_actual = self._q[(estado, accion)]
            max_q_sig = max(self._q[(s_siguiente, b)] for b in ACCIONES_CARGA)
            td_error = recompensa + self.gamma * max_q_sig - q_actual
            self._q[(estado, accion)] = q_actual + self.alfa * td_error

            estado = s_siguiente

    def obtener_politica(self) -> dict[EstadoTarifa, AccionCarga]:
        """Retorna la acción voraz de mayor Q para cada estado."""
        return {e: max(ACCIONES_CARGA, key=lambda a: self._q[(e, a)]) for e in ESTADOS_TARIFA}

    def obtener_tabla_q(self) -> dict[tuple[EstadoTarifa, AccionCarga], float]:
        """Retorna una copia de la tabla Q aprendida."""
        return dict(self._q)
