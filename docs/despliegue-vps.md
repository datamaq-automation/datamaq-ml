# Despliegue del batch `disaggregate` en el VPS

Documento de planificación. **No se ejecutó nada en el VPS.** Todas las cifras de recursos son de esta
máquina de desarrollo, con datos sintéticos (ver §4). Antes de instalar en el VPS hay que repetir la
medición allí con un día real (ver §7).

## 1. Versión mínima de Python

- **Mínimo declarado y verificado: Python 3.10.** `pyproject.toml` declara `requires-python = ">=3.10"`.
- Verificado: la suite completa (281 tests) pasa con Python 3.10.20 en un venv limpio con
  `requirements-dev.txt`, y el CLI `disaggregate` corre de punta a punta con 3.10.20 usando solo
  `requirements.txt`. Ver el commit `fix(compat)`: antes, siete archivos importaban `datetime.UTC`
  (3.11+) y el mínimo declarado era falso.
- CI usa 3.12 (`.github/workflows/ci.yml`). No hay nada en el código que requiera 3.11 o superior.

**Verificar en el VPS sin instalar nada** (solo lectura):

```bash
# 1. ¿Qué Python hay? Debe imprimir 3.10 o superior.
python3 --version
ls /usr/bin/python3* 2>/dev/null

# 2. Chequeo de versión mínima (sale con 0 si cumple)
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' && echo "OK: >= 3.10"

# 3. ¿Está el módulo venv y ensurepip? Si falla, falta el paquete python3-venv (no se instala aquí).
python3 -c 'import venv, ensurepip' && echo "OK: venv disponible"

# 4. Requisito declarado en el repo que se va a desplegar (solo lectura)
grep -n requires-python /ruta/al/repo/pyproject.toml
```

Si el paso 1 muestra solo 3.8 o 3.9, no alcanza: hay que instalar un Python 3.10+ por otro medio
(decisión del dueño sobre el VPS).

## 2. Dependencias

Archivo `requirements.txt` (runtime). Requisitos mínimos declarados:

| Paquete | Requisito | Usado por `disaggregate` |
|---|---|---|
| fastapi | >=0.115.0 | no (lo usa la API) |
| uvicorn[standard] | >=0.31.0 | no (lo usa la API) |
| pydantic | >=2.9.0 | sí |
| pydantic-settings | >=2.5.0 | sí (configuración) |
| scikit-learn | >=1.5 | no (entrenamiento y evaluación) |
| pandas | >=2.1 | no (entrenamiento y evaluación) |
| joblib | >=1.3 | no (modelos) |

`requirements-dev.txt` agrega pytest, pytest-asyncio, httpx2 y ruff. **No se instalan en el VPS.**

Verificado con `grep` de importaciones: `src/domain`, `src/application` y `src/infrastructure/cli`
no importan pandas, sklearn, numpy ni scipy en el camino de `disaggregate`. Medido en el intérprete:
tras importar `src.infrastructure.cli.desagregar_cargas`, `sklearn`, `pandas`, `numpy`, `scipy` y
`fastapi` no están en `sys.modules`; `pydantic` sí.

Consecuencia: el costo de importar pandas y sklearn (§4) **no lo paga el timer diario**. Lo pagan
`train` y `evaluate`.

## 3. Tamaño del `.venv`

| Venv | Python | Contenido | Tamaño |
|---|---|---|---|
| `.venv` de desarrollo (esta máquina) | 3.14.8 | `requirements-dev.txt` | 451 MB |
| venv de producción (medido) | 3.10.20 | solo `requirements.txt` | 294 MB |

Para el VPS, el tamaño a planificar es el de producción: **~300 MB** más el espacio de datos. El
tamaño depende de la versión de Python y de las ruedas de la plataforma; medir en el VPS con
`du -sh <repo>/.venv` después de instalar.

## 4. Medición (datos sintéticos, esta máquina)

**Método.** Un medidor sintético de 365 días (1 de enero a 31 de diciembre de 2026), una muestra por
minuto (1440 por día, cota superior; ver nota), tres firmas (compresor 45 kW, bomba 22 kW, cinta 8 kW),
con arranques y paradas aleatorias. Cada día se procesó con **una invocación separada** de
`python -m src.infrastructure.cli.desagregar_cargas`, porque el CLI procesa un día por ejecución. El
pico de RAM se tomó de cada proceso con `wait4` (`ru_maxrss` de ese proceso, no acumulado). La
secuencia de 365 corridas sirve para los tres casos: 1 y 30 días son las primeras 1 y 30 corridas.

**Máquina:** 8 núcleos, 30 GB de RAM, Python 3.14.8 con el `.venv` de desarrollo. Corridas de los 365
días: todas con código de salida 0.

| Periodo | Corridas | Tiempo total | Mediana por corrida | RAM pico (máx. de un proceso) |
|---|---|---|---|---|
| 1 día | 1 | 0,4 s | 0,404 s | 46,8 MB |
| 30 días | 30 | 12,3 s | 0,407 s | 47,0 MB |
| 365 días | 365 | 156,6 s (≈ 2 min 37 s) | 0,415 s | 47,1 MB |

