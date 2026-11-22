"""tests/unit/test_presentacion_explica.py — Narración (--explica) e histograma en texto (--grafico) (#29)."""

from __future__ import annotations

import pytest

from src.application.cargas.dtos.identificar_cargas import (
    AgrupamientoResponse,
    BarraHistogramaResponse,
    CargaResponse,
    IdentificarCargasResponse,
    UmbralResponse,
)
from src.infrastructure.cli import presentacion as p


@pytest.fixture(autouse=True)
def terminal_fija(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "80")


def _barras() -> list[BarraHistogramaResponse]:
    cantidades = [(0, 5, 100), (5, 10, 40), (10, 15, 10), (45, 50, 4), (50, 55, 2)]
    return [BarraHistogramaResponse(desde_kw=a, hasta_kw=b, cantidad=c) for a, b, c in cantidades]


def _respuesta(kw: float | None = 48.9, sin_grupo: int = 8) -> IdentificarCargasResponse:
    return IdentificarCargasResponse(
        medidor="sintetico",
        mediciones=4032,
        eventos=496,
        eventos_sin_grupo=sin_grupo,
        potencia_media_kw=160.0,
        cargas=[
            CargaResponse(
                potencia_tipica_kw=89.5,
                encendidos=245,
                apagados=243,
                ciclos=243,
                on_off=False,
                dispersion_kw=4.1,
            )
        ],
        umbral=UmbralResponse(kw=kw, automatico=True, separacion=0.9, confiable=True),
        agrupamiento=AgrupamientoResponse(
            radio_kw=8.2, radio_automatico=True, min_eventos=14, min_eventos_automatico=True
        ),
        dias=14.0,
        histograma=_barras(),
    )


def test_histograma_marca_el_tramo_del_corte_y_cuenta_lo_que_queda_bajo_el() -> None:
    lineas = p.lineas_histograma(_barras(), 48.9, unicode=True)
    marcada = [linea for linea in lineas if "← corte" in linea]
    assert len(marcada) == 1 and "45–50 kW" in marcada[0]
    # Tramos que terminan antes del corte (48,9 kW): 100 + 40 + 10 = 150. El de 45–50 lo contiene.
    assert lineas[-1] == "150 saltos quedan bajo el corte y no cuentan como eventos."


def test_histograma_sin_unicode_usa_numeral_y_menor_que() -> None:
    lineas = p.lineas_histograma(_barras(), 48.9, unicode=False)
    assert "#" in lineas[1] and "█" not in "\n".join(lineas)
    assert any("<" in linea for linea in lineas)


def test_histograma_sin_saltos_avisa_en_vez_de_dibujar() -> None:
    assert p.lineas_histograma([], 10.0) == ["No hay saltos para graficar."]


def test_la_barra_mas_larga_ocupa_el_ancho_del_gráfico() -> None:
    lineas = p.lineas_histograma(_barras(), None, unicode=True)
    barras = [linea.split("│")[1].split(" ")[0] for linea in lineas[1:6]]
    assert len(barras[0]) == 40 and len(barras[0]) > len(barras[1]) > len(barras[2])


def test_explicacion_narra_cuatro_pasos_con_sus_valores() -> None:
    texto = "\n".join(p.lineas_explicacion(_respuesta()))
    for paso in ("Paso 1 ·", "Paso 2 ·", "Paso 3 ·", "Paso 4 ·"):
        assert paso in texto
    assert "η = 0,90, confiable" in texto
    assert "Quedan 8 eventos sin grupo" in texto
    assert "1 carga." in texto
    assert "\x1b[" not in texto


def test_explicacion_no_modifica_el_resultado() -> None:
    r = _respuesta()
    antes = r.model_dump()
    p.lineas_explicacion(r)
    p.lineas_histograma(r.histograma, r.umbral.kw)
    assert r.model_dump() == antes


def test_siguiente_paso_apunta_al_grafico_cuando_hay_aviso() -> None:
    assert p.siguiente_paso_entrenamiento(_respuesta(), "sintetico") == (
        "./run.sh train sintetico --grafico   (ver dónde caen los saltos)"
    )
