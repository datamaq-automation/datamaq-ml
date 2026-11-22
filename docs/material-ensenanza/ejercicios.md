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

## Bloque 5 — Selección de modelos y validación sin respuestas correctas

**E8. Elegir parámetros sin la verdad.** Los parámetros de DBSCAN se estiman con reglas (ver `docs/cuaderno-alumno.md`,
secciones 4 a 6):

1. Corran `./run.sh train sintetico` y anoten el umbral de Otsu y el radio que muestra la salida. Expliquen de dónde
   sale cada uno, sin mirar el código.
2. Con la verdad, comparen el radio automático con los radios 2, 5 y 10. ¿El automático está entre los mejores?
3. Propongan un criterio sin verdad para elegir el radio (por ejemplo, la silueta de la práctica E7). Pruébenlo con el
   tablero sintético: ¿coincide con el que mide la verdad?

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
