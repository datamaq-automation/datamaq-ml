"""tests/unit/test_practica_supervisado.py — La práctica de arranques etiquetados corre y aprende (datos sintéticos)."""

import importlib.util
from pathlib import Path

RUTA = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "material-ensenanza"
    / "practicas"
    / "practica_supervisado_arranques.py"
)


def _practica():
    spec = importlib.util.spec_from_file_location("practica_supervisado_arranques", RUTA)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_los_arranques_tienen_su_carga_verdadera_como_etiqueta() -> None:
    practica = _practica()
    datos = practica.ejemplos(dias=7)
    assert datos, "debería haber arranques en una semana sintética"
    etiquetas = {etiqueta for _, etiqueta in datos}
    assert etiquetas <= {"90 kW", "40 kW", "15 kW"}


def test_los_tres_metodos_aprenden_sobre_la_parte_reciente() -> None:
    practica = _practica()
    resultados = practica.evaluar(practica.ejemplos(dias=14))
    assert set(resultados) == {"k-NN (k=5)", "Bayes gaussiano", "árbol de decisión"}
    assert all(exactitud >= 0.7 for exactitud in resultados.values())
