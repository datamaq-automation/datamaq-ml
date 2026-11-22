"""src/domain/cargas/catalogo_placa.py — Firma esperada de cada motor según su placa y su forma de arranque.

La placa da la potencia nominal y el cos φ típico. De ahí salen la reactiva esperada (Q = P · tan φ) y la
relación ΔQ/ΔP que se espera ver en el medidor. La forma de arranque cambia qué escalón ve el motor:

- directo: un escalón de P al arrancar (el caso fácil).
- estrella-triángulo: arranca en estrella con P/3 y, al pasar a triángulo, sube a P: dos escalones, no uno.
  Un par de arranque y parada de P no se ve como un escalón de P entero.
- variador: el arranque es una rampa de frecuencia, sin escalón único. No es detectable como escalón.
- arranque suave: rampa de tensión, igual que el variador en la práctica: no hay escalón único.

El cos φ típico de un motor de inducción a plena carga ronda 0,85; es un valor de referencia, no un dato
de la placa. Se puede cambiar por motor en el catálogo.
"""

import math
from dataclasses import dataclass

FORMAS_ARRANQUE = ("directo", "estrella_triangulo", "variador", "arranque_suave")
COS_PHI_TIPICO = 0.85
TOLERANCIA_POTENCIA_KW = 5.0  # mismo orden que la tolerancia de una firma confirmada
TOLERANCIA_RATIO = 0.15  # |ΔQ/ΔP| medido contra el esperado


@dataclass(frozen=True)
class PlacaMotor:
    etiqueta: str
    potencia_nominal_kw: float
    trafo: str
    tipo_proceso: str
    forma_arranque: str
    cos_phi: float = COS_PHI_TIPICO


@dataclass(frozen=True)
class FirmaEsperada:
    etiqueta: str
    potencia_nominal_kw: float
    reactiva_esperada_kvar: float
    ratio_qp_esperado: float
    pasos_kw: tuple[float, ...]
    detectable_como_escalon: bool
    nota: str


@dataclass(frozen=True)
class ModoObservado:
    """Un modo que descubrió train: centro de |ΔP| y relación ΔQ/ΔP mediana (None sin reactiva)."""

    centro_kw: float
    ratio_qp: float | None


@dataclass(frozen=True)
class Comparacion:
    etiqueta: str
    estado: str  # coincide | coincide_forma_distinta | sin_modo | sin_escalon
    modo_kw: float | None
    ratio_observado: float | None
    ratio_esperado: float


def ratio_qp(cos_phi: float) -> float:
    """Q/P de un motor con ese cos φ: tan(arccos(cos φ))."""
    return math.tan(math.acos(cos_phi))


def firma_esperada(placa: PlacaMotor) -> FirmaEsperada:
    if placa.forma_arranque not in FORMAS_ARRANQUE:
        raise ValueError(f"forma de arranque desconocida: {placa.forma_arranque}")
    p = placa.potencia_nominal_kw
    ratio = ratio_qp(placa.cos_phi)
    pasos, detectable, nota = _pasos_por_forma(p, placa.forma_arranque)
    return FirmaEsperada(
        etiqueta=placa.etiqueta,
        potencia_nominal_kw=p,
        reactiva_esperada_kvar=round(ratio * p, 2),
        ratio_qp_esperado=round(ratio, 3),
        pasos_kw=pasos,
        detectable_como_escalon=detectable,
        nota=nota,
    )


def _pasos_por_forma(p: float, forma: str) -> tuple[tuple[float, ...], bool, str]:
    if forma == "directo":
        return (p,), True, "escalón único de potencia nominal"
    if forma == "estrella_triangulo":
        return (
            (round(p / 3, 2), round(2 * p / 3, 2)),
            True,
            "dos escalones: P/3 en estrella y 2P/3 al pasar a triángulo",
        )
    return (), False, "rampa sin escalón único: no es emparejable como firma de escalón"


def comparar_con_modos(
    firmas: list[FirmaEsperada],
    modos: list[ModoObservado],
    tolerancia_kw: float = TOLERANCIA_POTENCIA_KW,
    tolerancia_ratio: float = TOLERANCIA_RATIO,
) -> list[Comparacion]:
    """Para cada motor: si algún modo de train cae en uno de sus escalones, y si la forma de la reactiva coincide."""
    return [_comparar_una(f, modos, tolerancia_kw, tolerancia_ratio) for f in firmas]


def _comparar_una(
    firma: FirmaEsperada,
    modos: list[ModoObservado],
    tolerancia_kw: float,
    tolerancia_ratio: float,
) -> Comparacion:
    if not firma.detectable_como_escalon:
        return Comparacion(firma.etiqueta, "sin_escalon", None, None, firma.ratio_qp_esperado)
    mejor: ModoObservado | None = None
    mejor_dist = tolerancia_kw
    for modo in modos:
        for paso in firma.pasos_kw:
            dist = abs(modo.centro_kw - paso)
            if dist <= mejor_dist:
                mejor, mejor_dist = modo, dist
    if mejor is None:
        return Comparacion(firma.etiqueta, "sin_modo", None, None, firma.ratio_qp_esperado)
    forma_ok = (
        mejor.ratio_qp is None or abs(mejor.ratio_qp - firma.ratio_qp_esperado) <= tolerancia_ratio
    )
    estado = "coincide" if forma_ok else "coincide_forma_distinta"
    return Comparacion(
        firma.etiqueta, estado, mejor.centro_kw, mejor.ratio_qp, firma.ratio_qp_esperado
    )
