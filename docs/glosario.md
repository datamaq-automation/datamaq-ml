# Glosario del módulo

Términos que usan los issues del épico #11. Cada uno tiene una definición corta y un ejemplo. Los ejemplos son **sintéticos** o hechos a mano; no hay datos de ninguna planta.

Los números de los ejemplos se reproducen con los scripts de `docs/ejemplos/`. Cuando un término viene de la NILM (monitoreo no intrusivo de cargas), la referencia de origen figura al final de cada entrada.

## Tipos de aprendizaje

**Aprendizaje supervisado.** Aprender a predecir una respuesta a partir de ejemplos que ya la tienen. *Ejemplo:* un arranque de 90 kW etiquetado como «horno» enseña al modelo qué forma tiene ese arranque. Ver #12, #13, #14, #15, #16.

**Aprendizaje no supervisado.** Encontrar grupos o estructura sin etiquetas. *Ejemplo:* agrupar 7 arranques en 3 grupos según su magnitud, sin que nadie diga qué equipo es cada uno. Ver #17.

**Aprendizaje por refuerzo.** Aprender una política de acciones a partir de recompensas, sin ejemplos etiquetados. *Ejemplo:* un agente que aprende a no arrancar en pico porque cuesta 5 unidades. Ver #18.

**Aprendizaje deductivo.** Regla escrita a mano por un experto a partir de lo que sabe. *Ejemplo:* «si ΔP ≥ 60 kW, es el horno». Ver #12.

**Aprendizaje inductivo.** Regla que sale de ejemplos etiquetados. *Ejemplo:* un árbol que pone un corte a mitad de camino entre dos ejemplos de 40 y 90 kW: 65 kW. Ver #12.

## Datos y evaluación

**Ejemplo etiquetado.** Un caso con su respuesta correcta. *Ejemplo:* un arranque de ΔP = 88 kW con la etiqueta «horno». Ver [docs/cuaderno-alumno.md](cuaderno-alumno.md).

**Atributo (o rasgo).** Una propiedad medible del caso. *Ejemplo:* ΔP, el salto de potencia al arrancar, en kW.

**Clase (o etiqueta).** La respuesta que el modelo tiene que predecir. *Ejemplo:* «horno», «compresor», «luz».

**Conjunto de entrenamiento.** Los ejemplos con los que se ajusta el modelo. *Ejemplo:* 60 arranques sintéticos.

**Conjunto de prueba.** Los ejemplos que se reservan para medir, sin tocarlos al elegir el modelo. *Ejemplo:* 200 arranques limpios separados antes de entrenar.

**Exactitud (accuracy).** Aciertos sobre el total de casos. *Ejemplo:* 5 aciertos de 6 casos = 0,83. Ver #12 y [src/domain/cargas/evaluacion.py](../src/domain/cargas/evaluacion.py).

**Matriz de confusión.** Tabla que cruza la clase verdadera con la predicha. *Ejemplo:* con dos clases, cuenta los aciertos y los errores de cada una por separado.

**Precisión (precision).** De los casos que el modelo dice positivos, cuántos lo son. *Ejemplo:* si dice «horno» 10 veces y 8 son horno, la precisión es 0,8.

**Sensibilidad (recall).** De los casos positivos reales, cuántos encuentra el modelo. *Ejemplo:* si hay 10 arranques de horno y el modelo encuentra 8, la sensibilidad es 0,8.

**F1.** Media armónica de precisión y sensibilidad. Castiga que una de las dos sea baja. *Ejemplo:* precisión 0,8 y sensibilidad 0,8 dan F1 = 0,8.

**Verdad de terreno.** La respuesta correcta conocida, que se usa solo para evaluar. *Ejemplo:* el simulador sabe qué carga arrancó en cada minuto; el modelo no lo ve. Ver el issue #20.

**Energía (kWh) y potencia (kW).** La potencia es la tasa en un instante; la energía es la potencia integrada en el tiempo. *Ejemplo:* 2 kW durante 30 min son 1 kWh.

**Residuo.** Energía medida menos energía atribuida. *Ejemplo:* medido 5 kWh, atribuido 4 kWh, residuo 1 kWh. Ver #20.

**Cobertura de energía.** Energía atribuida sobre energía medida. *Ejemplo:* 19 de 24 kWh = 79,2 %. Ver #20.

