"""tests/unit/test_presentacion_cli.py — Presentación de la terminal (#29): formato, veredictos, siguiente paso y run.sh.

Todas las salidas se prueban con NO_COLOR=1 y COLUMNS=80: sin colores y con el ancho de la terminal.
"""

from __future__ import annotations

import pytest

from src.application.cargas.dtos.identificar_cargas import (
    AgrupamientoResponse,
    CargaResponse,
    IdentificarCargasResponse,
    UmbralResponse,
)
from src.infrastructure.cli import presentacion as p

ANSI = "\x1b["


@pytest.fixture(autouse=True)
def terminal_fija(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "80")


def _respuesta(cargas: list[CargaResponse], sin_grupo: int, sin_modos: bool = False):
    return IdentificarCargasResponse(
        medidor="sintetico",
        mediciones=4032,
        eventos=496,
        eventos_sin_grupo=sin_grupo,
        potencia_media_kw=160.0,
        cargas=cargas,
        umbral=UmbralResponse(kw=48.9, automatico=True, separacion=0.9, confiable=True),
        agrupamiento=AgrupamientoResponse(
            radio_kw=8.2, radio_automatico=True, min_eventos=14, min_eventos_automatico=True
        ),
        sin_modos_separables=sin_modos,
        dias=14.0,
        histograma=[],
    )


def _carga() -> CargaResponse:
    return CargaResponse(
        potencia_tipica_kw=89.5,
        encendidos=245,
        apagados=243,
        ciclos=243,
        on_off=False,
        dispersion_kw=4.1,
    )


def test_numero_usa_coma_decimal_y_punto_de_miles() -> None:
    assert p.numero(4031, 0) == "4.031"
    assert p.numero(48.94) == "48,9"
    assert p.numero(0.5, 2) == "0,50"


def test_veredicto_tiene_simbolo_y_palabra_en_ambos_formatos() -> None:
    assert p.veredicto("ok", "todo bien", unicode=True).startswith("✔ OK")
    assert p.veredicto("aviso", "cuidado", unicode=True).startswith("⚠ AVISO")
    assert p.veredicto("error", "roto", unicode=True).startswith("✘ ERROR")
    assert p.veredicto("error", "roto", unicode=False) == "[ERROR] roto"


def test_tabla_alinea_columnas_al_ancho_de_la_celda_mas_larga() -> None:
    lineas = p.tabla(["Carga", "Potencia"], [["carga 1", "89,5 kW"], ["c2", "5 kW"]])
    assert lineas[0].index("Potencia") == lineas[2].index("89,5 kW") == lineas[3].index("5 kW")
    assert lineas[1] == "-------  --------"


def test_error_que_ensena_tiene_que_por_que_y_como() -> None:
    lineas = p.error_que_ensena("Falta el CSV.", "no existe.", "copiá el archivo.", "README.md")
    assert lineas[0].startswith("✘ ERROR") or lineas[0].startswith("[ERROR]")
    assert any("Por qué:" in linea for linea in lineas)
    assert any("Cómo:" in linea for linea in lineas)
    assert lineas[-1].strip().startswith("Guía:")


def test_ancho_de_terminal_respeta_columns_y_tiene_minimo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "100")
    assert p.ancho_terminal() == 100
    monkeypatch.setenv("COLUMNS", "abc")
    assert p.ancho_terminal() == 80
    monkeypatch.setenv("COLUMNS", "10")
    assert p.ancho_terminal() == 40


def test_entrenamiento_sin_ruido_da_ok_y_siguiente_paso_supervise() -> None:
    r = _respuesta([_carga()], sin_grupo=0)
    assert p.veredicto_entrenamiento(r)[0] == "ok"
    assert p.siguiente_paso_entrenamiento(r, "sintetico").startswith("./run.sh supervise")


def test_eventos_sin_grupo_dan_aviso_con_la_cifra_y_ayuda_que_existe() -> None:
    r = _respuesta([_carga()], sin_grupo=8)
    nivel, texto = p.veredicto_entrenamiento(r)
    assert nivel == "aviso"
    assert "8 de 496 eventos" in texto
    assert p.siguiente_paso_entrenamiento(r, "sintetico") == (
        "./run.sh train sintetico --grafico   (ver dónde caen los saltos)"
    )


def test_sin_modos_separables_no_inventa_cargas() -> None:
    r = _respuesta([], sin_grupo=0, sin_modos=True)
    nivel, texto = p.veredicto_entrenamiento(r)
    assert nivel == "aviso"
    assert "no se agrupan cargas" in texto


def test_resumen_tiene_tabla_veredicto_y_siguiente_paso_sin_ansi() -> None:
    lineas = p.lineas_resumen_entrenamiento(_respuesta([_carga()], sin_grupo=8), "sintetico")
    salida = "\n".join(lineas)
    assert "Resumen de «sintetico» (4032 mediciones, 14,0 días)" in salida
    assert "89,5 kW" in salida
    assert "Umbral · radio · mínimo: 48,9 kW · 8,2 kW · 14 eventos" in salida
    assert "Siguiente paso:" in salida
    assert ANSI not in salida
    assert max(len(linea) for linea in lineas) <= 80
