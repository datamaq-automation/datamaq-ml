"""tests/unit/test_diagnostico_regimen.py — Los diagnósticos usan el umbral del entrenamiento y sobreviven a un catálogo vacío.

Datos sintéticos. Se arma una carpeta TRABAJO como la del procedimiento (mapa, días, entrenamiento, catálogo,
validación) y se corren los dos diagnósticos. Casos:
- catálogo vacío (régimen sin modos separables): el diagnóstico 1 no revienta y el 2 también corre;
- catálogo con una firma por dispersión y cortes reales: los conteos de eventos y de cortados del diagnóstico
  coinciden con la validación que escribe la CLI (antes no coincidían: usaban el mínimo del catálogo y la
  tolerancia cruda).
"""

import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from src.infrastructure.cli.desagregar_cargas import ventana_utc_del_dia

RAIZ = Path(__file__).resolve().parents[2]
DIAG_1 = RAIZ / "scripts" / "diagnostico_privado_1.sh"
DIAG_2 = RAIZ / "scripts" / "diagnostico_privado_2.sh"
ID = "11111111-1111-4111-8111-111111111111"
FECHAS = ["2026-09-20", "2026-09-21"]


def _potencias(desde: datetime) -> list[float]:
    """288 muestras de 5 min: base de 20 kW, una carga de 120 kW (sin firma) que se cruza con una de 90 kW (con firma)."""
    p = [20.0] * 288
    for inicio in (30, 110, 190):
        for i in range(inicio, inicio + 20):
            p[i] += 120.0  # 120 kW sin firma, encendida 20 muestras
        for i in range(inicio + 10, inicio + 30):
            p[i] += 90.0  # 90 kW con firma: arranca dentro de la de 120 y sobrevive a su apagado
        for i in range(inicio + 60, inicio + 70):
            p[i] += (
                60.0  # 60 kW sin firma: el umbral del entrenamiento (40 kW) la ve; el mínimo del catálogo, no
            )
        for i in range(inicio + 80, inicio + 90):
            p[i] += (
                75.0  # 75 kW: cae dentro de la tolerancia por dispersión de la firma, fuera de la cruda
            )
    return [round(x + 0.2 * ((i * 7) % 3 - 1), 2) for i, x in enumerate(p)]


def _escribir_dias(datos: Path) -> list[Path]:
    archivos = []
    for fecha in FECHAS:
        desde, _hasta = ventana_utc_del_dia(date.fromisoformat(fecha))
        ruta = datos / f"{ID}_{fecha}.csv"
        lineas = ["instante,potencia_kw,reactiva_kvar"]
        for i, p in enumerate(_potencias(desde)):
            lineas.append(f"{(desde + timedelta(minutes=5 * i)).isoformat()},{p},{0.6 * p:.2f}")
        ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        archivos.append(ruta)
    return archivos


def _armar(tmp_path: Path, catalogo: list[dict], sin_modos: bool) -> tuple[Path, Path]:
    datos = tmp_path / "datos"
    trabajo = tmp_path / "trabajo"
    datos.mkdir()
    for sub in ("clusters", "catalogos", "validacion", "entrada"):
        (trabajo / sub).mkdir(parents=True)
    _escribir_dias(datos)
    (trabajo / "mapa.txt").write_text(f"{ID} T1\n", encoding="utf-8")
    (trabajo / "utilizables.txt").write_text(
        "".join(f"{ID} {f} 288\n" for f in FECHAS), encoding="utf-8"
    )
    (trabajo / "validar_T1.txt").write_text(
        "".join(f"{ID} {f} 288\n" for f in FECHAS), encoding="utf-8"
    )
    concatenado = "instante,potencia_kw,reactiva_kvar\n"
    for f in FECHAS:
        cuerpo = (datos / f"{ID}_{f}.csv").read_text(encoding="utf-8").splitlines()[1:]
        concatenado += "\n".join(cuerpo) + "\n"
    (trabajo / "entrada" / "T1.csv").write_text(concatenado, encoding="utf-8")
    sidecar = {
        "umbral_kw": 40.0,
        "separacion": 0.7,
        "regimen": "sin_modos_separables" if sin_modos else "valle_claro",
        "sin_modos_separables": sin_modos,
        "eventos": 0,
        "radio_kw": None,
        "modos": [],
    }
    (trabajo / "clusters" / "entrenamiento_T1.json").write_text(
        json.dumps(sidecar), encoding="utf-8"
    )
    (trabajo / "catalogos" / "catalogo_T1.json").write_text(json.dumps(catalogo), encoding="utf-8")
    for f in FECHAS:
        subprocess.run(
            [
                sys.executable, "-m", "src.infrastructure.cli.validar_dia_real",
                "--archivo", str(datos / f"{ID}_{f}.csv"),
                "--firmas", str(trabajo / "catalogos" / "catalogo_T1.json"),
                "--fecha", f,
                "--salida-json", str(trabajo / "validacion" / f"T1_{f}.json"),
                "--entrenamiento", str(trabajo / "clusters" / "entrenamiento_T1.json"),
                "--tolerancia-por-dispersion", "--tolerancia-max-kw", "25",
            ],
            cwd=RAIZ, check=True, capture_output=True,
        )  # fmt: skip
    return datos, trabajo


def _correr(script: Path, datos: Path, trabajo: Path) -> subprocess.CompletedProcess[str]:
    entorno = {
        **os.environ,
        "DATOS": str(datos),
        "TRABAJO": str(trabajo),
        "REPO": str(RAIZ),
        "TOL_MAX": "25",
    }
    return subprocess.run(
        ["bash", str(script)], env=entorno, capture_output=True, text=True, check=False
    )


def _valor(texto: str, prefijo: str, patron: str) -> str:
    import re

    for linea in texto.splitlines():
        if linea.strip().startswith(prefijo):
            m = re.search(patron, linea)
            if m:
                return m.group(1)
    raise AssertionError(f"no está la línea {prefijo!r}")


def test_catalogo_vacio_no_revienta_el_diagnostico_1_ni_el_2(tmp_path: Path) -> None:
    datos, trabajo = _armar(tmp_path, catalogo=[], sin_modos=True)
    for script in (DIAG_1, DIAG_2):
        resultado = _correr(script, datos, trabajo)
        assert resultado.returncode == 0, resultado.stderr[-600:]
        assert "Traceback" not in resultado.stderr
        assert "Listo" in resultado.stdout


def test_los_eventos_y_cortados_del_diagnostico_1_coinciden_con_la_validacion(
    tmp_path: Path,
) -> None:
    firma = {
        "machine_id": "m1",
        "nombre": "Carga 90",
        "potencia_nominal_kw": 91.4,
        "reactiva_tipica_kvar": 0.0,
        "tolerancia_kw": 5.0,
        "umbral_marcha_kw": 1.0,
        "dispersion_kw": 9.5,
    }
    datos, trabajo = _armar(tmp_path, catalogo=[firma], sin_modos=False)
    resultado = _correr(DIAG_1, datos, trabajo)
    assert resultado.returncode == 0, resultado.stderr[-600:]
    salida = resultado.stdout
    eventos = _valor(salida, "[5b] Eventos en días de validación", r": (\d+) \(validación JSON")
    eventos_json = _valor(salida, "[5b] Eventos en días de validación", r"JSON: (\d+)\)")
    assert eventos == eventos_json
    linea_cortados = next(linea for linea in salida.splitlines() if linea.startswith("[6]"))
    assert "coincide: sí" in linea_cortados
