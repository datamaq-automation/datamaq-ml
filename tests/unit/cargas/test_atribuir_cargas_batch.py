"""tests/unit/cargas/test_atribuir_cargas_batch.py — Caso de uso de desagregación batch diaria (contrato nilm.intervalos.v1)."""

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    AtribuirCargasBatchResponseDTO,
    FirmaConfirmadaDTO,
)
from src.application.cargas.use_cases.atribuir_cargas_batch import (
    AtribuirCargasBatchUseCase,
)
from src.domain.cargas.entities import Medicion

DEVICE_ID = "00000000-0000-4000-8000-000000000001"
FECHA_LOCAL = date(2026, 9, 20)
# 2026-09-20 00:00 ART = 2026-09-20 03:00 UTC; el día termina 2026-09-21 03:00 UTC (exclusivo).
DESDE = datetime(2026, 9, 20, 3, 0)
HASTA = datetime(2026, 9, 21, 3, 0)
CINCO_MIN = timedelta(minutes=5)


def U(*partes: int) -> datetime:
    """Instante en UTC con zona, como lo devuelve la salida."""
    return datetime(*partes, tzinfo=timezone.utc)


def peticion(
    mediciones: list[Medicion],
    firmas: list[FirmaConfirmadaDTO],
    desde: datetime = DESDE,
    hasta: datetime = HASTA,
) -> AtribuirCargasBatchRequestDTO:
    return AtribuirCargasBatchRequestDTO(
        device_id=DEVICE_ID,
        etiqueta_ml="Trafo arriba",
        fecha_local=FECHA_LOCAL,
        ventana_desde_utc=desde,
        ventana_hasta_utc=hasta,
        generado_en_utc=datetime(2026, 9, 21, 3, 30),
        mediciones=mediciones,
        firmas=firmas,
    )


def ejecutar(
    mediciones: list[Medicion],
    firmas: list[FirmaConfirmadaDTO],
    desde: datetime = DESDE,
    hasta: datetime = HASTA,
) -> AtribuirCargasBatchResponseDTO:
    return AtribuirCargasBatchUseCase().ejecutar(peticion(mediciones, firmas, desde, hasta))


def intervalos_de(resp: AtribuirCargasBatchResponseDTO, nombre: str) -> list:
    return next(c.intervalos for c in resp.cargas if c.nombre == nombre)


def serie(
    inicio: datetime, cantidad: int, paso: timedelta, p: float, q: float | None
) -> list[Medicion]:
    return [
        Medicion(instante=inicio + paso * i, potencia_kw=p, reactiva_kvar=q)
        for i in range(cantidad)
    ]


COMPRESOR = FirmaConfirmadaDTO(
    machine_id="m-compressor",
    nombre="Compresor 50kW",
    potencia_nominal_kw=50.0,
    reactiva_tipica_kvar=30.0,
    tolerancia_kw=5.0,
    load_id="11111111-1111-1111-1111-111111111111",
)
MOLINO = FirmaConfirmadaDTO(
    machine_id="m-molino",
    nombre="Molino Continuo",
    potencia_nominal_kw=100.0,
    reactiva_tipica_kvar=50.0,
    tolerancia_kw=10.0,
)


def test_energia_y_potencia_se_miden_no_se_toman_de_la_nominal() -> None:
    """Compresor de 50 kW nominales sobre base de 10 kW: energía y potencia medidas, sin la base."""
    t0 = datetime(2026, 9, 20, 11, 0)  # 08:00 ART
    mediciones = [Medicion(instante=t0 - CINCO_MIN, potencia_kw=10.0, reactiva_kvar=5.0)]
    # 24 muestras de 5 min en marcha (08:00 a 09:55 ART) y la primera apagada a las 10:00 ART.
    mediciones += serie(t0, 24, CINCO_MIN, p=60.0, q=35.0)
    mediciones.append(Medicion(instante=t0 + 24 * CINCO_MIN, potencia_kw=10.0, reactiva_kvar=5.0))

    resp = ejecutar(mediciones, [COMPRESOR])
    (it,) = intervalos_de(resp, "Compresor 50kW")

    assert it.inicio_utc == U(2026, 9, 20, 11, 0)
    assert it.fin_utc == U(2026, 9, 20, 13, 0)
    assert it.horas == 2.0
    # Trapecios sobre (P - 10): 23 tramos de 50 kW·5 min, más medio tramo hasta la apagada.
    assert it.energia_kwh_medida == pytest.approx(97.917, abs=0.01)
    assert it.energia_kwh_medida != pytest.approx(100.0)  # no es potencia nominal × horas
    assert it.potencia_media_kw == pytest.approx(48.958, abs=0.01)
    # Reactiva medida: 30 kVAr sobre la base de 5 kVAr durante el mismo tramo.
    assert it.delta_reactiva_kvar == pytest.approx(29.375, abs=0.01)
    assert it.confianza == 1.0
    assert it.origen == "INFERIDA"


