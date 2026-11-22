# SRS-SPECS: datamaq-ml (Identificación de Cargas NILM) — Single Source of Truth (SSOT) & Especificación del Sistema

> **Documento:** `srs-spec-ml.md`
> **Versión:** `1.0.0`
> **Estado:** `borrador en revisión`
> **Fecha:** `2026-11-22`
> **Autor(es):** Dueño del proyecto, con redacción asistida por la sesión hija de `datamaq-ml` (Claude Code).
> **Repositorio / Módulo:** `datamaq-automation/datamaq-ml`

> 💡 **Acompañamiento Pedagógico:** Antes de completar o revisar esta especificación, se recomienda consultar la [Guía de Andamiaje Pedagógico y Metacognición](./guia-andamiaje-proyectos.md) para reflexionar sobre los problemas de negocio, casos de borde y evitar la sobreingeniería.

> **Convención de este documento.** Las referencias `decisions/` y `specs/` apuntan al repo padre `datamaq` (no a este repo). Cada afirmación técnica cita el archivo que la respalda. Lo que la plantilla pide y el repo no tiene se marca como **brecha** (§6), no se afirma. Lo que depende de una decisión del negocio figura como **A definir por el dueño**.

---

## 1. Contexto Estratégico & Propuesta de Valor

### 1.1. Foco Estratégico & Alcance
* **Problema que resuelve:** identificar qué cargas electromecánicas (motores, bombas, cintas) están en marcha detrás de la acometida o del TGBT de una planta industrial, a partir de la potencia medida en ese punto (NILM: *Non-Intrusive Load Monitoring*). El objetivo derivado es atribuir horas de marcha a cada carga. Fuente: `specs/identificacion-cargas-ml-nilm.md` §1 (repo padre), `decisions/2026-11-21_priorizacion-identificacion-cargas-ml-antes-de-cbm.md` §1.
* **Consumidor del resultado:** `datamaq-telemetry`, que importa el JSON del batch por el contrato `nilm.intervalos.v1` (`src/application/cargas/dtos/desagregar_cargas.py`, constante `CONTRATO_INTERVALOS`). Este repo no escribe en la base de datos de producción: `disaggregate` lee CSV y escribe JSON (`src/infrastructure/cli/desagregar_cargas.py`, docstring).
* **Uso como material de enseñanza:** módulo docente con tablero simulado y guía para alumnos (`docs/material-ensenanza/`, `docs/cuaderno-alumno.md`, ruta `/guia` en `src/main.py`). Los datos reales no se entregan a estudiantes: ver la decisión `decisions/2026-11-22_datamaq-ml-material-de-ensenanza-con-datos-reales-anonimizados.md`.
* **Mercado Objetivo:** plantas industriales con telemetría eléctrica en TGBT o acometida. Segmento comercial: **A definir por el dueño**.
* **Buyer Persona (Decisor / Cliente Ideal):** **A definir por el dueño.**
* **User Persona (Operador / Usuario Final):** **A definir por el dueño.** Usuarios técnicos actuales: el dueño y las sesiones de desarrollo (ver `AGENTS.md`).
* **Alcance Geográfico & Modalidad:** batch diario sobre CSV locales o descargados por SSH desde el VPS de producción; API FastAPI local (`run.sh start`, escucha en `0.0.0.0`; puerto 8000 por defecto, y el siguiente libre si está ocupado: `resolve_port` en `run.sh`). Despliegue en VPS como batch programado: **propuesta** documentada en `docs/despliegue-vps.md` §6, no ejecutada.
* **Fuera de Alcance (*Out of Scope*):**
  1. **Cadencia de muestreo distinta de 300 s.** La telemetría vigente muestrea cada 5 min (`decisions/2026-11-21_desagregacion-nilm-arquitectura-batch-diario.md`, adenda 2026-11-21, punto 4 y adenda 2026-11-22). No hay validación con otra cadencia.
  2. **Banco de capacitores automático.** El dueño confirmó el banco **fijo** el 2026-11-22; un banco con conmutación frecuente fue descartado por la validación (misma decisión, adenda 2026-11-22, última sección).
  3. **Identificación de cargas individuales pequeñas.** **Pendiente de confirmar por el dueño:** no aparece en `decisions/` ni en `specs/` del repo padre. El código solo fija un piso de 0,1 kW en el umbral de marcha (`src/application/cargas/use_cases/atribuir_cargas_batch.py`, `umbral_minimo_kw`), sin una decisión que lo justifique.
  4. **Mantenimiento basado en condición (CBM / GMAO / Órdenes de Trabajo) y horómetros de máquina en el HMI.** Postergados hasta validar la desagregación (`decisions/2026-11-21_priorizacion-identificacion-cargas-ml-antes-de-cbm.md` §2.1). La proyección a `machine_availability_events` queda fuera de este repo (`decisions/2026-11-21_desagregacion-nilm-arquitectura-batch-diario.md`, adenda 2026-11-21, punto 1).
  5. **Ejecución como daemon HTTP persistente en producción.** Decidido en contra: el proceso corre por timer diario (`decisions/2026-11-21_desagregacion-nilm-arquitectura-batch-diario.md` §2.1).
  6. **Acceso de escritura a la base de datos de producción.** `datamaq-ml` no escribe en MySQL; la importación la hace `datamaq-telemetry` (misma decisión, adenda 2026-11-21, punto 2).

