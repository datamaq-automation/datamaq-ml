"""tests/unit/cargas/test_atribuir_debounce.py — El debounce del motor quita picos de una lectura (datos sintéticos)."""

from datetime import date, datetime, timedelta

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    FirmaConfirmadaDTO,
    ParametrosMotorDTO,
)
from src.application.cargas.use_cases.atribuir_cargas_batch import AtribuirCargasBatchUseCase
from src.domain.cargas.entities import Medicion

DESDE = datetime(2026, 9, 20, 3, 0)
HASTA = datetime(2026, 9, 21, 3, 0)
MOTOR = FirmaConfirmadaDTO(
    machine_id="m", nombre="Motor", potencia_nominal_kw=50.0, tolerancia_kw=5.0
)
CINCO = timedelta(minutes=5)
T0 = datetime(2026, 9, 20, 10, 0)


def _ejecutar(mediciones: list[Medicion], muestras: int):
    return AtribuirCargasBatchUseCase().ejecutar(
        AtribuirCargasBatchRequestDTO(
            device_id="d",
            etiqueta_ml="d",
            fecha_local=date(2026, 9, 20),
            ventana_desde_utc=DESDE,
            ventana_hasta_utc=HASTA,
            generado_en_utc=DESDE,
            mediciones=mediciones,
            firmas=[MOTOR],
            parametros_motor=ParametrosMotorDTO(muestras_debounce=muestras),
        )
    )


def _serie(niveles: list[float]) -> list[Medicion]:
    return [Medicion(instante=T0 + i * CINCO, potencia_kw=p) for i, p in enumerate(niveles)]


def test_un_pico_de_una_lectura_genera_un_intervalo_espurio_sin_debounce() -> None:
    serie = _serie([10.0] * 3 + [60.0] + [10.0] * 4)  # +50 kW durante una sola muestra
    assert len(_ejecutar(serie, muestras=1).cargas[0].intervalos) == 1


def test_con_debounce_dos_el_pico_no_genera_intervalo() -> None:
    serie = _serie([10.0] * 3 + [60.0] + [10.0] * 4)
    assert _ejecutar(serie, muestras=2).cargas[0].intervalos == []


def test_con_debounce_dos_un_arranque_real_sigue_dando_su_intervalo() -> None:
    serie = _serie([10.0] * 3 + [60.0, 60.5, 59.8, 60.2, 60.0] + [10.0] * 3)
    intervalos = _ejecutar(serie, muestras=2).cargas[0].intervalos
    assert len(intervalos) == 1
