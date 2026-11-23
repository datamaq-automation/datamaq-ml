"""Issue #14 (FOIL): cláusulas para «dependiente(X, Y)» con 4 equipos. Datos sintéticos.

Hechos de fondo: despues(X, Y) = el equipo X arranca después del equipo Y.
A = compresor, B = bomba, C = ventilador, D = luz.
Ganancia FOIL de un literal: t · (log2(p1/(p1+n1)) − log2(p0/(p0+n0))), con t = positivos que siguen cubiertos.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_14.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.domain.cargas.foil_learner import (  # noqa: E402
    BaseConocimientoRelacional,
    ClausulaHorn,
    FOILLearner,
    calcular_ganancia_foil,
)

EQUIPOS = ["A", "B", "C", "D"]
DESPUES = {("A", "B"), ("C", "A"), ("D", "C")}
POS = {("A", "B"), ("C", "A"), ("C", "B"), ("D", "C"), ("D", "A"), ("D", "B")}
NEG = {(x, y) for x in EQUIPOS for y in EQUIPOS if x != y} - POS


if __name__ == "__main__":
    assert len(POS) == 6 and len(NEG) == 6

    bc = BaseConocimientoRelacional(entidades=EQUIPOS)
    for x, y in DESPUES:
        bc.agregar_hecho("despues", x, y)

    # Cláusula 1: dependiente(X, Y) :- despues(X, Y)
    cl1 = ClausulaHorn("dependiente", [("despues", "X", "Y")])
    g1, cubiertos1 = calcular_ganancia_foil(cl1, POS, NEG, bc)
    print(f"ganancia de despues(X,Y) sobre el conjunto completo: {g1:.2f}")
    assert abs(g1 - 3.00) < 0.01

    pos_restantes = POS - cubiertos1
    print("positivos que quedan tras la primera cláusula:", sorted(pos_restantes))

    # Cláusula 2: dependiente(X, Y) :- despues(X, Z), despues(Z, Y)
    cl2 = ClausulaHorn("dependiente", [("despues", "X", "Z"), ("despues", "Z", "Y")])
    g2, cubiertos2 = calcular_ganancia_foil(cl2, pos_restantes, NEG, bc)
    print(f"ganancia de despues(X,Z), despues(Z,Y) sobre lo que queda: {g2:.2f}")
    assert abs(g2 - 3.17) < 0.01

    pos_restantes = pos_restantes - cubiertos2
    print("positivos que siguen sin cubrir:", sorted(pos_restantes))
    assert pos_restantes == {("D", "B")}

    # Cláusula 3: dependiente(X, Y) :- despues(X, Z), despues(Z, W), despues(W, Y)
    cl3 = ClausulaHorn(
        "dependiente",
        [
            ("despues", "X", "Z"),
            ("despues", "Z", "W"),
            ("despues", "W", "Y"),
        ],
    )
    g3, cubiertos3 = calcular_ganancia_foil(cl3, pos_restantes, NEG, bc)
    print(f"ganancia de despues(X,Z), despues(Z,W), despues(W,Y) sobre (D,B): {g3:.2f}")
    assert abs(g3 - 2.81) < 0.01

    # Inducción completa y verificación
    learner = FOILLearner(bc)
    clausulas = learner.entrenar_relacion("dependiente", POS, NEG)
    assert len(clausulas) == 3
    assert not any(learner.probar("dependiente", x, y) for x, y in NEG)
    assert all(learner.probar("dependiente", x, y) for x, y in POS)
    print("con las tres cláusulas: cubre los 6 positivos y ningún negativo")
