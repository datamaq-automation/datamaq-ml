"""Issue #18 (Q-learning tabular): cuándo arrancar un equipo. Datos sintéticos, sin librerías de refuerzo.

Dos estados (valle y pico de tarifa), dos acciones (arrancar, esperar). Transiciones deterministas:
valle → pico → valle. Recompensa de arrancar: +2 en valle (ahorro); r_pico en pico (costo).
Analítico (γ = 0,9): V(valle) = 2 / (1 − γ²) = 10,526 si r_pico = −5; 15,263 si r_pico = +1.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_18.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.domain.cargas.refuerzo_qlearning import (  # noqa: E402
    AgenteQLearningTabular,
    EntornoTarifaHoraria,
)


def entrenar(
    r_pico: float, pasos: int = 20000, alfa: float = 0.1, epsilon: float = 0.2, semilla: int = 0
):
    env = EntornoTarifaHoraria(r_pico=r_pico, recompensa_valle=2.0)
    agente = AgenteQLearningTabular(alfa=alfa, gamma=0.9, epsilon=epsilon, semilla=semilla)
    agente.entrenar(env, pasos=pasos)
    return agente.obtener_tabla_q(), agente.obtener_politica()


if __name__ == "__main__":
    q, pol = entrenar(r_pico=-5.0)
    print(
        f"r_pico = -5: Q(valle, arrancar) = {q[('valle', 'arrancar')]:.2f} (analítico 10,53); política {pol}"
    )
    assert abs(q[("valle", "arrancar")] - 10.526) < 0.5 and pol == {
        "valle": "arrancar",
        "pico": "esperar",
    }
    q, pol = entrenar(r_pico=1.0)
    print(
        f"r_pico = +1: Q(valle, arrancar) = {q[('valle', 'arrancar')]:.2f} (analítico 15,26); política {pol}"
    )
    assert abs(q[("valle", "arrancar")] - 15.263) < 0.5 and pol == {
        "valle": "arrancar",
        "pico": "arrancar",
    }