### 1.2. Pilares de Valor de la Solución
| Pilar | Enfoque | Implementación en este Sistema |
| :--- | :--- | :--- |
| **1. Activos & Entorno Operativo** | Infraestructura física, dispositivos, hardware o fuentes de datos base. | Medidor de acometida o TGBT con muestreo de 300 s (`decisions/2026-11-21_desagregacion-nilm-arquitectura-batch-diario.md`). Entrada: CSV diario `<device-id>_<AAAA-MM-DD>.csv` (`src/infrastructure/csv/medicion_repository.py`) o lectura por SSH de solo lectura (`src/infrastructure/ssh/medicion_repository.py`). |
| **2. Software & Lógica de Negocio** | Captura, procesamiento en tiempo real, persistencia y APIs. | Motor de detección de escalones ΔP, emparejamiento por firmas con pesos de P y Q, banco de capacitores tratado aparte (`src/domain/cargas/`, `src/application/cargas/use_cases/`). Batch diario por CLI (`disaggregate`) y API FastAPI (`src/main.py`). Sin persistencia propia: salidas en JSON y CSV. |
| **3. Impacto Económico & ROI** | Optimización de costos, generación de ingresos o eficiencia operativa. | **A definir por el dueño.** No hay análisis económico en este repo. |

### 1.3. Coordinación Operativa, Roles & Seguridad
* **Liderazgo Técnico / Responsable:** **A definir por el dueño.** Operación de sesiones: el repo padre define una sesión de orquestación y una sesión hija por repo; las publicaciones a `main` y los despliegues los ejecuta el dueño (`AGENTS.md` del repo padre `datamaq`, §1, tabla «Quién decide qué»).
* **Ventanas Operativas & Disponibilidad:** batch diario a las 03:30 UTC (00:30 hora de Argentina), procesando el día anterior (D-1) (`src/infrastructure/cli/desagregar_cargas.py`, docstring; `decisions/2026-11-21_desagregacion-nilm-arquitectura-batch-diario.md` §2.1). Esta ventana es una propuesta: el timer no existe todavía en el repo (`docs/despliegue-vps.md` §6).
* **Habilitaciones, Normativas & Seguridad:** no hay certificación normativa definida en el repo. Requisitos de seguridad vigentes: credenciales fuera del repo (`.gitignore`: `.env`, `.env.*`; `.env.example` sin valores), lectura de la base solo por SSH con una única sentencia SELECT (`tests/unit/test_exportar_dias_ssh.py`), y exportaciones fuera de git con permisos 0700 y archivos 0600 (`src/infrastructure/cli/exportar_dias_ssh.py`). Datos de clientes: no se versionan; la salida de validación solo contiene agregados (`src/infrastructure/cli/validar_dia_real.py`, docstring).

---

## 2. Modelo de Negocio Canvas (BMC de 9 Bloques) & Gobernanza

### 2.1. Matriz del Business Model Canvas
Los bloques de negocio no están definidos en el repo. La columna de software describe lo que existe.

| Bloque Canvas | Definición Estratégica | Componentes Clave en el Software |
| :--- | :--- | :--- |
| **1. Socios Clave (KP)** | **A definir por el dueño.** | Consumidor del contrato: `datamaq-telemetry` (`nilm.intervalos.v1`). Fuente de datos: VPS de producción por SSH (`src/infrastructure/ssh/medicion_repository.py`). |
| **2. Actividades Clave (KA)** | **A definir por el dueño.** | Batch diario `disaggregate`; entrenamiento `train`; evaluación `evaluate`; validación sin verdad de terreno `validar_dia_real` (`scripts/`, `run.sh`). |
| **3. Recursos Clave (KR)** | **A definir por el dueño.** | Catálogo de firmas confirmadas (JSON, `--firmas`), modelos serializados con joblib (`MODELOS_DIR`, `data/models/`). |
| **4. Propuesta de Valor (VP)** | **A definir por el dueño.** | Horas de marcha por carga inferidas desde la acometida (`IntervaloMarchaDTO`, `src/application/cargas/dtos/desagregar_cargas.py`). |
| **5. Relación con Clientes (CR)** | **A definir por el dueño.** | No hay notificaciones ni alertas en el código. |
| **6. Canales de Distribución (CH)** | **A definir por el dueño.** | API REST (`/api/v1/...`), CLI (`run.sh`), JSON de salida. |
| **7. Segmentos de Clientes (CS)** | **A definir por el dueño.** | No hay control de roles. Ver brecha de autorización en §6. |
| **8. Estructura de Costos (CS)** | **A definir por el dueño.** | Costo de cómputo del batch medido: 0,4 s y 47 MB por día (`docs/despliegue-vps.md` §4). |
| **9. Fuentes de Ingresos (RS)** | **A definir por el dueño.** | No hay facturación en el repo. |

### 2.2. Organigrama Operativo / Gobernanza de Agentes IA
Gobernanza real del trabajo en este repo, según `AGENTS.md`:
* **Sesión padre (orquestación):** decide y despacha; no ejecuta código de subrepos (`AGENTS.md` del repo padre, §2). Este repo es un subrepo de producto y no contiene la orquestación.
* **Sesión hija de `datamaq-ml`:** implementa en su rama temática y abre PR hacia `develop` con el gauntlet local en verde (`AGENTS.md` del repo padre, §1 y §5).
* **Dueño:** decide merges a `main`, despliegues y acceso a datos reales (`AGENTS.md` del repo padre, §1).

