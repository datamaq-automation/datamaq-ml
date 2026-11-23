"""tests/unit/test_catalogo_placa_csv.py — Lector del catálogo por placa y su CLI (datos sintéticos)."""

import json
from pathlib import Path

import pytest

from src.infrastructure.cli.comparar_placas import main as comparar
from src.infrastructure.csv.catalogo_placa_repository import leer_catalogo_placa

CABECERA = "etiqueta,potencia_nominal_kw,trafo,tipo_proceso,forma_arranque,cos_phi"


def _csv(tmp_path: Path, *filas: str) -> Path:
    ruta = tmp_path / "placas.csv"
    ruta.write_text("\n".join([CABECERA, *filas]) + "\n", encoding="utf-8")
    return ruta


@pytest.mark.parametrize(
    "fila",
    [
        "Motor A,,T1,bombeo,directo,0.85",
        "Motor A,abc,T1,bombeo,directo,0.85",
        "Motor A,0,T1,bombeo,directo,0.85",
        "Motor A,90,T1,bombeo,a-mano,0.85",
        "Motor A,90,T1,bombeo,directo,1.4",
        ",90,T1,bombeo,directo,0.85",
    ],
)
def test_una_fila_invalida_es_error_con_su_linea(tmp_path: Path, fila: str) -> None:
    with pytest.raises(ValueError, match="línea 2"):
        leer_catalogo_placa(_csv(tmp_path, fila))


def test_una_etiqueta_repetida_es_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repetida"):
        leer_catalogo_placa(
            _csv(tmp_path, "Motor A,90,T1,bombeo,directo,0.85", "Motor A,45,T1,bombeo,directo,0.85")
        )


def test_faltar_una_columna_obligatoria_es_error(tmp_path: Path) -> None:
    ruta = tmp_path / "placas.csv"
    ruta.write_text("etiqueta,potencia_nominal_kw\nMotor A,90\n", encoding="utf-8")
    with pytest.raises(ValueError, match="faltan columnas"):
        leer_catalogo_placa(ruta)


def test_sin_cos_phi_queda_el_tipico(tmp_path: Path) -> None:
    ruta = tmp_path / "placas.csv"
    ruta.write_text(
        "etiqueta,potencia_nominal_kw,trafo,tipo_proceso,forma_arranque\nMotor A,90,T1,bombeo,directo\n",
        encoding="utf-8",
    )
    (placa,) = leer_catalogo_placa(ruta)
    assert placa.cos_phi == 0.85


def test_la_cli_compara_y_escribe_el_detalle(tmp_path: Path) -> None:
    placas = _csv(tmp_path, "Motor A,90,T1,bombeo,directo,0.85")
    cargas = tmp_path / "cargas_T1.csv"
    cargas.write_text(
        "potencia_tipica_kw,encendidos,apagados,ciclos,dispersion_kw,reactiva_tipica_kvar,ratio_qp_mediana\n"
        "91.0,40,40,40,9.5,50.0,0.6\n",
        encoding="utf-8",
    )
    salida = tmp_path / "detalle.json"
    assert (
        comparar(["--placas", str(placas), "--cargas", str(cargas), "--salida-json", str(salida)])
        == 0
    )
    (fila,) = json.loads(salida.read_text(encoding="utf-8"))
    assert fila["estado"] == "coincide" and fila["forma_arranque"] == "directo"


def test_la_cli_sale_con_2_si_falta_el_archivo_de_cargas(tmp_path: Path) -> None:
    placas = _csv(tmp_path, "Motor A,90,T1,bombeo,directo,0.85")
    assert comparar(["--placas", str(placas), "--cargas", str(tmp_path / "no.csv")]) == 2
