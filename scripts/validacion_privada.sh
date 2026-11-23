#!/usr/bin/env bash
# validacion_privada.sh — procedimiento de validación con el motor nuevo (entrenamiento, catálogo, validación y resumen)
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
MIN_FILAS="${MIN_FILAS:-280}"
umask 077
mkdir -p "$TRABAJO"/{entrada,clusters,catalogos,validacion}
chmod 700 "$TRABAJO" "$TRABAJO"/{entrada,clusters,catalogos,validacion}

# 1) Filas de datos por archivo (sin cabecera). Id y fecha quedan solo en archivos privados.
cd "$DATOS"
: > "$TRABAJO/conteo.txt"
for f in *.csv; do
  n=$(( $(wc -l < "$f") - 1 ))
  id=${f%%_*}; fecha=${f#*_}; fecha=${fecha%.csv}
  printf '%s %s %s\n' "$id" "$fecha" "$n" >> "$TRABAJO/conteo.txt"
done
cd "$REPO"  # python -m necesita estar en la raíz del repo (src/)
# Etiqueta T1, T2... por medidor (el orden es el del id; la etiqueta no revela el id).
awk '{print $1}' "$TRABAJO/conteo.txt" | sort -u > "$TRABAJO/ids.txt"
awk '{print $1, "T" NR}' "$TRABAJO/ids.txt" > "$TRABAJO/mapa.txt"
awk -v min="$MIN_FILAS" '$3 >= min' "$TRABAJO/conteo.txt" | sort -k1,1 -k2,2 > "$TRABAJO/utilizables.txt"

echo "== 1. Días por trafo (conteos) =="
awk -v min="$MIN_FILAS" 'NR == FNR { e[$1] = $2; next }
  { t = e[$1]; tot[t]++
    if ($3 == 0) cero[t]++; else if ($3 < min) bajo[t]++; else ok[t]++ }
  END { for (t in tot) printf "%s: archivos=%d, sin_filas=%d, menos_de_%d=%d, utilizables=%d\n",
        t, tot[t], cero[t] + 0, min, bajo[t] + 0, ok[t] + 0 }' \
  "$TRABAJO/mapa.txt" "$TRABAJO/conteo.txt" | sort

# 2) Por trafo: primera mitad (cronológica) para entrenar, segunda mitad para validar.
#    Así la validación no usa los mismos días con que se formaron los clústeres.
while read -r id etiqueta; do
  awk -v i="$id" '$1 == i' "$TRABAJO/utilizables.txt" | sort -k2,2 > "$TRABAJO/dias_$etiqueta.txt"
  n=$(wc -l < "$TRABAJO/dias_$etiqueta.txt")
  mitad=$(( n / 2 ))
  head -n "$mitad" "$TRABAJO/dias_$etiqueta.txt" > "$TRABAJO/entrenar_$etiqueta.txt"
  tail -n +"$(( mitad + 1 ))" "$TRABAJO/dias_$etiqueta.txt" > "$TRABAJO/validar_$etiqueta.txt"
  # train lee un CSV por medidor: se concatenan los días de entrenamiento (cabecera una vez).
  : > "$TRABAJO/entrada/$etiqueta.csv"
  primero=1
  while read -r _ fecha _; do
    if [ "$primero" = 1 ]; then
      cat "$DATOS/${id}_${fecha}.csv" >> "$TRABAJO/entrada/$etiqueta.csv"; primero=0
    else
      tail -n +2 "$DATOS/${id}_${fecha}.csv" >> "$TRABAJO/entrada/$etiqueta.csv"
    fi
  done < "$TRABAJO/entrenar_$etiqueta.txt"
done < "$TRABAJO/mapa.txt"

# 3) Clústeres por trafo con el entrenamiento existente (no supervisado, DBSCAN).
MEDICIONES_CSV_DIR="$TRABAJO/entrada" RESULTADOS_DIR="$TRABAJO/clusters" MEDICIONES_SOURCE=local \
  "$PY" -m src.infrastructure.cli.entrenar_cargas > "$TRABAJO/train.log" 2>&1

# 4) Catálogo de firmas candidatas por trafo, desde cargas_<T>.csv y entrenamiento_<T>.json (issue #24).
for archivo in "$TRABAJO"/clusters/cargas_*.csv; do
  etiqueta=$(basename "$archivo" .csv); etiqueta=${etiqueta#cargas_}
  "$PY" -m src.infrastructure.cli.catalogo_desde_entrenamiento \
    --cargas "$archivo" \
    --entrenamiento "$TRABAJO/clusters/entrenamiento_${etiqueta}.json" \
    --salida "$TRABAJO/catalogos/catalogo_${etiqueta}.json" > /dev/null
  echo "$etiqueta: catálogo armado"
done

# 5) Validación día por día (solo días de la segunda mitad), salida privada.
: > "$TRABAJO/validacion/fallos.txt"
while read -r id etiqueta; do
  while read -r _ fecha _; do
    if ! "$PY" -m src.infrastructure.cli.validar_dia_real \
        --archivo "$DATOS/${id}_${fecha}.csv" \
        --firmas "$TRABAJO/catalogos/catalogo_${etiqueta}.json" \
        --fecha "$fecha" \
        --entrenamiento "$TRABAJO/clusters/entrenamiento_${etiqueta}.json" \
        --tolerancia-por-dispersion --tolerancia-max-kw "${TOL_MAX:-25}" \
        --salida-json "$TRABAJO/validacion/${etiqueta}_${fecha}.json" \
        > /dev/null 2>> "$TRABAJO/validacion/errores.txt"; then
      echo "$etiqueta" >> "$TRABAJO/validacion/fallos.txt"
    fi
  done < "$TRABAJO/validar_$etiqueta.txt"
done < "$TRABAJO/mapa.txt"

# 6) Resumen agregado (sin fechas, sin instantes, sin identificadores).
"$PY" - "$TRABAJO" <<'PY'
import json, sys
from collections import defaultdict
from pathlib import Path
trabajo = Path(sys.argv[1])
val = trabajo / "validacion"
fallos = sum(1 for _ in open(val / "fallos.txt", encoding="utf-8")) if (val / "fallos.txt").exists() else 0
trafos: dict[str, dict] = defaultdict(lambda: defaultdict(float))
cargas: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
for archivo in sorted(val.glob("T*_*.json")):
    etiqueta = archivo.name.split("_", 1)[0]
    m = json.loads(archivo.read_text(encoding="utf-8"))
    t = trafos[etiqueta]
    t["dias"] += 1
    t["calidad_baja"] += int(bool(m.get("calidad_baja")))
    t["medida"] += m["energia_medida_kwh"]
    t["atrib_pq"] += m["energia_atribuida_kwh"]
    t["atrib_p"] += m.get("energia_atribuida_solo_p_kwh", 0.0)
    t["eventos"] += m["eventos"]
    t["sin_atribuir"] += m["eventos_sin_atribuir"]
    t["cerrados"] += m["intervalos_cerrados"]
    t["abiertos"] += m["intervalos_abiertos"]
    t["cortados"] += m["intervalos_cortados_por_caida"]
    t["banco"] += m.get("eventos_banco_dp_bajo_dq_alto", 0)
    for c in m["cargas"]:
        nombre = c["nombre"].split(" carga ", 1)[-1]
        d = cargas[etiqueta][nombre]
        d["intervalos"] += c["intervalos"]
        d["horas"] += c["horas"]
        d["energia"] += c["energia_kwh"]
print(f"Archivos de validación con error: {fallos}")
for etiqueta in sorted(trafos):
    t = trafos[etiqueta]
    pct = lambda parte, total: (100.0 * parte / total) if total else 0.0
    print(f"\n== Trafo {etiqueta} ==")
    entr = json.loads((trabajo / "clusters" / f"entrenamiento_{etiqueta}.json").read_text(encoding="utf-8"))
    print(f"Entrenamiento: régimen {entr.get('regimen')}; umbral {entr.get('umbral_kw')} kW; η {entr.get('separacion')}; modos {len(entr.get('modos', []))}")
    print(f"Días validados: {int(t['dias'])}; calidad baja: {int(t['calidad_baja'])} ({pct(t['calidad_baja'], t['dias']):.1f} %)")
    print(f"Eventos: {int(t['eventos'])}; sin atribuir: {int(t['sin_atribuir'])} ({pct(t['sin_atribuir'], t['eventos']):.1f} %)")
    print(f"Intervalos: cerrados {int(t['cerrados'])}, abiertos {int(t['abiertos'])}, cortados {int(t['cortados'])}")
    print(f"Eventos de banco (ΔP bajo, ΔQ alto): {int(t['banco'])}")
    print(f"Energía medida: {t['medida']:.1f} kWh")
    print(f"Energía atribuida (P y Q): {t['atrib_pq']:.1f} kWh ({pct(t['atrib_pq'], t['medida']):.1f} % de la medida)")
    print(f"Energía atribuida (solo P): {t['atrib_p']:.1f} kWh ({pct(t['atrib_p'], t['medida']):.1f} % de la medida)")
    catalogo = json.loads((trabajo / "catalogos" / f"catalogo_{etiqueta}.json").read_text(encoding="utf-8"))
    con_intervalos = sum(1 for nombre, d in cargas[etiqueta].items() if d["intervalos"] > 0)
    print(f"Clústeres/firmas en el catálogo: {len(catalogo)}; con intervalos atribuidos: {con_intervalos}")
    for nombre in sorted(cargas[etiqueta], key=lambda n: int(n) if n.isdigit() else 0):
        d = cargas[etiqueta][nombre]
        print(f"  carga {nombre}: intervalos {int(d['intervalos'])}, horas {d['horas']:.1f}, energía {d['energia']:.1f} kWh")
PY
echo
echo "Listo. Lo de arriba son solo conteos y porcentajes. Los archivos privados quedan en la carpeta TRABAJO."
