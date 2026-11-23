"""tests/unit/test_ejemplo_verdad_documentado.py — El ejemplo de la documentación cumple el contrato (datos sintéticos)."""

from pathlib import Path

from src.application.cargas.dtos.verdad_intervalos import VerdadIntervalosDTO

EJEMPLO = Path(__file__).resolve().parents[2] / "docs" / "ejemplos" / "verdad_sintetica.json"


def test_el_ejemplo_documentado_valida_contra_el_esquema_estricto() -> None:
    verdad = VerdadIntervalosDTO.model_validate_json(EJEMPLO.read_text(encoding="utf-8"))
    assert verdad.contrato == "nilm.verdad.v1"
    assert [c.nombre for c in verdad.cargas] == ["Carga 90 kW", "Carga 15 kW"]
    assert verdad.medidor.fuente == "simulador"
