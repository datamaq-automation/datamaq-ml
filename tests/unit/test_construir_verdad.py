"""tests/unit/test_construir_verdad.py — Verdad simulada: energía conocida, desfase registrado y CLI (datos sintéticos)."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.application.cargas.dtos.verdad_intervalos import VerdadIntervalosDTO
from src.application.cargas.use_cases.construir_verdad import construir_verdad_simulada
from src.infrastructure.cli.simular_tablero import main as simular

INICIO = datetime(2026, 9, 1)


def _tramos() -> list[list[tuple[datetime, datetime]]]:
    return [
        [(INICIO + timedelta(hours=1), INICIO + timedelta(hours=1, minutes=30))],
        [],
    ]


def test_la_verdad_construida_pasa_el_esquema_y_trae_energia_del_simulador() -> None:
    verdad = construir_verdad_simulada(
        [("Carga 90 kW", 90.0), ("Carga 40 kW", 40.0)],
        _tramos(),
        INICIO,
        1,
        0.0,
        "sintetico",
        "simulado",
    )
    revalidada = VerdadIntervalosDTO.model_validate_json(verdad.model_dump_json())
    intervalo = revalidada.cargas[0].intervalos[0]
    assert intervalo.horas == 0.5
    assert intervalo.energia_kwh_medida == 45.0  # 90 kW × 0,5 h
    assert intervalo.origen == "MEDIDO"
    assert revalidada.medidor.fuente == "simulador"


def test_el_desfase_queda_registrado_y_la_ventana_lo_cubre() -> None:
    verdad = construir_verdad_simulada(
        [("Carga 90 kW", 90.0), ("Carga 40 kW", 40.0)],
        _tramos(),
        INICIO,
        1,
        -6.0,
        "sintetico",
        "simulado",
    )
    assert verdad.medidor.desfase_reloj_s == -6.0
    assert verdad.ventana_utc.desde < verdad.cargas[0].intervalos[0].inicio_utc


def test_una_maquina_sin_intervalos_de_su_lista_es_error() -> None:
    with pytest.raises(ValueError):
        construir_verdad_simulada([("A", 1.0)], [], INICIO, 1, 0.0, "x", "y")


def test_la_cli_escribe_una_verdad_valida_con_el_desfase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MEDICIONES_CSV_DIR", str(tmp_path / "in"))
    monkeypatch.setenv("VERDAD_DIR", str(tmp_path / "verdad"))
    monkeypatch.setattr(
        "sys.argv",
        ["simular", "--dias", "1", "--verdad-json", str(tmp_path / "v.json"), "--desfase-s", "2.5"],
    )
    from src.infrastructure.settings.config import get_settings

    get_settings.cache_clear()
    try:
        simular()
    finally:
        get_settings.cache_clear()
    datos = json.loads((tmp_path / "v.json").read_text(encoding="utf-8"))
    verdad = VerdadIntervalosDTO.model_validate(datos)
    assert verdad.medidor.desfase_reloj_s == 2.5
    assert [c.nombre for c in verdad.cargas] == ["Carga 90 kW", "Carga 40 kW", "Carga 15 kW"]
