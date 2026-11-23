#!/usr/bin/env bash
# diagnostico_privado_1.sh — diagnóstico de histogramas, carga base y cortes
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

for falta in mapa.txt utilizables.txt entrada catalogos validacion; do
  if [ ! -e "$TRABAJO/$falta" ]; then
    echo "Falta $falta en TRABAJO: corré antes el procedimiento de validación."
    exit 1
  fi
done

cd "$REPO"
"$PY" - "$REPO" "$DATOS" "$TRABAJO" <<'PY'
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

REPO, DATOS, TRABAJO = (Path(a) for a in sys.argv[1:4])
sys.path.insert(0, str(REPO))

from sklearn.cluster import DBSCAN  # noqa: E402

from src.application.cargas.dtos.desagregar_cargas import (  # noqa: E402
    FirmaConfirmadaDTO,
    ParametrosMotorDTO,
)
from src.application.cargas.use_cases.validar_desagregacion import (  # noqa: E402
    CORTADO,
    _atribuir,
    _clasificar_con_motor,
    _eventos,
    _umbral_usado,
    _ventana,
)
from src.domain.cargas.banco_capacitores import (  # noqa: E402
    UMBRAL_P_BANCO_KW,
    UMBRAL_Q_BANCO_KVAR,
    detectar_conmutaciones,
)
from src.domain.cargas.services import (  # noqa: E402
    detectar_eventos,
    estimar_min_eventos,
    estimar_radio,
    estimar_umbral,
    nivel_de_ruido,
)
from src.infrastructure.cli.desagregar_cargas import ventana_utc_del_dia  # noqa: E402
from src.infrastructure.csv.medicion_repository import CsvMedicionRepository  # noqa: E402
from src.infrastructure.sklearn.dbscan_agrupador import DbscanAgrupador  # noqa: E402

# Los módulos del repo registran en el log la ruta de cada CSV (con el id del medidor y la fecha).
# Se silencian: este script imprime solo sus propios conteos.
import logging  # noqa: E402
logging.getLogger("datamaq-ml").setLevel(logging.CRITICAL)

TZ = ZoneInfo("America/Argentina/Buenos_Aires")
ANCHO, TOPE, CERO_KW = 5.0, 100.0, 2.0
HUECO = timedelta(minutes=5)
NBINS = int(TOPE / ANCHO)
ETIQ = [f"{int(i * ANCHO)}-{int((i + 1) * ANCHO)}" for i in range(NBINS)] + [f"≥{int(TOPE)}"]


