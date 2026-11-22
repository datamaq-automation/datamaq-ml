"""tests/unit/cargas/test_tolerancia_dispersion.py — Tolerancia por dispersión acotada (datos sintéticos)."""

from datetime import date, datetime

import pytest

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    FirmaConfirmadaDTO,
    ParametrosMotorDTO,
)
from src.application.cargas.use_cases.atribuir_cargas_batch import (
    AtribuirCargasBatchUseCase,
    tolerancia_efectiva,
)
from src.domain.cargas.entities import Medicion

DESDE = datetime(2026, 9, 20, 3, 0)
HASTA = datetime(2026, 9, 21, 3, 0)
ACTIVA = ParametrosMotorDTO(tolerancia_por_dispersion=True)


def _firma(tolerancia: float, dispersion: float | None) -> FirmaConfirmadaDTO:
    return FirmaConfirmadaDTO(
        machine_id="x",
        nombre="X",
        potencia_nominal_kw=75.0,
        tolerancia_kw=tolerancia,
        dispersion_kw=dispersion,
    )


def test_por_defecto_se_usa_la_tolerancia_explicita() -> None:
    assert tolerancia_efectiva(_firma(24.0, 3.0), ParametrosMotorDTO()) == 24.0


def test_con_el_modo_activo_la_tolerancia_sale_de_la_dispersion_y_se_acota() -> None:
    assert tolerancia_efectiva(_firma(24.0, 3.0), ACTIVA) == pytest.approx(6.0)  # 2 × 3
    assert tolerancia_efectiva(_firma(24.0, 0.5), ACTIVA) == pytest.approx(2.0)  # piso
    assert tolerancia_efectiva(_firma(24.0, 25.8), ACTIVA) == pytest.approx(8.0)  # tope
    assert tolerancia_efectiva(_firma(24.0, None), ACTIVA) == 24.0  # sin dispersión, la explícita


def _escenario(tolerancia: float, dispersion: float | None, params: ParametrosMotorDTO):
    """Carga X de 75 kW de 10 a 11 y carga Y de 60 kW de 12 a 13. Solo hay firma para X."""
    t = lambda h: datetime(2026, 9, 20, h, 0)  # noqa: E731
    niveles = [(t(9), 10.0), (t(10), 85.0), (t(11), 10.0), (t(12), 70.0), (t(13), 10.0)]
    mediciones = [Medicion(instante=i, potencia_kw=p) for i, p in niveles]
    firma = FirmaConfirmadaDTO(
        machine_id="x",
        nombre="X",
        potencia_nominal_kw=75.0,
        tolerancia_kw=tolerancia,
        dispersion_kw=dispersion,
    )
    return AtribuirCargasBatchUseCase().ejecutar(
        AtribuirCargasBatchRequestDTO(
            device_id="d",
            etiqueta_ml="d",
            fecha_local=date(2026, 9, 20),
            ventana_desde_utc=DESDE,
            ventana_hasta_utc=HASTA,
            generado_en_utc=DESDE,
            mediciones=mediciones,
            firmas=[firma],
            parametros_motor=params,
        )
    )


def test_tolerancia_ancha_atribuye_la_carga_de_60_kw_a_la_firma_de_75() -> None:
    """Antes: tolerancia 24 kW. La carga Y (60 kW) cae a 15 kW de X y se cierra como X: intervalo espurio."""
    resp = _escenario(tolerancia=24.0, dispersion=3.0, params=ParametrosMotorDTO())
    assert len(resp.cargas[0].intervalos) == 2


def test_con_tolerancia_por_dispersion_acotada_la_carga_de_60_kw_no_se_atribuye() -> None:
    resp = _escenario(tolerancia=24.0, dispersion=3.0, params=ACTIVA)
    assert len(resp.cargas[0].intervalos) == 1
    assert resp.cargas[0].intervalos[0].inicio_utc.hour == 10
