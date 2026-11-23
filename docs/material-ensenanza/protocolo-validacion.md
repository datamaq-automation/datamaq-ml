# Protocolo de Validación y Verificación sin Verdad de Terreno

Guía metodológica para el módulo «Procesamiento de Aprendizaje Automático» (ISFT 199).

---

## 1. El Problema: Validar cuando no hay Respuestas Correctas

En problemas reales de desagregación energética (NILM) e inferencia industrial, casi nunca se cuenta con sensores individuales en cada máquina ni con registros manuales exhaustivos de cada arranque. No existe una «verdad de terreno» (*ground truth*) que indique con certeza qué carga encendió o apagó en cada instante.

Frente a esta limitación, el analista no puede calcular directamente métricas supervisadas tradicionales como la matriz de confusión, precisión o sensibilidad. Debe implementar un **protocolo de validación por plausibilidad física y balance de energía**.

> Analogía: Validar sin verdad de terreno es como cuadrar una caja registradora al final del turno sin tener todos los tickets individuales. Que la suma total cuadre no demuestra que cada gasto esté bien clasificado, pero un faltante inexplicable indica exactamente en qué franja horaria hay que investigar.

---

## 2. Marco del Procedimiento de Validación Industrial

El procedimiento de validación en entornos de producción (implementado en ↗ [src/infrastructure/cli/validar_dia_real.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/cli/validar_dia_real.py) y ↗ [src/application/cargas/use_cases/validar_desagregacion.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/application/cargas/use_cases/validar_desagregacion.py)) se basa en tres principios no negociables:

1. **Agregados Seguros:** Se evalúan únicamente agregados estadísticos y energéticos por día o franja horaria. Jamás se exponen ni comparten registros crudos sin consentimiento.
2. **Invarianza Física:** La energía total atribuida a las cargas no puede superar la energía total medida por el transformador de cabecera. El algoritmo no puede «crear» energía.
3. **Consistencia Operativa:** Los intervalos de marcha deben abrirse con un escalón positivo y cerrarse de forma coherente con un escalón negativo o una caída de potencia base, sin solapamientos físicamente incompatibles.

---

## 3. Las Tres Métricas Cardinales del Protocolo

Para auditar un modelo de desagregación sin etiquetas de referencia se calculan tres dimensiones:

### A. Cobertura de Energía Total

La fracción de la energía medida en el medidor general que el algoritmo logra atribuir a las firmas conocidas:

- Cobertura = (Energía Atribuida Total en kWh) / (Energía Medida Total en kWh)

Una cobertura típica en plantas reales se ubica entre el 40 % y el 80 %, dependiendo del porcentaje de cargas menores no catalogadas o ruido de fondo.

### B. Residuo por Intervalo y Concentración de Errores

El residuo en cada intervalo de tiempo i (por ejemplo, muestras de 15 minutos):

- Residuo_i = Energía Medida_i − Energía Atribuida_i (en kWh)

El análisis del residuo evalúa si la energía no explicada se distribuye de manera homogénea (consumo base continuo) o si se concentra en picos en intervalos puntuales:
- Si el residuo es uniforme y bajo, corresponde a cargas pequeñas bajo el umbral de detección o consumo pasivo.
- Si el residuo salta abruptamente en ciertos intervalos (por ejemplo, Residuo_i > 0,5 kWh), revela una carga industrial omitida, un arranque no detectado o un apagado prematuro.

### C. Pruebas de Consistencia y Casos Marcados

Se inspeccionan las siguientes banderas rojas de plausibilidad:
1. **Energía Inventada (Residuo Negativo):** Si en algún intervalo Energía Atribuida_i > Energía Medida_i, el emparejamiento asignó una firma errónea o mantuvo abierta una marcha inexistente.
2. **Intervalos Abiertos al Cierre:** Máquinas que quedaron en marcha al finalizar la ventana diaria sin registro de parada.
3. **Intervalos Cortados por Caída:** Intervalos interrumpidos forzosamente porque la potencia total del transformador cayó por debajo de la potencia nominal de la carga.
4. **Solapamientos Físicos Anómalos:** Cargas de un mismo proceso secuencial que aparecen encendidas en simultáneo cuando el circuito eléctrico lo prohíbe.

