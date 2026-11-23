"""tests/unit/test_protocolo_validacion.py — Tests del protocolo didáctico de validación (Issue #20).

Verifica el cálculo de cobertura, residuo por intervalo y las reglas de consistencia
didáctica para validación sin verdad de terreno.
"""

from __future__ import annotations

import pytest
from docs.ejemplos.ejemplo_issue_20 import (
    ATRIBUIDO,
    MEDIDO,
    calcular_cobertura,
    calcular_residuo,
    evaluar_consistencia_dia,
    intervalos_residuo_critico,
)


def test_ejemplo_issue_20_valores_nominales() -> None:
    """Verifica el ejemplo sintético del Issue #20 con 8 intervalos."""
    total_medido = sum(MEDIDO)
    total_atribuido = sum(ATRIBUIDO)
    cobertura = calcular_cobertura(MEDIDO, ATRIBUIDO)
    residuo = calcular_residuo(MEDIDO, ATRIBUIDO)
    criticos = intervalos_residuo_critico(residuo, umbral=0.5)

    assert total_medido == 24.0
    assert total_atribuido == 19.0
    assert round(cobertura, 3) == 0.792
    assert residuo == [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 3.0]
    assert criticos == [2, 3, 7]
    assert sum(residuo[i] for i in criticos) == 5.0


def test_evaluar_consistencia_dia_rechaza_residuo_concentrado() -> None:
    """El ejemplo de 79.2% de cobertura tiene residuo concentrado (>20% del total)."""
    es_valido, motivo = evaluar_consistencia_dia(MEDIDO, ATRIBUIDO)
    assert not es_valido
    assert "Residuo concentrado en intervalos [2, 3, 7]" in motivo


def test_evaluar_consistencia_dia_rechaza_energia_inventada() -> None:
    """Un día con 95% de cobertura global pero con energía inventada en un intervalo debe ser rechazado."""
    # 8 intervalos: 7 intervalos normales de 10 kWh donde se atribuye 10 kWh.
    # En el intervalo 7 se mide 10 kWh pero se atribuye 15 kWh.
    medido = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 30.0]
    atribuido = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 15.0, 20.0]  # total 95 vs 100 (95% cob)

    cobertura = calcular_cobertura(medido, atribuido)
    assert cobertura == 0.95

    es_valido, motivo = evaluar_consistencia_dia(medido, atribuido)
    assert not es_valido
    assert "Energía inventada en intervalo 6" in motivo


def test_evaluar_consistencia_dia_acepta_dia_distribuido() -> None:
    """Un día con cobertura adecuada y residuos homogéneos pequeños es aceptado."""
    medido = [10.0, 10.0, 10.0, 10.0, 10.0]
    atribuido = [9.0, 9.0, 9.0, 9.0, 9.0]  # 45 / 50 = 90% cob, residuo 1.0 en c/u (ninguno domina)

    cobertura = calcular_cobertura(medido, atribuido)
    assert cobertura == 0.90

    # Si el umbral de residuo es 1.5, ningún intervalo es crítico
    es_valido, motivo = evaluar_consistencia_dia(medido, atribuido, umbral_residuo=1.5)
    assert es_valido
    assert "Día consistente" in motivo


def test_calcular_residuo_dimensiones_invalidas() -> None:
    """Debe fallar si las series no tienen la misma longitud."""
    with pytest.raises(ValueError, match="misma longitud"):
        calcular_residuo([1.0, 2.0], [1.0])