def test_con_contador_acumulado_la_energia_es_su_diferencia_menos_la_base() -> None:
    """Si la fuente trae energía acumulada, se usa su delta: 120 kWh del medidor menos 20 kWh de base."""
    t0 = datetime(2026, 9, 20, 11, 0)
    mediciones = [
        Medicion(
            instante=t0 - CINCO_MIN, potencia_kw=10.0, reactiva_kvar=5.0, energia_acumulada_kwh=0.0
        ),
        Medicion(instante=t0, potencia_kw=60.0, reactiva_kvar=35.0, energia_acumulada_kwh=500.0),
        Medicion(
            instante=t0 + timedelta(hours=2),
            potencia_kw=10.0,
            reactiva_kvar=5.0,
            energia_acumulada_kwh=620.0,
        ),
    ]
    resp = ejecutar(mediciones, [COMPRESOR])
    (it,) = intervalos_de(resp, "Compresor 50kW")
    # Contador: 620 - 500 = 120 kWh. Base: 10 kW × 2 h = 20 kWh. Máquina: 100 kWh.
    # Con solo estas tres muestras, la integral de P daría 25 kWh: el contador es el que manda.
    assert it.energia_kwh_medida == pytest.approx(100.0)


def test_intervalo_abierto_se_cierra_en_la_ultima_medicion_real_no_a_las_2359() -> None:
    """Arranque a las 22:00 ART sin apagado: termina en la última medición del día, 23:50 ART."""
    t_arranque = datetime(2026, 9, 21, 1, 0)  # 22:00 ART del día 20
    mediciones = [
        Medicion(instante=t_arranque - CINCO_MIN, potencia_kw=0.0, reactiva_kvar=0.0),
        Medicion(instante=t_arranque, potencia_kw=100.0, reactiva_kvar=50.0),
        Medicion(instante=datetime(2026, 9, 21, 2, 50), potencia_kw=100.0, reactiva_kvar=50.0),
    ]
    resp = ejecutar(mediciones, [MOLINO])
    (it,) = intervalos_de(resp, "Molino Continuo")

    assert it.fin_utc == U(2026, 9, 21, 2, 50)  # 23:50 ART = 02:50 UTC
    assert it.fin_utc != U(2026, 9, 21, 2, 59, 59)
    assert it.horas == pytest.approx(1.8333, abs=0.0001)
    assert it.energia_kwh_medida == pytest.approx(183.333, abs=0.01)
    assert it.potencia_media_kw == pytest.approx(100.0)
    assert it.delta_reactiva_kvar == pytest.approx(50.0)


def test_corte_en_el_limite_de_la_ventana_ignora_lo_que_cae_fuera_del_dia() -> None:
    """Dentro de la ventana el molino sigue en marcha; el apagado de las 03:05 UTC es del día siguiente."""
    mediciones = [
        Medicion(instante=datetime(2026, 9, 21, 2, 40), potencia_kw=0.0, reactiva_kvar=0.0),
        Medicion(instante=datetime(2026, 9, 21, 2, 45), potencia_kw=100.0, reactiva_kvar=50.0),
        Medicion(instante=datetime(2026, 9, 21, 2, 50), potencia_kw=100.0, reactiva_kvar=50.0),
        Medicion(instante=datetime(2026, 9, 21, 2, 55), potencia_kw=100.0, reactiva_kvar=50.0),
        Medicion(
            instante=datetime(2026, 9, 21, 3, 0), potencia_kw=100.0, reactiva_kvar=50.0
        ),  # fuera
        Medicion(instante=datetime(2026, 9, 21, 3, 5), potencia_kw=0.0, reactiva_kvar=0.0),  # fuera
    ]
    resp = ejecutar(mediciones, [MOLINO])
    (it,) = intervalos_de(resp, "Molino Continuo")

    # El intervalo termina en la última medición dentro de la ventana, no en el límite de 03:00.
    assert it.inicio_utc == U(2026, 9, 21, 2, 45)
    assert it.fin_utc == U(2026, 9, 21, 2, 55)
    assert it.horas == pytest.approx(10 / 60, abs=0.0001)
    assert resp.medidor.ultima_lectura_utc == U(2026, 9, 21, 2, 55)