### 2.3. Escalera de Valor / Modelo de Conversión
* **Nivel de Entrada:** **A definir por el dueño.** Hoy existe el tablero simulado (`src/infrastructure/cli/simular_tablero.py`) y la guía docente (`/guia`).
* **Servicio Core:** **A definir por el dueño.** Hoy: batch diario de desagregación y validación.
* **Nivel Avanzado:** **A definir por el dueño.**

---

## 3. Especificación de Requisitos de Software (SRS)

### 3.1. Requisitos Funcionales (FR)

Cada FR se corresponde con código existente. Los requisitos genéricos de la plantilla que el repo no cumple (autenticación, persistencia propia, eventos, anti-abuso) están en §6, no aquí.

* **FR-01 - Ingesta de mediciones desde CSV:** el sistema debe leer lecturas `instante, potencia_kw[, reactiva_kvar[, energia_kwh]]` de un CSV por medidor y día, con instantes UTC sin zona y validación por DTOs Pydantic. Fuente: `src/infrastructure/csv/medicion_repository.py`; ruta por defecto `<MEDICIONES_CSV_DIR>/<device-id>_<fecha>.csv` en `src/infrastructure/cli/desagregar_cargas.py`.
* **FR-02 - Extracción de lecturas por SSH en solo lectura:** el sistema debe descargar las lecturas de un medidor desde la base del VPS con una única sentencia SELECT. El adaptador rechaza cualquier texto con `;` o que no empiece por `SELECT` antes de conectarse (`ejecutar_consulta_de_lectura`, `src/infrastructure/ssh/medicion_repository.py`; prueba `test_el_adaptador_rechaza_cualquier_cosa_que_no_sea_un_select` en `tests/unit/test_exportar_dias_ssh.py`). El identificador del medidor debe ser un UUID canónico, validado antes de armar la consulta (`consulta_dia`, `src/infrastructure/cli/exportar_dias_ssh.py`).
* **FR-03 - Exportación diaria desde el VPS con guardas:** el CLI `scripts/exportar_dias_ssh.py` exporta días por medidor con tope de filas (5000 por defecto) y sale con código 3 si un día supera el tope, sin escribir ese día. Rechaza directorios dentro de un repositorio git y crea el directorio con permisos 0700 (`preparar_salida`).
* **FR-04 - Simulación de un tablero con cargas conocidas:** el sistema debe generar mediciones sintéticas de un tablero con cargas de verdad conocida, con banco de capacitores fijo o automático (`simular_tablero_con_reactiva`, `BANCO_FIJO`, `BANCO_AUTOMATICO`, `src/domain/cargas/simulacion.py`; CLI `run.sh simulate`).
* **FR-05 - Entrenamiento de clasificadores:** el sistema debe entrenar clasificadores de firmas de cargas (árbol de decisión, Bayes, KNN) y serializarlos (`src/application/cargas/use_cases/entrenar_clasificador.py`, `src/infrastructure/sklearn/`; CLI `run.sh train` y `run.sh supervise`).
* **FR-06 - Evaluación contra verdad conocida:** el sistema debe comparar lo identificado con la verdad de un medidor simulado y publicar métricas (`evaluar_identificacion`, `src/application/cargas/use_cases/evaluar_identificacion.py`; CLI `run.sh evaluate`; endpoint `GET /api/v1/metrics`, `src/infrastructure/fastapi/routers/clasificar.py`).
* **FR-07 - Desagregación batch diaria:** el comando `run.sh disaggregate` debe procesar un día local de Argentina con la ventana UTC `[D 03:00Z, D+1 03:00Z)` (`ventana_utc_del_dia`, `src/infrastructure/cli/desagregar_cargas.py`). Sin `--fecha` procesa D-1 (`dia_local_anterior`). Detecta escalones |ΔP| sobre el umbral mínimo de las firmas, los empareja con las firmas confirmadas y calcula horas de marcha y energía por carga (`AtribuirCargasBatchUseCase`, `src/application/cargas/use_cases/atribuir_cargas_batch.py`).
* **FR-08 - Contrato de salida `nilm.intervalos.v1`:** la salida JSON debe tener `contrato = "nilm.intervalos.v1"` y solo las claves del contrato. El test `test_salida_tiene_exactamente_las_claves_del_contrato_v1` (`tests/unit/cargas/test_atribuir_cargas_batch.py`) las fija. Cada intervalo lleva `origen = "INFERIDA"` (`IntervaloMarchaDTO`) y los instantes en UTC con sufijo `Z` (verificado en el JSON generado por el batch, 20 instantes con `Z` y ninguno con `+00:00`). Los DTO no tienen `extra="forbid"`: la garantía de claves es el test, no Pydantic.
* **FR-09 - Atribución con pesos de P y Q:** el emparejamiento de un escalón con una firma usa la distancia ponderada `√((peso_p·ΔP)² + (peso_q·ΔQ)²)`. Los pesos son configurables y valen 1,0 por defecto (`ParametrosBancoDTO`, `src/application/cargas/dtos/desagregar_cargas.py`; `buscar_firma_compatible`, `atribuir_cargas_batch.py`). El peso de Q puede ponerse en 0, y entonces el emparejamiento usa solo P (prueba `test_peso_de_q_en_cero_equivale_a_usar_solo_p`).
* **FR-10 - Tratamiento del banco de capacitores:** las conmutaciones de banco (|ΔP| < 1,5 kW y |ΔQ| ≥ 10 kvar) se detectan y se excluyen de la atribución a cargas. Una ΔQ que coincide con una conmutación dentro de 5 min se marca como no confiable y no se usa para el emparejamiento (`src/domain/cargas/banco_capacitores.py`, constantes `UMBRAL_P_BANCO_KW`, `UMBRAL_Q_BANCO_KVAR`, `TOLERANCIA_COINCIDENCIA`). Base: el banco es fijo (decisión del dueño, 2026-11-22).
* **FR-11 - Calidad de día:** la validación marca un día como de calidad baja cuando tiene más huecos de muestreo mayores a 5 min que un umbral (`UMBRAL_HUECOS_CALIDAD = 10`, editable con `--umbral-huecos`). La marca va en la salida de `validar_dia_real`, **no** en el contrato v1 (`src/application/cargas/use_cases/validar_desagregacion.py`, `src/infrastructure/cli/validar_dia_real.py`).
* **FR-12 - Validación de un día sin verdad de terreno:** el CLI `validar_dia_real` debe calcular métricas de un día (eventos, intervalos cerrados, abiertos y cortados, energía atribuida frente a medida, solapamientos, huecos, eventos de banco) y escribir solo agregados en JSON. Los argumentos `--archivo`, `--firmas`, `--fecha` y `--salida-json` son obligatorios (`src/infrastructure/cli/validar_dia_real.py`).
* **FR-13 - Tolerancia por dispersión y filtro de picos (modo opcional):** el motor puede (a) descartar pares encendido–apagado de una sola lectura (`muestras_debounce`, default 1) y (b) calcular la tolerancia de cada firma desde su dispersión medida, acotada entre 2 y 8 kW (`tolerancia_por_dispersion`, default apagado). Ambos modos están **apagados por defecto** (`ParametrosMotorDTO`, `src/application/cargas/dtos/desagregar_cargas.py`).
* **FR-14 - Fusión de grupos que son la misma máquina (solo evaluación):** la validación cuenta pares de grupos que se superponen de forma sistemática y los solapamientos que quedan tras fusionarlos. No cambia la energía ni la atribución (`candidatos_a_fusion`, `src/application/cargas/use_cases/validar_desagregacion.py`).
* **FR-15 - Máquinas inferidas por dispositivo:** `GET /api/v1/dispositivos/{dispositivo_id}/maquinas/inferidas` devuelve las cargas detectadas por NILM para un dispositivo (`src/infrastructure/fastapi/routers/maquinas_inferidas.py`). La respuesta sale de una caché LRU de 128 entradas, actualizada por cron a las 3:30 UTC (`src/infrastructure/cache/maquinas_cache.py`, docstring).
* **FR-16 - Servidor MCP local:** `POST /api/v1/mcp` atiende JSON-RPC 2.0 con herramientas locales para consultar el modelo (`servidor_mcp`, `src/infrastructure/fastapi/routers/clasificar.py`; caso de uso `src/application/cargas/use_cases/servidor_mcp.py`).
* **FR-17 - Explicabilidad:** `GET /api/v1/explain/tree` devuelve la explicación del árbol clasificador (`src/infrastructure/fastapi/routers/clasificar.py`; caso de uso `explicar_arbol`).
* **FR-18 - Seudonimización de mediciones para material docente:** el CLI `seudonimizar_mediciones` reemplaza el nombre de la empresa y de los medidores, verifica fila por fila que instantes y potencias no cambien, y se niega a escribir dentro de un repositorio git (`src/infrastructure/cli/seudonimizar_mediciones.py`; prueba `tests/unit/test_seudonimizar_mediciones.py`).
* **FR-19 - Interfaz web estática:** el sistema sirve la página de energía (`/`), la guía docente de alumnos (`/guia`) y el cuaderno del alumno en Markdown (`/guia/cuaderno-alumno.md`) desde `web/` y `docs/` (`src/main.py`). La guía docente no se publica: el propio `src/main.py` lo indica.

