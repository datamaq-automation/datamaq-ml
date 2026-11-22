"""tests/unit/cargas/test_calidad_dia.py — Un día con muchos huecos de muestreo es de calidad baja (datos sintéticos)."""

from datetime import datetime, timedelta

import pytest

from src.application.cargas.dtos.desagregar_cargas import FirmaConfirmadaDTO
from src.application.cargas.use_cases.validar_desagregacion import ValidarDesagregacionDiaUseCase
from src.domain.cargas.entities import Medicion

DESDE = datetime(2026, 9, 20, 3, 0)
HASTA = datetime(2026, 9, 21, 3, 0)
FIRMA = FirmaConfirmadaDTO(machine_id="m", nombre="M", potencia_nominal_kw=50.0, tolerancia_kw=5.0)


def _dia_con_huecos(cantidad: int) -> list[Medicion]:
    """Un día de muestras cada 5 min, con `cantidad` huecos de 15 minutos (se quitan 2 muestras cada uno)."""
    muestras = [DESDE + timedelta(minutes=5 * i) for i in range(288)]
    quitar = set()
    for h in range(cantidad):
        base = 10 + 20 * h
        quitar.update({base, base + 1})
    return [
        Medicion(instante=t, potencia_kw=10.0) for i, t in enumerate(muestras) if i not in quitar
    ]


def test_un_dia_con_pocos_huecos_no_es_de_calidad_baja() -> None:
    m = ValidarDesagregacionDiaUseCase().ejecutar(_dia_con_huecos(3), [FIRMA], DESDE, HASTA)
    assert m.huecos_mayores_a_5_min == 3
    assert m.calidad_baja is False


def test_un_dia_con_muchos_huecos_es_de_calidad_baja() -> None:
    m = ValidarDesagregacionDiaUseCase().ejecutar(_dia_con_huecos(12), [FIRMA], DESDE, HASTA)
    assert m.huecos_mayores_a_5_min == 12
    assert m.calidad_baja is True


def test_el_umbral_es_configurable() -> None:
    m = ValidarDesagregacionDiaUseCase(umbral_huecos_calidad=2).ejecutar(
        _dia_con_huecos(3), [FIRMA], DESDE, HASTA
    )
    assert m.calidad_baja is True


def test_un_umbral_negativo_es_error() -> None:
    with pytest.raises(ValueError):
        ValidarDesagregacionDiaUseCase(umbral_huecos_calidad=-1)