def test_dia_sin_datos_devuelve_cargas_vacias_y_sin_ultima_lectura() -> None:
    resp = ejecutar([], [COMPRESOR])
    assert resp.cargas[0].intervalos == []
    assert resp.medidor.ultima_lectura_utc is None


def test_una_sola_medicion_no_genera_intervalos() -> None:
    mediciones = [
        Medicion(instante=datetime(2026, 9, 20, 11, 0), potencia_kw=60.0, reactiva_kvar=35.0)
    ]
    resp = ejecutar(mediciones, [COMPRESOR])
    assert resp.cargas[0].intervalos == []
    assert resp.medidor.ultima_lectura_utc == U(2026, 9, 20, 11, 0)


def test_encendido_en_la_ultima_medicion_da_intervalo_de_duracion_cero() -> None:
    """Un solo dato en marcha al final del día: 0 horas, 0 kWh, potencia = salto sobre la base."""
    t = datetime(2026, 9, 20, 11, 0)
    mediciones = [
        Medicion(instante=t - CINCO_MIN, potencia_kw=10.0, reactiva_kvar=5.0),
        Medicion(instante=t, potencia_kw=60.0, reactiva_kvar=35.0),
    ]
    resp = ejecutar(mediciones, [COMPRESOR])
    (it,) = intervalos_de(resp, "Compresor 50kW")
    assert it.horas == 0.0
    assert it.energia_kwh_medida == 0.0
    assert it.potencia_media_kw == pytest.approx(50.0)


def test_sin_reactiva_la_energia_se_mide_y_la_reactiva_queda_en_null() -> None:
    t0 = datetime(2026, 9, 20, 11, 0)
    mediciones = [Medicion(instante=t0 - CINCO_MIN, potencia_kw=10.0)]
    mediciones += serie(t0, 12, CINCO_MIN, p=60.0, q=None)
    mediciones.append(Medicion(instante=t0 + 12 * CINCO_MIN, potencia_kw=10.0))

    resp = ejecutar(mediciones, [COMPRESOR])
    (it,) = intervalos_de(resp, "Compresor 50kW")
    assert it.energia_kwh_medida > 0
    assert it.delta_reactiva_kvar is None


def test_confianza_promedia_encendido_y_apagado_segun_su_distancia_a_la_nominal() -> None:
    """Encendido de 47 kW (nominal 50, tolerancia 5) da confianza 0,4; apagado de 50 kW da 1,0. Promedio: 0,7."""
    t0 = datetime(2026, 9, 20, 11, 0)
    mediciones = [
        Medicion(instante=t0 - CINCO_MIN, potencia_kw=10.0, reactiva_kvar=5.0),
        Medicion(instante=t0, potencia_kw=57.0, reactiva_kvar=35.0),  # encendido: +47
        Medicion(instante=t0 + CINCO_MIN, potencia_kw=60.0, reactiva_kvar=35.0),  # +3: no es evento
        Medicion(
            instante=t0 + timedelta(hours=1), potencia_kw=10.0, reactiva_kvar=5.0
        ),  # apagado: -50
    ]
    resp = ejecutar(mediciones, [COMPRESOR])
    (it,) = intervalos_de(resp, "Compresor 50kW")
    assert it.confianza == pytest.approx(0.7, abs=0.01)


