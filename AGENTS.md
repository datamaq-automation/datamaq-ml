# AGENTS.md — datamaq-ml (NILM Industrial & Machine Learning)

Subrepositorio de Machine Learning del ecosistema **DataMaq**. Responsable de la identificación no intrusiva de cargas industriales (NILM), desagregación de potencia y asignación de maquinaria a partir de telemetría de transformador (TGBT).

---

## 1. Rol y Propósito

`datamaq-ml` implementa el motor analítico de desagregación de cargas eléctricas:
1. **Detección de Escalones:** Identificación determinista de transitorios de encendido y apagado ($\Delta P, \Delta Q$).
2. **Clustering No Supervisado:** Agrupamiento de densidades por **DBSCAN** para aislar firmas típicas de motores y equipos industriales.
3. **Clasificación y Explicabilidad:** Extracción de reglas conjuntivas vía árboles CART y aprendizaje en espacio de versiones (*Version Space Learner*).
4. **Asignación de Activos:** Mapeo de clusters a `MachineModel` para telemetría de horas de marcha y disponibilidad operativa.

---

## 2. Arquitectura de Código (Clean Architecture)

- `src/domain/cargas/`: Entidades y reglas de negocio puras (Zero External Dependencies).
- `src/application/cargas/`: Casos de uso de identificación, evaluación, métricas y DTOs Pydantic.
- `src/infrastructure/`: Adaptadores externos:
  - `sklearn/`: Agrupador DBSCAN, Árbol CART, clasificadores Naive Bayes y KNN.
  - `fastapi/`: Servidor REST y routers (`/cargas`, `/clasificar`, `/maquinas-inferidas`, `/mediciones`).
  - `cli/`: Scripts de ejecución (`entrenar_cargas.py`, `evaluar_cargas.py`, `simular_tablero.py`, `supervisar_cargas.py`).
  - `csv/` y `ssh/`: Repositorios de ingesta de telemetría.
- `tests/`:
  - `unit/`: Pruebas de dominio y aplicación.
  - `integration/`: Pruebas de adaptadores e infraestructura sklearn/csv.
  - `e2e/`: Pruebas de endpoints FastAPI y flujos CLI.
  - Guanteletes arquitectónicos: `test_architecture.py`, `test_clean_design.py`, `test_god_components.py`.

---

## 3. Comandos de Operación (`run.sh`)

- `./run.sh dev`: Inicia el servidor FastAPI con hot-reload en puerto dinámico libre.
- `./run.sh train`: Ejecuta la identificación no supervisada sobre archivos CSV de telemetría.
- `./run.sh simulate`: Genera dataset sintético con cargas controladas para benchmarking.
- `./run.sh evaluate`: Evalúa métricas de precisión y recall contra verdad conocida.
- `./run.sh supervise`: Entrena clasificador supervisado CART.
- `./run.sh test`: Corre la suite completa de pruebas con pytest.
- `./run.sh lint`: Valida formato y reglas de código con ruff.
