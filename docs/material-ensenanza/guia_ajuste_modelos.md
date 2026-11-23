# Guía: Ajuste de Modelos, Sobreajuste y Validación Cruzada

Material pedagógico para el módulo «Procesamiento de Aprendizaje Automático» (ISFT 199).

---

## 1. El Dilema del Sobreajuste (*Overfitting*)

Un modelo de aprendizaje automático no solo debe memorizar los datos con los que fue entrenado; su objetivo real es **generalizar** ante casos futuros no observados.

- **Subajuste (*Underfitting*):** El modelo es demasiado simple (ej. un árbol de profundidad 1) y no captura la estructura real del problema.
- **Sobreajuste (*Overfitting*):** El modelo tiene demasiada capacidad o complejidad (ej. un árbol sin límite de profundidad) y termina memorizando las peculiaridades, ruidos e imprecisiones de las etiquetas de entrenamiento.

> Analogía: Estudiar para un examen de memoria repitiendo las preguntas del año pasado. Si las preguntas cambian levemente en el examen real, quien memorizó reprueba, mientras que quien aprendió el principio general aprueba.

---

## 2. Experimento con Ruido en Etiquetas

En ↗ [docs/ejemplos/ejemplo_issue_16.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_16.py) se diseña un experimento controlado:
1. Se toman 60 ejemplos de entrenamiento del tablero sintético.
2. Se introduce un 20 % de ruido artificial en las etiquetas (19 etiquetas alteradas aleatoriamente), simulando errores humanos o lecturas transitorias ambiguas.
3. Se entrena un árbol CART con profundidades 2, 4 y sin límite (`None`).
4. Se evalúa el desempeño sobre un conjunto de prueba limpio e independiente de 200 arranques.

### Resultados de la Curva de Validación

| Profundidad del Árbol | Hojas | Exactitud en Entrenamiento (Ruidoso) | Exactitud en Prueba (Limpio) | Diagnóstico |
|---|---|---|---|---|
| **Profundidad 2** | 4 | **71.7 %** | **78.0 %** | **Modelo Óptimo:** Generaliza el patrón principal sin aprender el ruido. |
| **Profundidad 4** | 11 | **80.0 %** | **65.0 %** | **Sobreajuste Moderado:** Comienza a crear ramas para acomodar errores. |
| **Sin límite (`None`)** | 25 | **98.3 %** | **57.5 %** | **Sobreajuste Severo:** Memorizó casi todas las etiquetas erróneas y colapsó en prueba. |

```text
Exactitud
1.00 ┤              Train (98.3%) ───► memoriza ruido
0.80 ┤  Train (71.7%)  ───────────► Train (80.0%)
     │  Test  (78.0%)  ───────────► Test  (65.0%)
0.60 ┤                                           Test (57.5%) ───► colapso
     └───────────────────────────────────────────────────────────
       Profundidad 2          Profundidad 4        Sin límite
```

---

## 3. Función Reutilizable de Validación Cruzada (*k-Fold*)

Para evitar el sesgo de una única partición fija, se utiliza la función polimórfica ↗ [src/infrastructure/sklearn/evaluacion_clasificadores.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/src/infrastructure/sklearn/evaluacion_clasificadores.py):

```python
from sklearn.tree import DecisionTreeClassifier
from src.infrastructure.sklearn.evaluacion_clasificadores import (
    evaluar_clasificador_cv,
)

clf = DecisionTreeClassifier(max_depth=3)
metricas = evaluar_clasificador_cv(clf, X, y, k=5)

print(f"Exactitud media en validación: {metricas['exactitud_validacion_media']:.2%}")
print(f"Desvío estándar: {metricas['desvio_estandar_validacion']:.3f}")
```

Esta función es compatible directamente con:
- Árboles de decisión (`DecisionTreeClassifier` y `ArbolClasificador`).
- Vecinos más cercanos (`KNeighborsClassifier`).
- Clasificadores probabilísticos (`GaussianNB`).

---

## 4. Advertencia: Series Temporales y Filtrado del Futuro

Al trabajar con telemetría industrial (como `t1.csv`, `t2.csv` o series temporales de potencia):
- **Prohibido barajar (*shuffle*) temporalmente de forma aleatoria:** Si los datos tienen correlación temporal, un k-fold aleatorio permite que el modelo «vea el futuro» para predecir el pasado, falseando la métrica.
- En problemas de predicción temporal (Issue #15), se debe utilizar partición temporal estricta o validación en ventana rodante (*rolling window* / *time-series split*).

---

## 5. Referencias Bibliográficas

- **Hastie, T., Tibshirani, R. y Friedman, J. (2009).** *The Elements of Statistical Learning* (2.ª ed.). Springer. [https://doi.org/10.1007/978-0-387-84858-7](https://doi.org/10.1007/978-0-387-84858-7).
- **Kohavi, R. (1995).** *A study of cross-validation and bootstrap for accuracy estimation and model selection.* IJCAI-95.
- **Bergmeir, C. y Benítez, J. M. (2012).** *On the use of cross-validation for time series predictor evaluation.* Information Sciences, 191, 192–213.
