"""tests/e2e/test_cli_desagregar_cargas.py — ./run.sh disaggregate de punta a punta (CSV diario, sin VPS)."""

import json
import re
from pathlib import Path

import pytest

from src.infrastructure.cli.desagregar_cargas import (
    CODIGO_ARGUMENTOS,
    CODIGO_DATOS,
    CODIGO_OK,
)
from src.infrastructure.cli.desagregar_cargas import main as desagregar
from src.infrastructure.settings.config import get_settings

DEVICE_ID = "a01b1642-ed29-4c3e-a793-f57de09504f8"


@pytest.fixture
def carpeta_mediciones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un archivo diario por medidor: <device-id>_<fecha>.csv, con la reactiva en la tercera columna."""
    entrada = tmp_path / "input"
    entrada.mkdir()
    filas = [
        "2026-09-20T08:00:00,10.0,5.0",
        "2026-09-20T08:05:00,60.0,35.0",
        "2026-09-20T09:05:00,60.0,35.0",
        "2026-09-20T09:10:00,10.0,5.0",
    ]
    (entrada / f"{DEVICE_ID}_2026-09-20.csv").write_text(
        "instante,potencia_kw,reactiva_kvar\n" + "\n".join(filas) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MEDICIONES_CSV_DIR", str(entrada))
    get_settings.cache_clear()
    yield entrada
    get_settings.cache_clear()


def _args(*extra: str) -> list[str]:
    base = [
        "Trafo arriba",
        "--device-id",
        DEVICE_ID,
        "--fecha",
        "2026-09-20",
        "--potencia",
        "50.0",
        "--reactiva",
        "30.0",
        "--nombre",
        "Compresor Test",
        "--machine-id",
        "comp-1",
    ]
    return base + list(extra)


def test_cli_desagregar_cargas_ejecucion(
    carpeta_mediciones: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO", logger="backend-api"):
        ret = desagregar(_args())
    assert ret == CODIGO_OK
    assert "Iniciando desagregación batch para 'Trafo arriba'" in caplog.text
    assert "Desagregación completada. Intervalos asignados: 1" in caplog.text
    # Energía medida, no 50 kW × 1,08 h: 08:05–09:05 a 50 kW (50 kWh) más la bajada a 09:10 (2,08 kWh).
    assert (
        "Máquina 'Compresor Test' (sin load_id): 1.08 h marcha, 1 ciclos, 52.08 kWh" in caplog.text
    )


def test_salida_json_tiene_el_contrato_nilm_intervalos_v1(
    carpeta_mediciones: Path, tmp_path: Path
) -> None:
    salida = tmp_path / "salida" / "nilm_2026-09-20.json"
    assert desagregar(_args("--salida-json", str(salida))) == CODIGO_OK

    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["contrato"] == "nilm.intervalos.v1"
    # Sin microsegundos, como en la §5: AAAA-MM-DDTHH:MM:SSZ
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", datos["generado_en_utc"])
    assert datos["fecha_local"] == "2026-09-20"
    assert datos["ventana_utc"] == {
        "desde": "2026-09-20T03:00:00Z",
        "hasta": "2026-09-21T03:00:00Z",
    }
    assert datos["medidor"]["device_id"] == DEVICE_ID
    assert datos["medidor"]["etiqueta_ml"] == "Trafo arriba"
    (intervalo,) = datos["cargas"][0]["intervalos"]
    assert intervalo["inicio_utc"] == "2026-09-20T08:05:00Z"
    assert intervalo["fin_utc"] == "2026-09-20T09:10:00Z"
    assert intervalo["energia_kwh_medida"] == pytest.approx(52.083, abs=0.001)
    assert intervalo["origen"] == "INFERIDA"


def test_firmas_inexistente_falla_con_codigo_2(
    carpeta_mediciones: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Antes salía 0 en silencio; ahora un catálogo que no existe es un error de argumentos."""
    with caplog.at_level("INFO", logger="backend-api"):
        ret = desagregar(
            [
                "Trafo arriba",
                "--device-id",
                DEVICE_ID,
                "--fecha",
                "2026-09-20",
                "--firmas",
                str(tmp_path / "no_existe.json"),
            ]
        )
    assert ret == CODIGO_ARGUMENTOS
    assert "no existe" in caplog.text


def test_sin_firmas_ni_potencia_falla_con_codigo_2(carpeta_mediciones: Path) -> None:
    ret = desagregar(["Trafo arriba", "--device-id", DEVICE_ID, "--fecha", "2026-09-20"])
    assert ret == CODIGO_ARGUMENTOS


def test_device_id_invalido_falla_con_codigo_2(carpeta_mediciones: Path) -> None:
    ret = desagregar(
        _args()[:1] + ["--device-id", "no-es-un-uuid", "--fecha", "2026-09-20", "--potencia", "50"]
    )
    assert ret == CODIGO_ARGUMENTOS


def test_archivo_del_dia_ausente_falla_con_codigo_3(carpeta_mediciones: Path) -> None:
    """No hay CSV para el 21: no es un error de argumentos, es un dato faltante."""
    ret = desagregar(
        ["Trafo arriba", "--device-id", DEVICE_ID, "--fecha", "2026-09-21", "--potencia", "50"]
    )
    assert ret == CODIGO_DATOS
