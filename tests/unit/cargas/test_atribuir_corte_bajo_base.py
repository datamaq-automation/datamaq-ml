"""tests/unit/cargas/test_atribuir_corte_bajo_base.py — Un intervalo no se estira por encima de una caída bajo la base."""

from datetime import UTC, datetime

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    FirmaConfirmadaDTO,
)
from src.application.cargas.use_cases.atribuir_cargas_batch import (
    AtribuirCargasBatchUseCase,
)
from src.domain.cargas.entities import Medicion

DESDE = datetime(2026, 9, 20, 0, 0)
HASTA = datetime(2026, 9, 21, 0, 0)
MOTOR_50 = FirmaConfirmadaDTO(
    machine_id="m50", nombre="Motor 50", potencia_nominal_kw=50.0, tolerancia_kw=5.0
)


def _ejecutar(mediciones: list[Medicion]):
    return AtribuirCargasBatchUseCase().ejecutar(
        AtribuirCargasBatchRequestDTO(
            device_id="prueba",
            etiqueta_ml="prueba",
            fecha_local=DESDE.date(),
            ventana_desde_utc=DESDE,
            ventana_hasta_utc=HASTA,
            generado_en_utc=DESDE,
            mediciones=mediciones,
            firmas=[MOTOR_50],
        )
    )


def test_otra_carga_que_se_apaga_durante_el_intervalo_no_produce_energia_negativa() -> None:
    """Una carga C de 80 kW (no catalogada) estaba encendida antes del motor y se apaga a las 09:30.

    La base previa al encendido del motor es 90 kW. Tras el apagado de C, la potencia baja a 60 kW,
    por debajo de la base: esa caída no es del motor. Sin el corte, el intervalo se estiraba hasta el
    apagado del motor (10:00) y la energía atribuida daba negativa.
    """
    t = lambda h, m: datetime(2026, 9, 20, h, m)  # noqa: E731
    mediciones = [
        Medicion(instante=t(8, 0), potencia_kw=90.0),  # base: C encendida
        Medicion(instante=t(8, 55), potencia_kw=90.0),  # última antes del encendido del motor
        Medicion(instante=t(9, 0), potencia_kw=140.0),  # motor ON: +50
        Medicion(instante=t(9, 30), potencia_kw=60.0),  # C OFF: -80, la potencia cae bajo la base
        Medicion(instante=t(10, 0), potencia_kw=10.0),  # motor OFF: -50
    ]
    resp = _ejecutar(mediciones)
    (it,) = resp.cargas[0].intervalos
    assert it.energia_kwh_medida >= 0.0
    # El intervalo termina en la caída de las 09:30, no en el apagado de las 10:00.
    assert it.fin_utc == datetime(2026, 9, 20, 9, 30, tzinfo=UTC)
    assert it.potencia_media_kw >= 0.0
