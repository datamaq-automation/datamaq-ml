"""tests/unit/test_evaluar_dia_calidad.py — El evaluador trata cada estado de calidad (datos sintéticos).

OK se evalúa y cuenta; DUDOSA se evalúa y queda marcada fuera del resumen; NO_UTILIZABLE se rechaza.
Las banderas --incluir-dudosos e --incluir-no-utilizables los cambian.
"""

import copy
import json
from pathlib import Path

from src.application.cargas.dtos.desagregar_cargas import AtribuirCargasBatchResponseDTO
from src.application.cargas.dtos.verdad_intervalos import VerdadIntervalosDTO
from src.application.cargas.use_cases.evaluar_contra_verdad import evaluar_dia, resumen_exclusiones

EJEMPLO = Path(__file__).resolve().parents[2] / "docs" / "ejemplos" / "verdad_sintetica.json"


def _verdad(estado: str | None, motivos: list[str] | None = None) -> VerdadIntervalosDTO:
    datos = copy.deepcopy(json.loads(EJEMPLO.read_text(encoding="utf-8")))
    if estado is None:
        datos["medidor"].pop("calidad", None)
    else:
        datos["medidor"]["calidad"] = {"estado": estado, "motivos": motivos or []}
    return VerdadIntervalosDTO.model_validate(datos)


def _inferido() -> AtribuirCargasBatchResponseDTO:
    # Un día inferido sin máquinas: el evaluador cuenta todo lo de la verdad como no encontrado.
    return AtribuirCargasBatchResponseDTO.model_validate(
        {
            "generado_en_utc": "2026-09-02T03:00:00Z",
            "fecha_local": "2026-09-01",
            "ventana_utc": {"desde": "2026-09-01T03:00:00Z", "hasta": "2026-09-02T03:00:00Z"},
            "medidor": {
                "device_id": "sintetico",
                "etiqueta_ml": "sintetico",
                "ultima_lectura_utc": None,
            },
            "cargas": [],
        }
    )


def test_ok_se_evalua_y_cuenta_en_el_resumen() -> None:
    ev = evaluar_dia(_inferido(), _verdad(None))
    assert ev.estado == "OK" and ev.evaluado and ev.en_resumen
    assert len(ev.resultados) == 2


def test_dudosa_se_evalua_y_queda_marcada_fuera_del_resumen_por_defecto() -> None:
    ev = evaluar_dia(_inferido(), _verdad("DUDOSA", ["huecos_seq"]))
    assert ev.estado == "DUDOSA" and ev.evaluado
    assert not ev.en_resumen
    assert ev.motivos == ("huecos_seq",)
    assert len(ev.resultados) == 2


def test_dudosa_con_incluir_dudosos_cuenta_en_el_resumen() -> None:
    ev = evaluar_dia(_inferido(), _verdad("DUDOSA", ["huecos_seq"]), incluir_dudosos=True)
    assert ev.evaluado and ev.en_resumen


def test_no_utilizable_se_rechaza_por_defecto_sin_evaluar() -> None:
    ev = evaluar_dia(_inferido(), _verdad("NO_UTILIZABLE", ["desvio_reloj", "sin_cobertura"]))
    assert ev.estado == "NO_UTILIZABLE" and not ev.evaluado and not ev.en_resumen
    assert ev.resultados == []
    assert ev.motivos == ("desvio_reloj", "sin_cobertura")


def test_no_utilizable_con_incluir_no_utilizables_se_evalua() -> None:
    ev = evaluar_dia(
        _inferido(), _verdad("NO_UTILIZABLE", ["desvio_reloj"]), incluir_no_utilizables=True
    )
    assert ev.evaluado and ev.en_resumen and len(ev.resultados) == 2


def test_la_bandera_de_dudosos_no_habilita_los_no_utilizables() -> None:
    ev = evaluar_dia(_inferido(), _verdad("NO_UTILIZABLE", ["sin_cobertura"]), incluir_dudosos=True)
    assert not ev.evaluado


def test_resumen_cuenta_excluidos_y_su_motivo() -> None:
    evaluaciones = [
        evaluar_dia(_inferido(), _verdad("NO_UTILIZABLE", ["desvio_reloj", "huecos_seq"])),
        evaluar_dia(_inferido(), _verdad("NO_UTILIZABLE", ["huecos_seq"])),
        evaluar_dia(_inferido(), _verdad("DUDOSA", ["sin_cobertura"])),
        evaluar_dia(_inferido(), _verdad(None)),
    ]
    resumen = resumen_exclusiones(evaluaciones)
    assert resumen["dias"] == 4
    assert resumen["excluidos"] == 2
    assert resumen["por_motivo"] == {"desvio_reloj": 1, "huecos_seq": 2}
