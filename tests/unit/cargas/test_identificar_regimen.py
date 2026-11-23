"""tests/unit/cargas/test_identificar_regimen.py — Entrenamiento con régimen bimodal y continuo (datos sintéticos)."""

import random
from datetime import datetime, timedelta

from src.application.cargas.dtos.identificar_cargas import IdentificarCargasRequest
from src.application.cargas.use_cases.identificar_cargas import (
    REGIMEN_SIN_MODOS,
    REGIMEN_VALLE,
    IdentificarCargasUseCase,
)
from src.domain.cargas.entities import EventoCarga, Medicion
from src.infrastructure.settings.logger import logger

T0 = datetime(2026, 9, 20)


class RepoFalso:
    def __init__(self, kw: list[float]) -> None:
        self.kw = kw

    def listar(self, medidor: str, desde: datetime, hasta: datetime) -> list[Medicion]:
        return [Medicion(T0 + timedelta(minutes=5 * i), p) for i, p in enumerate(self.kw)]


class AgrupadorQueNoDebeUsarse:
    def agrupar(self, eventos: list[EventoCarga], radio_kw: float, min_eventos: int) -> list[int]:
        raise AssertionError("En régimen de valle no se usa DBSCAN")


def _serie(magnitudes: list[float], semilla: int) -> list[float]:
    """Potencia con pares de saltos: sube m y baja casi m, así el nivel vuelve a la base."""
    r = random.Random(semilla)
    p, serie = 10.0, [10.0]
    for m in magnitudes:
        p += m
        serie.append(p)
        p -= m * r.uniform(0.9, 1.1)
        serie.append(p)
    return serie


def _bimodal(semilla: int) -> list[float]:
    r = random.Random(semilla)
    ruido = [r.uniform(0.2, 18.0) for _ in range(1500)]
    eventos = [r.uniform(77.0, 110.0) for _ in range(120)]
    mezcla = ruido + eventos
    r.shuffle(mezcla)
    return _serie(mezcla, semilla)


def _continuo(semilla: int) -> list[float]:
    r = random.Random(semilla)
    ruido = [r.uniform(0.2, 12.0) for _ in range(1500)]
    cuerpo = [r.uniform(15.0, 150.0) for _ in range(1200)]
    mezcla = ruido + cuerpo
    r.shuffle(mezcla)
    return _serie(mezcla, semilla)


def _pedir(kw: list[float]):
    caso = IdentificarCargasUseCase(
        RepoFalso(kw),
        AgrupadorQueNoDebeUsarse(),
        umbral_kw=None,
        logger=logger,
        separacion_minima=0.99,  # fuerza el régimen de valle: el η de estos datos no es el del trafo real
    )
    return caso.execute(
        IdentificarCargasRequest(medidor="X", desde=T0, hasta=T0 + timedelta(days=3))
    )


def test_bimodal_usa_el_valle_y_da_una_carga_con_su_modo() -> None:
    res = _pedir(_bimodal(11))
    assert res.umbral.regimen == REGIMEN_VALLE
    assert res.umbral.kw is not None and 18.0 <= res.umbral.kw <= 77.0
    assert not res.sin_modos_separables
    assert len(res.modos) == 1
    assert len(res.cargas) == 1
    carga = res.cargas[0]
    assert 84.0 <= carga.potencia_tipica_kw <= 102.0
    assert 6.0 <= carga.dispersion_kw <= 12.0  # uniforme 77-110: σ ≈ 9,5
    assert res.eventos_sin_grupo < res.eventos  # los eventos del modo tienen grupo


def test_continuo_sin_valle_marca_sin_modos_y_no_inventa_cargas() -> None:
    res = _pedir(_continuo(12))
    assert res.umbral.regimen == REGIMEN_SIN_MODOS
    assert res.sin_modos_separables
    assert res.cargas == []
    assert res.modos == []
    assert res.eventos_sin_grupo == res.eventos > 0


def test_el_ratio_mediano_de_un_grupo_es_la_mediana_de_dq_sobre_dp() -> None:
    """Eventos con ΔQ = 0,56 · ΔP: el ratio mediano del grupo tiene que ser 0,56."""
    from src.domain.cargas.services import resumir_cargas

    eventos = [
        EventoCarga(T0, 90.0, 50.4),
        EventoCarga(T0, -91.0, -50.96),
        EventoCarga(T0, 89.0, 49.84),
    ]
    (carga,) = resumir_cargas(eventos, [0, 0, 0])
    assert carga.ratio_qp_mediana is not None
    assert abs(carga.ratio_qp_mediana - 0.56) < 0.005


def test_sin_reactiva_el_ratio_es_none() -> None:
    from src.domain.cargas.services import resumir_cargas

    (carga,) = resumir_cargas([EventoCarga(T0, 90.0), EventoCarga(T0, -90.0)], [0, 0])
    assert carga.ratio_qp_mediana is None
