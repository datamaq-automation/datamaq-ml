"""tests/unit/cargas/test_validar_banco.py — Métricas de contaminación por banco en la validación (datos sintéticos)."""

from datetime import datetime

from src.application.cargas.dtos.desagregar_cargas import FirmaConfirmadaDTO
from src.application.cargas.use_cases.validar_desagregacion import ValidarDesagregacionDiaUseCase
from src.domain.cargas.entities import CargaSimulada
from src.domain.cargas.simulacion import BANCO_AUTOMATICO, BANCO_FIJO, simular_tablero_con_reactiva

INICIO = datetime(2026, 9, 20, 3, 0)  # 00:00 ART del día 20
DESDE = INICIO
HASTA = datetime(2026, 9, 21, 3, 0)
CARGAS = [
    CargaSimulada(potencia_kw=50.0, ciclos_por_dia=8.0, duracion_min=45.0),
    CargaSimulada(potencia_kw=30.0, ciclos_por_dia=12.0, duracion_min=20.0),
]
FIRMAS = [
    FirmaConfirmadaDTO(machine_id="c50", nombre="C50", potencia_nominal_kw=50.0, tolerancia_kw=5.0),
    FirmaConfirmadaDTO(machine_id="c30", nombre="C30", potencia_nominal_kw=30.0, tolerancia_kw=3.0),
]


def _metricas(banco: str):
    mediciones, _ = simular_tablero_con_reactiva(
        CARGAS, dias=2, ruido_kw=0.1, ruido_kvar=0.1, semilla=5, inicio=INICIO, banco=banco
    )
    return ValidarDesagregacionDiaUseCase().ejecutar(mediciones, FIRMAS, DESDE, HASTA)


def test_con_banco_fijo_el_indicador_de_banco_es_cero() -> None:
    assert _metricas(BANCO_FIJO).eventos_banco_dp_bajo_dq_alto == 0


def test_con_banco_automatico_el_indicador_de_banco_es_positivo() -> None:
    assert _metricas(BANCO_AUTOMATICO).eventos_banco_dp_bajo_dq_alto >= 1


def test_la_atribucion_solo_con_p_se_reporta_junto_a_la_de_p_y_q() -> None:
    m = _metricas(BANCO_AUTOMATICO)
    assert m.energia_atribuida_solo_p_kwh >= 0.0
    assert isinstance(m.diferencia_pct_p_vs_pq, float)
    assert m.eventos_carga_con_banco >= 0