### 3.2. Requisitos No Funcionales (NFR)

* **NFR-01 - Latencia y Rendimiento de la API:** **No definido ni medido.** No hay objetivo de latencia p95 para ningún endpoint ni prueba de carga en el repo. Ver brecha §6.
* **NFR-02 - Rendimiento del batch diario:** procesar un día de un medidor con 1 muestra por minuto (1440 muestras) tarda **0,4 s** en promedio, con **47 MB** de RAM residente en el pico. Medido sobre 365 corridas sintéticas, una por día, con Python 3.14 en la máquina de desarrollo (`docs/despliegue-vps.md` §4). La medición en el VPS con un día real está pendiente.
* **NFR-03 - Escalabilidad del batch:** el consumo de RAM no crece con el número de días, porque cada día corre en un proceso propio. Un año de corridas tarda 156,6 s en total en la máquina de desarrollo (`docs/despliegue-vps.md` §4).
* **NFR-04 - Huella de instalación:** venv de producción de **294 MB** con `requirements.txt` en Python 3.10.20 (`docs/despliegue-vps.md` §3). El venv de desarrollo, con dependencias de pruebas, ocupa 451 MB.
* **NFR-05 - Versión mínima de Python:** **Python 3.10** (`pyproject.toml`: `requires-python = ">=3.10"`). Verificado: la suite completa pasa con 3.10.20 en un venv limpio (`docs/despliegue-vps.md` §1). La CI usa 3.12 (`.github/workflows/ci.yml`).
* **NFR-06 - Disponibilidad & Resiliencia:** **No definido.** El batch es un proceso que corre una vez por día. Si falla, no reintenta ni alerta: el timer con `Persistent=true` (propuesto en `docs/despliegue-vps.md` §6) recupera la ejecución perdida, pero no existe todavía. Ver brecha §6.
* **NFR-07 - Seguridad y Cifrado:** los secretos viven fuera del repo: `.env` está ignorado por `.gitignore`, `.env.example` no tiene valores reales (`.env.example`), y el acceso al VPS va en `~/.ssh/config` (comentario de `.env.example`). La prueba `test_no_hardcoded_secrets` del guantelete los detecta en el código (`tests/test_architecture.py`). **Cifrado en tránsito (TLS) no implementado:** `run.sh start` sirve HTTP plano (brecha §6).
* **NFR-08 - Privacidad de datos:** no se versionan datos de medidores. Los guardas de exportación y seudonimización (FR-03, FR-18) y la salida solo con agregados de `validar_dia_real` (FR-12) están cubiertos por pruebas.
* **NFR-09 - Conformidad Arquitectónica:** el guantelete de 11 baterías pasa en cada PR en la CI (`tests/test_architecture.py`; `run.sh gauntlet`; `.github/workflows/ci.yml`, paso «Restricciones arquitectónicas (gauntlet)»).

