"""Issue #15 (pronóstico con partición temporal). Serie sintética de 10 días de energía diaria (kWh, inventada).

Partición temporal: los primeros 7 días entrenan y los últimos 3 prueban. Nunca se mezcla el orden.
Tres pronósticos sencillos: promedio histórico, último valor y tendencia lineal en el tiempo.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_15.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.domain.cargas.pronostico_demanda import (  # noqa: E402
    ArbolRegresionContinuo,
    ModeloPromedio,
    ModeloTendenciaLineal,
    ModeloUltimoValor,
    calcular_mae,
    calcular_rmse,
    comparar_particion_temporal_vs_aleatoria,
)

SERIE = [
    100.0,
    104.0,
    99.0,
    105.0,
    101.0,
    107.0,
    102.0,
    108.0,
    104.0,
    110.0,
]  # kWh por día, sintéticos
ENTRENA, PRUEBA = SERIE[:7], SERIE[7:]


if __name__ == "__main__":
    horizonte = len(PRUEBA)

    # 1. Promedio histórico
    m_prom = ModeloPromedio()
    m_prom.ajustar(ENTRENA)
    prev_prom = m_prom.predecir(horizonte)
    mae_prom = calcular_mae(PRUEBA, prev_prom)
    rmse_prom = calcular_rmse(PRUEBA, prev_prom)
    print(
        f"{'promedio':>13}: pronóstico {[round(p, 2) for p in prev_prom]}  MAE {mae_prom:.2f}  RMSE {rmse_prom:.2f}"
    )
    assert abs(mae_prom - 4.76) < 0.01
    assert abs(rmse_prom - 5.38) < 0.01

    # 2. Último valor (persistencia)
    m_ult = ModeloUltimoValor()
    m_ult.ajustar(ENTRENA)
    prev_ult = m_ult.predecir(horizonte)
    mae_ult = calcular_mae(PRUEBA, prev_ult)
    rmse_ult = calcular_rmse(PRUEBA, prev_ult)
    print(
        f"{'último valor':>13}: pronóstico {[round(p, 2) for p in prev_ult]}  MAE {mae_ult:.2f}  RMSE {rmse_ult:.2f}"
    )
    assert abs(mae_ult - 5.33) < 0.01
    assert abs(rmse_ult - 5.89) < 0.01

    # 3. Tendencia lineal
    m_tend = ModeloTendenciaLineal()
    m_tend.ajustar(ENTRENA)
    prev_tend = m_tend.predecir(horizonte)
    mae_tend = calcular_mae(PRUEBA, prev_tend)
    rmse_tend = calcular_rmse(PRUEBA, prev_tend)
    print(
        f"{'tendencia':>13}: pronóstico {[round(p, 2) for p in prev_tend]}  MAE {mae_tend:.2f}  RMSE {rmse_tend:.2f}"
    )
    assert abs(mae_tend - 2.98) < 0.01
    assert abs(rmse_tend - 3.29) < 0.01

    # 4. Árbol de regresión continuo
    m_arbol = ArbolRegresionContinuo(max_profundidad=2)
    m_arbol.ajustar(ENTRENA)
    prev_arbol = m_arbol.predecir(horizonte)
    mae_arbol = calcular_mae(PRUEBA, prev_arbol)
    rmse_arbol = calcular_rmse(PRUEBA, prev_arbol)
    print(
        f"{'árbol CART':>13}: pronóstico {[round(p, 2) for p in prev_arbol]}  MAE {mae_arbol:.2f}  RMSE {rmse_arbol:.2f}"
    )

    print(f"prueba real: {PRUEBA}")

    # Demostración del efecto de la partición aleatoria vs temporal
    sesgo = comparar_particion_temporal_vs_aleatoria(SERIE, fraccion=0.7)
    print(
        f"Sesgo: MAE temporal = {sesgo['mae_temporal']:.2f} vs MAE aleatorio = {sesgo['mae_aleatoria']:.2f}"
    )
    assert sesgo["mae_aleatoria"] < sesgo["mae_temporal"]
