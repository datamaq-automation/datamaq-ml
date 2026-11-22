"""src/domain/cargas/banco_capacitores.py — Conmutaciones de banco de capacitores: cambios de Q sin cambio de P.

Un banco de capacitores en paralelo con los motores no consume potencia activa de forma apreciable. Cuando
cambia de escalón, el medidor ve ΔP ≈ 0 y ΔQ grande. Eso no es una carga industrial: se detecta, se cuenta y
se excluye de la atribución a máquinas. Además, si una conmutación ocurre cerca de un escalón de carga, la ΔQ de
ese escalón está contaminada, y el emparejamiento no debe usarla (ver el caso de uso de atribución).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from src.domain.cargas.entities import EventoCarga, Medicion

UMBRAL_P_BANCO_KW = 1.5  # |ΔP| por debajo de esto se considera ≈ 0
UMBRAL_Q_BANCO_KVAR = 10.0  # |ΔQ| por encima de esto es un escalón del banco
TOLERANCIA_COINCIDENCIA = timedelta(minutes=5)  # una muestra: "en la misma ventana"


@dataclass(frozen=True)
class ConmutacionBanco:
    """Cambio de reactiva sin cambio apreciable de potencia activa."""

    instante: datetime
    delta_kvar: float


def es_conmutacion(
    delta_kw: float, delta_kvar: float, umbral_p_kw: float, umbral_q_kvar: float
) -> bool:
    """¿El par de muestras es una conmutación de banco? |ΔP| bajo el umbral y |ΔQ| sobre el umbral."""
    return abs(delta_kw) < umbral_p_kw and abs(delta_kvar) >= umbral_q_kvar


def detectar_conmutaciones(
    mediciones: list[Medicion],
    umbral_p_kw: float = UMBRAL_P_BANCO_KW,
    umbral_q_kvar: float = UMBRAL_Q_BANCO_KVAR,
) -> list[ConmutacionBanco]:
    """Conmutaciones entre muestras consecutivas (ordenadas por instante). Sin reactiva, no hay nada que detectar."""
    ordenadas = sorted(
        (m for m in mediciones if m.reactiva_kvar is not None), key=lambda m: m.instante
    )
    conmutaciones: list[ConmutacionBanco] = []
    for previa, actual in zip(ordenadas, ordenadas[1:], strict=False):
        delta_p = actual.potencia_kw - previa.potencia_kw
        delta_q = (actual.reactiva_kvar or 0.0) - (previa.reactiva_kvar or 0.0)
        if es_conmutacion(delta_p, delta_q, umbral_p_kw, umbral_q_kvar):
            conmutaciones.append(ConmutacionBanco(instante=actual.instante, delta_kvar=delta_q))
    return conmutaciones


def es_evento_de_banco(evento: EventoCarga, umbral_p_kw: float, umbral_q_kvar: float) -> bool:
    """¿Un evento de carga es en realidad una conmutación de banco? (ΔP ≈ 0 y ΔQ grande)."""
    return es_conmutacion(evento.delta_kw, evento.delta_kvar, umbral_p_kw, umbral_q_kvar)


def coincide_con_banco(
    instante: datetime,
    conmutaciones: list[ConmutacionBanco],
    tolerancia: timedelta = TOLERANCIA_COINCIDENCIA,
) -> bool:
    """¿Hay una conmutación de banco dentro de la tolerancia de este instante?"""
    return any(abs(instante - c.instante) <= tolerancia for c in conmutaciones)