**Error absoluto medio (MAE).** Promedio del error absoluto de un pronóstico. *Ejemplo:* errores de 2, 4 y 6 dan MAE = 4. Ver #15.

**Raíz del error cuadrático medio (RMSE).** Raíz del promedio del error al cuadrado; penaliza más los errores grandes. *Ejemplo:* errores de 2, 4 y 6 dan RMSE ≈ 4,32. Ver #15 y Hyndman y Koehler (2006).

## Modelos y ajuste

**Árbol de decisión.** Secuencia de preguntas sobre atributos con cortes, que termina en una clase. *Ejemplo:* «¿ΔP ≥ 60?» → horno; si no, «¿ΔP ≥ 25?» → compresor. Ver #12 y Breiman et al. (1984).

**Árbol de regresión.** Árbol cuyas hojas predicen un número, no una clase. *Ejemplo:* una hoja que predice 102 kWh de demanda para los días de un rango. Ver #15.

**Espacio de versiones.** Conjunto de reglas consistentes con todos los ejemplos. *Ejemplo:* todos los intervalos de ΔP que incluyen 88 y 92 y excluyen 40. Ver Mitchell (1997).

**Regla (o condición conjuntiva).** Condición con varias partes unidas por «y». *Ejemplo:* ΔP > 25 y ΔQ < 5.

**Complejo (AQ).** Condición que cubre ejemplos positivos de una clase y excluye los negativos. *Ejemplo:* 16 < ΔP < 88 cubre los dos arranques de 40 kW. Ver #13.

**Cubrimiento secuencial.** Buscar un complejo, quitar los positivos cubiertos y buscar otro. *Ejemplo:* dos pasadas de rodillo para pintar una pared. Ver #13.

**Cláusula de Horn.** Regla de la forma «cabeza si cuerpo», con condiciones unidas por «y». *Ejemplo:* `dependiente(X, Y) :- despues(X, Z), despues(Z, Y).` Ver #14 y Quinlan (1990).

**Literal.** Una condición dentro de una cláusula. *Ejemplo:* `despues(X, Z)` es un literal de la cláusula anterior.

**Ganancia FOIL.** Medida de cuánto mejora una cláusula al agregar un literal. *Ejemplo:* agregar `despues(X,Y)` a `dependiente` da ganancia 3,00 en el caso del issue #14.

