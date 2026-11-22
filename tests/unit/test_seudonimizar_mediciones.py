"""tests/unit/test_seudonimizar_mediciones.py — Seudonimización: instantes y potencias idénticos (datos sintéticos)."""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.infrastructure.cli.seudonimizar_mediciones import (
    CODIGO_ARGUMENTOS,
    main,
    verificar_mediciones,
)

EMPRESA = "ACME Papeles S.A."
MEDIDOR_REAL = "TGBT Arriba"


def _escribir_csv(ruta: Path, potencias: list[float]) -> None:
    inicio = datetime(2026, 9, 20, 3, 0)
    with ruta.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["instante", "potencia_kw", "reactiva_kvar"])
        for i, p in enumerate(potencias):
            escritor.writerow([(inicio + timedelta(minutes=5 * i)).isoformat(), p, p / 2])


@pytest.fixture
def entrada(tmp_path: Path) -> Path:
    carpeta = tmp_path / "entrada"
    carpeta.mkdir()
    _escribir_csv(
        carpeta / f"{MEDIDOR_REAL}_2026-09-20.csv", [10.0 + (i % 7) * 1.5 for i in range(288)]
    )
    (carpeta / "notas.md").write_text(
        f"Datos de {EMPRESA}, planta de {MEDIDOR_REAL}.\n", encoding="utf-8"
    )
    return carpeta


@pytest.fixture
def configuracion(tmp_path: Path) -> Path:
    ruta = tmp_path / "config_fuera_del_repo.json"
    ruta.write_text(
        json.dumps(
            {
                "medidores": {MEDIDOR_REAL: "Trafo 1"},
                "empresa": {"patron": EMPRESA, "reemplazo": "una papelera"},
            }
        ),
        encoding="utf-8",
    )
    return ruta


def test_renombra_medidor_y_reemplaza_la_empresa(
    entrada: Path, configuracion: Path, tmp_path: Path
) -> None:
    salida = tmp_path / "salida"
    assert main([str(entrada), "--salida", str(salida), "--config", str(configuracion)]) == 0
    assert (salida / "Trafo 1_2026-09-20.csv").exists()
    assert not (salida / f"{MEDIDOR_REAL}_2026-09-20.csv").exists()
    notas = (salida / "notas.md").read_text(encoding="utf-8")
    assert "una papelera" in notas
    assert EMPRESA not in notas
    assert MEDIDOR_REAL not in notas


def test_instantes_y_potencias_salen_identicos(
    entrada: Path, configuracion: Path, tmp_path: Path
) -> None:
    salida = tmp_path / "salida"
    main([str(entrada), "--salida", str(salida), "--config", str(configuracion)])
    origen = entrada / f"{MEDIDOR_REAL}_2026-09-20.csv"
    destino = salida / "Trafo 1_2026-09-20.csv"
    assert verificar_mediciones(origen, destino)
    with origen.open(encoding="utf-8") as a, destino.open(encoding="utf-8") as b:
        assert list(csv.reader(a)) == list(csv.reader(b))


def test_la_verificacion_detecta_un_valor_alterado(tmp_path: Path) -> None:
    origen = tmp_path / "a.csv"
    destino = tmp_path / "b.csv"
    _escribir_csv(origen, [10.0, 20.0, 30.0])
    _escribir_csv(destino, [10.0, 20.5, 30.0])
    assert not verificar_mediciones(origen, destino)


def test_destino_dentro_de_un_repo_git_se_rechaza(
    entrada: Path, configuracion: Path, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    salida = repo / "material"
    assert (
        main([str(entrada), "--salida", str(salida), "--config", str(configuracion)])
        == CODIGO_ARGUMENTOS
    )
    assert not salida.exists()


def test_configuracion_incompleta_falla_con_codigo_2(entrada: Path, tmp_path: Path) -> None:
    config = tmp_path / "mala.json"
    config.write_text(json.dumps({"medidores": {}}), encoding="utf-8")
    assert (
        main([str(entrada), "--salida", str(tmp_path / "s"), "--config", str(config)])
        == CODIGO_ARGUMENTOS
    )


def test_el_log_no_muestra_nombres_ni_empresa(
    entrada: Path, configuracion: Path, tmp_path: Path, caplog
) -> None:
    with caplog.at_level("INFO", logger="backend-api"):
        main([str(entrada), "--salida", str(tmp_path / "salida"), "--config", str(configuracion)])
    assert EMPRESA not in caplog.text
    assert MEDIDOR_REAL not in caplog.text
    assert "Trafo 1" not in caplog.text
