# Banco de Ejercicios — Respuestas y Guía para Docentes

> **USO EXCLUSIVO DOCENTE.** Este documento contiene las soluciones comentadas, análisis teóricos y criterios de corrección para los ejercicios de ↗ [docs/material-ensenanza/ejercicios.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/ejercicios.md).

---

## Bloque 1 — Aprendizaje Supervisado: Árboles y Modelos Probabilísticos

### E0. Regla del experto frente a regla inducida
- **1. Cortes inductivos a mano:**
  - Punto medio 1: `(15 + 40) / 2 = 27.5 kW`.
  - Punto medio 2: `(40 + 90) / 2 = 65.0 kW`.
- **2. Matrices de confusión y exactitud:**
  - Ambos obtienen exactitud `5 / 6 = 83.33 %`.
  - Matriz Experto: acierta 15 (en 20), acierta 40 (en 30 y 55), acierta 90 (en 62 y 70). Falla en `ΔP = 26` (lo clasifica como 40, cuando era 15).
  - Matriz Inducida: acierta 15 (en 20 y 26), acierta 40 (en 30 y 55), acierta 90 (en 70). Falla en `ΔP = 62` (lo clasifica como 40, cuando era 90).
- **3. Peligro de equivalencia:** No son equivalentes porque sus fallos tienen consecuencias operativas asimétricas: clasificar un motor principal de 90 kW como una bomba de 40 kW (error de la regla inducida) falsea la potencia del proceso y enmascara un equipo crítico para mantenimiento, mientras que confundir una oscilación de 26 kW del compresor con 40 kW solo afecta una carga secundaria.

### E1. Un árbol que explica
- **1. Variables utilizadas:** El árbol CART evalúa primero la magnitud del salto de potencia activa (`|ΔP|`) para discriminar la potencia de la carga involucrada, y luego el signo de `ΔP` para clasificar si es un encendido (`ΔP > 0`) o un apagado (`ΔP < 0`).
- **2. Profundidad 3 vs. defecto:** Una profundidad reducida (3) generaliza mejor y produce un árbol legible con menos nodos hoja, evitando sobreajuste sobre ruidos de conmutación. La profundidad por defecto puede generar ramas espurias que intentan clasificar fluctuaciones aleatorias de ±3 kW.
- **3. Predicción con profundidad 1:** No. Un árbol de profundidad 1 (un solo corte o *decision stump*) solo puede dividir el espacio en dos particiones. Para separar tres cargas distintas se requieren como mínimo dos divisiones (profundidad >= 2).

### E2. Instancias y Naive Bayes
- **1. Diferencia conceptual:** k-NN es un método no paramétrico y perezoso (*lazy learner*) que decide por cercanía geométrica local en el espacio de características sin asumir distribuciones. Naive Bayes es un clasificador paramétrico y probabilístico que calcula la probabilidad a posteriori `P(Carga | Salto)` asumiendo independencia condicional entre las variables.
- **2. Salto de 49 kW vs. 60 kW:** En 49 kW ambos clasificadores coinciden sólidamente en la Carga A (siendo cercana a 50 kW y lejana de las demás). En 60 kW se produce ambigüedad si coincide con un salto puente (apagado/encendido simultáneo) o cola de dispersión, donde las densidades gaussianas de Naive Bayes pueden diferir de la distancia euclidiana de k-NN.
- **3. Supuesto de independencia:** Naive Bayes asume que `ΔP` y el contexto temporal son estadísticamente independientes dado el equipo. En la física industrial real esto es falso: la potencia activa y reactiva (`ΔP` y `ΔQ`) están estrechamente ligadas por el factor de potencia inductivo del motor.

---

## Bloque 2 — Espacio de Versiones y Reglas

### E3. Reglas desde el árbol
- **1. Formato conjuntivo:** Cada camino de la raíz a una hoja genera una regla: `SI |ΔP| >= 35.0 Y ΔP > 0 ENTONCES Encendido_Carga_B`.
- **2. Evaluación de ejemplos:** Las hojas puras cubren eventos reales de `sintetico.csv`. Las colisiones ocurren en saltos compuestos donde dos motores conmutan en la misma ventana de 5 min.

