"""Issue #13 (algoritmo AQ): el paso de cubrimiento de una clase, con un atributo. Datos sintéticos.

AQ busca, para cada clase, un complejo (condición sobre ΔP) que cubra sus ejemplos positivos y ningún negativo.
Con un solo atributo, el complejo más general es el intervalo abierto entre el negativo más cercano por debajo
y el más cercano por encima de los positivos.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_13.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.domain.cargas.aq_learner import AQLearner, inducir_complejo_1d  # noqa: E402

EJEMPLOS = [(88, 90), (92, 90), (40, 40), (42, 40), (15, 15), (16, 15)]  # (ΔP en kW, clase en kW)
INF = float("inf")


def complejo(clase: int) -> tuple[float, float]:
    """Calcula el complejo más general 1D usando la función de dominio inducir_complejo_1d."""
    comp = inducir_complejo_1d([(float(dp), c) for dp, c in EJEMPLOS], clase_objetivo=clase)
    return comp.minimo, comp.maximo


def cubre(clase: int) -> tuple[list[int], list[int]]:
    """Positivos y negativos que caen dentro del complejo de la clase."""
    lo, hi = complejo(clase)
    dentro = [(dp, c) for dp, c in EJEMPLOS if lo < dp < hi]
    return sorted(dp for dp, c in dentro if c == clase), sorted(
        dp for dp, c in dentro if c != clase
    )


if __name__ == "__main__":
    assert complejo(90) == (42, INF)
    assert complejo(40) == (16, 88)
    assert complejo(15) == (-INF, 40)
    for clase in (90, 40, 15):
        positivos, negativos = cubre(clase)
        assert negativos == [], f"el complejo de {clase} cubre negativos: {negativos}"
        print(
            f"clase {clase} kW: complejo {complejo(clase)}, cubre positivos {positivos}, negativos {negativos}"
        )
    lo, hi = complejo(40)
    print(f"un arranque de 60 kW cae en el complejo de 40 kW ({lo} < 60 < {hi}): {lo < 60 < hi}")

    # Verificación con AQLearner
    modelo = AQLearner()
    modelo.entrenar([({"dp": float(dp)}, c) for dp, c in EJEMPLOS])
    pred_60 = modelo.predecir({"dp": 60.0})
    assert pred_60 == 40
    print(f"Predicción AQLearner para 60 kW: {pred_60} kW (correcto según cobertura)")
