"""tests/unit/test_catalogo_desde_entrenamiento.py — Catálogo de firmas desde lo que entrenó train (datos sintéticos)."""

import json
from pathlib import Path

from src.application.cargas.dtos.desagregar_cargas import FirmaConfirmadaDTO
from src.infrastructure.cli.catalogo_desde_entrenamiento import main

CABECERA = "potencia_tipica_kw,encendidos,apagados,ciclos,dispersion_kw,reactiva_tipica_kvar,ratio_qp_mediana"


def _escribir(tmp_path: Path, filas: list[str], regimen: dict) -> tuple[Path, Path]:
    cargas = tmp_path / "cargas_T1.csv"
    cargas.write_text("\n".join([CABECERA, *filas]) + "\n", encoding="utf-8")
    entrenamiento = tmp_path / "entrenamiento_T1.json"
    entrenamiento.write_text(json.dumps(regimen), encoding="utf-8")
    return cargas, entrenamiento


def test_cada_cluster_es_una_firma_con_reactiva_por_ratio_y_dispersion(tmp_path: Path) -> None:
    cargas, entrenamiento = _escribir(
        tmp_path, ["91.4,120,118,118,9.5,51.2,0.56"], {"sin_modos_separables": False}
    )
    salida = tmp_path / "catalogo.json"
    assert (
        main(
            [
                "--cargas",
                str(cargas),
                "--entrenamiento",
                str(entrenamiento),
                "--salida",
                str(salida),
            ]
        )
        == 0
    )
    (firma,) = json.loads(salida.read_text(encoding="utf-8"))
    dto = FirmaConfirmadaDTO(
        **firma
    )  # el catálogo tiene que ser una lista de FirmaConfirmadaDTO válida
    assert dto.potencia_nominal_kw == 91.4
    assert dto.reactiva_tipica_kvar == round(0.56 * 91.4, 2)
    assert dto.dispersion_kw == 9.5
    assert dto.tolerancia_kw == 5.0


def test_sin_modos_separables_deja_el_catalogo_vacio(tmp_path: Path) -> None:
    cargas, entrenamiento = _escribir(
        tmp_path, ["88.0,40,40,40,9.0,30.0,"], {"sin_modos_separables": True}
    )
    salida = tmp_path / "catalogo.json"
    assert (
        main(
            [
                "--cargas",
                str(cargas),
                "--entrenamiento",
                str(entrenamiento),
                "--salida",
                str(salida),
            ]
        )
        == 0
    )
    assert json.loads(salida.read_text(encoding="utf-8")) == []


def test_sin_ratio_la_reactiva_queda_en_cero(tmp_path: Path) -> None:
    cargas, entrenamiento = _escribir(tmp_path, ["60.0,10,10,10,4.0,0.0,"], {})
    salida = tmp_path / "catalogo.json"
    main(["--cargas", str(cargas), "--entrenamiento", str(entrenamiento), "--salida", str(salida)])
    (firma,) = json.loads(salida.read_text(encoding="utf-8"))
    assert firma["reactiva_tipica_kvar"] == 0.0


def test_un_archivo_ausente_falla_con_codigo_2(tmp_path: Path) -> None:
    codigo = main(
        [
            "--cargas", str(tmp_path / "no.csv"),
            "--entrenamiento", str(tmp_path / "no.json"),
            "--salida", str(tmp_path / "catalogo.json"),
        ]
    )  # fmt: skip
    assert codigo == 2