**Sobreajuste.** Cuando el modelo aprende el ruido de los ejemplos y empeora con casos nuevos. *Ejemplo:* un árbol sin límite llega a 0,983 de exactitud con sus ejemplos y a 0,575 con casos nuevos (issue #16).

**Validación cruzada.** Partir el entrenamiento en k bloques y medir cada bloque con el modelo entrenado sin él. *Ejemplo:* 5 bloques de 12 arranques: se entrena 5 veces y se promedian los 5 aciertos.

**Partición temporal.** Dividir una serie en el orden del tiempo: el entrenamiento va antes que la prueba. *Ejemplo:* días 1 a 7 para entrenar y días 8 a 10 para probar. Ver #15 y Bergmeir y Benítez (2012).

**Hiperparámetro.** Una perilla que se fija antes de entrenar. *Ejemplo:* la profundidad máxima del árbol, o `k` en k vecinos más cercanos.

**k vecinos más cercanos (k-NN).** Clasifica un caso con la clase mayoritaria de sus `k` vecinos más cercanos. *Ejemplo:* con k = 3, si dos de los tres vecinos son «horno», el caso es «horno».

**Clasificador bayesiano (Naive Bayes).** Clasifica con probabilidades, suponiendo independencia entre atributos. *Ejemplo:* calcula la probabilidad de que un arranque de ΔP = 40 kW sea compresor frente a horno.

## Agrupamiento y no supervisado

**k-medias.** Agrupa en k grupos moviendo los centros hasta que los puntos queden cerca de su centro. *Ejemplo:* 7 puntos en 3 grupos. Ver MacQueen (1967).

**DBSCAN.** Agrupa por densidad: un punto es núcleo si tiene al menos `min_samples` vecinos a distancia `eps`; los puntos sin grupo son ruido. *Ejemplo:* `eps` = 8 kW y `min_samples` = 14 eventos. Ver Ester et al. (1996).

**Silueta.** Mide qué tan bien encaja cada punto en su grupo frente al grupo vecino. Va de −1 a 1. Ver Rousseeuw (1987).

**Agrupamiento aglomerativo (jerárquico).** Empieza con cada punto solo y une de a dos grupos hasta tener uno. *Ejemplo:* 7 puntos unidos paso a paso. Ver #17.

**Enlace (linkage).** Cómo se mide la distancia entre dos grupos. *Ejemplo:* enlace simple usa la distancia mínima entre puntos; enlace completo, la máxima. Ver #17.

**Enlace simple.** Distancia mínima entre un punto de cada grupo. Forma cadenas largas. *Ejemplo:* 1 y 5 se unen por 1–2–3,5–5. Ver #17.

**Enlace completo.** Distancia máxima entre un punto de cada grupo. Forma grupos compactos. *Ejemplo:* 1 y 5 no se unen antes de cortar en 3 grupos. Ver #17.

**Ward.** Une los dos grupos que menos aumentan la suma de cuadrados dentro de los grupos. Ward (1963). *Ejemplo:* da la misma partición en 3 grupos que el enlace completo del ejemplo de #17.

**Dendrograma.** Gráfico de las fusiones del agrupamiento jerárquico; la altura de cada unión es la distancia de fusión. Cortarlo define los grupos. Ver #17.

## Refuerzo

**Agente.** Quien elige acciones. *Ejemplo:* el programa que decide cuándo arrancar un equipo.

**Estado y acción.** El estado es la situación; la acción es lo que el agente elige. *Ejemplo:* estado «valle» (tarifa baja), acción «arrancar».

**Recompensa.** Número que el entorno devuelve tras una acción. *Ejemplo:* +2 por arrancar en valle, −5 por arrancar en pico. Ver #18.

**Valor Q.** Cuánto se espera ganar desde un estado si se elige una acción y después se actúa bien. *Ejemplo:* Q(valle, arrancar) = 10,53 con las recompensas del issue #18.

**Política.** Regla que dice qué acción elegir en cada estado. *Ejemplo:* «en valle, arrancar; en pico, esperar».

**Factor de descuento (γ).** Cuánto pesa el futuro frente al presente. *Ejemplo:* γ = 0,9 hace que una recompensa dentro de un paso valga 0,9.

## Optimización

**Algoritmo genético.** Búsqueda que mantiene una población de soluciones y las mejora con selección, cruce y mutación. Ver Holland (1975).

**Individuo.** Una solución candidata dentro de la población. *Ejemplo:* (0, 1, 1, 1), la hora de arranque de cada carga.

**Aptitud (fitness).** Qué tan buena es una solución. *Ejemplo:* la demanda máxima del individuo, que se quiere bajar.

**Cruce.** Mezcla genes de dos padres. *Ejemplo:* las dos primeras cargas del padre con las dos últimas de la madre.

**Mutación.** Cambio aleatorio de un gen. *Ejemplo:* cambiar la hora de arranque de la bomba.

**Elitismo.** Pasar los mejores individuos a la generación siguiente sin cambios. *Ejemplo:* los dos mejores de cada generación siguen tal cual.

**Fuerza bruta.** Probar todas las soluciones posibles. *Ejemplo:* 4 cargas en 4 horas dan 4⁴ = 256 combinaciones. Ver #19.

## Contexto del hilo conductor

**NILM (monitoreo no intrusivo de cargas).** Identificar los equipos de una planta a partir de la potencia medida en la acometida, sin medidores en cada equipo. Ver Hart (1992).

**Evento (o salto).** Cambio brusco de potencia entre dos muestras. *Ejemplo:* de 0 a 50 kW en un minuto es un evento de +50 kW.

**Umbral.** Valor a partir del cual un salto cuenta como evento. *Ejemplo:* 20 kW: un salto de 15 kW se ignora.

**Método de Otsu.** Elige el umbral que mejor separa dos grupos de valores en un histograma, maximizando la varianza entre grupos. Otsu (1979).

**Tablero sintético.** Datos generados por el simulador (`./run.sh simulate`), con cargas y arranques conocidos. Es el único tipo de dato que se usa en el material del módulo.

---

Este glosario lo enlazan los issues del épico #11. Si falta un término, se agrega aquí en el mismo PR que lo usa.
