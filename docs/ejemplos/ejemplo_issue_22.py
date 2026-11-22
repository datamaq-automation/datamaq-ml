"""Issue #22 (programa, mapa y rúbrica): horas de trabajo de los issues contra el plan de 4 h semanales.

Las horas salen de la sección «Tiempo estimado» de cada issue (rango mínimo y máximo). Número de semanas
del módulo: supuesto a confirmar con el docente (aquí 16 semanas).
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_22.py
"""

HORAS_POR_SEMANA = 4
SEMANAS = 16

ESTIMACIONES = {  # issue: (mínimo, máximo) en horas
    12: (4, 6),
    13: (8, 10),
    14: (6, 8),
    15: (6, 8),
    16: (6, 8),
    17: (4, 5),
    18: (6, 8),
    19: (6, 8),
    20: (4, 6),
    21: (6, 8),
    22: (8, 10),
    23: (1, 2),
}

if __name__ == "__main__":
    minimo = sum(lo for lo, _ in ESTIMACIONES.values())
    maximo = sum(hi for _, hi in ESTIMACIONES.values())
    disponible = HORAS_POR_SEMANA * SEMANAS
    semanas_min = minimo / HORAS_POR_SEMANA
    semanas_max = maximo / HORAS_POR_SEMANA
    print(f"horas estimadas de los issues: {minimo} a {maximo}")
    print(f"horas disponibles en {SEMANAS} semanas a {HORAS_POR_SEMANA} h: {disponible}")
    print(f"semanas necesarias: {semanas_min:.1f} a {semanas_max:.1f}")
    assert (minimo, maximo) == (65, 87)
    assert maximo > disponible, "si el máximo entra en el plazo, no hay que recortar"
    print("el programa no entra en 16 semanas: hace falta recortar o alargar el plazo")