def test_dos_motores_con_arranques_solapados_mantienen_sus_duraciones() -> None:
    """Motor de 75 kW y motor de 15 kW en paralelo: cada uno con su propio intervalo."""
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
    mediciones = [
        Medicion(instante=datetime(2026, 9, 20, 11, 0), potencia_kw=0.0, reactiva_kvar=0.0),
        Medicion(instante=datetime(2026, 9, 20, 11, 5), potencia_kw=75.0, reactiva_kvar=45.0),
        Medicion(instante=datetime(2026, 9, 20, 11, 30), potencia_kw=90.0, reactiva_kvar=55.0),
        Medicion(instante=datetime(2026, 9, 20, 12, 0), potencia_kw=15.0, reactiva_kvar=10.0),
        Medicion(instante=datetime(2026, 9, 20, 12, 30), potencia_kw=0.0, reactiva_kvar=0.0),
    ]
    resp = ejecutar(mediciones, firmas)
    (it_75,) = intervalos_de(resp, "Motor 75kW")
    (it_15,) = intervalos_de(resp, "Motor 15kW")
    # Motor 75: 11:05 a 12:00 UTC = 55 min. Motor 15: 11:30 a 12:30 UTC = 60 min.
    assert it_75.horas == pytest.approx(55 / 60, abs=0.0001)
    assert it_15.horas == 1.0


def test_dos_cargas_igual_potencia_se_discriminan_por_reactiva() -> None:
    """Motor inductivo (30 kW, 25 kvar) y horno resistivo (30 kW, 0 kvar) con igual P."""
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
    mediciones = [
        Medicion(instante=datetime(2026, 9, 20, 13, 0), potencia_kw=0.0, reactiva_kvar=0.0),
        Medicion(instante=datetime(2026, 9, 20, 13, 5), potencia_kw=30.0, reactiva_kvar=25.0),
        Medicion(instante=datetime(2026, 9, 20, 13, 10), potencia_kw=60.0, reactiva_kvar=25.0),
        Medicion(instante=datetime(2026, 9, 20, 14, 0), potencia_kw=30.0, reactiva_kvar=25.0),
        Medicion(instante=datetime(2026, 9, 20, 15, 0), potencia_kw=0.0, reactiva_kvar=0.0),
    ]
    resp = ejecutar(mediciones, firmas)
    (motor,) = intervalos_de(resp, "Bomba Inductiva")
    (horno,) = intervalos_de(resp, "Horno Resistivo")
    assert motor.inicio_utc == U(2026, 9, 20, 13, 5)
    assert motor.fin_utc == U(2026, 9, 20, 15, 0)
    assert horno.inicio_utc == U(2026, 9, 20, 13, 10)
    assert horno.fin_utc == U(2026, 9, 20, 14, 0)


def test_salida_tiene_exactamente_las_claves_del_contrato_v1() -> None:
    """La salida es nilm.intervalos.v1 con las claves de la §5 y nada más."""
    t0 = datetime(2026, 9, 20, 11, 0)
    mediciones = [Medicion(instante=t0 - CINCO_MIN, potencia_kw=10.0, reactiva_kvar=5.0)]
    mediciones += serie(t0, 3, CINCO_MIN, p=60.0, q=35.0)
    mediciones.append(Medicion(instante=t0 + 3 * CINCO_MIN, potencia_kw=10.0, reactiva_kvar=5.0))

    datos = json.loads(ejecutar(mediciones, [COMPRESOR]).model_dump_json())

    assert set(datos) == {
        "contrato",
        "generado_en_utc",
        "fecha_local",
        "zona_horaria",
        "ventana_utc",
        "medidor",
        "cargas",
    }
    assert datos["contrato"] == "nilm.intervalos.v1"
    assert datos["zona_horaria"] == "America/Argentina/Buenos_Aires"
    assert datos["fecha_local"] == "2026-09-20"
    assert datos["ventana_utc"] == {
        "desde": "2026-09-20T03:00:00Z",
        "hasta": "2026-09-21T03:00:00Z",
    }
    assert set(datos["medidor"]) == {"device_id", "etiqueta_ml", "ultima_lectura_utc"}
    assert datos["medidor"]["device_id"] == DEVICE_ID
    carga = datos["cargas"][0]
    assert set(carga) == {"load_id", "nombre", "intervalos"}
    assert carga["load_id"] == "11111111-1111-1111-1111-111111111111"
    assert set(carga["intervalos"][0]) == {
        "inicio_utc",
        "fin_utc",
        "horas",
        "energia_kwh_medida",
        "potencia_media_kw",
        "delta_reactiva_kvar",
        "confianza",
        "origen",
    }
    assert carga["intervalos"][0]["origen"] == "INFERIDA"
    assert carga["intervalos"][0]["inicio_utc"].endswith("Z")
