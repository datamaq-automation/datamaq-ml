"""tests/unit/test_verdad_intervalos_esquema.py — Esquema estricto de la verdad de terreno nilm.verdad.v1 (datos sintéticos)."""

import copy
import json

import pytest
from pydantic import ValidationError

from src.application.cargas.dtos.verdad_intervalos import VerdadIntervalosDTO


def _ejemplo() -> dict:
    """Un día sintético: una máquina con dos marchas, en la ventana UTC de un día argentino."""
    return {
        "contrato": "nilm.verdad.v1",
        "generado_en_utc": "2026-09-21T03:30:00Z",
        "fecha_local": "2026-09-20",
        "zona_horaria": "America/Argentina/Buenos_Aires",
        "ventana_utc": {"desde": "2026-09-20T03:00:00Z", "hasta": "2026-09-21T03:00:00Z"},
        "medidor": {"device_id": "sintetico", "etiqueta_ml": "sintetico", "fuente": "simulador"},
        "cargas": [
            {
                "nombre": "Compresor 90 kW",
                "intervalos": [
                    {
                        "inicio_utc": "2026-09-20T10:00:00Z",
                        "fin_utc": "2026-09-20T10:25:00Z",
                        "horas": 0.416667,
                        "origen": "MEDIDO",
                    },
                    {
                        "inicio_utc": "2026-09-20T14:00:00Z",
                        "fin_utc": "2026-09-20T15:00:00Z",
                        "horas": 1.0,
                        "origen": "MEDIDO",
                    },
                ],
            }
        ],
    }


def _con(cambio, datos: dict | None = None) -> dict:
    datos = copy.deepcopy(datos or _ejemplo())
    cambio(datos)
    return datos


def test_el_ejemplo_sintetico_es_valido() -> None:
    verdad = VerdadIntervalosDTO.model_validate(_ejemplo())
    assert verdad.contrato == "nilm.verdad.v1"
    assert [c.nombre for c in verdad.cargas] == ["Compresor 90 kW"]
    assert all(i.origen == "MEDIDO" for i in verdad.cargas[0].intervalos)


def test_el_json_del_ejemplo_se_lee_desde_texto() -> None:
    verdad = VerdadIntervalosDTO.model_validate_json(json.dumps(_ejemplo()))
    assert len(verdad.cargas[0].intervalos) == 2


@pytest.mark.parametrize(
    "cambio",
    [
        lambda d: d.update(contrato="nilm.intervalos.v1"),
        lambda d: d.update(clave_extra=1),
        lambda d: d["medidor"].update(origen="INFERIDA"),
        lambda d: d["cargas"][0]["intervalos"][0].update(origen="INFERIDA"),
        lambda d: d["cargas"][0]["intervalos"][0].update(clave_extra=1),
        lambda d: d["cargas"][0].update(clave_extra=1),
        lambda d: d["cargas"][0]["intervalos"][0].update(inicio_utc="2026-09-20T10:00:00"),
        lambda d: d["cargas"][0]["intervalos"][0].update(inicio_utc="2026-09-20T10:00:00-03:00"),
        lambda d: d["cargas"][0]["intervalos"][0].update(fin_utc="2026-09-20T09:00:00Z"),
        lambda d: d["cargas"][0]["intervalos"][0].update(horas=0.5),
        lambda d: d["cargas"][0]["intervalos"][0].update(confianza=1.5),
        lambda d: d["cargas"][0]["intervalos"][0].update(horas=-1.0),
        lambda d: d["cargas"][0].update(nombre=""),
        lambda d: d["cargas"].append(copy.deepcopy(d["cargas"][0])),
        lambda d: d["cargas"][0]["intervalos"].reverse(),
        lambda d: d["cargas"][0]["intervalos"].append(
            {
                "inicio_utc": "2026-09-20T10:10:00Z",
                "fin_utc": "2026-09-20T10:20:00Z",
                "horas": 0.166667,
                "origen": "MEDIDO",
            }
        ),
        lambda d: d["cargas"][0]["intervalos"][0].update(inicio_utc="2026-09-20T02:00:00Z"),
        lambda d: d["ventana_utc"].update(hasta="2026-09-20T12:00:00Z"),
    ],
)
def test_el_esquema_estricto_rechaza_cada_violacion(cambio) -> None:
    with pytest.raises(ValidationError):
        VerdadIntervalosDTO.model_validate(_con(cambio))


def test_las_energias_son_opcionales_pero_si_estan_se_validan() -> None:
    con_energia = _con(
        lambda d: d["cargas"][0]["intervalos"][0].update(
            energia_kwh_medida=38.5, potencia_media_kw=92.4
        )
    )
    assert (
        VerdadIntervalosDTO.model_validate(con_energia).cargas[0].intervalos[0].energia_kwh_medida
        == 38.5
    )