**Costo de importar** (mediana de 8 repeticiones, con una corrida de calentamiento descartada,
Python 3.10.20 de producción):

| Import | Tiempo | RAM residente |
|---|---|---|
| intérprete vacío (`python -c pass`) | 0,02 s | 15 MB |
| `import pandas` | 0,65 s | 75 MB |
| `import sklearn` | 1,8 s | 145 MB |
| `import pandas, sklearn` | 1,7 s | 144 MB |

La fila `pandas, sklearn` sale más rápida que `sklearn` solo, aunque importa más módulos. Eso es
ruido de la medición (±0,2 s entre repeticiones). Tomar ~1,7–1,8 s como costo de importar sklearn.

**Lectura de los números:**

- La RAM no crece con el número de días: cada día es un proceso nuevo y se libera al terminar.
  El pico (~47 MB) es el del día más pesado, no la suma.
- El CLI no carga pandas ni sklearn (§2), así que sus 47 MB son Python más pydantic y los datos del día.
- El tiempo total es lineal en los días: ~0,4 s por día con 1440 muestras.

**Nota sobre la muestra.** Se usó 1 muestra por minuto como cota superior. Si el medidor real muestrea
cada 5 minutos, el número de filas por día baja cinco veces y el tiempo y la RAM también bajan. No se
midió con datos reales (ver §7).

## 5. Variables de configuración

Vienen de `src/infrastructure/settings/config.py` (`pydantic-settings`, lee `.env` y el entorno).
Para `disaggregate` importan estas:

| Variable | Default | Uso |
|---|---|---|
| `MEDICIONES_CSV_DIR` | `data/input` | Carpeta de los CSV diarios `<device-id>_<AAAA-MM-DD>.csv`. **En el VPS poner ruta absoluta.** |
| `LOG_LEVEL` | `INFO` | Nivel de log. |
| `ENVIRONMENT` | `development` | Usar `production` en el VPS. |

Otras variables de `Settings` (`MEDICIONES_SOURCE`, `MEDICIONES_CACHE_DIR`, `RESULTADOS_DIR`,
`MODELOS_DIR`, `NILM_*`) las usan la API y los comandos de entrenamiento; `disaggregate` no las lee,
salvo `MEDICIONES_CSV_DIR`.

Por línea de comandos (sin variable de entorno): `--archivo` reemplaza la ruta del CSV, `--firmas`
apunta al catálogo JSON, `--salida-json` escribe el contrato `nilm.intervalos.v1`, `--fecha` fija el
día (si se omite, es D-1 en Argentina).

## 6. Timer

**Propuesta; no existe todavía en el repo.** `docs/PRODUCCION.md` solo tiene un esqueleto de servicio
de la API. El timer diario de las 03:30 UTC se toma del docstring de `desagregar_cargas.py`: "el timer
de las 03:30 UTC procesa el día que ya cerró". A las 03:30 UTC son las 00:30 de Argentina, así que el
día cerrado es D-1 (por eso `--fecha` se omite).

Unidades systemd propuestas (rutas y medidor de ejemplo; reemplazar por los reales):

`/etc/systemd/system/datamaq-disaggregate.service`

```ini
[Unit]
Description=DataMaq: desagregación batch diaria (nilm.intervalos.v1)

[Service]
Type=oneshot
User=<usuario-de-servicio-no-root>
WorkingDirectory=<ruta-absoluta-al-repo>
Environment="MEDICIONES_CSV_DIR=<ruta-absoluta-a-los-csv>"
Environment="ENVIRONMENT=production"
ExecStart=<ruta-absoluta-al-repo>/.venv/bin/python -m src.infrastructure.cli.desagregar_cargas "<etiqueta-del-medidor>" --device-id <uuid-del-medidor> --salida-json <ruta-absoluta-de-salida>/nilm_ayer.json
```

`/etc/systemd/system/datamaq-disaggregate.timer`

```ini
[Unit]
Description=Dispara la desagregación batch diaria a las 03:30 UTC

[Timer]
OnCalendar=*-*-* 03:30:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

Comandos para habilitarlo (los ejecuta el dueño en `datamaq-vps`, con confirmación):

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now datamaq-disaggregate.timer
systemctl list-timers datamaq-disaggregate.timer
```

El servicio es `oneshot`: si falla, sale con código 2 (argumentos o catálogo) o 3 (CSV ausente o
inválido). Revisar con `journalctl -u datamaq-disaggregate.service`.

## 7. Pendiente antes de instalar en el VPS

1. Repetir §4 con un día real del medidor, en el VPS, con la misma secuencia de 1, 30 y 365 días
   (solo lectura de los CSV que ya estén en el servidor).
2. Confirmar la frecuencia real de muestreo y ajustar la estimación de RAM y tiempo.
3. Crear el timer solo con la confirmación escrita del dueño en `datamaq-vps`.
