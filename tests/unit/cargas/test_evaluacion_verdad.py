"""tests/unit/cargas/test_evaluacion_verdad.py — Evaluador de intervalos contra la verdad (datos sintéticos)."""

from datetime import datetime, timedelta

import pytest

from src.domain.cargas.evaluacion_verdad import Tramo, emparejar, evaluar, evaluar_maquina, unir

T0 = datetime(2026, 9, 20, 10, 0)


def _marchas(n: int = 10, duracion_min: float = 20.0, separacion_min: float = 60.0) -> list[Tramo]:
    return [
        Tramo(
            T0 + timedelta(minutes=separacion_min * k),
            T0 + timedelta(minutes=separacion_min * k + duracion_min),
        )
        for k in range(n)
    ]


def _desplazar(tramos: list[Tramo], segundos: float) -> list[Tramo]:
    return [
        Tramo(t.inicio + timedelta(seconds=segundos), t.fin + timedelta(seconds=segundos))
        for t in tramos
    ]


def test_caso_perfecto_da_precision_y_sensibilidad_uno_y_error_de_energia_cero() -> None:
    verdad = _marchas()
    r = evaluar_maquina(
        "Compresor", verdad, verdad, energia_inferida_kwh=60.0, energia_verdadera_kwh=60.0
    )
    assert r.tiempo.precision == 1.0 and r.tiempo.sensibilidad == 1.0
    assert r.arranques.precision == 1.0 and r.arranques.sensibilidad == 1.0
    assert r.paradas.precision == 1.0 and r.paradas.sensibilidad == 1.0
    assert r.error_energia_pct == 0.0


def test_un_desfase_de_10_segundos_no_cambia_los_eventos_con_tolerancia_de_300() -> None:
    verdad = _marchas()
    r = evaluar_maquina("Compresor", _desplazar(verdad, 10), verdad, tolerancia_s=300)
    assert r.arranques.emparejados == 10 and r.paradas.emparejados == 10
    assert r.arranques.sensibilidad == 1.0
    # El tiempo sí degrada, en proporción al desfase: 10 s sobre 20 min de marcha.
    assert 0.98 < r.tiempo.precision < 1.0


def test_con_tolerancia_menor_que_el_desfase_los_eventos_no_se_emparejan() -> None:
    verdad = _marchas()
    r = evaluar_maquina("Compresor", _desplazar(verdad, 10), verdad, tolerancia_s=5)
    assert r.arranques.emparejados == 0
    assert r.arranques.sensibilidad == 0.0 and r.arranques.precision == 0.0


def test_los_arranques_perdidos_bajan_la_sensibilidad_de_eventos() -> None:
    verdad = _marchas(10)
    inferido = verdad[:8]  # se pierden dos marchas completas
    r = evaluar_maquina("Compresor", inferido, verdad)
    assert r.arranques.sensibilidad == pytest.approx(0.8)
    assert r.paradas.sensibilidad == pytest.approx(0.8)
    assert r.arranques.precision == 1.0  # lo que se infiere sí es verdad
    assert r.tiempo.sensibilidad == pytest.approx(0.8)


def test_las_paradas_de_mas_bajan_la_precision_de_eventos() -> None:
    verdad = _marchas(10)
    extra = [
        Tramo(T0 + timedelta(minutes=600 + 60 * k), T0 + timedelta(minutes=610 + 60 * k))
        for k in range(3)
    ]
    r = evaluar_maquina("Compresor", verdad + extra, verdad)
    assert r.paradas.precision == pytest.approx(10 / 13, abs=1e-4)
    assert r.paradas.sensibilidad == 1.0
    assert r.tiempo.precision < 1.0


def test_el_error_de_energia_solo_se_calcula_con_verdad_de_energia() -> None:
    verdad = _marchas(2)
    sin_energia = evaluar_maquina("Compresor", verdad, verdad, energia_inferida_kwh=30.0)
    assert sin_energia.error_energia_pct is None
    con_energia = evaluar_maquina(
        "Compresor", verdad, verdad, energia_inferida_kwh=30.0, energia_verdadera_kwh=25.0
    )
    assert con_energia.error_energia_pct == 20.0


def test_una_maquina_solo_inferida_tiene_precision_cero_y_sensibilidad_uno() -> None:
    resultados = evaluar({"Fantasma": _marchas(2)}, {})
    (r,) = resultados
    assert r.maquina == "Fantasma"
    assert r.tiempo.precision == 0.0 and r.tiempo.sensibilidad == 1.0


def test_una_maquina_solo_en_la_verdad_tiene_sensibilidad_cero() -> None:
    (r,) = evaluar({}, {"Perdida": _marchas(2)})
    assert r.tiempo.sensibilidad == 0.0 and r.tiempo.precision == 1.0


def test_unir_funde_tramos_que_se_solapan_y_se_tocan() -> None:
    tramos = [
        Tramo(T0, T0 + timedelta(minutes=10)),
        Tramo(T0 + timedelta(minutes=5), T0 + timedelta(minutes=20)),
        Tramo(T0 + timedelta(minutes=20), T0 + timedelta(minutes=30)),
    ]
    (fundido,) = unir(tramos)
    assert fundido.minutos == 30.0


def test_emparejar_usa_cada_inferido_una_sola_vez() -> None:
    real = [T0, T0 + timedelta(seconds=100)]
    inferido = [T0 + timedelta(seconds=50)]
    assert emparejar(real, inferido, tolerancia_s=300) == 1
