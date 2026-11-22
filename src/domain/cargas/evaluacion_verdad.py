"""src/domain/cargas/evaluacion_verdad.py — Compara intervalos inferidos contra la verdad de terreno, por máquina.

Dos vistas, porque cuentan cosas distintas:
- por tiempo: minutos en marcha que coinciden (precisión y sensibilidad sobre minutos);
- por eventos: arranques y paradas emparejados uno a uno si caen a ±tolerancia (300 s por defecto, un
  medidor cada 300 s; configurable). Un arranque inferido sin verdad cerca es una falsa alarma; una
  parada verdadera sin inferencia cerca es un evento perdido.

Convención sin denominador: si no hay minutos o eventos inferidos, la precisión vale 1 (no hubo
afirmaciones falsas); si no hay verdad, la sensibilidad vale 1 (nada que encontrar). El error de
energía solo se calcula si la verdad trae energía y es mayor que cero.
"""

from dataclasses import dataclass
from datetime import datetime

TOLERANCIA_EVENTO_S = (
    300.0  # un medidor cada 300 s: un evento real puede caer hasta un ciclo de distancia
)


@dataclass(frozen=True)
class Tramo:
    """Intervalo de marcha [inicio, fin)."""

    inicio: datetime
    fin: datetime

    @property
    def minutos(self) -> float:
        return (self.fin - self.inicio).total_seconds() / 60.0


@dataclass(frozen=True)
class MetricasTiempo:
    inferido_min: float
    verdadero_min: float
    coincidente_min: float
    precision: float
    sensibilidad: float


@dataclass(frozen=True)
class MetricasEventos:
    verdaderos: int
    inferidos: int
    emparejados: int
    precision: float
    sensibilidad: float


@dataclass(frozen=True)
class ResultadoMaquina:
    maquina: str
    tiempo: MetricasTiempo
    arranques: MetricasEventos
    paradas: MetricasEventos
    energia_inferida_kwh: float
    energia_verdadera_kwh: float | None
    error_energia_pct: float | None


def unir(tramos: list[Tramo]) -> list[Tramo]:
    """Ordena y funde los tramos que se solapan o se tocan: la marcha es un conjunto de minutos."""
    fundidos: list[Tramo] = []
    for tramo in sorted(tramos, key=lambda t: t.inicio):
        if fundidos and tramo.inicio <= fundidos[-1].fin:
            previo = fundidos[-1]
            fundidos[-1] = Tramo(previo.inicio, max(previo.fin, tramo.fin))
        else:
            fundidos.append(tramo)
    return fundidos


def _minutos_coincidentes(a: list[Tramo], b: list[Tramo]) -> float:
    """Minutos en que ambas listas (ya fundidas) están en marcha a la vez."""
    total = 0.0
    i = j = 0
    while i < len(a) and j < len(b):
        inicio = max(a[i].inicio, b[j].inicio)
        fin = min(a[i].fin, b[j].fin)
        if fin > inicio:
            total += (fin - inicio).total_seconds() / 60.0
        if a[i].fin < b[j].fin:
            i += 1
        else:
            j += 1
    return total


def _cociente(numerador: float, denominador: float) -> float:
    return numerador / denominador if denominador > 0 else 1.0


def metricas_tiempo(inferidos: list[Tramo], verdaderos: list[Tramo]) -> MetricasTiempo:
    a, b = unir(inferidos), unir(verdaderos)
    inferido = sum(t.minutos for t in a)
    verdadero = sum(t.minutos for t in b)
    coincidente = _minutos_coincidentes(a, b)
    return MetricasTiempo(
        inferido_min=round(inferido, 3),
        verdadero_min=round(verdadero, 3),
        coincidente_min=round(coincidente, 3),
        precision=round(_cociente(coincidente, inferido), 4),
        sensibilidad=round(_cociente(coincidente, verdadero), 4),
    )


def emparejar(verdaderos: list[datetime], inferidos: list[datetime], tolerancia_s: float) -> int:
    """Cantidad de pares uno a uno: cada verdad se empareja con el inferido más cercano sin usar,
    si está a no más de `tolerancia_s`. Las verdades se toman en orden cronológico."""
    libres = sorted(inferidos)
    emparejados = 0
    for real in sorted(verdaderos):
        mejor = None
        mejor_dist = tolerancia_s
        for k, inferido in enumerate(libres):
            dist = abs((inferido - real).total_seconds())
            if dist <= mejor_dist:
                mejor, mejor_dist = k, dist
        if mejor is not None:
            libres.pop(mejor)
            emparejados += 1
    return emparejados


def metricas_eventos(
    inferidos: list[datetime], verdaderos: list[datetime], tolerancia_s: float
) -> MetricasEventos:
    emparejados = emparejar(verdaderos, inferidos, tolerancia_s)
    return MetricasEventos(
        verdaderos=len(verdaderos),
        inferidos=len(inferidos),
        emparejados=emparejados,
        precision=round(_cociente(emparejados, len(inferidos)), 4),
        sensibilidad=round(_cociente(emparejados, len(verdaderos)), 4),
    )


def evaluar_maquina(
    maquina: str,
    inferidos: list[Tramo],
    verdaderos: list[Tramo],
    tolerancia_s: float = TOLERANCIA_EVENTO_S,
    energia_inferida_kwh: float = 0.0,
    energia_verdadera_kwh: float | None = None,
) -> ResultadoMaquina:
    error = None
    if energia_verdadera_kwh is not None and energia_verdadera_kwh > 0:
        error = round(
            100.0 * (energia_inferida_kwh - energia_verdadera_kwh) / energia_verdadera_kwh, 2
        )
    return ResultadoMaquina(
        maquina=maquina,
        tiempo=metricas_tiempo(inferidos, verdaderos),
        arranques=metricas_eventos(
            [t.inicio for t in inferidos], [t.inicio for t in verdaderos], tolerancia_s
        ),
        paradas=metricas_eventos(
            [t.fin for t in inferidos], [t.fin for t in verdaderos], tolerancia_s
        ),
        energia_inferida_kwh=round(energia_inferida_kwh, 3),
        energia_verdadera_kwh=energia_verdadera_kwh,
        error_energia_pct=error,
    )


def evaluar(
    inferidos: dict[str, list[Tramo]],
    verdaderos: dict[str, list[Tramo]],
    tolerancia_s: float = TOLERANCIA_EVENTO_S,
    energias_inferidas: dict[str, float] | None = None,
    energias_verdaderas: dict[str, float | None] | None = None,
) -> list[ResultadoMaquina]:
    """Evalúa cada máquina que aparece en cualquiera de las dos listas, en orden de nombre.

    Una máquina solo inferida tiene sensibilidad 1 (no hay nada que perder) y precisión 0 si tiene minutos.
    Una máquina solo en la verdad tiene sensibilidad 0 si hubo marcha.
    """
    energias_inf = energias_inferidas or {}
    energias_ver = energias_verdaderas or {}
    resultados = []
    for maquina in sorted(set(inferidos) | set(verdaderos)):
        resultados.append(
            evaluar_maquina(
                maquina,
                inferidos.get(maquina, []),
                verdaderos.get(maquina, []),
                tolerancia_s,
                energias_inf.get(maquina, 0.0),
                energias_ver.get(maquina),
            )
        )
    return resultados
