"""Issue #18 (Q-learning tabular): cuándo arrancar un equipo. Datos sintéticos, sin librerías de refuerzo.

Dos estados (valle y pico de tarifa), dos acciones (arrancar, esperar). Transiciones deterministas:
valle → pico → valle. Recompensa de arrancar: +2 en valle (ahorro); r_pico en pico (costo).
Analítico (γ = 0,9): V(valle) = 2 / (1 − γ²) = 10,526 si r_pico = −5; 15,263 si r_pico = +1.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_18.py
"""

import random

GAMMA = 0.9
ESTADOS = ("valle", "pico")
ACCIONES = ("arrancar", "esperar")


def recompensa(estado, accion, r_pico):
    if accion == "esperar":
        return 0.0
    return 2.0 if estado == "valle" else r_pico


def siguiente(estado):
    return "pico" if estado == "valle" else "valle"


def entrenar(r_pico, pasos=20000, alfa=0.1, epsilon=0.2, semilla=0):
    rng = random.Random(semilla)
    q = {(e, a): 0.0 for e in ESTADOS for a in ACCIONES}
    estado = "valle"
    for _ in range(pasos):
        if rng.random() < epsilon:
            accion = rng.choice(ACCIONES)
        else:
            accion = max(ACCIONES, key=lambda x: q[(estado, x)])
        r = recompensa(estado, accion, r_pico)
        s2 = siguiente(estado)
        q[(estado, accion)] += alfa * (
            r + GAMMA * max(q[(s2, b)] for b in ACCIONES) - q[(estado, accion)]
        )
        estado = s2
    politica = {e: max(ACCIONES, key=lambda x: q[(e, x)]) for e in ESTADOS}
    return q, politica


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
    print("cambiar la recompensa en pico cambia la política en pico")
