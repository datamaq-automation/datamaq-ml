# Ejercicios por bloque

Todos los ejercicios usan el tablero **sintético**: `./run.sh simulate` genera `data/input/sintetico.csv` y su verdad
en `data/verdad/sintetico.csv`. No usan datos reales (ver `README.md`, condición de consentimiento).

Preparación, una vez:

```bash
./run.sh install
./run.sh simulate
```

Para mirar la verdad solo después de responder: `data/verdad/sintetico.csv`.

---

## Bloque 1 — Aprendizaje supervisado: árboles de decisión

**E0. Regla del experto frente a regla inducida.** Comparar una regla deductiva manual con una regla inducida de datos (ver ↗ [reglas_deductivas_ejemplo.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/reglas_deductivas_ejemplo.md) y script ↗ [ejemplo_issue_12.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_12.py)):

```bash
python docs/ejemplos/ejemplo_issue_12.py
```

1. Calculá a mano los cortes inductivos entre los ejemplos de entrenamiento 15, 40 y 90 kW y confirmá que den 27,5 y 65,0 kW.
2. Armá la matriz de confusión 3x3 para la regla del experto y para la regla inducida sobre los seis casos de prueba. ¿Qué exactitud global tiene cada una?
3. Si ambas tienen 5/6 (83,3 %) de exactitud, ¿por qué no son equivalentes? Explicá qué error comete cada una y cuál es más peligroso para el mantenimiento de la planta.

**E1. Un árbol que explica.** Entrená un árbol con la verdad del tablero sintético:

```bash
./run.sh supervise sintetico
./run.sh supervise sintetico --profundidad 3
```

1. ¿Qué variables usa el árbol para decidir si un salto es un encendido o un apagado? ¿Cuál aparece primero?
2. Comparen la profundidad 3 con la profundidad por defecto. ¿Cambia el error en la verificación? ¿Cambia la explicación?
3. **Predecí** antes de correr: ¿un árbol de profundidad 1 puede separar tres cargas de potencias parecidas? Justificá.

**E2. Instancias y Naive Bayes.** Con `./run.sh dev` (servidor en `http://localhost:8000`), abran `/docs` y prueben
`POST /api/v1/classify/knn` y `POST /api/v1/classify/bayes` con el mismo ejemplo.

1. ¿Qué diferencia hay entre clasificar por vecinos cercanos (instancias) y por probabilidad (Naive Bayes)?
2. Cambien el ejemplo: un salto de 49 kW, después uno de 60 kW. ¿En cuál coinciden los dos clasificadores? ¿Por qué?
3. ¿Qué supone Naive Bayes sobre las variables? ¿Se cumple en un salto de potencia con su contexto?

## Bloque 2 — Espacio de versiones y reglas

**E3. Reglas desde el árbol.** Con `GET /api/v1/explain/tree` (o la salida de `./run.sh supervise sintetico`):

1. Escriban cada hoja del árbol como una regla «si … entonces …».
2. Elijan una regla y busquen en `data/input/sintetico.csv` dos ejemplos que la cumplan y uno que no. ¿La regla se
   sostiene con los tres?

**E4. Espacio de versiones en papel.** Dados estos ejemplos positivos (encendido de carga X) y negativos, sin computadora:

| Ejemplo | ΔP (kW) | ΔQ (kvar) | Etiqueta |
|---|---|---|---|
| 1 | 38 | 40 | sí |
| 2 | 42 | 44 | sí |
| 3 | 8 | 3 | no |
| 4 | 65 | 10 | no |

1. ¿Cuál es la hipótesis más específica que cubre los positivos y no los negativos? (el límite S)
2. ¿Cuál es la más general? (el límite G)
3. Agreguen el ejemplo 5 (ΔP = 30, ΔQ = 33, sí). ¿Cómo cambian S y G? Verifiquen con `POST /api/v1/version-space/step`.

