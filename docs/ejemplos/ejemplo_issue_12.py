"""Issue #12 (inductivo vs. deductivo): dos reglas sobre 6 casos de prueba, hechas a mano. Datos sintéticos.

ΔP es el salto de potencia de un arranque, en kW. La carga verdadera es la etiqueta.
Ejecutar: python docs/ejemplos/ejemplo_issue_12.py
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

ENTRENA = [(90.0, 90), (40.0, 40), (15.0, 15)]  # (ΔP, carga verdadera)
PRUEBA = [(55.0, 40), (70.0, 90), (30.0, 40), (20.0, 15), (62.0, 90), (26.0, 15)]


def experto(dp: float) -> int:
    """Regla deductiva escrita a mano por el experto: umbrales 25 y 60 kW."""
    return 90 if dp >= 60 else (40 if dp >= 25 else 15)


def cortes_inducidos(
    entrena: list[tuple[float, int]] | None = None,
) -> tuple[float, float]:
    """Cada corte inductivo se sitúa a mitad de camino entre dos valores de entrenamiento vecinos."""
    datos = entrena if entrena is not None else ENTRENA
    valores = sorted(v for v, _ in datos)
    if len(valores) < 3:
        raise ValueError("Se requieren al menos 3 ejemplos para inducir 2 cortes.")
    return (valores[0] + valores[1]) / 2, (valores[1] + valores[2]) / 2


def inducida(dp: float, c1: float, c2: float) -> int:
    """Regla inductiva aprendida de los datos: clasifica según los cortes c1 y c2."""
    return 15 if dp < c1 else (40 if dp < c2 else 90)


def evaluar_clasificador(
    casos: list[tuple[float, int]],
    clasificador: Callable[[float], int],
) -> dict[str, Any]:
    """Evalúa un clasificador sobre una serie de casos de prueba."""
    aciertos = 0
    fallos: list[tuple[float, int, int]] = []
    for dp, y in casos:
        pred = clasificador(dp)
        if pred == y:
            aciertos += 1
        else:
            fallos.append((dp, pred, y))
    total = len(casos)
    return {
        "total": total,
        "aciertos": aciertos,
        "exactitud": aciertos / total if total > 0 else 0.0,
        "fallos": fallos,
    }


def matriz_confusion_3x3(
    casos: list[tuple[float, int]],
    clasificador: Callable[[float], int],
    clases: list[int] | None = None,
) -> dict[tuple[int, int], int]:
    """Genera la matriz de confusión como diccionario (verdad, predicción) -> conteo."""
    etiquetas = clases if clases is not None else [15, 40, 90]
    matriz: dict[tuple[int, int], int] = {(v, p): 0 for v in etiquetas for p in etiquetas}
    for dp, y in casos:
        pred = clasificador(dp)
        if (y, pred) in matriz:
            matriz[(y, pred)] += 1
    return matriz


if __name__ == "__main__":
    c1, c2 = cortes_inducidos()
    assert (c1, c2) == (27.5, 65.0)

    res_exp = evaluar_clasificador(PRUEBA, experto)
    res_ind = evaluar_clasificador(PRUEBA, lambda dp: inducida(dp, c1, c2))

    assert res_exp["aciertos"] == 5 and res_ind["aciertos"] == 5
    fallos_exp = [dp for dp, _, _ in res_exp["fallos"]]
    fallos_ind = [dp for dp, _, _ in res_ind["fallos"]]
    assert fallos_exp == [26.0] and fallos_ind == [62.0]

    print(f"cortes inducidos: {c1} y {c2}")
    print(f"experto: {res_exp['aciertos']}/6, falla en ΔP={fallos_exp}")
    print(f"inducida: {res_ind['aciertos']}/6, falla en ΔP={fallos_ind}")
    print("\nTabla de Comparación:")
    print("ΔP\tVerdad\tExperto\tInducida")
    for dp, y in PRUEBA:
        exp_ok = "✔" if experto(dp) == y else "✘"
        ind_ok = "✔" if inducida(dp, c1, c2) == y else "✘"
        print(f"{dp}\t{y}\t{experto(dp)} {exp_ok}\t{inducida(dp, c1, c2)} {ind_ok}")
