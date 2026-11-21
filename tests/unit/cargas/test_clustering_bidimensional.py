"""tests/unit/cargas/test_clustering_bidimensional.py — Pruebas de clustering bidimensional (P, Q)."""

import math
from datetime import datetime, timedelta

import pytest

from src.domain.cargas.entities import EventoCarga, Medicion
from src.domain.cargas.services import detectar_eventos, resumir_cargas
from src.infrastructure.sklearn.dbscan_agrupador import DbscanAgrupador

T0 = datetime(2026, 9, 20, 10, 0, 0)


def test_entidades_medicion_y_evento_carga_con_reactiva() -> None:
    # Medicion con reactiva opcional
    m = Medicion(instante=T0, potencia_kw=50.0, reactiva_kvar=30.0)
    assert m.potencia_kw == 50.0
    assert m.reactiva_kvar == 30.0

    # EventoCarga y factor_potencia_evento
    e_motor = EventoCarga(instante=T0, delta_kw=30.0, delta_kvar=25.0)
    assert e_motor.delta_kw == 30.0
    assert e_motor.delta_kvar == 25.0
    assert e_motor.factor_potencia_evento is not None
    # cos(atan2(25, 30)) = 30 / sqrt(30^2 + 25^2) = 30 / 39.051248... ≈ 0.7682
    esperado = 30.0 / math.sqrt(30.0**2 + 25.0**2)
    assert pytest.approx(e_motor.factor_potencia_evento, rel=1e-4) == esperado

    e_cero = EventoCarga(instante=T0, delta_kw=0.0, delta_kvar=10.0)
    assert e_cero.factor_potencia_evento is None


def test_deteccion_conjunta_saltos_p_y_q() -> None:
    # Serie de mediciones con P y Q
    mediciones = [
        Medicion(instante=T0, potencia_kw=100.0, reactiva_kvar=50.0),
        Medicion(instante=T0 + timedelta(minutes=5), potencia_kw=130.0, reactiva_kvar=75.0),
        Medicion(instante=T0 + timedelta(minutes=10), potencia_kw=130.0, reactiva_kvar=75.0),
        Medicion(instante=T0 + timedelta(minutes=15), potencia_kw=100.0, reactiva_kvar=50.0),
    ]
    eventos = detectar_eventos(mediciones, umbral_kw=10.0)
    assert len(eventos) == 2

    # Encendido: Delta P = +30, Delta Q = +25
    assert eventos[0].delta_kw == pytest.approx(30.0)
    assert eventos[0].delta_kvar == pytest.approx(25.0)
    assert eventos[0].es_encendido

    # Apagado: Delta P = -30, Delta Q = -25
    assert eventos[1].delta_kw == pytest.approx(-30.0)
    assert eventos[1].delta_kvar == pytest.approx(-25.0)
    assert not eventos[1].es_encendido


def test_deteccion_eventos_retrocompatible_sin_reactiva() -> None:
    mediciones = [
        Medicion(instante=T0, potencia_kw=100.0),
        Medicion(instante=T0 + timedelta(minutes=5), potencia_kw=150.0),
    ]
    eventos = detectar_eventos(mediciones, umbral_kw=10.0)
    assert len(eventos) == 1
    assert eventos[0].delta_kw == 50.0
    assert eventos[0].delta_kvar == 0.0


def test_dbscan_separa_cargas_con_igual_p_y_distinto_q() -> None:
    """Valida la separación de dos cargas con igual |ΔP| (30 kW) pero distinta firma reactiva:

    - Carga A: Motor inductivo (30 kW, 25 kvar)
    - Carga B: Resistencia pura (30 kW, 0 kvar)
    """
    eventos = [
        # 4 eventos de Motor inductivo (30 kW, 25 kvar)
        EventoCarga(T0 + timedelta(minutes=1), delta_kw=30.0, delta_kvar=25.0),
        EventoCarga(T0 + timedelta(minutes=2), delta_kw=-30.2, delta_kvar=-24.8),
        EventoCarga(T0 + timedelta(minutes=3), delta_kw=29.8, delta_kvar=25.1),
        EventoCarga(T0 + timedelta(minutes=4), delta_kw=-30.0, delta_kvar=-25.0),
        # 4 eventos de Resistencia calefactora (30 kW, 0 kvar)
        EventoCarga(T0 + timedelta(minutes=5), delta_kw=30.1, delta_kvar=0.0),
        EventoCarga(T0 + timedelta(minutes=6), delta_kw=-29.9, delta_kvar=0.2),
        EventoCarga(T0 + timedelta(minutes=7), delta_kw=30.0, delta_kvar=0.1),
        EventoCarga(T0 + timedelta(minutes=8), delta_kw=-30.0, delta_kvar=-0.1),
    ]

    agrupador = DbscanAgrupador()
    # Con radio eps=5.0, la distancia entre motor (30, 25) y resistencia (30, 0) es 25 >> 5.0
    etiquetas = agrupador.agrupar(eventos, radio_kw=5.0, min_eventos=3)

    assert len(etiquetas) == 8
    # Los primeros 4 pertenecen al mismo cluster
    assert len(set(etiquetas[:4])) == 1
    cluster_motor = etiquetas[0]
    assert cluster_motor != -1

    # Los siguientes 4 pertenecen a otro cluster
    assert len(set(etiquetas[4:8])) == 1
    cluster_resistencia = etiquetas[4]
    assert cluster_resistencia != -1

    # Motor y Resistencia quedaron discriminados inequívocamente
    assert cluster_motor != cluster_resistencia

    # Resumen de cargas
    cargas = resumir_cargas(eventos, etiquetas)
    assert len(cargas) == 2

    # Una carga tiene reactiva cercana a 25 y cos phi ~0.77; la otra reactiva ~0 y cos phi 1.0
    cargas_por_reactiva = sorted(cargas, key=lambda c: c.reactiva_tipica_kvar, reverse=True)
    c_motor = cargas_por_reactiva[0]
    c_resistencia = cargas_por_reactiva[1]

    assert c_motor.potencia_tipica_kw == pytest.approx(30.0, abs=0.5)
    assert c_motor.reactiva_tipica_kvar == pytest.approx(25.0, abs=0.5)
    assert c_motor.cos_phi_estimado is not None
    assert pytest.approx(c_motor.cos_phi_estimado, abs=0.02) == 0.768

    assert c_resistencia.potencia_tipica_kw == pytest.approx(30.0, abs=0.5)
    assert c_resistencia.reactiva_tipica_kvar == pytest.approx(0.1, abs=0.2)
    assert c_resistencia.cos_phi_estimado is not None
    assert pytest.approx(c_resistencia.cos_phi_estimado, abs=0.01) == 1.0