**E4b. Algoritmo AQ frente a Espacio de Versiones y Árboles CART.**
Con los 6 arranques sintéticos de prueba: (88, 90), (92, 90), (40, 40), (42, 40), (15, 15) y (16, 15) (donde cada tupla es `(ΔP, clase)` en kW):
1. Calculen a mano el complejo más general (1D) para cada una de las 3 clases.
2. ¿Por qué un nuevo arranque de 60 kW es clasificado por AQ como clase 40 kW si no había ningún dato de 60 kW en el entrenamiento?
3. Comparen conceptualmente las reglas de AQ con las obtenidas por un árbol CART (`./run.sh supervise`) y las del espacio de versiones: comparen número de reglas, complejidad e interpretabilidad. Verifiquen con `python docs/ejemplos/ejemplo_issue_13.py`.

## Bloque 3 — Medidas de rendimiento

**E5. Medir sin inventar números.** Con la verdad del tablero:

```bash
./run.sh evaluate sintetico
```

1. Expliquen con sus palabras **exactitud**, **precisión** (de lo que encontró, cuánto era real) y **sensibilidad**
   (de lo real, cuánto encontró). ¿Cuál les importaría más si el costo de una falsa alarma es alto?
2. Cambien el umbral (`NILM_UMBRAL_KW=60 ./run.sh evaluate sintetico`). ¿Sube la precisión, la sensibilidad o las dos?
3. Armen la matriz de confusión a mano para 10 eventos que les dé la salida y calculen las tres medidas.

## Bloque 4 — Aprendizaje no supervisado: clustering

**E6. DBSCAN y sus parámetros.** Sin etiquetas, el tablero solo tiene escalones de potencia.

```bash
./run.sh train sintetico
./run.sh train sintetico --umbral 60
./run.sh train sintetico --radio 3
```

1. ¿Cuántas cargas encuentra con el umbral automático? ¿Y con `--umbral 60`? ¿Por qué cambia?
2. Con `--radio 3` y con `--radio 15`: ¿qué le pasa a la cantidad de grupos y a los eventos sin grupo?
3. **Predecí** antes de correr: si el radio es muy chico, ¿aparecen más grupos o más eventos sin grupo? Verifiquen.

**E7. k-medias frente a DBSCAN sobre los mismos escalones.** Es la práctica de comparación del módulo:

```bash
./.venv/bin/python docs/material-ensenanza/practicas/practica_kmeans_dbscan.py
./.venv/bin/python docs/material-ensenanza/practicas/practica_kmeans_dbscan.py --k 2
./.venv/bin/python docs/material-ensenanza/practicas/practica_kmeans_dbscan.py --k 4 --eps 4
```

1. k-medias necesita que digan cuántos grupos hay (`--k`). DBSCAN no. ¿Qué pasa si `--k` es distinto de los grupos
   reales?
2. Comparen la **silueta** (qué tan separados están los grupos, de −1 a 1) entre `--k 2`, `--k 3` y `--k 4`. ¿Cuál
   k elegirían sin mirar la verdad? ¿Coincide con el que mide la verdad?
3. DBSCAN marca como «sin grupo» a los valores aislados. ¿Eso es un defecto o una ventaja para un tablero industrial?
   Justifiquen con un caso concreto (un arranque aislado, una falla de medición).
4. ¿Cuándo esperarían que k-medias y DBSCAN den el mismo resultado? ¿Cuándo no?

**E7b. Dendrograma y cortes aglomerativos.** (ver práctica ↗ [practica_aglomerativo.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/practicas/practica_aglomerativo.py) y script ↗ [ejemplo_issue_17.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_17.py)):

```bash
./.venv/bin/python docs/material-ensenanza/practicas/practica_aglomerativo.py --comparar-todos
./.venv/bin/python docs/material-ensenanza/practicas/practica_aglomerativo.py --k 3 --metodo complete
```