---

## 4. El Peligro de la «Cobertura Ciega»: Por qué una Cobertura Alta no Alcanza

Un error frecuente es asumir que una cobertura global alta (por ejemplo, 80 % o 95 %) garantiza un modelo correcto:

1. **Compensación de Errores:** Si el algoritmo sobre-atribuye 20 kWh en el turno mañana (asignando una potencia excesiva) y sub-atribuye 25 kWh en el turno tarde (perdiendo arranques reales), la cobertura global puede alcanzar el 95 %, pero ambas conclusiones de mantenimiento son completamente falsas.
2. **Concentración Oculta:** En el ejemplo sintético de 8 intervalos:
   - Medido: [2.0, 2.0, 5.0, 5.0, 2.0, 2.0, 3.0, 3.0] → 24.0 kWh.
   - Atribuido: [2.0, 2.0, 4.0, 4.0, 2.0, 2.0, 3.0, 0.0] → 19.0 kWh.
   - Cobertura global: 79.2 %.
   Aunque 79.2 % parece aceptable, el residuo no está repartido: 3.0 kWh de los 5.0 kWh faltantes se concentran exclusivamente en el intervalo 7 (donde el algoritmo atribuyó 0 kWh frente a 3 kWh medidos). El modelo no falló un poco en todo el día: ignoró por completo un evento en el intervalo 7.

---

## 5. Implementación Práctica y Ejemplo Reproducible

El script ↗ [docs/ejemplos/ejemplo_issue_20.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_20.py) proporciona la implementación determinística de las funciones de cálculo y evaluación:

```bash
# Ejecutar desde la raíz del repositorio
python docs/ejemplos/ejemplo_issue_20.py
```

Salida esperada:
```
energía medida 24.0 kWh, atribuida 19.0 kWh, cobertura 79.2%
residuo por intervalo: [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 3.0]
intervalos con residuo > 0,5 kWh: [2, 3, 7], suman 5.0 kWh
la cobertura no dice dónde falla: el residuo se concentra en los intervalos 2, 3 y 7
```

---

## 6. Actividades para el Estudiante (por Niveles de Autonomía)

- **Nivel Guiado:** Ejecutar `ejemplo_issue_20.py`, comprobar la cobertura de 79.2 % y verificar por qué los intervalos 2, 3 y 7 acumulan el residuo crítico.
- **Nivel Semi-guiado:** Implementar una variante que calcule el residuo porcentual relativo `(R_i / M_i)` por intervalo y determine qué fracción del día estuvo dentro de una banda de tolerancia del ±10 %.
- **Nivel Autónomo:** Diseñar una serie sintética de 24 horas donde la cobertura diaria sea del 95 % pero que deba ser rechazada por el protocolo debido a compensación cruzada (energía inventada en horario nocturno y faltante en horario pico).

---

## 7. Criterios de Aceptación y Evaluación (Rúbrica)

Este protocolo se evalúa según el criterio **Validación y verificación de modelos** de ↗ [docs/material-ensenanza/rubrica.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/rubrica.md):
- **Logrado:** Distingue consistencia (energía atribuida <= medida, cierres, solapamientos) de exactitud supervisada, y explicita qué conclusiones no pueden extraerse sin verdad de terreno.
- **Avanzado:** Propone verificaciones independientes, identifica compensación de errores en coberturas altas y diseña pruebas de consistencia física antes de emitir informes.

---

## 8. Referencias Bibliográficas

- **Hart, G. W. (1992).** *Nonintrusive appliance load monitoring.* Proceedings of the IEEE, 80(12), 1870–1891. [https://doi.org/10.1109/5.192069](https://doi.org/10.1109/5.192069).
- **Hastie, T., Tibshirani, R. y Friedman, J. (2009).** *The Elements of Statistical Learning* (2.ª ed.). Springer. [https://doi.org/10.1007/978-0-387-84858-7](https://doi.org/10.1007/978-0-387-84858-7).
