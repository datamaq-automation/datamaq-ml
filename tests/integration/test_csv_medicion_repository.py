"""tests/integration/test_csv_medicion_repository.py — Lectura y filtrado por rango desde CSV."""

from datetime import datetime
from pathlib import Path

import pytest

from src.infrastructure.csv.medicion_repository import CsvMedicionRepository


def test_listar_filtra_por_rango(tmp_path: Path) -> None:
    (tmp_path / "planta.csv").write_text(
        "instante,potencia_kw\n2026-09-20T00:00:00,1.5\n2026-09-20T00:05:00,2.5\n2026-09-21T00:00:00,9.0\n",
        encoding="utf-8",
    )
    mediciones = CsvMedicionRepository(tmp_path).listar(
        "planta", datetime(2026, 9, 20), datetime(2026, 9, 21)
    )
    assert [m.potencia_kw for m in mediciones] == [1.5, 2.5]
    assert mediciones[0].instante == datetime(2026, 9, 20)


def test_listar_sin_columna_reactiva_es_compatible(tmp_path: Path) -> None:
    """Un CSV viejo con solo instante,potencia_kw sigue funcionando; la reactiva es None."""
    (tmp_path / "planta.csv").write_text(
        "instante,potencia_kw\n2026-09-20T00:00:00,1.5\n", encoding="utf-8"
    )
    (medicion,) = CsvMedicionRepository(tmp_path).listar(
        "planta", datetime(2026, 9, 20), datetime(2026, 9, 21)
    )
    assert medicion.reactiva_kvar is None


def test_listar_lee_columna_reactiva_opcional(tmp_path: Path) -> None:
    """Con la columna reactiva_kvar se lee en kVAr; una celda vacía queda como None."""
    (tmp_path / "planta.csv").write_text(
        "instante,potencia_kw,reactiva_kvar\n"
        "2026-09-20T00:00:00,1.5,0.8\n"
        "2026-09-20T00:05:00,2.5,\n",
        encoding="utf-8",
    )
    mediciones = CsvMedicionRepository(tmp_path).listar(
        "planta", datetime(2026, 9, 20), datetime(2026, 9, 21)
    )
    assert [m.reactiva_kvar for m in mediciones] == [0.8, None]
    assert [m.potencia_kw for m in mediciones] == [1.5, 2.5]


def test_listar_lee_energia_acumulada_opcional(tmp_path: Path) -> None:
    """Con la columna energia_kwh se lee el contador acumulado; vacío o ausente es None."""
    (tmp_path / "planta.csv").write_text(
        "instante,potencia_kw,reactiva_kvar,energia_kwh\n"
        "2026-09-20T00:00:00,1.5,0.8,1000.25\n"
        "2026-09-20T00:05:00,2.5,0.9,\n",
        encoding="utf-8",
    )
    mediciones = CsvMedicionRepository(tmp_path).listar(
        "planta", datetime(2026, 9, 20), datetime(2026, 9, 21)
    )
    assert [m.energia_acumulada_kwh for m in mediciones] == [1000.25, None]


def test_listar_sin_columna_energia_deja_none(tmp_path: Path) -> None:
    (tmp_path / "planta.csv").write_text(
        "instante,potencia_kw,reactiva_kvar\n2026-09-20T00:00:00,1.5,0.8\n", encoding="utf-8"
    )
    (medicion,) = CsvMedicionRepository(tmp_path).listar(
        "planta", datetime(2026, 9, 20), datetime(2026, 9, 21)
    )
    assert medicion.energia_acumulada_kwh is None


def test_leer_archivo_usa_ventana_semiabierta_en_utc(tmp_path: Path) -> None:
    """La ventana [desde, hasta) es en UTC; un instante con zona se pasa a UTC antes de comparar."""
    ruta = tmp_path / "trafo_2026-09-20.csv"
    ruta.write_text(
        "instante,potencia_kw\n"
        "2026-09-20T02:55:00,1.0\n"  # antes de la ventana
        "2026-09-20T03:00:00,2.0\n"  # inicio incluido
        "2026-09-21T02:55:00,3.0\n"  # último instante de la ventana
        "2026-09-21T03:00:00,4.0\n"  # fin excluido
        "2026-09-20T06:00:00-03:00,5.0\n",  # = 2026-09-20T09:00Z, dentro
        encoding="utf-8",
    )
    desde, hasta = datetime(2026, 9, 20, 3, 0), datetime(2026, 9, 21, 3, 0)
    mediciones = CsvMedicionRepository(tmp_path).leer_archivo(ruta, desde, hasta)
    assert [m.potencia_kw for m in mediciones] == [2.0, 3.0, 5.0]
    assert mediciones[-1].instante == datetime(2026, 9, 20, 9, 0)


def test_listar_rechaza_medidores_que_no_son_csv_de_la_carpeta(tmp_path: Path) -> None:
    (tmp_path / "planta.csv").write_text("instante,potencia_kw\n", encoding="utf-8")
    repo = CsvMedicionRepository(tmp_path)
    assert repo.medidores() == ["planta"]
    with pytest.raises(LookupError):
        repo.listar("../.env", datetime(2026, 9, 20), datetime(2026, 9, 21))
