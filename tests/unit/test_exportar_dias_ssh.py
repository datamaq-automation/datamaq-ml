"""tests/unit/test_exportar_dias_ssh.py — Exportación diaria desde el VPS, con ssh simulado (sin red, sin producción)."""

import stat
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.infrastructure.cli.exportar_dias_ssh import (
    CODIGO_ARGUMENTOS,
    CODIGO_OK,
    CODIGO_TOPE,
    ErrorExportacion,
    consulta_dia,
    escribir_csv,
    main,
    preparar_salida,
)
from src.infrastructure.ssh.medicion_repository import (
    FilaDia,
    SshMedicionRepository,
    ejecutar_consulta_de_lectura,
    parsear_filas_dia,
)

DEVICE = "a01b1642-ed29-4c3e-a793-f57de09504f8"
ESCRITURAS = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE", "TRUNCATE")


def _consulta(con_energia: bool = True, tope: int = 5000) -> str:
    return consulta_dia(
        DEVICE, datetime(2026, 9, 12, 3, 0), datetime(2026, 9, 13, 3, 0), tope, con_energia
    )


def test_la_consulta_es_un_select_de_la_ventana_con_datos_confiables() -> None:
    sql = _consulta()
    assert sql.startswith("SELECT ")
    assert f"t.device_id = '{DEVICE}'" in sql
    assert "t.recorded_at >= '2026-09-12 03:00:00' AND t.recorded_at < '2026-09-13 03:00:00'" in sql
    assert "t.es_dato_confiable = 1" in sql
    assert "LIMIT 5001" in sql  # tope + 1 para detectar el desborde
    assert not any(palabra in sql.upper() for palabra in ESCRITURAS)


def test_sin_energia_la_consulta_no_une_la_tabla_de_energia() -> None:
    sql = _consulta(con_energia=False)
    assert "telemetry_energy" not in sql
    assert "net_active_energy_kwh" not in sql


def test_un_device_id_que_no_es_uuid_canonico_se_rechaza_antes_de_armar_la_consulta() -> None:
    with pytest.raises(ErrorExportacion) as error:
        consulta_dia(
            "x'; DROP TABLE devices; --", datetime(2026, 9, 12), datetime(2026, 9, 13), 10, True
        )
    assert error.value.codigo == CODIGO_ARGUMENTOS


