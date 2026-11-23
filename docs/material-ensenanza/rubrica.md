# Rúbrica — referenciales para la evaluación del módulo

Para el docente. Evalúa el trabajo sobre el caso de estudio (`caso-de-estudio.md`, con sus datos agregados) y
sobre los ejercicios con el tablero sintético. Cada referencial tiene cuatro niveles. Un trabajo se califica en cada
referencial; el promedio no reemplaza la lectura del trabajo.

Niveles: **Inicial** (no cumple lo mínimo), **En desarrollo**, **Logrado**, **Avanzado** (va más allá: propone una
mejora fundamentada).

> **Referencia externa pendiente (issue #22).** Los referenciales oficiales de evaluación del módulo (ISFT 199) no
> están en este repo y no están verificados. Hay que pedirlos al docente y citarlos aquí con su fuente antes de usar
> esta rúbrica como referencia. Hasta entonces, los cuatro niveles de cada referencial son una propuesta interna del
> proyecto, no el texto oficial.

---

## 1. Validación y verificación de modelos

| Nivel | Criterio |
|---|---|
| Inicial | Reporta una métrica sin decir sobre qué datos ni con qué verdad. |
| En desarrollo | Separa lo que sirve para ajustar (umbral, radio) de lo que sirve para evaluar, pero no lo justifica. |
| Logrado | Distingue consistencia (energía atribuida ≤ medida, cierres, solapamientos) de exactitud, y dice qué no puede concluir sin verdad de terreno. |
| Avanzado | Propone una verificación independiente para el caso (una medición de referencia, una prueba de consistencia nueva) y dice qué resultado la refutaría. |

## 2. Resolución de problemas de predicción

| Nivel | Criterio |
|---|---|
| Inicial | Describe el problema sin precisar qué se predice ni en qué unidad (evento, intervalo, carga). |
| En desarrollo | Define la variable objetivo y la unidad, pero no reconoce el desbalance (muchos eventos ambiguos, pocos ciclos). |
| Logrado | Define la predicción (encendido, apagado o carga), elige la unidad correcta, y analiza los casos de borde (día sin datos, intervalo abierto al final del día). |
| Avanzado | Muestra que un error de predicción tiene consecuencias distintas según el tipo (falsa alarma frente a falso negativo) y lo traduce a una decisión de parámetros. |

## 3. Aplicación de técnicas de aprendizaje automático

| Nivel | Criterio |
|---|---|
| Inicial | Corre el comando pero no explica qué hace el algoritmo. |
| En desarrollo | Explica la técnica (árbol, vecinos cercanos, Naive Bayes, DBSCAN, k-medias) con sus supuestos, sin relacionarla con los datos. |
| Logrado | Elige la técnica según el problema, justifica el parámetro (profundidad, radio, k) y lo prueba contra una alternativa (E7). |
| Avanzado | Señala cuándo la técnica falla con estos datos (por ejemplo, sin reactiva, dos cargas de igual potencia activa no se separan) y propone el cambio. |

## 4. Construcción de sistemas supervisados

| Nivel | Criterio |
|---|---|
| Inicial | Entrena un clasificador sin separar datos de entrenamiento y de evaluación. |
| En desarrollo | Separa entrenamiento y evaluación y mide exactitud, precisión y sensibilidad (E5). |
| Logrado | Lee la matriz de confusión, interpreta las reglas del árbol (E3) y relaciona el error con la clase que confunde. |
| Avanzado | Diseña el paso de etiquetado (qué se confirma y quién) y explica cómo el sistema incorpora una etiqueta nueva. |

## 5. Construcción de sistemas no supervisados

| Nivel | Criterio |
|---|---|
| Inicial | Agrupa sin decir cómo se eligieron los parámetros. |
| En desarrollo | Elige los parámetros con una regla (umbral de Otsu, radio) y describe qué hace cada uno (E6). |
| Logrado | Compara dos algoritmos sobre los mismos datos (E7) con criterios sin etiquetas (grupos, ruido, silueta), y elige uno con argumentos. |
| Avanzado | Propone un criterio de selección de parámetros que se pueda aplicar a otra planta sin re-etiquetar, y lo valida con el tablero sintético (E8). |

---

## Cómo usar la rúbrica con el caso de estudio y el programa

El caso de estudio entrega solo resultados agregados. Para el referencial 1, pedir que expliquen qué les dice el
porcentaje atribuido y qué no les dice. Para el referencial 5, pedir la comparación de k-medias y DBSCAN con el tablero
sintético: el caso real no tiene verdad de terreno, así que la comparación solo se hace sobre sintéticos.

- Planificación curricular y cronograma semanal: ↗ [programa.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/programa.md)
- Banco de respuestas docentes: ↗ [respuestas-ejercicios.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/respuestas-ejercicios.md)
- Ejercicios de los estudiantes: ↗ [ejercicios.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/ejercicios.md)
