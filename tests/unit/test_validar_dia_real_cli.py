"""tests/unit/test_validar_dia_real_cli.py — La validación de un día escribe solo agregados (datos sintéticos)."""

import json
from pathlib import Path

import pytest

from src.infrastructure.cli.validar_dia_real import (
    CODIGO_ARGUMENTOS,
    CODIGO_DATOS,
    CODIGO_OK,
    main,
)


@pytest.fixture
def dia_sintetico(tmp_path: Path) -> tuple[Path, Path]:
    """Un día de muestras cada 5 min (en UTC) con una carga de 50 kW de 10:00 a 11:00 ART (13:00-14:00 UTC)."""
    filas = ["instante,potencia_kw,reactiva_kvar"]
    from datetime import datetime, timedelta

    inicio = datetime(2026, 9, 20, 3, 0)  # 00:00 ART = 03:00 UTC
    for i in range(288):
        t = inicio + timedelta(minutes=5 * i)
        en_marcha = datetime(2026, 9, 20, 13, 0) <= t < datetime(2026, 9, 20, 14, 0)
        p = 10.0 + (50.0 if en_marcha else 0.0)
        filas.append(f"{t.isoformat()},{p},{5.0 + (30.0 if en_marcha else 0.0)}")
    csv = tmp_path / "medidor.csv"
    csv.write_text("\n".join(filas) + "\n", encoding="utf-8")
    firmas = tmp_path / "firmas.json"
    firmas.write_text(
        json.dumps(
            [
                {
                    "machine_id": "m50",
                    "nombre": "Motor 50",
                    "potencia_nominal_kw": 50.0,
                    "tolerancia_kw": 5.0,
                }
            ]
        ),
        encoding="utf-8",
    )
    return csv, firmas


def test_escribe_metricas_agregadas_sin_filas_de_mediciones(dia_sintetico, tmp_path: Path) -> None:
    csv, firmas = dia_sintetico
    salida = tmp_path / "salida" / "metricas.json"
    ret = main(
        [
            "--archivo",
            str(csv),
            "--firmas",
            str(firmas),
            "--fecha",
            "2026-09-20",
            "--salida-json",
            str(salida),
        ]
    )
    assert ret == CODIGO_OK
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["intervalos_cerrados"] == 1
    assert datos["eventos_sin_atribuir"] == 0
    assert datos["energia_atribuida_excede_medida"] is False
    texto = salida.read_text(encoding="utf-8")
    assert "instante" not in texto  # no se copian filas de mediciones
    assert "2026-09-20T" not in texto


def test_catalogo_inexistente_falla_con_codigo_2(dia_sintetico, tmp_path: Path) -> None:
    csv, _ = dia_sintetico
    ret = main(
        [
            "--archivo",
            str(csv),
            "--firmas",
            str(tmp_path / "no.json"),
            "--fecha",
            "2026-09-20",
            "--salida-json",
            str(tmp_path / "x.json"),
        ]
    )
    assert ret == CODIGO_ARGUMENTOS


def test_csv_del_dia_ausente_falla_con_codigo_3(dia_sintetico, tmp_path: Path) -> None:
    _, firmas = dia_sintetico
    ret = main(
        [
            "--archivo",
            str(tmp_path / "no.csv"),
            "--firmas",
            str(firmas),
            "--fecha",
            "2026-09-20",
            "--salida-json",
            str(tmp_path / "x.json"),
        ]
    )
    assert ret == CODIGO_DATOS


def test_la_salida_incluye_los_indicadores_de_banco(dia_sintetico, tmp_path: Path) -> None:
    """El JSON de la validación trae el indicador que decide la hipótesis del banco fijo."""
    csv, firmas = dia_sintetico
    salida = tmp_path / "banco.json"
    ret = main(
        [
            "--archivo",
            str(csv),
            "--firmas",
            str(firmas),
            "--fecha",
            "2026-09-20",
            "--salida-json",
            str(salida),
        ]
    )
    assert ret == CODIGO_OK
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert "eventos_banco_dp_bajo_dq_alto" in datos
    assert "energia_atribuida_solo_p_kwh" in datos
    assert "diferencia_pct_p_vs_pq" in datos
