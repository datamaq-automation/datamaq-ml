# Mapa: contenido del módulo → archivo del repo → ejercicio

Cada fila conecta un tema del temario con el código que lo implementa y con el ejercicio que lo practica.
Los ejercicios se hacen con el tablero sintético (`./run.sh simulate`).

## Aprendizaje supervisado

| Tema | Archivo del repo | Ejercicio |
|---|---|---|
| Clasificadores: asignar una etiqueta a un ejemplo | `src/domain/cargas/supervisado.py` (ejemplos de salto con su contexto) | E1 |
| Instancias (aprendizaje basado en instancias, k vecinos más cercanos) | `src/infrastructure/sklearn/knn_clasificador.py`, `src/application/cargas/use_cases/clasificar_knn.py` | E2 |
| Naive Bayes (clasificador probabilístico) | `src/infrastructure/sklearn/bayes_clasificador.py`, `src/application/cargas/use_cases/clasificar_bayes.py` | E2 |
| Árboles de decisión (CART) | `src/infrastructure/sklearn/arbol_clasificador.py`, `src/infrastructure/cli/supervisar_cargas.py` (`./run.sh supervise`) | E3 |
| Extracción de reglas desde un árbol | `src/infrastructure/sklearn/extractor_reglas.py`, `src/application/cargas/use_cases/explicar_arbol.py` | E3 |
| Espacio de versiones y aprendizaje de reglas conjuntivas | `src/domain/cargas/version_space_learner.py`, `src/domain/cargas/espacio_versiones.py`, `src/application/cargas/use_cases/inducir_reglas.py` | E4 |
| Medidas de rendimiento: exactitud, precisión, sensibilidad, matriz de confusión | `src/domain/cargas/evaluacion.py`, `MatrizConfusion` en `src/domain/cargas/entities.py`, `src/application/cargas/use_cases/evaluar_identificacion.py` (`./run.sh evaluate`) | E5 |

## Aprendizaje no supervisado

| Tema | Archivo del repo | Ejercicio |
|---|---|---|
| Clustering por densidad (DBSCAN) | `src/infrastructure/sklearn/dbscan_agrupador.py`, `src/application/cargas/use_cases/identificar_cargas.py` (`./run.sh train`) | E6 |
| k-medias | `src/infrastructure/sklearn/comparacion_agrupadores.py` (`agrupar_kmeans`) | E7 |
| Comparación de agrupamientos: grupos, ruido, silueta | `src/infrastructure/sklearn/comparacion_agrupadores.py` (`agrupar_dbscan`, `ResultadoAgrupamiento`) | E7 |
| Selección de parámetros sin etiquetas: umbral (Otsu), radio (Freedman–Diaconis), mínimo de eventos | `src/domain/cargas/services.py` (`estimar_umbral`, `estimar_radio`, `estimar_min_eventos`) | E6, E8 |
| Validación sin respuestas correctas | `docs/cuaderno-alumno.md`, sección 6 (con el tablero sintético) | E8 |

## Validación y verificación de modelos

| Tema | Archivo del repo | Ejercicio |
|---|---|---|
| Separación entre entrenamiento y verdad de terreno | `data/verdad/` (solo para evaluar) y `src/infrastructure/csv/verdad_repository.py` | E5 |
| Pruebas de arquitectura y de unidad sobre los algoritmos | `tests/` y `./run.sh gauntlet` | E9 |
| Medir el efecto de un cambio de parámetro | `NILM_UMBRAL_KW`, `NILM_EPS_KW` en `src/infrastructure/settings/config.py` | E6, E8 |

## Ejercicios por bloque

Ver `ejercicios.md`. Todos usan el tablero sintético. La práctica de comparación k-medias frente a DBSCAN está en
`practicas/practica_kmeans_dbscan.py`.
