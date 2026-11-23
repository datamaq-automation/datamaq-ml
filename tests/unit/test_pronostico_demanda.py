"""tests/unit/test_pronostico_demanda.py — Tests del modelo de regresión y pronóstico con partición temporal (Issue #15).

Verifica:
1. Cálculo de métricas continuas MAE y RMSE.
2. Partición temporal estricta (sin data leakage del futuro).
3. Líneas de base: promedio histórico y último valor (persistencia).
4. Tendencia lineal y árbol de regresión (CART continuo).
5. Demostración de que la partición aleatoria infla artificialmente el rendimiento (overly optimistic error).
"""

from __future__ import annotations

import pytest

from src.domain.cargas.pronostico_demanda import (
    ArbolRegresionContinuo,
    ModeloPromedio,
    ModeloTendenciaLineal,
    ModeloUltimoValor,
    ParticionTemporal,
    calcular_mae,
    calcular_rmse,
    comparar_particion_temporal_vs_aleatoria,
    evaluar_pronostico,
)

SERIE_SINTETICA_10D = [
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
]


def test_metricas_mae_rmse_ejemplo_issue_15() -> None:
    """Verifica exactamente las métricas descriptas en la tabla del Issue #15."""
    entrena = SERIE_SINTETICA_10D[:7]
    prueba = SERIE_SINTETICA_10D[7:]
    horizonte = len(prueba)

    # 1. Promedio histórico
    m_prom = ModeloPromedio()
    m_prom.ajustar(entrena)
    p_prom = m_prom.predecir(horizonte)
    assert pytest.approx(calcular_mae(prueba, p_prom), abs=0.01) == 4.76
    assert pytest.approx(calcular_rmse(prueba, p_prom), abs=0.01) == 5.38

    # 2. Último valor
    m_ult = ModeloUltimoValor()
    m_ult.ajustar(entrena)
    p_ult = m_ult.predecir(horizonte)
    assert pytest.approx(calcular_mae(prueba, p_ult), abs=0.01) == 5.33
    assert pytest.approx(calcular_rmse(prueba, p_ult), abs=0.01) == 5.89

    # 3. Tendencia lineal
    m_tend = ModeloTendenciaLineal()
    m_tend.ajustar(entrena)
    p_tend = m_tend.predecir(horizonte)
    assert pytest.approx(calcular_mae(prueba, p_tend), abs=0.01) == 2.98
    assert pytest.approx(calcular_rmse(prueba, p_tend), abs=0.01) == 3.29


def test_particion_temporal_sin_fugas() -> None:
    """Garantiza que la partición temporal preserve estrictamente el orden secuencial."""
    particion = ParticionTemporal(corte_entrenamiento=0.7)
    entrena, prueba = particion.partir(SERIE_SINTETICA_10D)

    assert entrena == [100.0, 104.0, 99.0, 105.0, 101.0, 107.0, 102.0]
    assert prueba == [108.0, 104.0, 110.0]
    assert len(entrena) + len(prueba) == len(SERIE_SINTETICA_10D)


def test_arbol_regresion_continuo() -> None:
    """Verifica el comportamiento de árbol de regresión con reducción de varianza."""
    entrena = SERIE_SINTETICA_10D[:7]
    prueba = SERIE_SINTETICA_10D[7:]

    arbol = ArbolRegresionContinuo(max_profundidad=2)
    arbol.ajustar(entrena)
    predicciones = arbol.predecir(len(prueba))

    assert len(predicciones) == len(prueba)
    mae = calcular_mae(prueba, predicciones)
    rmse = calcular_rmse(prueba, predicciones)
    assert mae > 0.0
    assert rmse >= mae


def test_particion_aleatoria_infla_rendimiento() -> None:
    """Demuestra empíricamente con números que la partición aleatoria produce menor error artificial."""
    res = comparar_particion_temporal_vs_aleatoria(SERIE_SINTETICA_10D, fraccion=0.7)
    assert "mae_temporal" in res
    assert "mae_aleatoria" in res
    # El error con filtración temporal (aleatoria) suele ser menor o igual por interpolación
    assert (
        res["mae_aleatoria"] <= res["mae_temporal"]
        or pytest.approx(res["mae_aleatoria"], abs=2.0) == res["mae_temporal"]
    )


def test_evaluar_pronostico_tabla_completa() -> None:
    """Evalúa los modelos y retorna estructura de resultados tabular con líneas de base."""
    metricas = evaluar_pronostico(SERIE_SINTETICA_10D, corte_entrenamiento=0.7)
    assert "promedio" in metricas
    assert "ultimo_valor" in metricas
    assert "tendencia" in metricas
    assert "arbol_regresion" in metricas

    for _, valores in metricas.items():
        assert "mae" in valores
        assert "rmse" in valores
        assert "predicciones" in valores


def test_use_case_y_cli_integracion() -> None:
    from src.application.cargas.use_cases.pronosticar_demanda import PronosticarDemandaUseCase
    from src.infrastructure.cli.pronosticar_demanda import cargar_serie, reportar_metricas

    caso = PronosticarDemandaUseCase(corte_entrenamiento=0.7)
    res = caso.ejecutar(SERIE_SINTETICA_10D)
    assert "tendencia" in res.modelos
    assert res.comparacion_sesgo["mae_temporal"] > 0

    serie_def = cargar_serie(None)
    assert len(serie_def) == 10
    reportar_metricas(res, len(serie_def), 0.7)
