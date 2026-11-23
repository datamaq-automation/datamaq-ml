"""Issue #19 (algoritmo genético): horarios de arranque para bajar la demanda máxima. Datos sintéticos.

4 cargas (kW) y 4 horas. Cada individuo es una lista: hora de arranque de cada carga.
La demanda de cada hora es la base de esa hora más las cargas que arrancan en ella. Se minimiza la máxima.
Fuerza bruta (4^4 = 256 combinaciones) como referencia. Semilla fija para que sea reproducible.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_19.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.domain.cargas.algoritmo_genetico import (  # noqa: E402
    OptimizadorHorariosGenetico,
    calcular_demanda_maxima,
    resolver_fuerza_bruta,
)

CARGAS = (90, 40, 25, 15)  # horno, compresor, luz, bomba (kW)
BASE = (20, 30, 50, 40)  # demanda de base por hora (kW)


if __name__ == "__main__":
    bruta_horarios, bruta_pico = resolver_fuerza_bruta(CARGAS, BASE)

    opt = OptimizadorHorariosGenetico(
        cargas=CARGAS,
        base=BASE,
        tam_poblacion=12,
        generaciones=40,
        tasa_mutacion=0.1,
        elitismo=2,
        semilla=1,
    )
    resultado = opt.optimizar()

    print(
        f"sin optimizar (todas a la hora 0): {calcular_demanda_maxima((0, 0, 0, 0), CARGAS, BASE):.0f} kW"
    )
    print(f"fuerza bruta: horarios {bruta_horarios}, máximo {bruta_pico:.0f} kW")
    print(f"genético:     horarios {resultado.horarios}, máximo {resultado.demanda_pico:.0f} kW")
    assert resultado.demanda_pico == bruta_pico
