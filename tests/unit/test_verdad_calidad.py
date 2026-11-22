"""tests/unit/test_verdad_calidad.py — Bloque `calidad` de nilm.verdad.v1: esquema y compatibilidad (datos sintéticos)."""

import copy
import json
from pathlib import Path

import pydantic
import pytest

from src.application.cargas.dtos.verdad_intervalos import VerdadIntervalosDTO

EJEMPLO = Path(__file__).resolve().parents[2] / "docs" / "ejemplos" / "verdad_sintetica.json"


def _base() -> dict:
    return json.loads(EJEMPLO.read_text(encoding="utf-8"))


def _con_calidad(calidad: dict | None) -> dict:
    datos = copy.deepcopy(_base())
    if calidad is None:
        datos["medidor"].pop("calidad", None)
    else:
        datos["medidor"]["calidad"] = calidad
    return datos


@pytest.mark.parametrize(
    "calidad",
    [
        {"estado": "OK", "motivos": []},
        {"estado": "OK"},
        {"estado": "DUDOSA", "motivos": ["huecos_seq"], "cobertura_pct": 72.5},
        {"estado": "NO_UTILIZABLE", "motivos": ["desvio_reloj", "sin_cobertura"]},
    ],
)
def test_bloque_calidad_valido_en_los_tres_estados(calidad: dict) -> None:
    verdad = VerdadIntervalosDTO.model_validate(_con_calidad(calidad))
    assert verdad.medidor.calidad is not None
    assert verdad.medidor.calidad.estado == calidad["estado"]


@pytest.mark.parametrize(
    "calidad",
    [
        {"estado": "DUDOSA", "motivos": ["causa_inventada"]},
        {"estado": "OK", "motivos": ["huecos_seq"]},
        {"estado": "DUDOSA", "motivos": []},
        {"estado": "NO_UTILIZABLE"},
        {"estado": "DUDOSA", "motivos": ["huecos_seq", "huecos_seq"]},
        {"estado": "BUENO", "motivos": []},
        {"estado": "OK", "cobertura_pct": 101},
        {"estado": "OK", "cobertura_pct": -1},
        {"estado": "OK", "nota": "clave fuera del contrato"},
    ],
)
def test_bloque_calidad_invalido_se_rechaza(calidad: dict) -> None:
    with pytest.raises(pydantic.ValidationError):
        VerdadIntervalosDTO.model_validate(_con_calidad(calidad))


def test_motivos_del_catalogo_cerrado_son_exactamente_cinco() -> None:
    for motivo in (
        "huecos_seq",
        "desvio_reloj",
        "hora_no_confiable",
        "sin_cobertura",
        "abierto_al_cierre",
    ):
        verdad = VerdadIntervalosDTO.model_validate(
            _con_calidad({"estado": "DUDOSA", "motivos": [motivo]})
        )
        assert verdad.medidor.calidad.motivos == [motivo]


def test_archivo_sin_bloque_calidad_sigue_valiendo_y_se_asume_ok() -> None:
    datos = _con_calidad(None)
    verdad = VerdadIntervalosDTO.model_validate(datos)
    assert verdad.medidor.calidad is None
    assert verdad.medidor.calidad_efectiva.estado == "OK"
    assert verdad.medidor.calidad_efectiva.motivos == []


def test_el_ejemplo_documentado_trae_calidad_ok() -> None:
    verdad = VerdadIntervalosDTO.model_validate_json(EJEMPLO.read_text(encoding="utf-8"))
    assert verdad.medidor.calidad is not None
    assert verdad.medidor.calidad.estado == "OK"
    assert verdad.medidor.calidad.motivos == []
