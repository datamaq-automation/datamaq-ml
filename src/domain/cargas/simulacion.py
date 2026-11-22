"""src/domain/cargas/simulacion.py — Tablero simulado con cargas conocidas, para evaluar el algoritmo."""

import math
import random
from datetime import datetime, timedelta

from src.domain.cargas.entities import CargaSimulada, EventoReal, Medicion

PASO_MIN = 5
MUESTRAS_POR_DIA = 24 * 60 // PASO_MIN


def simular_tablero(
    cargas: list[CargaSimulada],
    dias: int,
    ruido_kw: float,
    semilla: int,
    inicio: datetime,
    base_kw: float = 120.0,
    variacion_diaria_kw: float = 20.0,
) -> tuple[list[Medicion], list[EventoReal]]:
    """Suma una base que sube y baja en el día, ruido y cada carga prendiéndose y apagándose.

    Devuelve las mediciones (lo que vería un medidor cada 5 minutos) y los eventos reales (la verdad).
    Con la misma semilla, el resultado es siempre el mismo.
    """
    azar = random.Random(semilla)
    n = dias * MUESTRAS_POR_DIA
    encendida = [_encendidos(c, n, azar) for c in cargas]
    mediciones: list[Medicion] = []
    verdad: list[EventoReal] = []
    for i in range(n):
        instante = inicio + timedelta(minutes=PASO_MIN * i)
        base = base_kw + variacion_diaria_kw * math.sin(2 * math.pi * i / MUESTRAS_POR_DIA)
        potencia = (
            base
            + azar.gauss(0, ruido_kw)
            + sum(c.potencia_kw for c, on in zip(cargas, encendida, strict=True) if on[i])
        )
        mediciones.append(Medicion(instante=instante, potencia_kw=round(potencia, 2)))
        for carga, on in zip(cargas, encendida, strict=True):
            if i and on[i] != on[i - 1]:
                signo = 1 if on[i] else -1
                verdad.append(
                    EventoReal(
                        instante=instante,
                        delta_kw=signo * carga.potencia_kw,
                        carga_kw=carga.potencia_kw,
                    )
                )
    return mediciones, verdad


def _encendidos(carga: CargaSimulada, n: int, azar: random.Random) -> list[bool]:
    """Para cada muestra, si la carga está prendida: tiempos entre arranques y duraciones al azar."""
    on = [False] * n
    i = azar.randrange(0, MUESTRAS_POR_DIA // 4)
    while i < n:
        duracion = max(
            1, round(azar.gauss(carga.duracion_min, carga.duracion_min * 0.2) / PASO_MIN)
        )
        for j in range(i, min(n, i + duracion)):
            on[j] = True
        # Tiempo entre arranques con media "un día / ciclos_por_dia"; la espera es lo que sobra
        # después de la duración, así la frecuencia real coincide con la pedida.
        entre_arranques = azar.expovariate(carga.ciclos_por_dia / MUESTRAS_POR_DIA)
        i += max(duracion + 1, round(entre_arranques))
    return on


BANCO_FIJO = "fijo"
BANCO_AUTOMATICO = "automatico"


def simular_tablero_con_reactiva(
    cargas: list[CargaSimulada],
    dias: int,
    ruido_kw: float,
    ruido_kvar: float,
    semilla: int,
    inicio: datetime,
    banco: str,
    factor_reactiva: float = 1.2,
    q_base_kvar: float = 40.0,
    q_banco_kvar: float = 20.0,
    escalon_banco_kvar: float = 10.0,
    conmutaciones_por_dia: int = 4,
    base_kw: float = 120.0,
) -> tuple[list[Medicion], list[EventoReal]]:
    """Tablero con potencia activa y reactiva neta: motores en paralelo con un banco de capacitores.

    Q medida = Q base + Σ (motores encendidos × factor_reactiva × P) − Q banco + ruido.
    - banco "fijo": Q banco constante (un desplazamiento de nivel). Los arranques y paradas de motor dejan ΔQ limpia.
    - banco "automatico": el banco cambia de escalón en instantes al azar (ΔP ≈ 0, ΔQ grande).
    La verdad (eventos de carga) no incluye las conmutaciones del banco: no son cargas.
    """
    if banco not in (BANCO_FIJO, BANCO_AUTOMATICO):
        raise ValueError(f"Tipo de banco desconocido: {banco}")
    azar = random.Random(semilla)
    n = dias * MUESTRAS_POR_DIA
    encendida = [_encendidos(c, n, azar) for c in cargas]
    estado_banco = _estado_banco(
        banco, n, dias, conmutaciones_por_dia, escalon_banco_kvar, azar, q_banco_kvar
    )
    mediciones: list[Medicion] = []
    verdad: list[EventoReal] = []
    for i in range(n):
        instante = inicio + timedelta(minutes=PASO_MIN * i)
        base = base_kw + 20.0 * math.sin(2 * math.pi * i / MUESTRAS_POR_DIA)
        activa = sum(c.potencia_kw for c, on in zip(cargas, encendida, strict=True) if on[i])
        potencia = base + azar.gauss(0, ruido_kw) + activa
        reactiva = (
            q_base_kvar + factor_reactiva * activa - estado_banco[i] + azar.gauss(0, ruido_kvar)
        )
        mediciones.append(
            Medicion(
                instante=instante,
                potencia_kw=round(potencia, 2),
                reactiva_kvar=round(reactiva, 2),
            )
        )
        for carga, on in zip(cargas, encendida, strict=True):
            if i and on[i] != on[i - 1]:
                signo = 1 if on[i] else -1
                verdad.append(
                    EventoReal(
                        instante=instante,
                        delta_kw=signo * carga.potencia_kw,
                        carga_kw=carga.potencia_kw,
                    )
                )
    return mediciones, verdad


def _estado_banco(
    banco: str,
    n: int,
    dias: int,
    conmutaciones_por_dia: int,
    escalon_kvar: float,
    azar: random.Random,
    q_fijo_kvar: float,
) -> list[float]:
    """Q que aporta el banco en cada muestra: constante (fijo) o con escalones que cambian (automático)."""
    if banco == BANCO_FIJO:
        return [q_fijo_kvar] * n
    cambios = sorted(azar.sample(range(1, n), min(n - 1, dias * conmutaciones_por_dia)))
    estado: list[float] = []
    nivel = escalon_kvar
    indices = set(cambios)
    for i in range(n):
        if i in indices:
            nuevo = escalon_kvar * azar.choice([0, 1, 2, 3])
            while nuevo == nivel:
                nuevo = escalon_kvar * azar.choice([0, 1, 2, 3])
            nivel = nuevo
        estado.append(nivel)
    return estado
