"""Issue #19 (algoritmo genético): horarios de arranque para bajar la demanda máxima. Datos sintéticos.

4 cargas (kW) y 4 horas. Cada individuo es una lista: hora de arranque de cada carga.
La demanda de cada hora es la base de esa hora más las cargas que arrancan en ella. Se minimiza la máxima.
Fuerza bruta (4^4 = 256 combinaciones) como referencia. Semilla fija para que sea reproducible.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_19.py
"""

import itertools
import random

CARGAS = (90, 40, 25, 15)  # horno, compresor, luz, bomba (kW)
BASE = (20, 30, 50, 40)  # demanda de base por hora (kW)
HORAS = len(BASE)


def demanda_maxima(horarios):
    demanda = list(BASE)
    for carga, h in zip(CARGAS, horarios, strict=False):
        demanda[h] += carga
    return max(demanda)


def fuerza_bruta():
    return min(itertools.product(range(HORAS), repeat=len(CARGAS)), key=demanda_maxima)


def genetico(semilla=1, poblacion=12, generaciones=40, mutacion=0.1):
    rng = random.Random(semilla)
    pob = [[rng.randrange(HORAS) for _ in CARGAS] for _ in range(poblacion)]
    for _ in range(generaciones):
        pob.sort(key=demanda_maxima)
        nueva = pob[:2]  # elitismo: los dos mejores pasan tal cual
        while len(nueva) < poblacion:
            padre = min(rng.sample(pob, 2), key=demanda_maxima)
            madre = min(rng.sample(pob, 2), key=demanda_maxima)
            corte = rng.randrange(1, len(CARGAS))
            hijo = padre[:corte] + madre[corte:]
            hijo = [rng.randrange(HORAS) if rng.random() < mutacion else g for g in hijo]
            nueva.append(hijo)
        pob = nueva
    return min(pob, key=demanda_maxima)


if __name__ == "__main__":
    bruta = fuerza_bruta()
    gen = genetico()
    print(f"sin optimizar (todas a la hora 0): {demanda_maxima((0, 0, 0, 0))} kW")
    print(f"fuerza bruta: horarios {bruta}, máximo {demanda_maxima(bruta)} kW")
    print(f"genético:     horarios {tuple(gen)}, máximo {demanda_maxima(gen)} kW")
    assert demanda_maxima(gen) == demanda_maxima(bruta)
