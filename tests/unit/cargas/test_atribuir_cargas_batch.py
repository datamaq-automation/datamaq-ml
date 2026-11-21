"""tests/unit/cargas/test_atribuir_cargas_batch.py — Pruebas unitarias del caso de uso de atribución batch diaria."""

from datetime import date, datetime, timedelta

import pytest

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    FirmaConfirmadaDTO,
)
from src.application.cargas.use_cases.atribuir_cargas_batch import (
    AtribuirCargasBatchUseCase,
)
from src.domain.cargas.entities import Medicion

FECHA_TEST = date(2026, 9, 20)
T0 = datetime(2026, 9, 20, 8, 0, 0)


def test_encendido_y_apagado_simple_calculo_exacto_horas_y_energia() -> None:
    """Valida un ciclo simple de 2 horas (08:00 a 10:00) para un motor de 50 kW."""
    firmas = [
        FirmaConfirmadaDTO(
            machine_id="m-compressor",
            nombre="Compresor 50kW",
            potencia_nominal_kw=50.0,
            reactiva_tipica_kvar=30.0,
            tolerancia_kw=5.0,
        )
    ]
    # Carga base de 10 kW. A las 08:00 sube a 60 kW (+50 kW). A las 10:00 baja a 10 kW (-50 kW).
    mediciones = [
        Medicion(instante=T0 - timedelta(minutes=5), potencia_kw=10.0, reactiva_kvar=5.0),
        Medicion(instante=T0, potencia_kw=60.0, reactiva_kvar=35.0),
        Medicion(instante=T0 + timedelta(hours=1), potencia_kw=60.0, reactiva_kvar=35.0),
        Medicion(instante=T0 + timedelta(hours=2), potencia_kw=10.0, reactiva_kvar=5.0),
    ]

    use_case = AtribuirCargasBatchUseCase()
    response = use_case.ejecutar(
        AtribuirCargasBatchRequestDTO(
            dispositivo_id="trafo-test",
            fecha=FECHA_TEST,
            mediciones=mediciones,
            firmas=firmas,
        )
    )

    assert len(response.intervalos) == 1
    it = response.intervalos[0]
    assert it.machine_id == "m-compressor"
    assert it.inicio == T0
    assert it.fin == T0 + timedelta(hours=2)
    assert it.duracion_segundos == 7200.0
    assert it.potencia_media_kw == 50.0
    assert it.reactiva_media_kvar == 30.0
    # cos(atan2(30, 50)) = 50 / sqrt(3400) ≈ 0.857
    assert pytest.approx(it.cos_phi_medio, abs=0.01) == 0.857
    # 50 kW * 2 h = 100 kWh
    assert pytest.approx(it.energia_kwh, abs=0.1) == 100.0

    assert len(response.resumen_maquinas) == 1
    res = response.resumen_maquinas[0]
    assert res.machine_id == "m-compressor"
    assert res.ciclos == 1
    assert res.horas_marcha == 2.0
    assert pytest.approx(res.energia_kwh, abs=0.1) == 100.0


def test_dos_motores_distinta_potencia_en_paralelo_sin_interferencia() -> None:
    """Valida dos motores (75 kW y 15 kW) operando con arranques y paradas solapados."""
    firmas = [
        FirmaConfirmadaDTO(
            machine_id="m-75",
            nombre="Motor 75kW",
            potencia_nominal_kw=75.0,
            reactiva_tipica_kvar=45.0,
            tolerancia_kw=5.0,
        ),
        FirmaConfirmadaDTO(
            machine_id="m-15",
            nombre="Motor 15kW",
            potencia_nominal_kw=15.0,
            reactiva_tipica_kvar=10.0,
            tolerancia_kw=3.0,
        ),
    ]

    # Cronología:
    # 08:00 Base = 0
    # 08:05 Arranca Motor 75 kW (+75 kW)
    # 08:30 Arranca Motor 15 kW (+15 kW -> Total 90 kW)
    # 09:00 Para Motor 75 kW (-75 kW -> Total 15 kW)
    # 09:30 Para Motor 15 kW (-15 kW -> Total 0 kW)
    t_0800 = datetime(2026, 9, 20, 8, 0, 0)
    t_0805 = datetime(2026, 9, 20, 8, 5, 0)
    t_0830 = datetime(2026, 9, 20, 8, 30, 0)
    t_0900 = datetime(2026, 9, 20, 9, 0, 0)
    t_0930 = datetime(2026, 9, 20, 9, 30, 0)

    mediciones = [
        Medicion(instante=t_0800, potencia_kw=0.0, reactiva_kvar=0.0),
        Medicion(instante=t_0805, potencia_kw=75.0, reactiva_kvar=45.0),
        Medicion(instante=t_0830, potencia_kw=90.0, reactiva_kvar=55.0),
        Medicion(instante=t_0900, potencia_kw=15.0, reactiva_kvar=10.0),
        Medicion(instante=t_0930, potencia_kw=0.0, reactiva_kvar=0.0),
    ]

    use_case = AtribuirCargasBatchUseCase()
    response = use_case.ejecutar(
        AtribuirCargasBatchRequestDTO(
            dispositivo_id="trafo-test",
            fecha=FECHA_TEST,
            mediciones=mediciones,
            firmas=firmas,
        )
    )

    assert len(response.intervalos) == 2
    it_75 = next(it for it in response.intervalos if it.machine_id == "m-75")
    it_15 = next(it for it in response.intervalos if it.machine_id == "m-15")

    # Motor 75: 08:05 a 09:00 = 55 min = 3300 s ≈ 0.9167 h
    assert it_75.inicio == t_0805
    assert it_75.fin == t_0900
    assert it_75.duracion_segundos == 3300.0

    # Motor 15: 08:30 a 09:30 = 60 min = 3600 s = 1.0 h
    assert it_15.inicio == t_0830
    assert it_15.fin == t_0930
    assert it_15.duracion_segundos == 3600.0

    # Resumenes
    res_75 = next(r for r in response.resumen_maquinas if r.machine_id == "m-75")
    res_15 = next(r for r in response.resumen_maquinas if r.machine_id == "m-15")
    assert pytest.approx(res_75.horas_marcha, abs=0.01) == 0.917
    assert res_15.horas_marcha == 1.0