def tramo(valor: float) -> int:
    return NBINS if abs(valor) >= TOPE else int(abs(valor) // ANCHO)


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


def imprimir_histograma(titulo: str, subidas: list[int], bajadas: list[int]) -> None:
    print(titulo)
    for k, etiqueta in enumerate(ETIQ):
        print(f"   {etiqueta:>8}: subidas {subidas[k]:>8}   bajadas {bajadas[k]:>8}")


por_etiqueta = {etq: id_ for id_, etq in lineas("mapa.txt")}
utiles = lineas("utilizables.txt")

for etq in sorted(por_etiqueta):
    id_ = por_etiqueta[etq]
    dias = sorted(f for i, f, _ in utiles if i == id_)
    dias_val = sorted(f for i, f, _ in lineas(f"validar_{etq}.txt"))
    firmas = [
        FirmaConfirmadaDTO(**x)
        for x in json.loads((TRABAJO / "catalogos" / f"catalogo_{etq}.json").read_text(encoding="utf-8"))
    ]
    # Mismo umbral y mismo régimen que la validación: lo fija el entrenamiento (sidecar de train).
    sidecar = TRABAJO / "clusters" / f"entrenamiento_{etq}.json"
    entrenamiento = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
    umbral = _umbral_usado(firmas, entrenamiento.get("umbral_kw"))  # sin firmas no hay min(): usa el entrenamiento
    # Mismos parámetros de tolerancia que validacion_privada.sh (--tolerancia-por-dispersion --tolerancia-max-kw).
    motor = ParametrosMotorDTO(
        tolerancia_por_dispersion=True, tolerancia_max_kw=float(os.environ.get("TOL_MAX", "25"))
    )
    print(
        f"Régimen {entrenamiento.get('regimen')}: umbral compartido {umbral:.1f} kW; "
        f"firmas en el catálogo {len(firmas)}"
    )

    hist_p = {"subidas": [0] * (NBINS + 1), "bajadas": [0] * (NBINS + 1)}
    hist_q = {"subidas": [0] * (NBINS + 1), "bajadas": [0] * (NBINS + 1)}
    pares = pares_hueco = 0
    hora_ev = [0] * 24
    hora_banco = [0] * 24
    hist_banco_q = [0] * (NBINS + 1)
    banco_total = banco_up = banco_hueco = 0
    for fecha in dias:
        meds = leer(DATOS / f"{id_}_{fecha}.csv")
        previa: dict[datetime, datetime] = {}
        for a, b in pairwise(meds):
            previa[b.instante] = a.instante
            if b.instante - a.instante > HUECO:
                pares_hueco += 1
                continue
            pares += 1
            dp = b.potencia_kw - a.potencia_kw
            hist_p["subidas" if dp > 0 else "bajadas"][tramo(dp)] += 1
            if a.reactiva_kvar is not None and b.reactiva_kvar is not None:
                dq = b.reactiva_kvar - a.reactiva_kvar
                hist_q["subidas" if dq > 0 else "bajadas"][tramo(dq)] += 1
        for e in detectar_eventos(meds, umbral):
            hora_ev[hora_local(e.instante)] += 1
        for c in detectar_conmutaciones(meds, UMBRAL_P_BANCO_KW, UMBRAL_Q_BANCO_KVAR):
            banco_total += 1
            banco_up += c.delta_kvar > 0
            hora_banco[hora_local(c.instante)] += 1
            hist_banco_q[tramo(c.delta_kvar)] += 1
            if c.instante - previa.get(c.instante, c.instante) > HUECO:
                banco_hueco += 1

    print(f"\n== Trafo {etq} ==")
    print(f"Días utilizables: {len(dias)}; días de validación: {len(dias_val)}")
    print(f"Pares de muestras consecutivas: {pares} sin hueco; {pares_hueco} con hueco (> 5 min, excluidos de [1] y [2])")
    imprimir_histograma("[1] |ΔP| entre muestras consecutivas, por tramo de 5 kW:", hist_p["subidas"], hist_p["bajadas"])
    imprimir_histograma("[2] |ΔQ| entre muestras consecutivas, por tramo de 5 kVAr (cambio de ΔQ en kVAr):", hist_q["subidas"], hist_q["bajadas"])
    print(f"[3] Saltos |ΔP| ≥ {umbral:.1f} kW (umbral compartido con el entrenamiento), por hora local:")
    print("   " + " ".join(f"{h:02d}:{hora_ev[h]}" for h in range(24)))
    print("    Eventos de banco (|ΔP| < 1,5 kW y |ΔQ| ≥ 10 kVAr; definición en src/domain/cargas/banco_capacitores.py, líneas 14-15 y 31), por hora local:")
    print("   " + " ".join(f"{h:02d}:{hora_banco[h]}" for h in range(24)))
    pct_up = 100.0 * banco_up / banco_total if banco_total else 0.0
    print(f"[4] Eventos de banco: {banco_total}; suben (ΔQ>0): {banco_up} ({pct_up:.1f} %); bajan: {banco_total - banco_up}; con hueco previo (> 5 min): {banco_hueco}")
    print("   histograma de |ΔQ| de esos eventos, por tramo de 5 kVAr:")
    for k, etiqueta in enumerate(ETIQ):
        print(f"   {etiqueta:>8}: {hist_banco_q[k]}")

    serie = leer(TRABAJO / "entrada" / f"{etq}.csv")
    est = estimar_umbral(serie)
    u_tr = est.umbral_kw if est else None
    ev_tr = detectar_eventos(serie, u_tr) if u_tr is not None else []
    ruido = nivel_de_ruido(serie, u_tr) if u_tr is not None else 0.0
    eps = estimar_radio(ev_tr, ruido)
    span = (serie[-1].instante - serie[0].instante).total_seconds() / 86400
    min_ev = estimar_min_eventos(span)
    print(f"[5a] Entrenamiento (lo que hizo train): umbral Otsu {u_tr} kW (η={est.separacion if est else None}); eventos {len(ev_tr)}; ruido {ruido:.2f} kW")
    print(f"     radio NILM_EPS_KW estimado = {eps} kW; mínimo de eventos por grupo = {min_ev} (span de {span:.1f} días)")
    if eps is not None and ev_tr:
        g2 = list(DbscanAgrupador().agrupar(ev_tr, eps, min_ev))
        g1 = list(DBSCAN(eps=eps, min_samples=min_ev).fit_predict([[abs(e.delta_kw)] for e in ev_tr]))
        for nombre, etiquetas in (("2D P-Q (como train)", g2), ("1D solo P", g1)):
            ruido_n = etiquetas.count(-1)
            grupos = len(set(etiquetas) - {-1})
            print(f"     DBSCAN {nombre}: grupos {grupos}; eventos sin grupo {ruido_n} ({100.0 * ruido_n / len(etiquetas):.1f} %)")
        for g in sorted(set(g1) - {-1}):
            mags = [abs(e.delta_kw) for e, k in zip(ev_tr, g1) if k == g]
            print(f"       grupo 1D {g}: {len(mags)} eventos, |ΔP| entre {min(mags):.1f} y {max(mags):.1f} kW")
        print("     firmas del catálogo (potencia nominal kW): " + ", ".join(f"{f.potencia_nominal_kw:.1f}" for f in firmas))

    hist_ev = {"subidas": [0] * (NBINS + 1), "bajadas": [0] * (NBINS + 1)}
    n_ev = dentro = cortados_total = cortados_json = eventos_json = 0
    cortados_cat: Counter = Counter()
    for fecha in dias_val:
        desde, hasta = ventana_utc_del_dia(date.fromisoformat(fecha))
        meds = leer(DATOS / f"{id_}_{fecha}.csv")
        ventana = _ventana(meds, desde, hasta)
        eventos = _eventos(ventana, firmas, umbral)
        n_ev += len(eventos)
        for e in eventos:
            hist_ev["subidas" if e.delta_kw > 0 else "bajadas"][tramo(e.delta_kw)] += 1
            if any(abs(abs(e.delta_kw) - f.potencia_nominal_kw) <= (eps or 0.0) for f in firmas):
                dentro += 1
        respuesta = _atribuir(ventana, firmas, desde, hasta, umbral_kw=umbral, motor=motor)
        ultimo = ventana[-1].instante if ventana else None
        indice = {m.instante: k for k, m in enumerate(ventana)}
        for _, it, tipo in _clasificar_con_motor(respuesta, eventos, firmas, motor, ultimo):
            if tipo != CORTADO:
                continue
            cortados_total += 1
            k = indice.get(it.fin_utc.replace(tzinfo=None))
            if k is None or k == 0:
                cortados_cat["sin_muestra_previa"] += 1
            elif ventana[k].instante - ventana[k - 1].instante > HUECO:
                cortados_cat["hueco"] += 1
            elif ventana[k].potencia_kw < CERO_KW:
                cortados_cat["caida_a_cero"] += 1
            else:
                cortados_cat["caida_parcial"] += 1
        ruta_json = TRABAJO / "validacion" / f"{etq}_{fecha}.json"
        if ruta_json.exists():
            datos = json.loads(ruta_json.read_text(encoding="utf-8"))
            eventos_json += datos["eventos"]
            cortados_json += datos["intervalos_cortados_por_caida"]

    print(f"[5b] Eventos en días de validación: {n_ev} (validación JSON: {eventos_json})")
    imprimir_histograma("     |ΔP| de esos eventos, por tramo de 5 kW:", hist_ev["subidas"], hist_ev["bajadas"])
    fuera = n_ev - dentro
    pct_fuera = 100.0 * fuera / n_ev if n_ev else 0.0
    print(f"     dentro del radio de alguna firma (|ΔP| a ≤ {eps} kW de su potencia nominal): {dentro}; fuera: {fuera} ({pct_fuera:.1f} %)")
    print(f"[6] Intervalos cortados por caída: {cortados_total} (validación JSON: {cortados_json}; coincide: {'sí' if cortados_total == cortados_json else 'no'})")
    print(f"     por hueco de datos (Δt > 5 min antes del corte): {cortados_cat['hueco']}")
    print(f"     por caída a casi cero (< {CERO_KW} kW en la muestra del corte): {cortados_cat['caida_a_cero']}")
    print(f"     por caída parcial (otra carga no catalogada se apagó): {cortados_cat['caida_parcial']}")
    print(f"     sin muestra previa: {cortados_cat['sin_muestra_previa']}")

print("\nListo: solo conteos y porcentajes.")
PY
