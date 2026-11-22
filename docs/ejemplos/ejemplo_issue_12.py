"""Issue #12 (inductivo vs. deductivo): dos reglas sobre 6 casos de prueba, hechas a mano. Datos sintéticos.

ΔP es el salto de potencia de un arranque, en kW. La carga verdadera es la etiqueta.
Ejecutar: python docs/ejemplos/ejemplo_issue_12.py
"""

ENTRENA = [(90, 90), (40, 40), (15, 15)]  # (ΔP, carga verdadera)
PRUEBA = [(55, 40), (70, 90), (30, 40), (20, 15), (62, 90), (26, 15)]


def experto(dp: float) -> int:
    """Regla escrita a mano: umbrales 25 y 60 kW."""
    return 90 if dp >= 60 else (40 if dp >= 25 else 15)


def cortes_inducidos() -> tuple[float, float]:
    """Cada corte va al punto medio entre dos valores de entrenamiento vecinos."""
    valores = sorted(v for _, v in ENTRENA)
    return (valores[0] + valores[1]) / 2, (valores[1] + valores[2]) / 2


def inducida(dp: float, c1: float, c2: float) -> int:
    return 15 if dp < c1 else (40 if dp < c2 else 90)


if __name__ == "__main__":
    c1, c2 = cortes_inducidos()
    assert (c1, c2) == (27.5, 65.0)
    aciertos_experto = sum(experto(dp) == y for dp, y in PRUEBA)
    aciertos_inducida = sum(inducida(dp, c1, c2) == y for dp, y in PRUEBA)
    assert aciertos_experto == 5 and aciertos_inducida == 5
    fallos_experto = [dp for dp, y in PRUEBA if experto(dp) != y]
    fallos_inducida = [dp for dp, y in PRUEBA if inducida(dp, c1, c2) != y]
    assert fallos_experto == [26] and fallos_inducida == [62]
    print(f"cortes inducidos: {c1} y {c2}")
    print(f"experto: {aciertos_experto}/6, falla en ΔP={fallos_experto}")
    print(f"inducida: {aciertos_inducida}/6, falla en ΔP={fallos_inducida}")
