# Mapa: Contenido del Módulo → Archivo del Repo → Ejercicio

Cada fila conecta un tema del temario del módulo «Procesamiento de Aprendizaje Automático» (ISFT 199) con el código que lo implementa y con el ejercicio que lo practica. Los ejercicios base se resuelven con el tablero sintético (`./run.sh simulate`) y el protocolo de validación con las acometidas didácticas (`./run.sh fetch-data`).

---

## 1. Fundamentos de Aprendizaje Automático

| Tema | Archivo del repo | Ejercicio / Práctica |
|---|---|---|
| Concepto, técnicas y objetivos del aprendizaje | ↗ [docs/guia-docente.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/guia-docente.md) (§1 y §5), ↗ [docs/material-ensenanza/programa.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/programa.md) | Semana 1, `./run.sh simulate` |
| El aprendizaje como búsqueda en el espacio de hipótesis | ↗ [src/domain/cargas/espacio_versiones.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/domain/cargas/espacio_versiones.py), ↗ [src/domain/cargas/version_space_learner.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/domain/cargas/version_space_learner.py) | E4 (límites S y G) |
| Aprendizaje inductivo vs. deductivo | ↗ [docs/material-ensenanza/reglas_deductivas_ejemplo.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/reglas_deductivas_ejemplo.md), ↗ [docs/ejemplos/ejemplo_issue_12.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_12.py) | E0, Contraste de reglas |
| Diseño de modelos y evaluación de aprendizaje | ↗ [src/domain/cargas/evaluacion.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/domain/cargas/evaluacion.py), ↗ [src/application/cargas/use_cases/evaluar_identificacion.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/application/cargas/use_cases/evaluar_identificacion.py) | E5 (`./run.sh evaluate`) |

---

## 2. Aprendizaje Supervisado

| Tema | Archivo del repo | Ejercicio / Práctica |
|---|---|---|
| Clasificadores y formulación de ejemplos | ↗ [src/domain/cargas/supervisado.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/domain/cargas/supervisado.py) | E1 |
| Aprendizaje basado en instancias (k vecinos más cercanos) | ↗ [src/infrastructure/sklearn/knn_clasificador.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/knn_clasificador.py), ↗ [src/application/cargas/use_cases/clasificar_knn.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/application/cargas/use_cases/clasificar_knn.py) | E2 |
| Clasificador probabilístico (Naive Bayes) | ↗ [src/infrastructure/sklearn/bayes_clasificador.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/bayes_clasificador.py), ↗ [src/application/cargas/use_cases/clasificar_bayes.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/application/cargas/use_cases/clasificar_bayes.py) | E2 |
| Árboles de decisión (CART) | ↗ [src/infrastructure/sklearn/arbol_clasificador.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/arbol_clasificador.py), ↗ [src/infrastructure/cli/supervisar_cargas.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/cli/supervisar_cargas.py) | E1 (`./run.sh supervise`) |
| Extracción de reglas conjuntivas desde árboles | ↗ [src/infrastructure/sklearn/extractor_reglas.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/extractor_reglas.py), ↗ [src/application/cargas/use_cases/explicar_arbol.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/application/cargas/use_cases/explicar_arbol.py) | E3 |
| Algoritmo AQ (inducción de reglas estrella) | ↗ [src/domain/cargas/aq_learner.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/domain/cargas/aq_learner.py), ↗ [docs/material-ensenanza/guia_algoritmo_aq.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/guia_algoritmo_aq.md), ↗ [docs/ejemplos/ejemplo_issue_13.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_13.py) | E4b (Práctica AQ y cubrimiento) |
| Programación lógica inductiva y algoritmo FOIL | ↗ [src/domain/cargas/foil_learner.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/domain/cargas/foil_learner.py), ↗ [docs/material-ensenanza/guia_foil_ilp.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/guia_foil_ilp.md), ↗ [docs/ejemplos/ejemplo_issue_14.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_14.py) | E4c (Inducción de relaciones de carga) |
| Árboles de regresión y predicción temporal de demanda | ↗ [src/domain/cargas/pronostico_demanda.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/domain/cargas/pronostico_demanda.py), ↗ [docs/material-ensenanza/guia_regresion_pronostico.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/guia_regresion_pronostico.md), ↗ [docs/ejemplos/ejemplo_issue_15.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_15.py) | E4d (`./run.sh forecast`) |
| Medidas de rendimiento (matriz de confusión, exactitud, precisión, recall) | ↗ [src/domain/cargas/evaluacion.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/domain/cargas/evaluacion.py), `MatrizConfusion` en ↗ [src/domain/cargas/entities.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/domain/cargas/entities.py) | E5 |
| Ajuste de modelos: sobreajuste y validación cruzada | ↗ [src/infrastructure/sklearn/evaluacion_clasificadores.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/evaluacion_clasificadores.py), ↗ [docs/material-ensenanza/guia_ajuste_modelos.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/guia_ajuste_modelos.md), ↗ [docs/ejemplos/ejemplo_issue_16.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_16.py) | E8b |