### E4. Espacio de versiones en papel
Dados los ejemplos:
- Ej. 1 (38, 40, sí), Ej. 2 (42, 44, sí), Ej. 3 (8, 3, no), Ej. 4 (65, 10, no).
- **1. Límite Específico S:** El rectángulo mínimo que cubre los positivos:
  `S = { (38 <= ΔP <= 42) ∧ (40 <= ΔQ <= 44) }`.
- **2. Límite General G:** Las hipótesis maximales que excluyen los negativos:
  `G = { (ΔP > 8 ∧ ΔQ > 3), (ΔP < 65 ∨ ΔQ > 10) }`.
- **3. Inclusión del Ejemplo 5 (30, 33, sí):**
  El límite S se generaliza para incluir (30, 33):
  `S' = { (30 <= ΔP <= 42) ∧ (33 <= ΔQ <= 44) }`.
  El límite G se especializa eliminando hipótesis que choquen con la expansión de S.

---

## Bloque 3 — Medidas de Rendimiento

### E5. Medir sin inventar números
- **1. Definiciones:**
  - **Exactitud:** Fracción de predicciones correctas sobre el total de eventos.
  - **Precisión:** De los eventos clasificados como carga X, qué porcentaje pertenecía realmente a X.
  - **Sensibilidad (Recall):** De todos los eventos reales de la carga X ocurridos en la planta, qué porcentaje detectó el sistema.
  - *Criterio de costo:* Si una falsa alarma dispara un mantenimiento costoso innecesario, se prioriza **alta precisión**. Si omitir una parada puede romper un equipo, se prioriza **alta sensibilidad**.
- **2. Subir umbral a 60 kW:** Al subir el umbral, se eliminan eventos de ruido (sube la precisión de las cargas grandes), pero caen drásticamente la detección y sensibilidad de las cargas medianas y pequeñas (15 kW y 40 kW quedan totalmente invisibles).
- **3. Matriz de confusión:** Debe sumar 10 eventos con True Positives (TP), False Positives (FP), True Negatives (TN) y False Negatives (FN).

---

## Bloque 4 — Aprendizaje No Supervisado: Clustering

### E6. DBSCAN y sus parámetros
- **1. Umbral automático vs. 60 kW:** Con umbral automático (~48 kW) se aíslan los escalones significativos. Con 60 kW los escalones de cargas de 40 kW se descartan antes de llegar a clustering.
- **2. Radio epsilon:**
  - Si `eps=3`, los grupos son muy compactos; si la carga tiene dispersión de carga variable, muchos puntos quedan marcados como ruido (`etiqueta = -1`).
  - Si `eps=15`, grupos vecinos se fusionan indebidamente en una macro-carga ficticia.
- **3. Predicción:** A menor radio, aumenta la cantidad de ruido (`-1`) y se fragmentan los grupos.

### E7. k-medias frente a DBSCAN
- **1. Fijar k arbitrariamente:** Si `k` es menor al real, fusiona clusters. Si `k` es mayor, divide arbitrariamente una nube continua de puntos.
- **2. Coeficiente de Silueta:** El valor máximo de silueta indica la partición natural de clusters. Sin etiquetas, es el criterio matemático primario para optimizar hiperparámetros.
- **3. Marcado de valores aislados en DBSCAN:** Es una ventaja capital en entornos industriales: permite filtrar arranques atípicos, maniobras transitorias y ruidos de red sin forzar su asignación a una máquina existente.
- **4. Coincidencia:** Coinciden cuando las cargas tienen clusters hiper-esféricos, densos y bien separados entre sí con varianza homogénea.

### E7b. Dendrograma y cortes aglomerativos
- **1. Enlace simple vs. completo en 7 puntos:**
  - El enlace simple mide la distancia mínima entre clusters. Por el efecto de encadenamiento (*chaining*), 1 se une a 2 (distancia 1.0), 2 a 3.5 (distancia 1.5) y 3.5 a 5 (distancia 1.5), fusionando `{1, 2, 3.5, 5}` en una sola cadena alargada.
  - El enlace completo mide la distancia máxima entre cualquier par de elementos. Como la distancia entre 1 y 5 es 4.0, resiste la fusión y mantiene `{1, 2}` separado de `{3.5, 5}`, produciendo clusters más compactos y esféricos.
