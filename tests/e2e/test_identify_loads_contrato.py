"""tests/e2e/test_identify_loads_contrato.py — Contrato de /identify-loads que consume datamaq-telemetry.

Si este test falla, se rompió un consumidor externo: agregar campos es seguro,
renombrar o quitar no lo es.
"""

from src.application.cargas.dtos.identificar_cargas import (
    CargaResponse,
    IdentificarCargasResponse,
)


def campos(modelo: type) -> set[str]:
    return set(modelo.model_json_schema()["properties"])


def test_contrato_de_la_respuesta() -> None:
    assert campos(IdentificarCargasResponse) == {
        "medidor",
        "mediciones",
        "eventos",
        "encendidos",
        "apagados",
        "eventos_sin_grupo",
        "dias",
        "potencia_media_kw",
        "cargas",
        "umbral",
        "agrupamiento",
        "serie",
        "detalle_eventos",
        "histograma",
        # Aditivos del issue #24: régimen de los saltos y modos separables (no rompen a quien ya consume).
        "sin_modos_separables",
        "modos",
        # Aditivo del issue #31: aviso de saltos bajo el umbral y energía desestimada.
        "saltos_bajo_umbral",
    }


def test_contrato_de_cada_carga() -> None:
    assert campos(CargaResponse) == {
        "potencia_tipica_kw",
        "encendidos",
        "apagados",
        "ciclos",
        "ciclos_por_dia",
        "on_off",
        "dispersion_kw",
        "reactiva_tipica_kvar",
        "cos_phi_estimado",
        "ratio_qp_mediana",
    }
