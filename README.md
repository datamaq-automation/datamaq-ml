# datamaq-ml

Motor de Machine Learning para **Monitoreo No Intrusivo de Cargas (NILM Industrial)** de DataMaq.

A partir del consumo general de un transformador o acometida de planta (TGBT), detecta automáticamente qué equipos se encienden y se apagan, agrupando escalones de potencia ($\Delta P, \Delta Q$) mediante **DBSCAN** y clasificándolos con árboles de decisión CART y aprendizaje en espacio de versiones (*Version Space Learner*).

## Cómo funciona

1. **Datos:** Potencia activa total ($P$) y reactiva ($Q$) en intervalos de 5 minutos (300 segundos).
2. **Eventos:** Detección de escalones $|\Delta P| \ge \text{umbral}$ entre muestras consecutivas (encendidos $\uparrow$ y apagados $\downarrow$).
3. **Clustering:** DBSCAN agrupa los eventos por densidad de potencia. Cada cluster resultante representa una máquina candidata con su potencia típica y firma reactiva.
4. **Asignación y Explicabilidad:** Extracción de reglas conjuntivas y clasificación supervisada para actualizar el catálogo de máquinas inferidas y horómetros digitales.

## Puesta en marcha

Requisitos: Python 3.10 o superior.

```bash
./run.sh install                  # crea .venv y sincroniza dependencias
cp .env.example .env              # opcional: solo para sobreescribir valores por defecto
```

El archivo `.env` es local y **no se versiona**. No pongas secretos en el repo: el acceso a la VPS se configura en `~/.ssh/config`.

## Datos de mediciones

> **Los datos reales no se versionan.** `data/input/` y `data/verdad/` están ignorados por Git,
> salvo el dataset sintético (`sintetico.csv`), que se genera con `./run.sh simulate`.

### Formato del CSV

Un archivo por medidor y día, con instantes en **UTC**:

```
instante,potencia_kw,reactiva_kvar,energia_kwh
2026-09-20T11:00:00,60.0,35.0,1000.25
```

| Columna | Obligatoria | Significado |
|---|---|---|
| `instante` | sí | ISO 8601. Sin zona se toma como UTC; con zona (`-03:00`) se convierte a UTC. |
| `potencia_kw` | sí | Potencia activa total, kW. |
| `reactiva_kvar` | no | Potencia reactiva, kVAr. Vacía o ausente: el discriminador P-Q se degrada a solo P y la reactiva del intervalo es `null`. |
| `energia_kwh` | no | Contador acumulado de energía activa, kWh. Si viene, la energía de cada intervalo es su diferencia; si no, la integral de la potencia. |

Un CSV viejo con solo `instante,potencia_kw` sigue funcionando.

### Medidores: nombre y `device-id`

El **medidor se identifica por `device-id`** (uuid de `devices.id` en datamaq-telemetry). El nombre es solo una etiqueta humana.

El mapeo entre etiqueta y `device-id` vive **fuera del repo** (configuración del despliegue, no versionada). Acá solo se
documenta el formato: `--device-id <uuid-del-medidor>`.

> **Escribí la etiqueta tal como figura en la configuración.** El nombre no identifica el medidor: lo que cuenta es `--device-id`.

## Comandos principales (`run.sh`)

```bash
./run.sh dev          # Servidor FastAPI con reload automático en puerto 8000
./run.sh start prod   # Servidor FastAPI con datos desde la VPS (ver docs/PRODUCCION.md)
./run.sh train        # Identifica las cargas de data/input/ y exporta resultados a data/output/
./run.sh simulate     # Genera tablero simulado con cargas conocidas para benchmarking
./run.sh evaluate     # Evalúa precisión y sensibilidad contra la verdad conocida
./run.sh supervise    # Entrena clasificador supervisado CART
./run.sh disaggregate # Desagrega cargas de un día cerrado y emite el JSON nilm.intervalos.v1
./run.sh test         # Suite completa de pruebas unitarias, de integración, e2e y de arquitectura
./run.sh gauntlet     # 11 reglas de arquitectura (tests/test_architecture.py)
./run.sh audit        # Código muerto y componentes Dios
./run.sh lint         # Estilo y formato con ruff
```

## Desagregación batch diaria (`disaggregate`)

```bash
./run.sh disaggregate "<etiqueta>" --device-id <uuid-del-medidor> \
    --fecha 2026-11-21 --firmas config/firmas.json --salida-json salida/nilm_2026-11-21.json
./run.sh disaggregate "<etiqueta>" --device-id <uuid-del-medidor> \
    --potencia 91.0 --nombre "Compresor 1"
```

### Día y zona horaria

- `--fecha` es un **día de Argentina**: zona `America/Argentina/Buenos_Aires` (UTC-3, sin horario de verano).
- Si se omite, es el **D-1**: el día anterior al que es en Argentina cuando corre el comando. El timer de las 03:30 UTC (00:30 ART) procesa así el día que ya cerró.
- La ventana del día es **semiabierta y en UTC**: `[D 03:00Z, D+1 03:00Z)`. Las mediciones fuera de esa ventana se descartan.

