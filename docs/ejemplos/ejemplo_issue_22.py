"""Issue #22 (programa, mapa y rúbrica): horas de trabajo de los issues contra el plan de 4 h semanales.

Las horas salen de la sección «Tiempo estimado» de cada issue (rango mínimo y máximo). Número de semanas
del módulo: supuesto a confirmar con el docente (aquí 16 semanas).
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_22.py
"""

from __future__ import annotations

from typing import Any

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


def calcular_horas_totales(
    estimaciones: dict[int, tuple[int, int]],
) -> tuple[int, int]:
    """Calcula la suma de horas mínimas y máximas de los issues."""
    minimo = sum(lo for lo, _ in estimaciones.values())
    maximo = sum(hi for _, hi in estimaciones.values())
    return minimo, maximo


def calcular_presupuesto_semanas(
    horas_min: int, horas_max: int, horas_por_semana: int = 4
) -> tuple[float, float]:
    """Calcula el rango de semanas necesarias para cubrir las horas estimadas."""
    if horas_por_semana <= 0:
        raise ValueError("Las horas por semana deben ser positivas.")
    return horas_min / horas_por_semana, horas_max / horas_por_semana


def distribuir_plan_16_semanas(
    estimaciones: dict[int, tuple[int, int]],
) -> list[dict[str, Any]]:
    """Distribuye los temas e issues en un plan semestral de 16 semanas x 4 h reloj presenciales.

    El exceso de horas (trabajo autónomo, lectura y preparación de entregas) se balancea
    en horas de taller asincrónico fuera del aula.
    """
    cronograma_tematico = [
        (1, "Introducción al NILM, tablero sintético y entorno", 29, 0),
        (2, "Aprendizaje inductivo vs. deductivo", 12, 1),
        (3, "Clasificación con árboles de decisión (CART) y Naive Bayes", 12, 1),
        (4, "Espacio de versiones y reglas conjuntivas", 13, 2),
        (5, "Algoritmo AQ y cobertura de reglas", 13, 2),
        (6, "Programación lógica inductiva y algoritmo FOIL", 14, 2),
        (7, "Ajuste de modelos, sobreajuste y validación cruzada", 16, 2),
        (8, "Regresión y predicción de series temporales de demanda", 15, 2),
        (9, "Clustering no supervisado por densidad (DBSCAN)", 17, 1),
        (10, "Estrategia aglomerativa (jerárquica) y dendrograma", 17, 1),
        (11, "Aprendizaje por refuerzo y Q-learning tabular", 18, 2),
        (12, "Algoritmos genéticos y optimización de horarios", 19, 2),
        (13, "Protocolo de validación sin verdad de terreno", 20, 1),
        (14, "Secuencias de análisis: librerías propias vs. externas", 21, 2),
        (15, "Evaluación integradora y contraste con datos reales T1/T2", 20, 1),
        (16, "Cierre de proyectos, rúbrica final y retroalimentación", 22, 1),
    ]

    plan: list[dict[str, Any]] = []
    for semana, tema, issue_ppal, horas_asincronicas in cronograma_tematico:
        plan.append(
            {
                "semana": semana,
                "tema": tema,
                "issue": issue_ppal,
                "horas_presenciales": 4,
                "horas_asincronicas": horas_asincronicas,
            }
        )
    return plan


if __name__ == "__main__":
    minimo, maximo = calcular_horas_totales(ESTIMACIONES)
    disponible = HORAS_POR_SEMANA * SEMANAS
    semanas_min, semanas_max = calcular_presupuesto_semanas(minimo, maximo, HORAS_POR_SEMANA)

    print(f"horas estimadas de los issues: {minimo} a {maximo}")
    print(f"horas disponibles en {SEMANAS} semanas a {HORAS_POR_SEMANA} h: {disponible}")
    print(f"semanas necesarias: {semanas_min:.1f} a {semanas_max:.1f}")

    assert (minimo, maximo) == (65, 87)
    assert maximo > disponible, "si el máximo entra en el plazo, no hay que recortar"
    print("el programa no entra en 16 semanas: hace falta recortar o alargar el plazo")

    plan = distribuir_plan_16_semanas(ESTIMACIONES)
    print(
        f"plan distribuido: {len(plan)} semanas, total presencial {sum(p['horas_presenciales'] for p in plan)} h"
    )
