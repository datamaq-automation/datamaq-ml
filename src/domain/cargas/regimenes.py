"""src/domain/cargas/regimenes.py — Régimen de los saltos |ΔP|: modos separables por valle o continuo sin valle.

Cuando η de Otsu es menor que 0,8 (ver EstimacionUmbral), el corte de Otsu no separa nada útil. Entonces
se busca el valle del histograma suavizado de |ΔP|:
- si el valle es claro (poca altura frente al modo siguiente), cada modo de eventos es una carga candidata,
  con su propia dispersión y su propio radio (2σ dentro de ±3σ del centro);
- si no hay valle, el régimen es «sin modos separables»: no se inventan clústeres.
"""

from dataclasses import dataclass
from statistics import median, pstdev

ANCHO_BIN_KW = 1.0  # resolución del histograma de |ΔP|
VENTANA_SUAVIZADO = 5  # bins de promedio móvil centrado
FRACCION_CERO_RUIDO = (
    0.01  # la cola del ruido termina cuando el histograma queda bajo el 1 % del pico
)
PROFUNDIDAD_VALLE_CLARO = 0.2  # el valle debe ser menor que el 20 % de la altura del modo siguiente
MIN_SALTOS_PARA_VALLE = 30  # con menos saltos no hay histograma que valga la pena
MIN_SALTOS_POR_MODO = 20  # un modo con menos saltos es ruido de la cola, no una carga
FRACCION_PICO_MODO = (
    0.1  # un modo nuevo arranca en un pico al menos del 10 % del más alto (sobre el valle)
)
PROFUNDIDAD_MODOS_SEPARADOS = (
    0.5  # dos picos vecinos son modos distintos si el valle entre ellos baja de la mitad
)
FACTOR_SIGMA_MODO = 3.0  # la dispersión del modo se mide dentro de ±3σ del centro


@dataclass(frozen=True)
class Modo:
    """Un modo de eventos: saltos con |ΔP| en [desde_kw, hasta_kw)."""

    desde_kw: float
    hasta_kw: float
    cantidad: int
    centro_kw: float
    dispersion_kw: float
    radio_kw: float


@dataclass(frozen=True)
class RegimenSaltos:
    """Resultado del análisis de valle: umbral de detección, profundidad del valle y modos separables."""

    umbral_kw: float | None
    profundidad_valle: float | None
    hay_modos: bool
    modos: list[Modo]


SIN_REGIMEN = RegimenSaltos(umbral_kw=None, profundidad_valle=None, hay_modos=False, modos=[])


def hallar_regimen(magnitudes_kw: list[float]) -> RegimenSaltos:
    """Analiza |ΔP| (en kW, ya sin signo) y devuelve el umbral del valle, la profundidad y los modos."""
    if len(magnitudes_kw) < MIN_SALTOS_PARA_VALLE:
        return SIN_REGIMEN
    suavizado = _suavizar(_contar(magnitudes_kw), VENTANA_SUAVIZADO)
    pico_ruido = max(range(len(suavizado)), key=lambda i: suavizado[i])
    valle = _centro_del_valle(suavizado, pico_ruido)
    if valle is None:
        return SIN_REGIMEN
    umbral = (valle + 0.5) * ANCHO_BIN_KW
    sobre_valle = range(valle + 1, len(suavizado))
    if not sobre_valle or max(suavizado[i] for i in sobre_valle) == 0:
        return RegimenSaltos(umbral_kw=umbral, profundidad_valle=None, hay_modos=False, modos=[])
    pico_siguiente = max(sobre_valle, key=lambda i: suavizado[i])
    profundidad = suavizado[valle] / suavizado[pico_siguiente]
    if profundidad > PROFUNDIDAD_VALLE_CLARO:
        return RegimenSaltos(
            umbral_kw=umbral, profundidad_valle=profundidad, hay_modos=False, modos=[]
        )
    modos = _modos_sobre_valle(magnitudes_kw, suavizado, valle)
    return RegimenSaltos(
        umbral_kw=umbral, profundidad_valle=profundidad, hay_modos=bool(modos), modos=modos
    )


def etiquetar_por_modos(magnitudes_kw: list[float], modos: list[Modo]) -> list[int]:
    """Índice del modo al que cae cada |ΔP|, o -1 si no cae en ninguno."""
    etiquetas = []
    for m in magnitudes_kw:
        indice = -1
        for k, modo in enumerate(modos):
            if modo.desde_kw <= m < modo.hasta_kw:
                indice = k
                break
        etiquetas.append(indice)
    return etiquetas