### Opciones

| Opción | Qué hace |
|---|---|
| `medidor` (posicional) | Etiqueta humana (por ejemplo `"Trafo 1"`). No identifica el medidor. |
| `--device-id` (obligatoria) | uuid del medidor en telemetry. Ver la tabla de arriba. |
| `--fecha YYYY-MM-DD` | Día local a procesar. Por defecto, D-1. |
| `--archivo RUTA` | CSV diario del medidor. Por defecto: `<MEDICIONES_CSV_DIR>/<device-id>_<fecha>.csv`. |
| `--firmas ARCHIVO.json` | Catálogo de firmas confirmadas (ver abajo). |
| `--potencia`, `--reactiva`, `--nombre`, `--machine-id` | Firma rápida para una sola carga, sin archivo. |
| `--salida-json RUTA` | Escribe la salida `nilm.intervalos.v1` (ver abajo). |

### Catálogo de firmas (`--firmas`)

Lista de objetos. Solo `machine_id`, `nombre` y `potencia_nominal_kw` son obligatorios:

```json
[
  {
    "machine_id": "bomba-2",
    "nombre": "Bomba 2",
    "potencia_nominal_kw": 37.0,
    "reactiva_tipica_kvar": 40.0,
    "tolerancia_kw": 5.0,
    "umbral_marcha_kw": 1.0,
    "load_id": "11111111-1111-1111-1111-111111111111"
  }
]
```

`load_id` es el uuid de `loads.id` en telemetry, si la carga ya está mapeada. Si no, va `null`. `machine_id` es un identificador interno del catálogo y no sale en el JSON.

### Cómo se miden energía, potencia y reactiva

Son **magnitudes medidas**, no la potencia nominal de la firma:

- **Tramo del intervalo:** desde la primera medición en marcha hasta la primera medición apagada. Si la máquina sigue en marcha al final del día, el tramo termina en la **última medición real** del día. Nunca se extiende a una hora inventada.
- **Carga base:** se resta la potencia de la medición anterior al encendido. Así no se atribuye a la máquina la carga permanente del tablero.
- **Energía (`energia_kwh_medida`):**
  - si el CSV trae `energia_kwh`, es la **diferencia del contador** entre los dos bordes del tramo, menos la base por el tiempo;
  - si no, es la **integral por trapecios** de la potencia menos la base (versión 1).
  La decisión se toma por intervalo: si falta el contador en alguno de los dos bordes del tramo, ese intervalo usa la integral.
  El error de la integral queda acotado por medio paso de muestreo (2,5 min con datos de 5 min).
- **Potencia media (`potencia_media_kw`):** energía dividida por horas.
- **Reactiva (`delta_reactiva_kvar`):** reactiva media del tramo menos la base. `null` si el CSV no trae reactiva.
- **Confianza (`confianza`, en [0, 1]):** promedio de qué tan cerca de la potencia nominal estuvieron el encendido y el apagado. 1 es un salto exacto; 0 es el borde de la tolerancia.

### Salida JSON (`--salida-json`): contrato `nilm.intervalos.v1`

Formato acordado con datamaq-telemetry (informe de la investigación de la Fase 3, §5). Las claves son exactas.

```json
{
  "contrato": "nilm.intervalos.v1",
  "generado_en_utc": "2026-11-22T03:30:12Z",
  "fecha_local": "2026-11-21",
  "zona_horaria": "America/Argentina/Buenos_Aires",
  "ventana_utc": { "desde": "2026-11-21T03:00:00Z", "hasta": "2026-11-22T03:00:00Z" },
  "medidor": {
    "device_id": "<uuid-del-medidor>",
    "etiqueta_ml": "<etiqueta>",
    "ultima_lectura_utc": "2026-11-21T23:55:00Z"
  },
  "cargas": [
    {
      "load_id": "11111111-1111-1111-1111-111111111111",
      "nombre": "Bomba 2",
      "intervalos": [
        {
          "inicio_utc": "2026-11-21T13:02:00Z",
          "fin_utc": "2026-11-21T14:17:30Z",
          "horas": 1.2583,
          "energia_kwh_medida": 318.4,
          "potencia_media_kw": 253.1,
          "delta_reactiva_kvar": 41.2,
          "confianza": 0.91,
          "origen": "INFERIDA"
        }
      ]
    }
  ]
}
```

- Todos los instantes llevan `Z` (UTC). `origen` es siempre `"INFERIDA"`.
- `cargas` incluye todas las firmas del catálogo, también las que no tuvieron intervalos (con `intervalos: []`).
- `ultima_lectura_utc` es `null` si el día no tuvo mediciones.
- La clave natural de un intervalo es `(device_id, inicio_utc, fin_utc)`.
- **No sale en el JSON:** el resumen por máquina (horas, ciclos, energía totales). Va al log, una línea por carga.

