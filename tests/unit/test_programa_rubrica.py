"""tests/unit/test_programa_rubrica.py — Verificación del cálculo de horas y planificación (Issue #22).

Comprueba que las estimaciones horarias de los issues sumen 65 a 87 horas, que el presupuesto
semanal detecte el desbalance sobre 16 semanas a 4 h/semana, y que el plan propuesto cubra 64 h
presenciales exactas.
"""

from __future__ import annotations

from docs.ejemplos.ejemplo_issue_22 import (
    ESTIMACIONES,
    calcular_horas_totales,
    calcular_presupuesto_semanas,
    distribuir_plan_16_semanas,
)


def test_horas_totales_estimaciones_coinciden_con_especificacion() -> None:
    """Verifica que la suma de estimaciones mínimas y máximas sea exactamente 65 y 87 horas."""
    minimo, maximo = calcular_horas_totales(ESTIMACIONES)
    assert (minimo, maximo) == (65, 87)


def test_presupuesto_semanas_excede_limite_semestral() -> None:
    """Verifica que a 4 h/semana se requieran entre 16.25 y 21.75 semanas."""
    semanas_min, semanas_max = calcular_presupuesto_semanas(65, 87, horas_por_semana=4)
    assert round(semanas_min, 2) == 16.25
    assert round(semanas_max, 2) == 21.75


def test_distribucion_plan_16_semanas_completa_64_horas_presenciales() -> None:
    """Verifica que el plan curricular distribuido asigne exactamente 64 h presenciales en 16 semanas."""
    plan = distribuir_plan_16_semanas(ESTIMACIONES)
    assert len(plan) == 16

    total_presencial = sum(s["horas_presenciales"] for s in plan)
    assert total_presencial == 64

    # Cada semana debe tener exactamente 4 h presenciales
    for s in plan:
        assert s["horas_presenciales"] == 4
        assert "tema" in s
        assert "semana" in s