def _contar(magnitudes_kw: list[float]) -> list[int]:
    alto = int(max(magnitudes_kw) // ANCHO_BIN_KW) + 1
    cuentas = [0] * alto
    for m in magnitudes_kw:
        cuentas[int(m // ANCHO_BIN_KW)] += 1
    return cuentas


def _suavizar(cuentas: list[int], ventana: int) -> list[float]:
    mitad = ventana // 2
    suavizado = []
    for i in range(len(cuentas)):
        vecinos = cuentas[max(0, i - mitad) : i + mitad + 1]
        suavizado.append(sum(vecinos) / len(vecinos))
    return suavizado


def _centro_del_valle(suavizado: list[float], pico_ruido: int) -> int | None:
    """Centro del valle entre la cola del ruido y el pico de eventos más alto; None si no hay valle.

    La cola del ruido termina cuando el histograma queda casi vacío (menos del 1 % del pico de ruido);
    el pico de eventos se busca solo después. El valle es el tramo de mínimo entre ambos: si hay una
    meseta de ceros, su centro.
    """
    fin_ruido = next(
        (
            i
            for i in range(pico_ruido, len(suavizado))
            if suavizado[i] <= FRACCION_CERO_RUIDO * suavizado[pico_ruido]
        ),
        None,
    )
    if fin_ruido is None:
        return None
    pico = max(range(fin_ruido, len(suavizado)), key=lambda i: suavizado[i])
    if pico == fin_ruido or suavizado[pico] == 0:
        return None
    tramo = _tramo_minimo_mas_largo(suavizado, fin_ruido, pico)
    if tramo is None:
        return None
    return (tramo[0] + tramo[1]) // 2


def _tramo_minimo_mas_largo(
    suavizado: list[float], inicio: int, fin: int
) -> tuple[int, int] | None:
    """Primer tramo más largo de bins con el valor mínimo del intervalo [inicio, fin]."""
    minimo = min(suavizado[inicio : fin + 1])
    mejor: tuple[int, int] | None = None
    i = inicio
    while i <= fin:
        if suavizado[i] <= minimo:
            j = i
            while j + 1 <= fin and suavizado[j + 1] <= minimo:
                j += 1
            if mejor is None or j - i > mejor[1] - mejor[0]:
                mejor = (i, j)
            i = j + 1
        else:
            i += 1
    return mejor


def _modos_sobre_valle(
    magnitudes_kw: list[float], suavizado: list[float], valle: int
) -> list[Modo]:
    segmentos = _segmentos_sobre_valle(suavizado, valle)
    modos: list[Modo] = []
    for izq, der in _fusionar_segmentos_poco_separados(suavizado, segmentos):
        valores = [m for m in magnitudes_kw if izq * ANCHO_BIN_KW <= m < (der + 1) * ANCHO_BIN_KW]
        if len(valores) >= MIN_SALTOS_POR_MODO:
            modos.append(_describir_modo(valores, izq, der))
    return modos


def _segmentos_sobre_valle(suavizado: list[float], valle: int) -> list[tuple[int, int]]:
    """Tramos de bins alrededor de cada pico (de más alto a más bajo), sin pasar por un valle."""
    disponible = list(suavizado)
    for i in range(valle + 1):
        disponible[i] = 0.0
    segmentos: list[tuple[int, int]] = []
    while True:
        candidatos = [i for i in range(valle + 1, len(disponible)) if disponible[i] > 0]
        if not candidatos:
            break
        pico = max(candidatos, key=lambda i: disponible[i])
        if disponible[pico] < FRACCION_PICO_MODO * suavizado[pico]:
            break
        izq, der = _limites_del_modo(disponible, pico, valle)
        for i in range(izq, der + 1):
            disponible[i] = 0.0
        segmentos.append((izq, der))
    return sorted(segmentos)


def _fusionar_segmentos_poco_separados(
    suavizado: list[float], segmentos: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Une vecinos cuyo valle entre ellos no baja de la mitad del pico más chico: son un mismo modo."""
    fusionados: list[tuple[int, int]] = []
    for seg in segmentos:
        if not fusionados:
            fusionados.append(seg)
            continue
        ant = fusionados[-1]
        entre = suavizado[ant[1] : seg[0] + 1]
        valle_entre = min(entre) if entre else 0.0
        pico_menor = min(max(suavizado[ant[0] : ant[1] + 1]), max(suavizado[seg[0] : seg[1] + 1]))
        if valle_entre >= PROFUNDIDAD_MODOS_SEPARADOS * pico_menor:
            fusionados[-1] = (ant[0], seg[1])
        else:
            fusionados.append(seg)
    return fusionados


def _limites_del_modo(disponible: list[float], pico: int, valle: int) -> tuple[int, int]:
    izq = pico
    while izq - 1 > valle and disponible[izq - 1] <= disponible[izq] and disponible[izq - 1] > 0:
        izq -= 1
    der = pico
    while (
        der + 1 < len(disponible)
        and disponible[der + 1] <= disponible[der]
        and disponible[der + 1] > 0
    ):
        der += 1
    return izq, der


def _describir_modo(valores: list[float], izq: int, der: int) -> Modo:
    centro = median(valores)
    sigma = pstdev(valores) if len(valores) > 1 else 0.0
    for _ in range(2):
        dentro = [v for v in valores if abs(v - centro) <= FACTOR_SIGMA_MODO * sigma] or valores
        centro = median(dentro)
        sigma = pstdev(dentro) if len(dentro) > 1 else 0.0
    return Modo(
        desde_kw=izq * ANCHO_BIN_KW,
        hasta_kw=(der + 1) * ANCHO_BIN_KW,
        cantidad=len(valores),
        centro_kw=round(centro, 2),
        dispersion_kw=round(sigma, 2),
        radio_kw=round(2 * sigma, 2),
    )
