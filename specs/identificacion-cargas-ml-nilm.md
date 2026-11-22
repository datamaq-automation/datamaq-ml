# Spec local: Identificación de cargas NILM — bloque `datamaq-ml`

> **Estado:** implementado en `feat/issue-208-fase3-operativa` · **Issue:** `datamaq-automation/datamaq#208` · **Fecha:** 2026-11-21
> **Spec del padre:** `specs/identificacion-cargas-ml-nilm.md` (repo de orquestación). Esta copia es el bloque de `datamaq-ml`.
> **Decisiones aplicables:** `decisions/2026-11-21_desagregacion-nilm-arquitectura-batch-diario.md` (con su adenda del 2026-11-21).

## 1. Objetivo y Contexto

*(Copiado de la sección 1 de la spec del padre. La redacta el padre.)*

Desagregar e identificar las cargas electromecánicas activas detrás de una acometida general o secundario de transformador (TGBT) a partir de telemetría cuatridimensional en baja frecuencia ($P, Q, S, \cos \phi$, cadencia de 300 segundos).

El objetivo operacional es **asignar de manera determinista o probabilística cada intervalo de consumo a una máquina registrada (`MachineModel`)**, permitiendo:
1. Conocer con precisión el estado de disponibilidad del activo (`APAGADA`, `STANDBY`/vacío, `OPERANDO`, `SOBRECARGA`).
2. Acumular horas de marcha efectivas ($P > P_{\text{umbral}}$) en el horómetro digital de cada máquina para habilitar en fases posteriores el mantenimiento predictivo (CBM / ISO 9001).
3. Aislar la carga base inelástica del transformador de la energía productiva de los procesos.

## Repo: datamaq-ml

**Traspasada a hija:** sí · **Bloque cerrado:** sí (desagregación batch diaria operativa; la proyección a horómetros de máquina queda fuera)

## 2. Diseño implementado

Cuatro capas, un commit por capa (ver `git log` de la rama):

| Capa | Qué cambió | Dónde |
|---|---|---|
| Infraestructura SSH | La consulta lee `total_reactive_power` (VAr → kVAr). `NULL` queda en `None`. El cache del VPS guarda `reactiva_kvar`. | `src/infrastructure/ssh/medicion_repository.py` |
| Infraestructura CSV | Columnas opcionales `reactiva_kvar` y `energia_kwh`. `leer_archivo(ruta, desde, hasta)` lee un CSV diario con ventana semiabierta en UTC. Instantes con zona se convierten a UTC. | `src/infrastructure/csv/medicion_repository.py` |
| Dominio | `integrar_trapecios` (función pura, sirve para kWh y kVArh). `Medicion.energia_acumulada_kwh` opcional. | `src/domain/cargas/services.py`, `entities.py` |
| Aplicación | Caso de uso `AtribuirCargasBatchUseCase` con energía medida, cierre en la última medición real, confianza, y salida con el contrato `nilm.intervalos.v1`. | `src/application/cargas/use_cases/atribuir_cargas_batch.py`, `dtos/desagregar_cargas.py` |
| CLI | `disaggregate` con `--device-id`, D-1 en Argentina, ventana UTC del día, códigos de salida y `--salida-json`. Sin conexión a MySQL ni VPS. | `src/infrastructure/cli/desagregar_cargas.py` |

**Decisiones de diseño tomadas (y a confirmar por el padre):**

1. **Base restada.** La energía y la potencia del intervalo son las de la máquina: se resta la potencia de la medición anterior al encendido. Sin esto, cada máquina cargaría con la carga permanente del tablero. Confirmar.
2. **Energía por contador o por trapecios.** Si el CSV trae `energia_kwh`, la energía es la diferencia de contadores entre los bordes del tramo, menos la base por el tiempo. Si no, la integral por trapecios de (P − base). Son dos caminos con el mismo significado; el contador es más preciso.
3. **Tramo termina en la medición apagada.** El error de la integral queda acotado por medio paso de muestreo (2,5 min con datos de 5 min).
4. **Día en UTC-3, ventana en UTC.** El día local es `America/Argentina/Buenos_Aires`. La ventana es `[D 03:00Z, D+1 03:00Z)`. El timer de las 03:30 UTC procesa D-1.
5. **Confianza.** Promedio de `1 − |distancia al nominal| / tolerancia` del encendido y del apagado, en [0, 1].
6. **`load_id` desde el catálogo.** La firma puede traer `load_id`; si no, `null`. ML no inventa identificadores de telemetry.

## 3. Contrato de interfaces

**Entrada (CSV diario por medidor):** `instante,potencia_kw[,reactiva_kvar[,energia_kwh]]`, instantes en UTC, un archivo por `device_id` y día, en `<MEDICIONES_CSV_DIR>/<device-id>_<YYYY-MM-DD>.csv` (o `--archivo`).

