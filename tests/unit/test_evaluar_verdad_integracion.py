"""tests/unit/test_evaluar_verdad_integracion.py — Inferencia real contra la verdad del simulador (datos sintéticos).

El día simulado tiene tres cargas con firmas conocidas. La inferencia (batch) y la verdad (contactores del mismo
simulador) pasan por el evaluador y la CLI. Las aserciones son de amplitud: lo que se fija es la forma del
resultado y que el evaluador cuenta lo que el motor no encontró, no un valor exacto del motor.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    FirmaConfirmadaDTO,
)
from src.application.cargas.use_cases.atribuir_cargas_batch import AtribuirCargasBatchUseCase
from src.application.cargas.use_cases.construir_verdad import construir_verdad_simulada
from src.application.cargas.use_cases.evaluar_contra_verdad import evaluar_contra_verdad
from src.domain.cargas.entities import CargaSimulada
from src.domain.cargas.simulacion import simular_contactores, simular_tablero
from src.infrastructure.cli.evaluar_verdad import main as evaluar_cli

INICIO = datetime(2026, 9, 1)
CARGAS = [
    CargaSimulada(potencia_kw=90, ciclos_por_dia=18, duracion_min=25),
    CargaSimulada(potencia_kw=40, ciclos_por_dia=6, duracion_min=60),
    CargaSimulada(potencia_kw=15, ciclos_por_dia=30, duracion_min=10),
]
NOMBRES = ["Carga 90 kW", "Carga 40 kW", "Carga 15 kW"]


def _inferir_y_verdad(desfase_s: float = 0.0):
    mediciones, _ = simular_tablero(CARGAS, dias=1, ruido_kw=3.0, semilla=1, inicio=INICIO)
    firmas = [
        FirmaConfirmadaDTO(
            machine_id=f"m{i}", nombre=n, potencia_nominal_kw=c.potencia_kw, tolerancia_kw=5.0
        )
        for i, (n, c) in enumerate(zip(NOMBRES, CARGAS, strict=True))
    ]
    inferido = AtribuirCargasBatchUseCase().ejecutar(
        AtribuirCargasBatchRequestDTO(
            device_id="sintetico",
            etiqueta_ml="sintetico",
            fecha_local=date(2026, 9, 1),
            ventana_desde_utc=INICIO,
            ventana_hasta_utc=INICIO + timedelta(days=1),
            generado_en_utc=INICIO,
            mediciones=mediciones,
            firmas=firmas,
        )
    )
    tramos = simular_contactores(CARGAS, dias=1, semilla=1, inicio=INICIO, desfase_s=desfase_s)
    verdad = construir_verdad_simulada(
        list(zip(NOMBRES, [c.potencia_kw for c in CARGAS], strict=True)),
        tramos, INICIO, 1, desfase_s, etiqueta="sintetico", device_id="sintetico",
    )  # fmt: skip
    return inferido, verdad


def test_cada_maquina_de_la_verdad_tiene_resultado_con_los_conteos_del_simulador() -> None:
    inferido, verdad = _inferir_y_verdad()
    resultados = {r.maquina: r for r in evaluar_contra_verdad(inferido, verdad)}
    assert set(resultados) == set(NOMBRES)
    grande = resultados["Carga 90 kW"]
    arranques_sim = sum(1 for c in verdad.cargas[0].intervalos)
    assert grande.arranques.verdaderos == arranques_sim
    for r in resultados.values():
        assert 0.0 <= r.tiempo.precision <= 1.0 and 0.0 <= r.tiempo.sensibilidad <= 1.0


def test_la_energia_de_la_verdad_del_simulador_permite_medir_el_error() -> None:
    inferido, verdad = _inferir_y_verdad()
    grande = next(r for r in evaluar_contra_verdad(inferido, verdad) if r.maquina == "Carga 90 kW")
    assert grande.energia_verdadera_kwh is not None and grande.energia_verdadera_kwh > 0
    assert grande.error_energia_pct is not None


def test_el_desfase_de_10_segundos_no_mueve_los_eventos_con_tolerancia_de_300() -> None:
    inferido, verdad_limpia = _inferir_y_verdad(0.0)
    _, verdad_desfasada = _inferir_y_verdad(10.0)
    limpia = {r.maquina: r for r in evaluar_contra_verdad(inferido, verdad_limpia)}
    desfasada = {r.maquina: r for r in evaluar_contra_verdad(inferido, verdad_desfasada)}
    for nombre in NOMBRES:
        assert desfasada[nombre].arranques.emparejados == limpia[nombre].arranques.emparejados
        assert desfasada[nombre].paradas.emparejados == limpia[nombre].paradas.emparejados


def test_la_cli_lee_los_dos_contratos_y_escribe_el_detalle(tmp_path: Path) -> None:
    inferido, verdad = _inferir_y_verdad()
    (tmp_path / "inferido.json").write_text(inferido.model_dump_json(), encoding="utf-8")
    (tmp_path / "verdad.json").write_text(verdad.model_dump_json(), encoding="utf-8")
    codigo = evaluar_cli(
        [
            "--inferido", str(tmp_path / "inferido.json"),
            "--verdad", str(tmp_path / "verdad.json"),
            "--salida-json", str(tmp_path / "detalle.json"),
        ]
    )  # fmt: skip
    assert codigo == 0
    detalle = json.loads((tmp_path / "detalle.json").read_text(encoding="utf-8"))
    assert sorted(d["maquina"] for d in detalle) == sorted(NOMBRES)


def test_una_verdad_que_no_cumple_el_contrato_sale_con_2(tmp_path: Path) -> None:
    inferido, verdad = _inferir_y_verdad()
    datos = json.loads(verdad.model_dump_json())
    datos["clave_extra"] = 1
    (tmp_path / "inferido.json").write_text(inferido.model_dump_json(), encoding="utf-8")
    (tmp_path / "verdad.json").write_text(json.dumps(datos), encoding="utf-8")
    codigo = evaluar_cli(
        ["--inferido", str(tmp_path / "inferido.json"), "--verdad", str(tmp_path / "verdad.json")]
    )
    assert codigo == 2