### Códigos de salida

| Código | Significado |
|---|---|
| `0` | Desagregación completada. Puede haber cero intervalos si el día no tuvo marchas. |
| `2` | Argumentos o catálogo inválidos: `--device-id` no es uuid, `--firmas` no existe o no es válido, o no hay firmas (ni `--firmas` ni `--potencia`). |
| `3` | Datos faltantes o inválidos: no existe el CSV del día, o el CSV no se puede leer. |

### Lo que este comando todavía no hace

- **No persiste** nada en telemetry: escribe el JSON y el log. La importación idempotente la hace datamaq-telemetry.
- **No se conecta** a MySQL ni al VPS. Los CSV diarios los genera un script de telemetry.
- **No proyecta** a `machine_availability_events` (horómetros de máquina): es un paso posterior, cuando una carga se confirme como máquina.

## Validación de un día sin verdad de terreno

`scripts/validar_dia_real.py` corre la desagregación sobre un día y escribe métricas **agregadas**
(conteos, energías, porcentajes, horas por carga). No escribe filas de mediciones, así que su salida
es segura de compartir aunque el CSV de entrada no lo sea.

```bash
./.venv/bin/python scripts/validar_dia_real.py --archivo <CSV diario> --firmas <catálogo.json> \
    --fecha 2026-09-20 --salida-json <ruta.json>
```

Métricas principales:

| Métrica | Qué mide |
|---|---|
| `eventos`, `encendidos`, `apagados` | Escalones de potencia detectados con el umbral del catálogo |
| `eventos_atribuidos`, `eventos_sin_atribuir` | Escalones explicados por una firma y los que no |
| `intervalos_cerrados` / `_abiertos` / `_cortados_por_caida` | Cómo terminó cada intervalo: por apagado de la misma firma, al final del día, o por un escalón ajeno |
| `energia_medida_kwh` | Integral de P sobre el día (trapecios) |
| `energia_atribuida_kwh`, `pct_energia_atribuida` | Energía de las cargas del catálogo y su parte del total |
| `energia_atribuida_excede_medida` | Control de plausibilidad: debe ser `false` |
| `solapamientos`, `horas_solapadas` | Pares de intervalos de cargas distintas que se superponen |
| `huecos_mayores_a_5_min` | Muestreo irregular: afecta la integral |

Límites: sin reactiva (solo P) no se separan cargas de igual potencia activa; con muestras cada 5 min,
los escalones menores a un paso de muestreo no se ven; sin verdad de terreno no se mide la exactitud,
solo la consistencia.

## Uso docente

Material para el módulo «Procesamiento de Aprendizaje Automático»: `docs/material-ensenanza/` (índice en su
`README.md`, mapa de contenidos, ejercicios por bloque, práctica k-medias frente a DBSCAN, rúbrica y caso de estudio).

**Regenerar los datos sintéticos** (lo único que se usa con estudiantes hasta contar con consentimiento):

```bash
./run.sh install
./run.sh simulate        # data/input/sintetico.csv y data/verdad/sintetico.csv
```

**Datos reales anonimizados: cómo se entregan.** No se entregan a estudiantes sin el consentimiento escrito de la
empresa. Cuando lo haya, el dueño los seudonimiza con `scripts/seudonimizar_mediciones.py`: reemplaza el nombre de la
empresa y los identificadores de medidor, y verifica que instantes y potencias queden idénticos. La salida va a una
carpeta fuera de git (el script se niega a escribir dentro de un repo) y se entrega por fuera del repo.

**No redistribuir.** Los datos reales anonimizados son del cliente. Quien los reciba no los copia, no los publica y no los
sube a ningún servicio. Las guías con respuestas (`docs/guia-docente.md`) no se publican a estudiantes.

## Configuración

Las variables están centralizadas en `src/infrastructure/settings/config.py` con valores por defecto.
`.env.example` documenta las que suelen cambiar. `MEDICIONES_CSV_DIR` define la carpeta de los CSV diarios.

## Arquitectura

Implementado bajo **Clean Architecture** estricta:
- `src/domain/cargas/`: Entidades puras, reglas de negocio, integración por trapecios, simulación y Version Space Learner.
- `src/application/cargas/`: Casos de uso de identificación, inducción de reglas, desagregación batch y DTOs fuertemente tipados (incluido el contrato `nilm.intervalos.v1`).
- `src/infrastructure/`: Scikit-learn (DBSCAN, CART, Naive Bayes, KNN), FastAPI REST endpoints, repositorios CSV y SSH, y CLI.

Documentación de producción (modo SSH, VPS, systemd): `docs/PRODUCCION.md`.
Especificación del pipeline NILM: `specs/identificacion-cargas-ml-nilm.md`.
