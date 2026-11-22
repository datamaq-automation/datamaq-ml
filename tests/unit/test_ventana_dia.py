"""tests/unit/test_ventana_dia.py — D-1 y ventana UTC del día argentino (America/Argentina/Buenos_Aires)."""

from datetime import date, datetime, timezone

from src.infrastructure.cli.desagregar_cargas import dia_local_anterior, ventana_utc_del_dia


def test_timer_de_las_0330_utc_procesa_el_dia_que_ya_cerro() -> None:
    """03:30 UTC del 22 son las 00:30 ART del 22: el día cerrado es el 21."""
    assert dia_local_anterior(datetime(2026, 11, 22, 3, 30, tzinfo=timezone.utc)) == date(
        2026, 11, 21
    )


def test_antes_de_medianoche_argentina_el_dia_local_sigue_siendo_el_anterior() -> None:
    """02:30 UTC del 22 son las 23:30 ART del 21: el día en curso es el 21, así que D-1 es el 20."""
    assert dia_local_anterior(datetime(2026, 11, 22, 2, 30, tzinfo=timezone.utc)) == date(
        2026, 11, 20
    )


def test_instante_sin_zona_se_toma_como_utc() -> None:
    assert dia_local_anterior(datetime(2026, 11, 22, 3, 30)) == date(2026, 11, 21)


def test_ventana_del_dia_local_es_semiabierta_y_en_utc() -> None:
    """00:00 ART es 03:00 UTC; el día termina en el 00:00 ART del día siguiente (03:00 UTC)."""
    desde, hasta = ventana_utc_del_dia(date(2026, 11, 21))
    assert desde == datetime(2026, 11, 21, 3, 0)
    assert hasta == datetime(2026, 11, 22, 3, 0)
    assert desde < hasta
