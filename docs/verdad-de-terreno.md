# Verdad de terreno por intervalos (`nilm.verdad.v1`)

La verdad de terreno dice, para cada máquina del medidor, en qué intervalos estuvo en marcha según una fuente
independiente del algoritmo: los contactos NA de los contactores de los motores (autómata), o un simulador que
conoce los arranques. Se compara contra la salida del batch (`nilm.intervalos.v1`) con el comando
`evaluar_verdad`.

## Forma del archivo

Es la misma forma que `nilm.intervalos.v1` (la salida del batch), con estas diferencias:

| Campo | `nilm.intervalos.v1` (inferido) | `nilm.verdad.v1` (verdad) |
|---|---|---|
| `contrato` | `"nilm.intervalos.v1"` | `"nilm.verdad.v1"` |
| `origen` de cada intervalo | `"INFERIDA"` | `"MEDIDO"` |
| `energia_kwh_medida` | siempre presente | opcional: un contactor no mide energía |
| `potencia_media_kw` / `delta_reactiva_kvar` | presentes | opcionales |
| `medidor.fuente` | no existe | `"simulador"` o `"automata"` |
| `medidor.desfase_reloj_s` | no existe | error de reloj del autómata, si se conoce |
| Esquema | no estricto | **estricto**: una clave fuera del contrato es error |

El resto es igual: `ventana_utc` (desde inclusive, hasta exclusive), `cargas[]` con `nombre` e `intervalos[]`,
y `horas` igual a `fin_utc − inicio_utc`. `nilm.intervalos.v1` no cambia.

Reglas del esquema, todas verificadas por tests (`tests/unit/test_verdad_intervalos_esquema.py`):
- todos los instantes llevan zona UTC (sufijo `Z`);
- `fin_utc` es posterior a `inicio_utc`, y `horas` coincide con la duración;
- los intervalos de una máquina están ordenados y no se solapan;
- los nombres de máquina son únicos;
- todos los intervalos caen dentro de `ventana_utc`.

## Ejemplo sintético

`docs/ejemplos/verdad_sintetica.json` tiene dos máquinas y dos marchas, con energía porque viene del simulador.
Un test lo valida contra el esquema, así que el ejemplo no puede quedar desactualizado.

## Cómo se obtiene

- **Simulador**: `./run.sh simulate --verdad-json <ruta>.json [--desfase-s 3]`. Trae energía (potencia × horas).
- **Autómata** (cuando esté instalado): la verdad sale de los contactos. El archivo sigue el mismo formato, con
  `medidor.fuente = "automata"`, y la energía en `null`.

Es un archivo local, no una tabla. En `datamaq-telemetry` los estados crudos van en una tabla aparte, y los
intervalos medidos se derivan de ella (decisión del repo padre, 2026-11-22).

## Evaluar

```bash
./.venv/bin/python -m src.infrastructure.cli.evaluar_verdad \
  --inferido <salida del batch>.json \
  --verdad <verdad>.json \
  --tolerancia-s 300 \
  --salida-json <detalle>.json
```

Por máquina, el detalle trae:
- **tiempo**: minutos en marcha inferidos, verdaderos y coincidentes; precisión y sensibilidad sobre minutos;
- **arranques** y **paradas**: verdaderos, inferidos, emparejados (a ±tolerancia, uno a uno), precisión y sensibilidad;
- **energía**: inferida, verdadera (si la verdad la trae) y error porcentual.

Las máquinas se emparejan por `nombre`: el nombre del catálogo de firmas tiene que ser el de la verdad.

Convención sin denominador: sin minutos o eventos inferidos, la precisión vale 1; sin verdad, la sensibilidad vale 1.