def test_dos_cargas_igual_p_discriminadas_por_reactiva_q() -> None:
    """Valida discriminación entre motor inductivo (30 kW, 25 kvar) y horno resistivo (30 kW, 0 kvar)."""
    firmas = [
        FirmaConfirmadaDTO(
            machine_id="m-motor",
            nombre="Bomba Inductiva",
            potencia_nominal_kw=30.0,
            reactiva_tipica_kvar=25.0,
            tolerancia_kw=5.0,
        ),
        FirmaConfirmadaDTO(
            machine_id="m-horno",
            nombre="Horno Resistivo",
            potencia_nominal_kw=30.0,
            reactiva_tipica_kvar=0.0,
            tolerancia_kw=5.0,
        ),
    ]

    t1 = datetime(2026, 9, 20, 10, 0, 0)
    t2 = datetime(2026, 9, 20, 10, 5, 0)  # Arranca Motor (P+30, Q+25)
    t3 = datetime(2026, 9, 20, 10, 10, 0)  # Arranca Horno (P+30, Q+0 -> Total 60, 25)
    t4 = datetime(2026, 9, 20, 11, 0, 0)  # Para Horno (P-30, Q-0 -> Total 30, 25)
    t5 = datetime(2026, 9, 20, 12, 0, 0)  # Para Motor (P-30, Q-25 -> Total 0, 0)

    mediciones = [
        Medicion(instante=t1, potencia_kw=0.0, reactiva_kvar=0.0),
        Medicion(instante=t2, potencia_kw=30.0, reactiva_kvar=25.0),
        Medicion(instante=t3, potencia_kw=60.0, reactiva_kvar=25.0),
        Medicion(instante=t4, potencia_kw=30.0, reactiva_kvar=25.0),
        Medicion(instante=t5, potencia_kw=0.0, reactiva_kvar=0.0),
    ]

    use_case = AtribuirCargasBatchUseCase()
    response = use_case.ejecutar(
        AtribuirCargasBatchRequestDTO(
            dispositivo_id="trafo-test",
            fecha=FECHA_TEST,
            mediciones=mediciones,
            firmas=firmas,
        )
    )

    assert len(response.intervalos) == 2
    it_motor = next(it for it in response.intervalos if it.machine_id == "m-motor")
    it_horno = next(it for it in response.intervalos if it.machine_id == "m-horno")

    # Motor arrancó en t2 y paró en t5 (10:05 a 12:00 = 1h 55min = 6900 s)
    assert it_motor.inicio == t2
    assert it_motor.fin == t5
    assert it_motor.duracion_segundos == 6900.0

    # Horno arrancó en t3 y paró en t4 (10:10 a 11:00 = 50min = 3000 s)
    assert it_horno.inicio == t3
    assert it_horno.fin == t4
    assert it_horno.duracion_segundos == 3000.0


def test_resiliencia_intervalo_incompleto_corte_a_medianoche() -> None:
    """Si una máquina arranca a las 22:00 y no se apaga en la jornada, se cierra a las 23:59:59."""
    firmas = [
        FirmaConfirmadaDTO(
            machine_id="m-nocturno",
            nombre="Molino Continuo",
            potencia_nominal_kw=100.0,
            reactiva_tipica_kvar=50.0,
            tolerancia_kw=10.0,
        )
    ]

    t_arranque = datetime(2026, 9, 20, 22, 0, 0)
    mediciones = [
        Medicion(instante=t_arranque - timedelta(minutes=5), potencia_kw=0.0, reactiva_kvar=0.0),
        Medicion(instante=t_arranque, potencia_kw=100.0, reactiva_kvar=50.0),
        Medicion(instante=datetime(2026, 9, 20, 23, 50, 0), potencia_kw=100.0, reactiva_kvar=50.0),
    ]

    use_case = AtribuirCargasBatchUseCase()
    response = use_case.ejecutar(
        AtribuirCargasBatchRequestDTO(
            dispositivo_id="trafo-test",
            fecha=FECHA_TEST,
            mediciones=mediciones,
            firmas=firmas,
        )
    )

    assert len(response.intervalos) == 1
    it = response.intervalos[0]
    assert it.machine_id == "m-nocturno"
    assert it.inicio == t_arranque
    # Límite fin de jornada: 23:59:59
    assert it.fin == datetime(2026, 9, 20, 23, 59, 59)
    # 22:00:00 a 23:59:59 = 1h 59min 59s = 7199 s ≈ 1.9997 h
    assert it.duracion_segundos == 7199.0
    assert pytest.approx(it.duracion_segundos / 3600.0, abs=0.001) == 2.0
