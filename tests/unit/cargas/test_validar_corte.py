"""tests/unit/cargas/test_validar_corte.py — La validación cuenta los intervalos cortados por caída bajo la base."""

from datetime import datetime

from src.application.cargas.dtos.desagregar_cargas import FirmaConfirmadaDTO
from src.application.cargas.use_cases.validar_desagregacion import (
    ValidarDesagregacionDiaUseCase,
)
from src.domain.cargas.entities import Medicion

DESDE = datetime(2026, 9, 20, 0, 0)
HASTA = datetime(2026, 9, 21, 0, 0)
MOTOR_50 = FirmaConfirmadaDTO(
    machine_id="m50", nombre="Motor 50", potencia_nominal_kw=50.0, tolerancia_kw=5.0
)


def test_intervalo_cortado_por_caida_bajo_la_base_se_cuenta_aparte() -> None:
    t = lambda h, m: datetime(2026, 9, 20, h, m)  # noqa: E731
    mediciones = [
        Medicion(instante=t(8, 0), potencia_kw=90.0),
        Medicion(instante=t(8, 55), potencia_kw=90.0),
        Medicion(instante=t(9, 0), potencia_kw=140.0),
        Medicion(instante=t(9, 30), potencia_kw=60.0),
        Medicion(instante=t(10, 0), potencia_kw=10.0),
    ]
    m = ValidarDesagregacionDiaUseCase().ejecutar(mediciones, [MOTOR_50], DESDE, HASTA)

    assert m.intervalos_cortados_por_caida == 1
    assert m.intervalos_cerrados == 0
    assert m.intervalos_abiertos == 0
    assert not m.energia_atribuida_excede_medida
    assert m.eventos_atribuidos + m.eventos_sin_atribuir == m.eventos
