# Guía Didáctica: Regresión y Pronóstico de Demanda con Partición Temporal

El pronóstico de demanda energética consiste en estimar valores continuos futuros ($\text{kWh}$ consumidos o $\text{kW}$ promedio por franja horaria) a partir de un histórico de mediciones de telemetría.

A diferencia de la clasificación binaria o multiclase de eventos transitorios, los problemas de regresión temporal imponen una restricción metodológica inviolable: **la partición de evaluación debe ser estrictamente cronológica**.

---

## 1. Métricas de Rendimiento Continuo

Dado un vector de valores reales $y = [y_1, y_2, \dots, y_H]$ y sus correspondientes pronósticos $\hat{y} = [\hat{y}_1, \hat{y}_2, \dots, \hat{y}_H]$ sobre un horizonte $H$:

### 1.1 Error Absoluto Medio (MAE)
$$\text{MAE} = \frac{1}{H} \sum_{t=1}^H |y_t - \hat{y}_t|$$
- Mide la magnitud promedio del error en las mismas unidades físicas de la variable ($\text{kWh}$).
- Es robusto frente a valores atípicos (outliers) esporádicos.
- Ideal para planificar el balance energético acumulado diario o mensual.

### 1.2 Raíz del Error Cuadrático Medio (RMSE)
$$\text{RMSE} = \sqrt{\frac{1}{H} \sum_{t=1}^H (y_t - \hat{y}_t)^2}$$
- Eleva las desviaciones al cuadrado antes de promediar, penalizando con severidad desproporcionada los errores grandes.
- Por desigualdad de Jensen, siempre se cumple que $\text{RMSE} \ge \text{MAE}$.
- Es la métrica crítica para decisiones de potencia contratada en transformador (TGBT), donde sobrepasar la capacidad de pico genera multas económicas por exceso de potencia o disparos de protecciones térmicas.

---

## 2. Modelos de Línea de Base (*Baselines*)

Antes de justificar el uso de modelos complejos (como redes recurrentes o árboles profundos), es indispensable contrastar el desempeño contra líneas de base triviales:

1. **Promedio Histórico:**
   $$\hat{y}_t = \bar{y}_{\text{train}} = \frac{1}{N} \sum_{i=1}^N y_i$$
   Asume que el proceso es estacionario y no presenta tendencia ni ciclos.
2. **Último Valor (Persistencia o Martingala):**
   $$\hat{y}_t = y_N$$
   Asume un paseo aleatorio (*random walk*): el mejor predictor del futuro inmediato es el estado más reciente.
3. **Tendencia Lineal (Mínimos Cuadrados Ordinarios - OLS):**
   $$\hat{y}_t = \hat{\beta}_0 + \hat{\beta}_1 \cdot t$$
   Captura la tasa de crecimiento o decaimiento tendencial en el tiempo.
4. **Árbol de Regresión (CART):**
   Particiona recursivamente el eje temporal o variables contextuales minimizando la varianza cuadrática intra-nodo (reducción de impureza MSE), prediciendo la media en cada hoja.

---

## 3. El Peligro de la Fuga Temporal (*Data Leakage*)

En aprendizaje automático tradicional con datos tabulares i.i.d. (independientes e idénticamente distribuidos), es habitual barajar (*shuffle*) las filas al azar (ej. `train_test_split(shuffle=True)`).

En series temporales de energía, **la partición aleatoria está terminantemente prohibida**:

| Tipo de Partición | Procedimiento | Comportamiento del Modelo | Error Reportado | Validez |
|---|---|---|---|---|
| **Temporal (Honesta)** | Entrena con $t \in [1, N]$, prueba con $t \in [N+1, N+H]$ | **Extrapolación** pura hacia el futuro desconocido | **Alto / Realista** | Válida para producción |
| **Aleatoria (Fuga de Datos)** | Mezcla aleatoriamente instantes de tiempo entre entrenamiento y prueba | **Interpolación** entre puntos pasados y futuros conocidos | **Bajo / Artificialmente Inflado** | Falsa e inutilizable |

### Demostración con Números:
En una serie industrial con tendencia y ciclo de 7 días:
- La **partición honesta temporal** arroja un $\text{MAE} \approx 6.33\text{ kWh}$ porque debe extrapolar fuera de la ventana observada.
- La **partición aleatoria** arroja un $\text{MAE} \approx 4.00\text{ kWh}$ ($\approx 37\%$ menos de error artificial) porque el modelo interpola usando puntos del futuro que ya revelaron la tendencia general.

---

## 4. Preguntas para Reflexionar

1. **¿Por qué el modelo de persistencia (último valor) suele superar al promedio histórico en horizontes cortos de 1 a 3 pasos?**
2. **Si una fábrica penaliza severamente superar los $500\text{ kW}$ durante 15 minutos, ¿qué métrica guiará la elección del modelo: MAE o RMSE?**
3. **¿Qué técnica de validación cruzada es admisible en series de tiempo?**
   (Respuesta: *Rolling origin / TimeSeriesSplit*, donde la ventana de entrenamiento solo se expande hacia adelante).