---

## 4. Stack Tecnológico, Arquitectura Limpia & Convenciones (CONVENTIONS)

### 4.1. Stack Tecnológico Base

Declarado en `requirements.txt` y `requirements-dev.txt`; versiones instaladas en el venv de desarrollo medidas el 2026-11-22.

| Componente | Declarado | Versión instalada (dev) | Uso real |
| :--- | :--- | :--- | :--- |
| Python | `>=3.10` (`pyproject.toml`) | 3.14.8 (dev), 3.10.20 (producción medida) | Lenguaje. |
| FastAPI | `>=0.115.0` | — | API REST y HTML estático (`src/main.py`). |
| uvicorn[standard] | `>=0.31.0` | — | Servidor ASGI (`run.sh start`). También da el formateador de logs (`src/infrastructure/settings/logger.py`). |
| Pydantic | `>=2.9.0` | — | DTO de todos los casos de uso (`src/application/cargas/dtos/`). |
| pydantic-settings | `>=2.5.0` | — | Configuración (`src/infrastructure/settings/config.py`). |
| scikit-learn | `>=1.5` | 1.9.1 | Árbol, Bayes, KNN, DBSCAN (`src/infrastructure/sklearn/`). |
| pandas | `>=2.1` | 3.1.1 | Lectura de datos en entrenamiento y evaluación. |
| joblib | `>=1.3` | — | Serialización de modelos (`MODELOS_DIR`). |
| pytest | `>=8.3.0` (dev) | — | Suite de pruebas. |
| pytest-asyncio | `>=0.24.0` (dev) | — | Declarado; no hay pruebas asíncronas en `tests/` que lo necesiten. |
| httpx2 | `>=2.13.1` (dev) | — | Cliente de pruebas que usa `TestClient` (`tests/conftest.py`). |
| ruff | `>=0.6.0` (dev) | — | Linter y formato (`run.sh lint`; `[tool.ruff]` en `pyproject.toml`, `target-version = "py310"`). |

* **Arquitectura:** Clean Architecture por capas, con *Screaming DDD* en `domain/cargas` y `application/cargas` (`src/`). Ver §4.4 para las reglas que se cumplen.
* **Persistencia:** ninguna propia. Entrada en CSV, catálogos en JSON, modelos en joblib (`data/models/`), salidas en JSON. No hay ORM ni driver de base de datos en `src/`.
* **Broker de mensajería:** ninguno.

### 4.2. Estructura Real de Directorios

Según `git ls-files` del repo (branch `develop`). Se omite el material docente detallado (`docs/material-ensenanza/`).

```
.
├── .env.example                         # Plantilla sin valores reales (solo claves y valores por defecto)
├── .gitignore                           # Ignora .env, .env.*, .venv, data/input (salvo sintético), *.log
├── .github/workflows/ci.yml             # CI en runner propio (etiquetas self-hosted, linux, datamaq-ci)
├── AGENTS.md                            # Rol, arquitectura y comandos del repo (3 secciones)
├── README.md                            # Uso de CLI, formato de datos, limitaciones físicas
├── pyproject.toml                       # Metadatos, requires-python, configuración de pytest y ruff
├── requirements.txt / requirements-dev.txt
├── run.sh                               # Orquestador: install, test, gauntlet, audit, lint, train, disaggregate…
│
├── data/                                # Datos locales (no versionados salvo sintéticos)
│   ├── input/                           # CSV de mediciones (sintetico.csv versionado)
│   ├── verdad/                          # Verdad conocida de los medidores simulados (sintetico.csv)
│   ├── models/ output/ prod-cache/      # Modelos, resultados y caché de SSH (solo .gitkeep)
│
├── docs/                                # PRODUCCION.md, despliegue-vps.md, guías docentes, esta especificación
├── scripts/                             # Envoltorios que agregan la raíz al sys.path y llaman a main()
├── specs/                               # Especificación técnica local (identificacion-cargas-ml-nilm.md)
├── web/                                 # HTML, CSS y JS estáticos (energia, guia, maquinas-*)
│
├── src/
│   ├── main.py                          # Entrypoint ASGI: app = create_app(); python -m src.main
│   ├── adapters/                        # VACÍO: solo __init__.py (ver brecha §6)
│   ├── application/cargas/
│   │   ├── dtos/                        # DTO Pydantic de entrada y salida
│   │   └── use_cases/                   # Casos de uso: atribuir_cargas_batch, validar_desagregacion, identificar_cargas…
│   ├── domain/cargas/                   # Entidades, servicios (detectar_eventos, integrar_trapecios), banco_capacitores,
│   │                                    # simulacion, evaluacion, supervisado, reglas, version_space_learner
│   └── infrastructure/
│       ├── cache/                       # Caché LRU de máquinas inferidas
│       ├── cli/                         # 8 CLI con main(): desagregar, validar, exportar, seudonimizar, entrenar, evaluar, simular, supervisar
│       ├── csv/                         # Repositorios CSV de mediciones, verdad y cargas
│       ├── fastapi/                     # Routers (cargas, clasificar, maquinas_inferidas, mediciones), dependencies, lifespan
│       ├── settings/                    # config.py (Settings) y logger.py
│       ├── sklearn/                     # Clasificadores y agrupadores
│       └── ssh/                         # Lectura de mediciones del VPS por SSH (solo SELECT)
│
└── tests/
    ├── test_architecture.py             # Guantelete: 11 baterías (AST)
    ├── test_clean_design.py             # Auditoría de diseño: código muerto, interfaces fantasma, pasamanos…
    ├── test_god_components.py           # Auditoría de componentes Dios (archivos, clases, funciones)
    ├── test_logging.py
    ├── conftest.py
    ├── unit/        (184 tests)
    ├── integration/ (27 tests)
    └── e2e/         (51 tests)
```