**Entrada (catálogo de firmas):** lista JSON de `{machine_id, nombre, potencia_nominal_kw, reactiva_tipica_kvar?, tolerancia_kw?, umbral_marcha_kw?, load_id?}`.

**Salida (`--salida-json`):** contrato `nilm.intervalos.v1`, claves exactas (§5 del informe de datamaq-telemetry):

- Raíz: `contrato`, `generado_en_utc`, `fecha_local`, `zona_horaria`, `ventana_utc{desde,hasta}`, `medidor{device_id,etiqueta_ml,ultima_lectura_utc}`, `cargas[]`.
- `cargas[]`: `load_id` (uuid o `null`), `nombre`, `intervalos[]`.
- `intervalos[]`: `inicio_utc`, `fin_utc`, `horas`, `energia_kwh_medida`, `potencia_media_kw`, `delta_reactiva_kvar` (o `null`), `confianza`, `origen` (`"INFERIDA"`).
- Instantes con `Z`. Clave natural del intervalo: `(device_id, inicio_utc, fin_utc)`.

**Códigos de salida:** `0` ok · `2` argumentos o catálogo inválidos · `3` CSV del día ausente o inválido.

**Mapeo de medidores (configurable por `--device-id`, no hardcodeado):**

- `Trafo arriba` → `a01b1642-ed29-4c3e-a793-f57de09504f8`
- `Trafo abajo` → `ce7e5a9a-c5e8-4936-be9a-a2057ccf8b4c`

## 4. Criterios de aceptación y evidencia

| Criterio | Estado | Evidencia |
|---|---|---|
| Gauntlet de restricciones 11/11 | Cumplido | `./run.sh gauntlet`: 11 APROBADO, exit 0 (en cada commit de la rama) |
| Tests en verde, 0 skipped | Cumplido | `./run.sh test`: 198 passed, 0 skipped (el número previo era 166) |
| Audit sin componentes Dios | Cumplido | `./run.sh audit`: sin componentes Dios |
| Lint y formato | Cumplido | `./run.sh lint`: All checks passed; formato limpio |
| Energía medida, no nominal | Cumplido | Test `test_energia_y_potencia_se_miden_no_se_toman_de_la_nominal` (97,92 kWh sobre 50 kW nominales) |
| Intervalo abierto cerrado en la última medición | Cumplido | Test `test_intervalo_abierto_se_cierra_en_la_ultima_medicion_real_no_a_las_2359` |
| Corte en el límite de la ventana | Cumplido | Test `test_corte_en_el_limite_de_la_ventana_ignora_lo_que_cae_fuera_del_dia` |
| Día sin datos, una sola medición, encendido en la última medición | Cumplido | Tests de borde del caso de uso |
| `--firmas` inexistente falla con código ≠ 0 | Cumplido | `test_firmas_inexistente_falla_con_codigo_2` (código 2) |
| D-1 en zona Argentina | Cumplido | `tests/unit/test_ventana_dia.py` (incluye 23:30 ART) |
| Salida con el contrato v1 | Cumplido | `test_salida_tiene_exactamente_las_claves_del_contrato_v1` y `test_salida_json_tiene_el_contrato_nilm_intervalos_v1` |
| F1 ≥ 0,90 sobre los 4 clusters de motores IEC | **No verificado** | Requiere datos reales calibrados y etiquetados; no se corrió en este bloque |
| Irregularidad de muestreo (Δt > 300 s) sin escalones espurios | Parcial | `integrar_trapecios` usa Δt real por tramo (test de espaciado irregular). El detector de escalones no filtra Δt > 300 s |

## 5. Pendientes, riesgos y decisiones abiertas

**Fuera de este bloque (no se resuelve acá):**

- **Persistencia en telemetry.** La importación idempotente de `nilm.intervalos.v1` la hace datamaq-telemetry (tabla `load_activity_intervals`, clave `(device_id, inicio_utc, fin_utc)`).
- **Proyección a horómetros de máquina** (`machine_availability_events`). Es un paso posterior, cuando una carga se confirme como máquina.
- **Resumen por máquina en el JSON.** Hoy va solo al log. Si telemetry lo necesita, es un cambio de contrato (`contrato_version`).
- **Timer systemd** (`datamaq-nilm.timer`, 03:30 UTC). Lo configura DevOps solo después de mergear esto.

**Riesgos y puntos a confirmar:**

- **Zona del día.** Se usa día argentino en UTC-3. Si el negocio cierra el día en UTC, la ventana cambia. Confirmar con el dueño.
- **`es_dato_confiable` sin escritor** en telemetry (hallazgo de la investigación). El batch no filtra calidad real más allá de ese flag.
- **Base restada**: ver decisión 1 de la sección 2.
- **Umbral fijo por firma.** `umbral_marcha_kw` y la tolerancia vienen del catálogo; no hay umbral automático para el batch.
- **Pyright del hook.** Se reportan símbolos que sí existen (el análisis no ve el código actualizado). Los tests son la verificación; no se modificó la configuración de pyright.