def test_el_adaptador_rechaza_cualquier_cosa_que_no_sea_un_select(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llamadas: list[str] = []
    monkeypatch.setattr(
        "src.infrastructure.ssh.medicion_repository.subprocess.run",
        lambda *a, **k: llamadas.append("x"),
    )
    repo = SshMedicionRepository(cache_dir=Path("/tmp/no-usado"))
    for mala in ["DELETE FROM devices", "SELECT 1; DROP TABLE devices", "UPDATE x SET y=1"]:
        with pytest.raises(ValueError):
            ejecutar_consulta_de_lectura(repo, mala)
    assert llamadas == []  # no se tocó la red


def test_las_unidades_son_w_a_kw_var_a_kvar_y_la_energia_no_cambia() -> None:
    filas = parsear_filas_dia("2026-09-12 03:00:01\t92000\t35000\t1000.5\n", con_energia=True)
    assert filas == [FilaDia("2026-09-12T03:00:01", 92.0, 35.0, 1000.5)]


def test_un_null_queda_como_none_y_una_fila_corta_es_error() -> None:
    filas = parsear_filas_dia("2026-09-12 03:05:01\t91000\tNULL\tNULL\n", con_energia=True)
    assert filas[0].reactiva_kvar is None and filas[0].energia_kwh is None
    with pytest.raises(ValueError):
        parsear_filas_dia("2026-09-12 03:05:01\t91000\n", con_energia=True)


def test_el_csv_tiene_la_cabecera_con_energia_y_permisos_600(tmp_path: Path) -> None:
    ruta = tmp_path / "medidor_2026-09-12.csv"
    escribir_csv(ruta, [FilaDia("2026-09-12T03:00:01", 92.0, None, None)], con_energia=True)
    assert ruta.read_text(encoding="utf-8").splitlines() == [
        "instante,potencia_kw,reactiva_kvar,energia_kwh",
        "2026-09-12T03:00:01,92.0,,",
    ]
    assert stat.S_IMODE(ruta.stat().st_mode) == 0o600


def test_el_directorio_se_crea_con_700_y_uno_con_otros_permisos_se_rechaza(tmp_path: Path) -> None:
    nuevo = tmp_path / "salida"
    preparar_salida(nuevo)
    assert stat.S_IMODE(nuevo.stat().st_mode) == 0o700
    abierto = tmp_path / "abierto"
    abierto.mkdir(mode=0o755)
    abierto.chmod(0o755)
    with pytest.raises(ErrorExportacion) as error:
        preparar_salida(abierto)
    assert error.value.codigo == CODIGO_ARGUMENTOS


def test_un_directorio_dentro_de_un_repo_git_se_rechaza(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    with pytest.raises(ErrorExportacion) as error:
        preparar_salida(repo / "salida")
    assert error.value.codigo == CODIGO_ARGUMENTOS


def _ssh_falso(filas_por_dia: dict[str, str]):
    """Simula `ssh vps mysql`: responde según el día del WHERE de la consulta."""

    def fake_run(args, input=None, **kwargs):  # noqa: A002
        for dia, salida in filas_por_dia.items():
            if f"recorded_at >= '{dia} 03:00:00'" in input:
                return SimpleNamespace(stdout=salida)
        return SimpleNamespace(stdout="")

    return fake_run


def test_main_escribe_un_archivo_por_dia_y_los_dias_vacios_solo_con_cabecera(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "src.infrastructure.ssh.medicion_repository.subprocess.run",
        _ssh_falso(
            {
                "2026-09-12": "2026-09-12 03:00:01\t92000\t35000\t1000.5\n2026-09-12 03:05:01\t91000\tNULL\tNULL\n"
            }
        ),
    )
    salida = tmp_path / "salida"
    with caplog.at_level("INFO", logger="backend-api"):
        codigo = main(
            [
                "--device-id",
                DEVICE,
                "--desde",
                "2026-09-12",
                "--hasta",
                "2026-09-13",
                "--salida-dir",
                str(salida),
            ]
        )
    assert codigo == CODIGO_OK
    dia = (salida / f"{DEVICE}_2026-09-12.csv").read_text(encoding="utf-8").splitlines()
    assert dia[1] == "2026-09-12T03:00:01,92.0,35.0,1000.5"
    vacio = (salida / f"{DEVICE}_2026-09-13.csv").read_text(encoding="utf-8").splitlines()
    assert vacio == ["instante,potencia_kw,reactiva_kvar,energia_kwh"]


def test_el_log_solo_tiene_conteos_no_valores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "src.infrastructure.ssh.medicion_repository.subprocess.run",
        _ssh_falso({"2026-09-12": "2026-09-12 03:00:01\t92000\t35000\t1000.5\n"}),
    )
    with caplog.at_level("INFO", logger="backend-api"):
        main(
            [
                "--device-id",
                DEVICE,
                "--desde",
                "2026-09-12",
                "--hasta",
                "2026-09-12",
                "--salida-dir",
                str(tmp_path / "s"),
            ]
        )
    assert "1 filas exportadas" in caplog.text
    assert DEVICE not in caplog.text
    assert "92" not in caplog.text


def test_un_dia_que_supera_el_tope_no_se_escribe_y_sale_con_codigo_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "src.infrastructure.ssh.medicion_repository.subprocess.run",
        _ssh_falso({"2026-09-12": "2026-09-12 03:00:01\t1\t1\t1\n" * 3}),
    )
    salida = tmp_path / "salida"
    codigo = main(
        [
            "--device-id",
            DEVICE,
            "--desde",
            "2026-09-12",
            "--hasta",
            "2026-09-12",
            "--salida-dir",
            str(salida),
            "--tope-filas-dia",
            "2",
        ]
    )
    assert codigo == CODIGO_TOPE
    assert not (salida / f"{DEVICE}_2026-09-12.csv").exists()


def test_sin_energia_la_cabecera_tiene_tres_columnas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "src.infrastructure.ssh.medicion_repository.subprocess.run",
        _ssh_falso({"2026-09-12": "2026-09-12 03:00:01\t92000\t35000\n"}),
    )
    salida = tmp_path / "salida"
    assert (
        main(
            [
                "--device-id",
                DEVICE,
                "--desde",
                "2026-09-12",
                "--hasta",
                "2026-09-12",
                "--salida-dir",
                str(salida),
                "--sin-energia",
            ]
        )
        == CODIGO_OK
    )
    assert (salida / f"{DEVICE}_2026-09-12.csv").read_text(encoding="utf-8").splitlines()[0] == (
        "instante,potencia_kw,reactiva_kvar"
    )


def test_un_rango_invertido_falla_con_codigo_2(tmp_path: Path) -> None:
    codigo = main(
        [
            "--device-id",
            DEVICE,
            "--desde",
            "2026-09-13",
            "--hasta",
            "2026-09-12",
            "--salida-dir",
            str(tmp_path / "s"),
        ]
    )
    assert codigo == CODIGO_ARGUMENTOS
