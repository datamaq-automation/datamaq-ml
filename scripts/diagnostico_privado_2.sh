#!/usr/bin/env bash
# diagnostico_privado_2.sh — diagnóstico de periodicidad, ΔQ/ΔP, pasos de Q y banco
#
# Herramienta de procedimiento del issue #24. Solo lee exportaciones privadas en $DATOS y escribe en
# $TRABAJO (700, fuera de git). Imprime solo conteos, porcentajes y medias: sin filas, sin instantes,
# sin fechas ni identificadores de medidor. No contiene datos. Ver el PR del issue #24 para el orden
# de ejecución.
set -euo pipefail

REPO="${REPO:-$(cd "$(dirname "$0")/.." && pwd)}"
PY="$REPO/.venv/bin/python"
DATOS="${DATOS:-$HOME/datos-privados/nilm-produccion}"
TRABAJO="${TRABAJO:-$HOME/datos-privados/nilm-trabajo}"
umask 077

for falta in mapa.txt utilizables.txt; do
  if [ ! -e "$TRABAJO/$falta" ]; then
    echo "Falta $falta en TRABAJO: corré antes el procedimiento de validación."
    exit 1
  fi
done

cd "$REPO"
"$PY" - "$REPO" "$DATOS" "$TRABAJO" <<'PY'
import sys
from datetime import datetime, timedelta, timezone
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

REPO, DATOS, TRABAJO = (Path(a) for a in sys.argv[1:4])
sys.path.insert(0, str(REPO))

from src.domain.cargas.banco_capacitores import (  # noqa: E402
    UMBRAL_P_BANCO_KW,
    UMBRAL_Q_BANCO_KVAR,
    es_conmutacion,
)
from src.infrastructure.csv.medicion_repository import CsvMedicionRepository  # noqa: E402

# Los módulos del repo registran en el log la ruta de cada CSV (id del medidor y fecha): se silencian.
import logging  # noqa: E402
logging.getLogger("datamaq-ml").setLevel(logging.CRITICAL)

TZ = ZoneInfo("America/Argentina/Buenos_Aires")
HUECO = timedelta(minutes=5)
HORAS_POR_MUESTRA = 5.0 / 60.0  # cada muestra cuenta 5 min (300 s), como pide el diagnóstico
GRANDE_KW = {"T1": 75.0, "T2": 100.0}  # umbral de «salto grande» por trafo (T2 por defecto)


def leer(ruta: Path) -> list:
    repo = CsvMedicionRepository(ruta.parent)
    return sorted(
        repo.leer_archivo(ruta, datetime(2000, 1, 1), datetime(2100, 1, 1)),
        key=lambda m: m.instante,
    )


def lineas(nombre: str) -> list[list[str]]:
    return [
        l.split() for l in (TRABAJO / nombre).read_text(encoding="utf-8").splitlines() if l.strip()
    ]


def hora_local(instante: datetime) -> int:
    return instante.replace(tzinfo=timezone.utc).astimezone(TZ).hour


