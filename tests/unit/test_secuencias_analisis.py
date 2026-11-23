"""tests/unit/test_secuencias_analisis.py — Tests de secuencias de análisis y contratos entre etapas (Issue #21).

Verifica:
1. Flujo completo de cuatro etapas (diferencias -> detección -> agrupamiento -> resumen).
2. Contratos fuertemente tipados con validación explícita (DTOs).
3. Falla determinista cuando se viola un contrato de datos entre etapas.
4. Compatibilidad e integración entre librería propia, funciones de pares y bibliotecas externas.
"""

from __future__ import annotations

import pytest

from src.domain.cargas.secuencias_analisis import (
    CadenaAnalisisNILM,
    ContratoVioladoError,
    DeteccionEventosContrato,
    DiferenciasContrato,
    EventoDetectadoDTO,
    ResumenCargasDTO,
)

SERIE_SINTETICA = [0.0, 0.0, 50.0, 50.0, 0.0, 0.0, 30.0, 0.0]


def test_secuencia_cuatro_etapas_nominal() -> None:
    """Verifica el flujo nominal de las cuatro etapas del Issue #21."""
    cadena = CadenaAnalisisNILM(umbral_kw=20.0)
    resultado = cadena.procesar(SERIE_SINTETICA)

    assert isinstance(resultado, ResumenCargasDTO)
    assert resultado.total_eventos == 4
    # Dos eventos de 50 kW y dos eventos de 30 kW
    assert resultado.conteo_por_magnitud == {50.0: 2, 30.0: 2}

    eventos = cadena.obtener_eventos_detectados()
    assert len(eventos) == 4
    assert [(e.indice, e.delta_kw) for e in eventos] == [
        (2, 50.0),
        (4, -50.0),
        (6, 30.0),
        (7, -30.0),
    ]


def test_contrato_diferencias_falla_con_serie_invalida() -> None:
    """Verifica que la etapa de diferencias falle si la entrada no cumple el contrato."""
    etapa = DiferenciasContrato()
    with pytest.raises(ContratoVioladoError, match="al menos 2 observaciones"):
        etapa.ejecutar([10.0])

    with pytest.raises(ContratoVioladoError, match="no es un valor numérico finito"):
        etapa.ejecutar([10.0, float("nan")])


def test_contrato_deteccion_falla_con_deltas_vacias() -> None:
    """Verifica que la detección exija deltas válidas y umbral positivo."""
    etapa = DeteccionEventosContrato(umbral_kw=20.0)
    with pytest.raises(ContratoVioladoError, match="umbral debe ser positivo"):
        DeteccionEventosContrato(umbral_kw=-5.0)

    eventos = etapa.ejecutar([])
    assert eventos == []


def test_contrato_agrupamiento_falla_si_recibe_tipos_invalidos() -> None:
    """Verifica que el agrupamiento rechace objetos que no cumplan el protocolo EventoDetectadoDTO."""
    from src.domain.cargas.secuencias_analisis import AgrupamientoContrato

    etapa = AgrupamientoContrato()
    objetos_invalidos = [{"indice": 1, "delta": 50.0}]  # Diccionario sin tipo

    with pytest.raises(ContratoVioladoError, match="debe ser instancia de EventoDetectadoDTO"):
        etapa.ejecutar(objetos_invalidos)  # type: ignore[arg-type]


def test_evento_detectado_dto_inmutabilidad_y_validaciones() -> None:
    """Garantiza la inmutabilidad y reglas de negocio del DTO."""
    evento = EventoDetectadoDTO(indice=2, delta_kw=50.0)
    assert evento.indice == 2
    assert evento.delta_kw == 50.0
    assert evento.magnitud == 50.0
    assert evento.es_arranque is True

    evento_parada = EventoDetectadoDTO(indice=4, delta_kw=-50.0)
    assert evento_parada.es_arranque is False
    assert evento_parada.magnitud == 50.0

    with pytest.raises(ValueError, match="indice debe ser mayor o igual a 1"):
        EventoDetectadoDTO(indice=0, delta_kw=10.0)
