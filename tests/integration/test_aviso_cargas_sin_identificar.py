"""tests/integration/test_aviso_cargas_sin_identificar.py — Verificación de aviso de saltos bajo el umbral (#31).

Verifica que train informe cuántos saltos y cuánta energía quedaron bajo el umbral,
que el campo persista en el JSON de entrenamiento, y que la advertencia solo aparezca
cuando efectivamente hay saltos sin analizar.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.application.cargas.dtos.identificar_cargas import IdentificarCargasRequest
from src.application.cargas.use_cases.identificar_cargas import IdentificarCargasUseCase
from src.domain.cargas.entities import Medicion
from src.domain.cargas.simulacion import simular_tablero
from src.infrastructure.cli import presentacion as p
from src.infrastructure.cli.entrenar_cargas import _resumen_entrenamiento
from src.infrastructure.cli.simular_tablero import CARGAS
from src.infrastructure.csv.carga_repository import CsvCargaRepository
from src.infrastructure.csv.medicion_repository import CsvMedicionRepository
from src.infrastructure.settings.logger import logger
from src.infrastructure.sklearn.dbscan_agrupador import DbscanAgrupador


@pytest.fixture
def entorno_sintetico(tmp_path: Path) -> tuple[Path, Path]:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    inicio = datetime(2026, 9, 1)
    mediciones, _ = simular_tablero(CARGAS, dias=7, ruido_kw=3.0, semilla=42, inicio=inicio)
    repo_mediciones = CsvMedicionRepository(input_dir)
    repo_mediciones.guardar("sintetico", mediciones)
    return input_dir, output_dir


def test_entrenamiento_con_saltos_sin_analizar_informa_en_resumen_y_json(
    entorno_sintetico: tuple[Path, Path],
) -> None:
    input_dir, output_dir = entorno_sintetico
    mediciones_repo = CsvMedicionRepository(input_dir)
    cargas_repo = CsvCargaRepository(output_dir)

    caso_de_uso = IdentificarCargasUseCase(
        mediciones=mediciones_repo,
        agrupador=DbscanAgrupador(),
        umbral_kw=None,  # Umbral automático (Otsu ~48.9 kW)
        logger=logger,
    )
    request = IdentificarCargasRequest(
        medidor="sintetico",
        desde=datetime(2000, 1, 1),
        hasta=datetime(2100, 1, 1),
    )
    respuesta = caso_de_uso.execute(request)

    # 1. Saltos y energía cuantificados
    assert respuesta.saltos_bajo_umbral.cantidad > 0
    assert respuesta.saltos_bajo_umbral.energia_kwh > 0.0

    # 2. Persistencia en entrenamiento_<medidor>.json
    resumen = _resumen_entrenamiento(respuesta)
    assert "saltos_bajo_umbral" in resumen
    assert resumen["saltos_bajo_umbral"]["cantidad"] == respuesta.saltos_bajo_umbral.cantidad
    assert resumen["saltos_bajo_umbral"]["energia_kwh"] == respuesta.saltos_bajo_umbral.energia_kwh

    cargas_repo.guardar_entrenamiento("sintetico", resumen)
    archivo_json = output_dir / "entrenamiento_sintetico.json"
    assert archivo_json.exists()
    datos_json = json.loads(archivo_json.read_text(encoding="utf-8"))
    assert datos_json["saltos_bajo_umbral"]["cantidad"] == respuesta.saltos_bajo_umbral.cantidad

    # 3. Presentación en terminal con advertencia y energía
    lineas = p.lineas_resumen_entrenamiento(respuesta, "sintetico")
    salida = "\n".join(lineas)
    assert "saltos quedaron bajo el umbral de" in salida
    assert "y no se analizaron" in salida
    assert "kWh estimados" in salida

    # 4. Siguiente paso sugiere --umbral más bajo
    paso = p.siguiente_paso_entrenamiento(respuesta, "sintetico")
    assert "probá con --umbral más bajo para ver cargas chicas" in paso
    assert "--umbral" in paso


def test_entrenamiento_sin_saltos_sin_analizar_no_muestra_advertencia(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input_limpio"
    input_dir.mkdir(parents=True)
    mediciones_repo = CsvMedicionRepository(input_dir)

    # Serie donde todos los saltos superan el umbral (umbral=10.0, saltos de 100 kW)
    inicio = datetime(2026, 9, 1, 0, 0)
    mediciones = [
        Medicion(instante=inicio, potencia_kw=100.0),
        Medicion(instante=inicio + timedelta(minutes=5), potencia_kw=200.0),
        Medicion(instante=inicio + timedelta(minutes=10), potencia_kw=100.0),
        Medicion(instante=inicio + timedelta(minutes=15), potencia_kw=200.0),
    ]
    mediciones_repo.guardar("sin_saltos", mediciones)

    caso_de_uso = IdentificarCargasUseCase(
        mediciones=mediciones_repo,
        agrupador=DbscanAgrupador(),
        umbral_kw=10.0,
        logger=logger,
    )
    request = IdentificarCargasRequest(
        medidor="sin_saltos",
        desde=datetime(2000, 1, 1),
        hasta=datetime(2100, 1, 1),
    )
    respuesta = caso_de_uso.execute(request)

    # No hay saltos desestimados
    assert respuesta.saltos_bajo_umbral.cantidad == 0
    assert respuesta.saltos_bajo_umbral.energia_kwh == 0.0

    # Resumen limpio sin advertencia
    lineas = p.lineas_resumen_entrenamiento(respuesta, "sin_saltos")
    salida = "\n".join(lineas)
    assert "quedaron bajo el umbral" not in salida

    # Siguiente paso no sugiere bajar umbral
    paso = p.siguiente_paso_entrenamiento(respuesta, "sin_saltos")
    assert "probá con --umbral más bajo" not in paso
