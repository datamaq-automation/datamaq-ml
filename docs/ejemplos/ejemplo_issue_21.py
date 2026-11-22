"""Issue #21 (secuencias de análisis con contratos entre etapas). Serie sintética, kW.

Cuatro etapas: diferencias → detección de eventos → agrupamiento por magnitud → resumen.
Cada etapa recibe y devuelve un tipo explícito; si el tipo no coincide, la cadena no corre.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_21.py
"""

from dataclasses import dataclass

SERIE = [0, 0, 50, 50, 0, 0, 30, 0]  # kW por minuto, sintética
UMBRAL_KW = 20


@dataclass(frozen=True)
class Evento:
    indice: int
    delta_kw: float


def diferencias(serie: list[float]) -> list[float]:
    return [b - a for a, b in zip(serie, serie[1:], strict=False)]


def detectar(deltas: list[float], umbral: float) -> list[Evento]:
    return [Evento(i + 1, d) for i, d in enumerate(deltas) if abs(d) >= umbral]


def agrupar(eventos: list[Evento]) -> dict[float, list[Evento]]:
    grupos: dict[float, list[Evento]] = {}
    for e in eventos:
        grupos.setdefault(abs(e.delta_kw), []).append(e)
    return grupos


def resumir(grupos: dict[float, list[Evento]]) -> dict[float, int]:
    return {magnitud: len(evs) for magnitud, evs in sorted(grupos.items(), reverse=True)}


if __name__ == "__main__":
    deltas = diferencias(SERIE)
    eventos = detectar(deltas, UMBRAL_KW)
    grupos = agrupar(eventos)
    resumen = resumir(grupos)
    print("eventos:", [(e.indice, e.delta_kw) for e in eventos])
    print("grupos por magnitud (kW → cantidad):", resumen)
    assert [(e.indice, e.delta_kw) for e in eventos] == [(2, 50), (4, -50), (6, 30), (7, -30)]
    assert resumen == {50: 2, 30: 2}
    print("dos clases de carga: una de 50 kW (2 arranques y 2 paradas) y otra de 30 kW")