1. Corré el script `ejemplo_issue_17.py` y observá la tabla de siete puntos: 1; 2; 3,5; 5; 9; 10; 12,5. ¿Por qué el enlace simple agrupa 1, 2, 3,5 y 5 juntos, mientras que el enlace completo separa {1, 2} de {3,5, 5}?
2. En la práctica sobre `sintetico.csv`, compará los cuatro métodos cortando en k=3. ¿Cuál método obtiene el mayor coeficiente de silueta y por qué?
3. En un dendrograma, ¿dónde conviene realizar el corte por distancia? Justificá utilizando el concepto de salto de altura (brecha máxima entre fusiones sucesivas).

## Bloque 5 — Selección de modelos y validación sin respuestas correctas

**E8. Elegir parámetros sin la verdad.** Los parámetros de DBSCAN se estiman con reglas (ver `docs/cuaderno-alumno.md`,
secciones 4 a 6):

1. Corran `./run.sh train sintetico` y anoten el umbral de Otsu y el radio que muestra la salida. Expliquen de dónde
   sale cada uno, sin mirar el código.
2. Con la verdad, comparen el radio automático con los radios 2, 5 y 10. ¿El automático está entre los mejores?
3. Propongan un criterio sin verdad para elegir el radio (por ejemplo, la silueta de la práctica E7). Pruébenlo con el
   tablero sintético: ¿coincide con el que mide la verdad?

**E8b. Curva de sobreajuste y ajuste de hiperparámetros.** (ver ↗ [guia_ajuste_modelos.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/guia_ajuste_modelos.md) y script ↗ [ejemplo_issue_16.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_16.py)):

```bash
python docs/ejemplos/ejemplo_issue_16.py
```

1. Corré el script y observá cómo evoluciona la exactitud de entrenamiento frente a la de prueba al pasar de profundidad 2 a 4 y sin límite (`None`).
2. ¿Por qué el árbol sin límite alcanza 98,3 % en entrenamiento pero cae abruptamente a 57,5 % en prueba? ¿Qué aprendió el árbol que perjudicó su generalización?
3. Utilizá la función de validación cruzada `evaluar_clasificador_cv` de ↗ [evaluacion_clasificadores.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/evaluacion_clasificadores.py). ¿Por qué la validación cruzada es más robusta que una única partición fija?

## Bloque 6 — Verificación del software de ML

**E9. Qué prueba cada test.** El repo tiene pruebas unitarias, de integración, e2e y de arquitectura:

```bash
./run.sh test
./run.sh gauntlet
```

1. Elijan un algoritmo (por ejemplo, el umbral de Otsu) y ubiquen su test unitario. ¿Qué caso de borde prueba?
2. Describan una prueba que detectaría que alguien cambió la potencia de un intervalo sin querer. ¿Dónde la escribirían?
3. ¿Por qué el gauntlet revisa que el dominio no importe infraestructura? ¿Qué problema evita en un proyecto que
   cambia de base de datos o de librería de ML?

**E10. Validación sin verdad de terreno: cobertura frente a residuo.** En problemas industriales reales no hay etiquetas de referencia. Guía completa en ↗ [protocolo-validacion.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/protocolo-validacion.md) y script reproducible en ↗ [ejemplo_issue_20.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_20.py):

```bash
python docs/ejemplos/ejemplo_issue_20.py
```

1. Corran el script y confirmen la cobertura de 79,2 %. ¿En qué intervalos se concentra el residuo crítico mayor a 0,5 kWh?
2. Si un algoritmo atribuye 10 kWh de más en el turno mañana y 10 kWh de menos en el turno tarde, ¿qué le pasa a la cobertura diaria total? ¿Por qué la cobertura global sola puede ser engañosa?
3. Diseñen un vector sintético de 8 intervalos donde la cobertura sea del 95 % pero que deba ser rechazado por contener energía inventada en uno de los intervalos (residuo negativo). Verifiquen su caso con `evaluar_consistencia_dia`.
