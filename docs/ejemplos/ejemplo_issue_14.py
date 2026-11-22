"""Issue #14 (FOIL): cláusulas para «dependiente(X, Y)» con 4 equipos. Datos sintéticos.

Hechos de fondo: despues(X, Y) = el equipo X arranca después del equipo Y.
A = compresor, B = bomba, C = ventilador, D = luz.
Ganancia FOIL de un literal: t · (log2(p1/(p1+n1)) − log2(p0/(p0+n0))), con t = positivos que siguen cubiertos.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_14.py
"""

import math

EQUIPOS = "ABCD"
DESPUES = {("A", "B"), ("C", "A"), ("D", "C")}
POS = {("A", "B"), ("C", "A"), ("C", "B"), ("D", "C"), ("D", "A"), ("D", "B")}
NEG = {(x, y) for x in EQUIPOS for y in EQUIPOS if x != y} - POS


def cl1(x, y):  # dependiente(X,Y) :- despues(X,Y)
    return (x, y) in DESPUES


def cl2(x, y):  # dependiente(X,Y) :- despues(X,Z), despues(Z,Y)
    return any((x, z) in DESPUES and (z, y) in DESPUES for z in EQUIPOS)


def cl3(x, y):  # dependiente(X,Y) :- despues(X,Z), despues(Z,W), despues(W,Y)
    return any(
        (x, z) in DESPUES and (z, w) in DESPUES and (w, y) in DESPUES
        for z in EQUIPOS
        for w in EQUIPOS
    )


def ganancia(cubre, pos_restantes, neg):
    """Ganancia FOIL del literal que agrega 'cubre' a una cláusula que cubre todos los negativos."""
    p0, n0 = len(pos_restantes), len(neg)
    p1 = sum(cubre(*e) for e in pos_restantes)
    n1 = sum(cubre(*e) for e in neg)
    if p1 == 0:
        return 0.0
    return p1 * (math.log2(p1 / (p1 + n1)) - math.log2(p0 / (p0 + n0)))


if __name__ == "__main__":
    assert len(POS) == 6 and len(NEG) == 6
    g1 = ganancia(cl1, POS, NEG)
    print(f"ganancia de despues(X,Y) sobre el conjunto completo: {g1:.2f}")
    assert abs(g1 - 3.00) < 0.01
    pos_restantes = {e for e in POS if not cl1(*e)}
    print("positivos que quedan tras la primera cláusula:", sorted(pos_restantes))
    g2 = ganancia(cl2, pos_restantes, NEG)
    print(f"ganancia de despues(X,Z), despues(Z,Y) sobre lo que queda: {g2:.2f}")
    assert abs(g2 - 3.17) < 0.01
    pos_restantes = {e for e in pos_restantes if not cl2(*e)}
    print("positivos que siguen sin cubrir:", sorted(pos_restantes))
    assert pos_restantes == {("D", "B")}
    assert not any(cl1(*e) or cl2(*e) or cl3(*e) for e in NEG)
    assert all(cl1(*e) or cl2(*e) or cl3(*e) for e in POS)
    print("con las tres cláusulas: cubre los 6 positivos y ningún negativo")
