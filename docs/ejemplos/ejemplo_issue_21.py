"""Issue #21 (secuencias de análisis con contratos entre etapas). Serie sintética, kW.

Cuatro etapas: diferencias → detección de eventos → agrupamiento por magnitud → resumen.
Cada etapa recibe y devuelve un tipo explícito; si el tipo no coincide, la cadena no corre.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_21.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.domain.cargas.secuencias_analisis import (  # noqa: E402
    CadenaAnalisisNILM,
    ContratoVioladoError,
    EventoDetectadoDTO,
)

SERIE = [0, 0, 50, 50, 0, 0, 30, 0]  # kW por minuto, sintética
UMBRAL_KW = 20


def diferencias(serie: list[float]) -> list[float]:
    cadena = CadenaAnalisisNILM(umbral_kw=UMBRAL_KW)
    return cadena.etapa1.ejecutar(serie)


def detectar(deltas: list[float], umbral: float) -> list[EventoDetectadoDTO]:
    cadena = CadenaAnalisisNILM(umbral_kw=umbral)
    return cadena.etapa2.ejecutar(deltas)


def agrupar(eventos: list[EventoDetectadoDTO]) -> dict[float, list[EventoDetectadoDTO]]:
    cadena = CadenaAnalisisNILM(umbral_kw=UMBRAL_KW)
    return cadena.etapa3.ejecutar(eventos)


def resumir(grupos: dict[float, list[EventoDetectadoDTO]]) -> dict[float, int]:
    cadena = CadenaAnalisisNILM(umbral_kw=UMBRAL_KW)
    res = cadena.etapa4.ejecutar(grupos)
    return res.conteo_por_magnitud


if __name__ == "__main__":
    cadena = CadenaAnalisisNILM(umbral_kw=UMBRAL_KW)
    resumen = cadena.procesar(SERIE)
    eventos = cadena.obtener_eventos_detectados()

    print("eventos:", [(e.indice, e.delta_kw) for e in eventos])
    print("grupos por magnitud (kW → cantidad):", resumen.conteo_por_magnitud)
    assert [(e.indice, e.delta_kw) for e in eventos] == [(2, 50), (4, -50), (6, 30), (7, -30)]
    assert resumen.conteo_por_magnitud == {50: 2, 30: 2}
    print("dos clases de carga: una de 50 kW (2 arranques y 2 paradas) y otra de 30 kW")

    # Demostración de robustez del contrato: rechazo inmediato si se pasa tipo inválido
    try:
        cadena.etapa3.ejecutar([{"indice": 2, "delta": 50}])  # type: ignore[list-item]
    except ContratoVioladoError:
        print("✓ Contrato verificado: agrupar() rechazó exitosamente diccionarios sin tipo.")