Las 19 pruebas restantes de los 281 recogidos por pytest están en los archivos de nivel raíz de `tests/` (por diferencia con los conteos por carpeta).

### 4.3. Configuración & Logging

#### A. Gestión de Entorno (`.env`, `.env.example`, `.gitignore`)
* `.gitignore` excluye `.env` y `.env.*`, con la excepción `!.env.example` (líneas 16–18).
* `.env.example` documenta solo claves con valores de ejemplo; los valores por defecto viven en `config.py`.

#### B. `src/infrastructure/settings/config.py` (Pydantic Settings)
La clase `Settings(BaseSettings)` lee `.env` y el entorno. Claves reales, con su valor por defecto:

| Clave | Default | Uso |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Entorno. |
| `DEBUG` | `False` | Modo depuración. |
| `LOG_LEVEL` | `INFO` | Nivel de log. |
| `PROJECT_NAME` | `datamaq-ml` | Nombre del logger y de la app. |
| `VERSION` | `1.0.0` | Versión expuesta en OpenAPI. |
| `API_V1_PREFIX` | `/api/v1` | Prefijo de la API. |
| `ALLOWED_HOSTS` | `["*"]` | Orígenes permitidos por CORS (ver brecha §6). |
| `MEDICIONES_CSV_DIR` | `data/input` | Carpeta de CSV diarios. |
| `MEDICIONES_SOURCE` | `local` | `local` o `ssh`. |
| `MEDICIONES_CACHE_DIR` | `data/prod-cache` | Caché de mediciones descargadas por SSH. |
| `RESULTADOS_DIR` | `data/output` | Salida de entrenamiento. |
| `VERDAD_DIR` | `data/verdad` | Verdad conocida de medidores simulados. |
| `MODELOS_DIR` | `data/models` | Modelos joblib. |
| `NILM_UMBRAL_KW` | `None` (automático, Otsu) | Umbral de ΔP. |
| `NILM_SEPARACION_MINIMA` | `0.8` | Separación mínima de Otsu para confiar en el umbral automático. |
| `NILM_EPS_KW` | `None` (automático) | Radio de DBSCAN. |
| `NILM_MIN_EVENTOS` | `None` (automático, uno por día, mínimo 3) | Eventos mínimos por carga. |
| `NILM_BALANCE_MINIMO` | `0.5` | Proporción mínima encendidos/apagados para una carga ON/OFF. |

Fuente: `src/infrastructure/settings/config.py`; el `.env.example` las lista con valores comentados.