- **2. Comparación sobre el tablero sintético:**
  - Los métodos Ward y complete alcanzan las siluetas más altas (~0.65 a 0.75) al aislar limpiamente los escalones típicos de 15, 40 y 90 kW. Enlace simple sufre encadenamiento espurio por el ruido de conmutación.
- **3. Criterio de corte en el dendrograma:**
  - El corte óptimo se sitúa en la mayor brecha vertical entre fusiones sucesivas. Una línea horizontal que cruce ese salto amplio asegura que los grupos sean estables y físicamente diferenciables sin sobresegmentar.

---

## Bloque 5 — Selección de Parámetros sin la Verdad

### E8. Elegir parámetros sin la verdad
- **1. Fuentes:**
  - Umbral de Otsu: maximiza la varianza inter-clase en el histograma de saltos de potencia, separando el ruido de fondo de las conmutaciones reales.
  - Radio (Freedman–Diaconis): se calcula a partir del rango intercuartílico (`IQR`) del conjunto de saltos: `h = 2 * IQR * n^(-1/3)`.
- **2. Comparación de radio:** El radio automático se sitúa en el codo de la curva de silueta sin requerir inspección visual.
- **3. Criterio sin verdad:** Optimizar maximizando la silueta promedio sujeta a una penalización por fracción de ruido (`pct_ruido < 15 %`).

### E8b. Curva de sobreajuste y ajuste de hiperparámetros
- **1. Evolución de la exactitud:**
  - Profundidad 2: Entrenamiento 71.7 %, Prueba 78.0 % (4 hojas).
  - Profundidad 4: Entrenamiento 80.0 %, Prueba 65.0 % (11 hojas).
  - Sin límite: Entrenamiento 98.3 %, Prueba 57.5 % (25 hojas).
- **2. Causa del colapso en prueba:** El árbol sin límite creó 25 hojas para aislar y clasificar correctamente las 19 etiquetas ruidosas o corruptas del entrenamiento. Al memorizar el ruido aleatorio en lugar de los patrones físicos de potencia, comete errores masivos al enfrentarse a los 200 casos de prueba limpios.
- **3. Ventaja de la validación cruzada:** La validación cruzada rota los datos de validación entre k particiones distintas, promediando el rendimiento y eliminando el riesgo de optimizar hiperparámetros para una partición de prueba afortunada o sesgada.

---

## Bloque 6 — Verificación del Software de ML

### E9. Qué prueba cada test
- **1. Test del umbral de Otsu:** En `tests/unit/cargas/test_services.py`, verifica casos de borde: serie plana (varianza 0), serie monótona sin valles, y saltos idénticos.
- **2. Prueba contra alteración inadvertida de potencia:** Test de regresión o invariancia de energía en `tests/unit/cargas/test_entities.py`, verificando que la integral horaria de potencia de un `IntervaloMarcha` sea idéntica a la suma de rectángulos.
- **3. Clean Architecture e inversión de dependencias:** El dominio no debe depender de librerías externas de ML ni de bases de datos para permitir sustituir algoritmos o repositorios sin reescribir las reglas de negocio de la empresa.

---

## Bloque 7 — Validación sin Verdad de Terreno

### E10. Cobertura frente a residuo
- **1. Cobertura 79.2 % y concentración:** El residuo se concentra en los intervalos 2, 3 y 7 (que acumulan 5.0 kWh de los 5.0 kWh faltantes totales). En particular, el intervalo 7 tiene residuo de 3.0 kWh (atribución 0 frente a 3 medidos).
- **2. Compensación cruzada:** Si atribuye +10 kWh en la mañana y -10 kWh en la tarde, la cobertura diaria global resulta 100 %, pero el modelo asignó horas de marcha a máquinas apagadas y omitió máquinas en marcha. La cobertura aislada es insuficiente para certificar un modelo.
- **3. Vector de 95 % rechazado:**
  - Medido: `[10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 30.0]` (total 100 kWh).
  - Atribuido: `[10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 15.0, 20.0]` (total 95 kWh).
  - Cobertura: 95.0 %.
  - Rechazado por: Energía inventada en el intervalo 6 (`atribuido=15.0 > medido=10.0`), violando la invarianza física.