---

## 3. Aprendizaje No Supervisado

| Tema | Archivo del repo | Ejercicio / Práctica |
|---|---|---|
| Clustering por densidad (DBSCAN) | ↗ [src/infrastructure/sklearn/dbscan_agrupador.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/dbscan_agrupador.py), ↗ [src/application/cargas/use_cases/identificar_cargas.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/application/cargas/use_cases/identificar_cargas.py) | E6 (`./run.sh train`) |
| Algoritmo k-medias y particionado | ↗ [src/infrastructure/sklearn/comparacion_agrupadores.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/comparacion_agrupadores.py) (`agrupar_kmeans`) | E7 |
| Comparación de agrupamientos (grupos, ruido, silueta) | ↗ [src/infrastructure/sklearn/comparacion_agrupadores.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/comparacion_agrupadores.py) (`ResultadoAgrupamiento`) | E7 |
| Estimación de parámetros sin etiquetas (Otsu, Freedman–Diaconis) | ↗ [src/domain/cargas/services.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/domain/cargas/services.py) (`estimar_umbral`, `estimar_radio`) | E6, E8 |
| Estrategia aglomerativa (jerárquica) y dendrogramas | ↗ [src/infrastructure/sklearn/comparacion_agrupadores.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/comparacion_agrupadores.py), ↗ [docs/material-ensenanza/practicas/practica_aglomerativo.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/practicas/practica_aglomerativo.py), ↗ [docs/ejemplos/ejemplo_issue_17.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_17.py) | E7b |
| Aprendizaje por refuerzo y Q-learning tabular | ↗ [docs/ejemplos/ejemplo_issue_18.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_18.py) | Optimización de demanda |

---

## 4. Capacidades Profesionales, Validación y Evaluación

| Tema | Archivo del repo | Ejercicio / Práctica |
|---|---|---|
| Optimización de horarios con algoritmos genéticos | ↗ [docs/ejemplos/ejemplo_issue_19.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_19.py) | Desplazamiento de picos |
| Protocolo de validación sin verdad de terreno | ↗ [docs/material-ensenanza/protocolo-validacion.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/protocolo-validacion.md), ↗ [docs/ejemplos/ejemplo_issue_20.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_20.py) | E10 |
| Secuencias de análisis con librerías propias vs. externas | ↗ [docs/ejemplos/ejemplo_issue_21.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_21.py) | Benchmarking de pipelines |
| Pruebas de arquitectura, límites de capas y guanteletes | ↗ [tests/test_architecture.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/tests/test_architecture.py), ↗ [tests/test_god_components.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/tests/test_god_components.py) | E9 (`./run.sh gauntlet`) |
| Programa, presupuesto horario y rúbrica por referenciales | ↗ [docs/material-ensenanza/programa.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/programa.md), ↗ [docs/material-ensenanza/rubrica.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/rubrica.md) | Evaluación semestral |