**Variables que la plantilla pide y el repo no tiene:** `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `DATABASE_URL`, `API_V1_PREFIX` existe pero sin autenticación detrás (ver §6).

#### C. Logging
`src/infrastructure/settings/logger.py` configura un logger con el mismo formateador de uvicorn (`DefaultFormatter`, nivel alineado, color si la salida es terminal), con `LOG_LEVEL` de `Settings`. **No hay salida JSON.** Es una diferencia con la plantilla (brecha §6).

### 4.4. Reglas de Arquitectura: Estado Real

Cada regla de la plantilla, con su estado verificado:

1. **Regla de dependencia de capas:** **cumplida y probada.** `test_application_and_adapters_layers` y `test_domain_isolation` (`tests/test_architecture.py`). El dominio no importa de `application`, `adapters`, `infrastructure` ni de frameworks.
2. **`__init__.py` de 0 bytes:** **cumplida y probada.** `test_init_files_must_be_empty`.
3. **Desacople de datos en `data/`:** **parcial.** Los datos están en `data/` y el código no los lleva embebidos, pero varias constantes de ingeniería están en el código (ver regla 4).
4. **Constantes críticas desde `Settings` o base de datos:** **no cumplida.** Hay constantes de ingeniería en el dominio y la aplicación: `UMBRAL_P_BANCO_KW = 1.5`, `UMBRAL_Q_BANCO_KVAR = 10.0`, `TOLERANCIA_COINCIDENCIA = 5 min` (`src/domain/cargas/banco_capacitores.py`), `UMBRAL_HUECOS_CALIDAD = 10` y `HUECO_MAXIMO_MIN = 5.0` (`src/application/cargas/use_cases/validar_desagregacion.py`), y los defaults del motor (`muestras_debounce`, factor 2, cotas 2–8 kW en `desagregar_cargas.py`). Ver brecha §6.
5. **Controladores delgados:** **cumplida en lo visible.** Los routers reciben casos de uso por `Depends` (`src/infrastructure/fastapi/routers/cargas.py`, línea 21) y no tocan ningún ORM, porque no hay ORM. El guantelete no verifica esta regla en los routers (ver brecha §6).
6. **Imports absolutos:** **cumplida y probada.** `test_no_relative_imports`.
7. **Tipado estricto:** **parcial.** El guantelete exige anotaciones de parámetros y de retorno en `domain` y `application` (`test_function_return_types`, `test_function_arg_types`). **Pyright no corre en ninguna parte del repo** (no hay `pyrightconfig.json` ni paso en `run.sh` ni en la CI).
8. **Cabecera de ruta relativa:** **cumplida y probada.** `test_relative_path_headers`.

---

## 5. Gobernanza Normativa, Calidad & Matriz de Pruebas

### 5.1. Filosofía de Desarrollo Asistido por Agentes IA
El repo aplica el principio de «rodear al agente de restricciones» a través del guantelete ejecutable (`tests/test_architecture.py`). El agente no lee el código para aprobarlo: lo aprueba el guantelete y la CI. No se cita a terceros.

### 5.2. Las 11 Baterías del Guantelete (`tests/test_architecture.py`)
Verificadas por nombre de función en el archivo (líneas 661–760):
1. `test_no_hardcoded_secrets` — secretos quemados en código.
2. `test_no_raw_sql_formatting` — SQL con f-strings en `text(...)`. **Vacía en la práctica:** el repo no usa `text()`. La defensa real contra inyección en la consulta SSH es la validación de UUID en `consulta_dia` y el rechazo de todo lo que no sea SELECT (FR-02). El guantelete no cubre esa construcción (brecha §6).
3. `test_no_os_environ_direct_access` — acceso al entorno fuera de `config.py`.
4. `test_domain_isolation` — dominio sin I/O ni frameworks.
5. `test_application_and_adapters_layers` — dependencias entre capas.
6. `test_function_return_types` — retorno anotado en `domain` y `application`.
7. `test_function_arg_types` — parámetros anotados en `domain` y `application`.
8. `test_init_files_must_be_empty` — `__init__.py` de 0 bytes.
9. `test_no_relative_imports` — imports absolutos.
10. `test_no_unstructured_prints` — sin `print()` en `src/`.
11. `test_relative_path_headers` — cabecera de ruta en cada `.py`.

Observación: el encabezado de `tests/test_architecture.py` (líneas 1–25) nombra baterías que no existen con esos nombres (`test_clean_architecture_compliance`, `test_all_functions_have_type_annotations`). Los nombres reales son los de arriba. Ver brecha §6.

### 5.3. Auditoría de Diseño y Componentes Dios
* **`tests/test_clean_design.py`:** detecta `UNREACHABLE_FILE`, `GHOST_INTERFACE`, `MIDDLE_MAN_METHOD`, `DEEP_INHERITANCE`, `ORPHAN_PRIVATE_SYMBOL` y `SPECULATIVE_MICRO_FILE`. Tiene modos `--strict` y `--json`. **En CI y en `run.sh audit` se ejecuta sin `--strict`**, así que las violaciones no fallan el paso (brecha §6).
* **`tests/test_god_components.py`:** límites por defecto de archivo ≤ 400 líneas, clase ≤ 250 líneas y ≤ 15 métodos, función ≤ 60 líneas, complejidad ciclomática ≤ 10 (constantes en la cabecera del archivo, líneas 32–36).

### 5.4. Estándares de Calidad, Trazabilidad & Commits Atómicos
* **Conventional Commits en español** con alcance opcional, por ejemplo `feat(validacion): …`, `fix(compat): …`, `docs(despliegue): …` (historial de `develop`).
* **Un commit por capa o por mejora**, cada uno con sus pruebas (`AGENTS.md` del repo padre, §7).
* **Ramas temáticas** `feat|fix|chore|test|docs/issue-N-slug`; nunca `main` (`AGENTS.md` del repo padre, §4, punto 3).
* **Merges:** PR hacia `develop`; el merge a `main` lo decide el dueño con CI verde (`AGENTS.md` del repo padre, §1).

### 5.5. Matriz de Verificación Automatizada

Comandos reales del repo (`run.sh`) y de la CI (`.github/workflows/ci.yml`):

| Paso | Comando real | En CI | Plantilla |
| :--- | :--- | :---: | :---: |
| Instalar | `./run.sh install` (crea `.venv` con Python de PATH; CI fija 3.12 y descarta `.venv` previo) | Sí | — |
| Pruebas | `./run.sh test` (`pytest`) | Sí | `pytest --maxfail=1 -v` |
| Guantelete | `./run.sh gauntlet` (`tests/test_architecture.py`) | Sí | `python3 tests/test_architecture.py` |
| Auditoría | `./run.sh audit` (`test_clean_design.py` y `test_god_components.py`, **sin `--strict`**) | Sí | `--strict` |
| Lint y formato | `./run.sh lint` (`ruff check .` y `ruff format --check .`) | Sí | `ruff check .` y `ruff format --check .` |
| Tipos | **No existe** | No | `pyright src/` |

### 5.6. Configuración del Editor (Pylance / VS Code)
**No existe:** no hay `pyrightconfig.json` ni `.vscode/settings.json`. `.gitignore` ignora el directorio `.vscode/` completo (línea 25), lo que impediría versionar un `settings.json` sin cambiar la regla (brecha §6).

### 5.7. Matriz de Pruebas por Nivel

| Nivel | Carpeta | Pruebas recogidas | Qué cubre |
| :--- | :--- | ---: | :--- |
| Unitario | `tests/unit/` | 184 | Dominio y casos de uso, parsing de CSV y SSH, CLI con `subprocess` simulado. |
| Integración | `tests/integration/` | 27 | Repositorios CSV, SSH (`test_ssh_medicion_repository.py`), agrupadores, árbol. |
| End-to-end | `tests/e2e/` | 51 | Endpoints FastAPI con `TestClient`, CLI con datos sintéticos, contrato de identificación. |
| Raíz | `tests/*.py` | 19 | Guantelete, auditorías y logging. |
| **Total** | | **281** | Recogidas con `pytest --collect-only` el 2026-11-22; 0 omitidas en la última corrida local. |

---

## 6. Brechas respecto de la plantilla

Una línea por brecha, para que el dueño decida si se adopta. «Adoptar» significa implementar; «descartar» significa que no aplica a este repo.

1. **Autenticación y autorización (FR-04 de la plantilla):** no hay ninguna. Ningún router tiene `Depends` de seguridad (`git grep` de `jwt|oauth|api_key|HTTPBasic` en `src/` sin resultados). Adoptar o descartar según si la API sale de la red interna.
2. **Rate limiting y anti-abuso (FR-05):** no implementado.
3. **Persistencia transaccional con ORM (FR-02 y `§4.1 ORM`):** no aplica hoy; el repo no escribe en base de datos. Descartar salvo que el batch deba escribir resultados.
4. **Eventos y notificaciones (FR-03) y broker (`§4.1`):** no existen. Descartar salvo necesidad de alertas.
5. **Cifrado en tránsito TLS 1.3 (NFR-04):** `run.sh start` sirve HTTP plano en 0.0.0.0. Adoptar si la API sale de la red interna.
6. **SLA y disponibilidad (NFR-03):** no definidos. Decidir objetivo y timer con reintento.
7. **Latencia p95 y concurrencia (NFR-01 y NFR-02):** no medidos. Hace falta una prueba de carga si la API se usa en línea.
8. **`src/adapters/` vacía (§4.2 de la plantilla):** existe solo `__init__.py`; no hay `controllers/`, `presenters/` ni `gateways/`. Descartar la capa o adoptarla cuando haya más de un adaptador.
9. **`mappers/` en `application/` (§4.2):** no existe. Las conversiones DTO ↔ entidad se hacen dentro de los casos de uso. Descartar.
10. **`src/infrastructure/fastapi/routers/` como endpoints delgados:** cumplido, pero el guantelete no verifica la regla 5 (controladores sin ORM); con no haber ORM, la verificación es vacía.
11. **Constantes de ingeniería hardcodeadas (regla 4 de la plantilla):** `UMBRAL_P_BANCO_KW`, `UMBRAL_Q_BANCO_KVAR`, `TOLERANCIA_COINCIDENCIA`, `UMBRAL_HUECOS_CALIDAD`, `HUECO_MAXIMO_MIN` y los defaults del motor (ver §4.4). Adoptar: moverlas a `Settings` o a `data/`. Hoy el banco fijo y el muestreo de 300 s son supuestos de diseño que el código asume.
12. **Pyright (§5.5, §5.6, regla 7):** no hay `pyrightconfig.json`, ni `.vscode/settings.json`, ni paso en CI. Adoptar.
13. **Auditoría sin `--strict` (§5.5):** `run.sh audit` y la CI no fallan por violaciones de `test_clean_design.py`. Adoptar `--strict` si se quiere bloquear.
14. **Logging JSON en producción (§4.3.C):** el logger usa el formato de texto de uvicorn y no tiene modo JSON. Adoptar si `datamaq-telemetry` lo consume.
15. **Cliente de pruebas `AsyncClient` (§5.7 de la plantilla, `httpx`):** las pruebas usan `TestClient` (sincrónico) con `httpx2`. Descartar: funciona igual para estos endpoints.
16. **`pytest-asyncio` declarado sin uso en `tests/`:** verificar si se quita o si se necesita para endpoints async futuros.
17. **Guía de andamiaje (enlace del encabezado):** existe en `docs/guia-andamiaje-proyectos.md`; el enlace de la plantilla apuntaba a otra ruta. Corregido en este documento.
18. **Encabezado de `tests/test_architecture.py` desalineado** con los nombres reales de sus baterías (§5.2). Corrección de documentación; adoptar.
19. **Cadencia de muestreo y banco fijo como supuestos de código:** el motor (`src/domain/cargas/services.py`) no tiene un parámetro de cadencia; las pruebas usan 5 min. Hace falta si se valida otra cadencia.
20. **Cargas individuales pequeñas:** no hay decisión documentada sobre su exclusión (§1.1, punto 3). Decisión pendiente del dueño.
21. **Documento SRS previo:** `docs/srs-spec-backend-fastapi.md` ya existe en este repo, titulado «EnergyAI-NILM», y no se modificó. Decidir si se reemplaza por este documento o se archiva.
22. **Autor y responsable técnico:** no están definidos en el repo (§1.3). Completar.
