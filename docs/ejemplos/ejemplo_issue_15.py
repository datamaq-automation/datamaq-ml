"""Issue #15 (pronóstico con partición temporal). Serie sintética de 10 días de energía diaria (kWh, inventada).

Partición temporal: los primeros 7 días entrenan y los últimos 3 prueban. Nunca se mezcla el orden.
Tres pronósticos sencillos: promedio histórico, último valor y tendencia lineal en el tiempo.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_15.py
"""

import math

SERIE = [100, 104, 99, 105, 101, 107, 102, 108, 104, 110]  # kWh por día, sintéticos
ENTRENA, PRUEBA = SERIE[:7], SERIE[7:]


def promedio(entrena, horizonte):
    return [sum(entrena) / len(entrena)] * horizonte


def ultimo_valor(entrena, horizonte):
    return [entrena[-1]] * horizonte


def tendencia(entrena, horizonte):
    """Recta de mínimos cuadrados sobre el índice del día."""
    n = len(entrena)
    t_medio = (n - 1) / 2
    y_medio = sum(entrena) / n
    pendiente = sum((t - t_medio) * (y - y_medio) for t, y in enumerate(entrena)) / sum(
        (t - t_medio) ** 2 for t in range(n)
    )
    ordenada = y_medio - pendiente * t_medio
    return [ordenada + pendiente * t for t in range(n, n + horizonte)]


def mae(real, previsto):
    return sum(abs(r - p) for r, p in zip(real, previsto, strict=False)) / len(real)


def rmse(real, previsto):
    return math.sqrt(sum((r - p) ** 2 for r, p in zip(real, previsto, strict=False)) / len(real))


if __name__ == "__main__":
    resultados = {}
    for nombre, modelo in (
        ("promedio", promedio),
        ("último valor", ultimo_valor),
        ("tendencia", tendencia),
    ):
        previsto = modelo(ENTRENA, len(PRUEBA))
        resultados[nombre] = (mae(PRUEBA, previsto), rmse(PRUEBA, previsto))
        print(
            f"{nombre:>13}: pronóstico {[round(p, 2) for p in previsto]}  MAE {resultados[nombre][0]:.2f}  RMSE {resultados[nombre][1]:.2f}"
        )
    print(f"prueba real: {PRUEBA}")