def hist(valores: list[float], inicio: float, ancho: float, n: int) -> tuple[list[int], int, int]:
    """Cuenta por tramos [inicio + i·ancho, inicio + (i+1)·ancho). Devuelve (tramos, bajo el inicio, sobre el final)."""
    cuentas = [0] * n
    bajo = sobre = 0
    for v in valores:
        if v < inicio:
            bajo += 1
        elif v >= inicio + ancho * n:
            sobre += 1
        else:
            cuentas[int((v - inicio) // ancho)] += 1
    return cuentas, bajo, sobre


def media(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def pct(ordenados: list[float], p: float) -> float:
    return ordenados[min(len(ordenados) - 1, round(p / 100 * (len(ordenados) - 1)))]


por_etiqueta = {etq: id_ for id_, etq in lineas("mapa.txt")}
utiles = lineas("utilizables.txt")

for etq in sorted(por_etiqueta):
    id_ = por_etiqueta[etq]
    dias = sorted(f for i, f, _ in utiles if i == id_)
    grande = GRANDE_KW.get(etq, 100.0)

    potencias: list[float] = []
    dps: list[float] = []
    grandes: list[tuple[datetime, float, float | None]] = []
    pasos_dq: list[datetime] = []
    pasos_dq_dp: list[float] = []
    horas_pasos = [0] * 24
    banco: list[tuple[datetime, float, float | None, float | None]] = []

    for fecha in dias:
        meds = leer(DATOS / f"{id_}_{fecha}.csv")
        potencias.extend(m.potencia_kw for m in meds)
        for a, b in pairwise(meds):
            if b.instante - a.instante > HUECO:
                continue
            dp = b.potencia_kw - a.potencia_kw
            dq = None
            if a.reactiva_kvar is not None and b.reactiva_kvar is not None:
                dq = b.reactiva_kvar - a.reactiva_kvar
            dps.append(dp)
            if abs(dp) >= grande:
                grandes.append((b.instante, dp, dq))
            if dq is not None and 10 <= abs(dq) < 15:
                pasos_dq.append(b.instante)
                pasos_dq_dp.append(abs(dp))
                horas_pasos[hora_local(b.instante)] += 1
            if dq is not None and es_conmutacion(dp, dq, UMBRAL_P_BANCO_KW, UMBRAL_Q_BANCO_KVAR):
                banco.append((b.instante, dq, a.reactiva_kvar, b.reactiva_kvar))

    print(f"\n== Trafo {etq} ==  (días utilizables: {len(dias)}; salto grande: |ΔP| ≥ {grande:.0f} kW)")

    # 1) Histograma fino de |ΔP| entre 60 y 200 kW
    sub = [v for v in dps if v > 0]
    baj = [-v for v in dps if v < 0]
    cs, cs_bajo, cs_sobre = hist(sub, 60.0, 2.5, 56)
    cb, cb_bajo, cb_sobre = hist(baj, 60.0, 2.5, 56)
    print("[1] |ΔP| entre muestras consecutivas, tramos de 2,5 kW entre 60 y 200 kW (subidas / bajadas):")
    for k in range(56):
        ini = 60.0 + 2.5 * k
        if cs[k] or cb[k]:
            print(f"   {ini:6.1f}-{ini + 2.5:6.1f}: {cs[k]:>7} / {cb[k]:>7}")
    print(f"   menos de 60 kW: {cs_bajo} / {cb_bajo};  200 kW o más: {cs_sobre} / {cb_sobre}")

    # 2) Carga base: percentiles de P y energía bajo P5 y P25
    orden = sorted(potencias)
    total_kwh = sum(potencias) * HORAS_POR_MUESTRA
    p = {q: pct(orden, q) for q in (1, 5, 25, 50, 75, 95, 99)}
    print(f"[2] Potencia activa (kW) sobre {len(potencias)} muestras ({len(potencias) * HORAS_POR_MUESTRA:.0f} h), energía total {total_kwh:.0f} kWh:")
    print("   " + "  ".join(f"P{q}={p[q]:.1f}" for q in (1, 5, 25, 50, 75, 95, 99)))
    e_p5 = sum(x for x in potencias if x < p[5]) * HORAS_POR_MUESTRA
    e_p25 = sum(x for x in potencias if x < p[25]) * HORAS_POR_MUESTRA
    print(f"   energía de muestras con P < P5: {100.0 * e_p5 / total_kwh:.1f} % del total;  con P < P25: {100.0 * e_p25 / total_kwh:.1f} % del total")

    # 3) Periodicidad de los saltos grandes
    subidas_t = [t for t, dp, _ in grandes if dp > 0]
    bajadas_n = sum(1 for _, dp, _ in grandes if dp < 0)
    s_s = [(t2 - t1).total_seconds() / 60.0 for t1, t2 in pairwise(subidas_t)]
    ciclos: list[float] = []
    ultima_subida = None
    for t, dp, _ in grandes:
        if dp > 0:
            ultima_subida = t
        elif ultima_subida is not None:
            ciclos.append((t - ultima_subida).total_seconds() / 60.0)
            ultima_subida = None
    print(f"[3] Saltos grandes: {len(subidas_t)} subidas, {bajadas_n} bajadas.")
    for titulo, serie in (("subida → subida siguiente", s_s), ("subida → bajada siguiente (duración de marcha)", ciclos)):
        cuentas, _, sobre = hist(serie, 0.0, 15.0, 24)
        print(f"   {titulo}, tramos de 15 min hasta 6 h (n={len(serie)}):")
        for k in range(24):
            if cuentas[k]:
                print(f"     {15 * k:>3}-{15 * (k + 1):>3} min: {cuentas[k]}")
        print(f"     más de 6 h: {sobre}")

    # 4) Relación ΔQ/ΔP de los saltos grandes
    razones = [dq / dp for _, dp, dq in grandes if dq is not None and dp != 0]
    cuentas, bajo_r, sobre_r = hist(razones, -1.0, 0.1, 30)
    print(f"[4] ΔQ/ΔP de los saltos grandes (n={len(razones)}, mediana {sorted(razones)[len(razones) // 2]:.2f}):" if razones else "[4] Sin ΔQ en los saltos grandes.")
    for k in range(30):
        if cuentas[k]:
            print(f"   {-1.0 + 0.1 * k:+.1f} a {-0.9 + 0.1 * k:+.1f}: {cuentas[k]}")
    if razones:
        print(f"   menos de -1,0: {bajo_r};  2,0 o más: {sobre_r}")

    # 5) Pico de |ΔQ| entre 10 y 15 kVAr
    n_pasos = len(pasos_dq)
    cerca_cero = sum(1 for dp in pasos_dq_dp if dp < 5.0)
    print(f"[5] Pasos de |ΔQ| entre 10 y 15 kVAr: {n_pasos}; con |ΔP| < 5 kW: {cerca_cero} ({100.0 * cerca_cero / n_pasos if n_pasos else 0.0:.1f} %)")
    entre = [(t2 - t1).total_seconds() / 60.0 for t1, t2 in pairwise(pasos_dq)]
    cuentas, _, sobre = hist(entre, 0.0, 5.0, 36)
    print("   tiempo entre pasos consecutivos, tramos de 5 min hasta 3 h:")
    for k in range(36):
        if cuentas[k]:
            print(f"     {5 * k:>3}-{5 * (k + 1):>3} min: {cuentas[k]}")
    print(f"     más de 3 h: {sobre}")
    print("   pasos por hora local (24): " + " ".join(f"{h:02d}:{horas_pasos[h]}" for h in range(24)))

    # 6) Eventos de banco: alternancia, compensación y nivel de Q
    signos = [dq > 0 for _, dq, _, _ in banco]
    cambios = sum(1 for s1, s2 in pairwise(signos) if s1 != s2)
    transiciones = max(0, len(signos) - 1)
    ups = [i for i, (_, dq, _, _) in enumerate(banco) if dq > 0]
    usados: set[int] = set()
    compensadas = 0
    for i in ups:
        t_i, dq_i, _, _ = banco[i]
        for j in range(i + 1, len(banco)):
            t_j, dq_j, _, _ = banco[j]
            if t_j - t_i > timedelta(hours=6):
                break
            if j in usados or dq_j >= 0:
                continue
            if abs(abs(dq_j) - dq_i) <= 0.25 * dq_i:
                usados.add(j)
                compensadas += 1
                break
    def nivel(eventos, antes):
        return media([(q_a if antes else q_b) for _, _, q_a, q_b in eventos if (q_a if antes else q_b) is not None])
    subidas_e = [e for e in banco if e[1] > 0]
    bajadas_e = [e for e in banco if e[1] < 0]
    print(f"[6] Eventos de banco: {len(banco)} (subidas {len(subidas_e)}, bajadas {len(bajadas_e)})")
    print(f"   transiciones que cambian de signo: {cambios} de {transiciones} ({100.0 * cambios / transiciones if transiciones else 0.0:.1f} %)")
    print(f"   subidas con una bajada compensatoria (±25 %) en las 6 h siguientes: {compensadas} de {len(ups)} ({100.0 * compensadas / len(ups) if ups else 0.0:.1f} %)")
    print(f"   Q medio (kVAr) antes → después: subidas {nivel(subidas_e, True):.1f} → {nivel(subidas_e, False):.1f};  bajadas {nivel(bajadas_e, True):.1f} → {nivel(bajadas_e, False):.1f}")

print("\nListo: solo conteos, porcentajes y medias; sin fechas ni identificadores.")
PY
