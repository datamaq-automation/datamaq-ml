# Guía Didáctica: Algoritmo AQ (Michalski, 1980)

El **Algoritmo AQ** es un método clásico de **inducción de reglas simbólicas** basado en el principio de **cubrimiento secuencial** (*sequential covering* o estrategia de separar y conquistar) y la construcción de **estrellas de complejos** (*star complexes*).

A diferencia de los árboles de decisión (que fragmentan el espacio recursivamente de forma ortogonal) y del espacio de versiones (que mantiene todas las hipótesis consistentes posibles), AQ busca inducir una regla disyuntiva compacta clase por clase.

---

## 1. Conceptos Fundamentales

- **Selector / Condición:** Una restricción elemental sobre un atributo (ej. $lo < \Delta P < hi$ o $\Delta P > 42$).
- **Complejo:** Una conjunción (AND lógico) de selectores. Geométricamente, representa un hiperrectángulo o intervalo en el espacio de características.
- **Regla AQ:** Una disyunción (OR lógico) de complejos para una clase dada:
  $$\text{SI } C_1 \lor C_2 \lor \dots \lor C_k \implies \text{Clase } Y$$
- **Cubrimiento Secuencial:**
  1. Para cada clase objetivo $C$, se consideran sus instancias como positivas ($P$) y el resto como negativas ($N$).
  2. Mientras queden positivos sin cubrir en $P$:
     - Se selecciona una semilla positiva $p \in P$.
     - Se genera una estrella (*star*) de complejos que cubran a $p$ sin cubrir a ningún negativo en $N$.
     - Se elige el complejo más general (o de mayor cobertura).
     - Se añaden los positivos cubiertos por este complejo y se remueven de $P$.
     - Se repite hasta que $P$ esté vacío.

---

## 2. Complejo 1D más General

En el caso unidimensional (analizando el salto de potencia activa $\Delta P$ en kW):
Dado un conjunto de ejemplos positivos $P$ y negativos $N$:
- El límite inferior $lo$ es el valor negativo más cercano por debajo de los positivos:
  $$lo = \max(\{n \in N \mid n < \min(P)\}, \text{default}=-\infty)$$
- El límite superior $hi$ es el valor negativo más cercano por encima de los positivos:
  $$hi = \min(\{n \in N \mid n > \max(P)\}, \text{default}=\infty)$$

El complejo resultante $(lo < \Delta P < hi)$ es el intervalo abierto maximal consistente con los datos de entrenamiento.

### Ejemplo de los 6 arranques sintéticos (Issue #13):
- Clase 90 kW: ejemplos {88, 92}. Negativos más cercanos: 42 por debajo, ninguno por encima.
  $$\text{Complejo: } \Delta P > 42$$
- Clase 40 kW: ejemplos {40, 42}. Negativos más cercanos: 16 por debajo, 88 por encima.
  $$\text{Complejo: } 16 < \Delta P < 88$$
- Clase 15 kW: ejemplos {15, 16}. Negativos más cercanos: ninguno por debajo, 40 por encima.
  $$\text{Complejo: } \Delta P < 40$$

---

## 3. Comparativa: AQ vs. Espacio de Versiones vs. Árboles CART

| Dimensión | Espacio de Versiones | Algoritmo AQ | Árboles de Decisión (CART) |
|---|---|---|---|
| **Estrategia** | Elimina hipótesis inconsistentes (límite $S$ y $G$) | Cubrimiento secuencial (separar y conquistar) | Partición recursiva por impureza (Gini/Entropía) |
| **Formato de Salida** | Espacio delimitado por $S$ y $G$ (conjuntivo puro) | Reglas disyuntivas de complejos ($C_1 \lor C_2$) | Estructura jerárquica de árbol (reglas mutuamente excluyentes) |
| **Manejo de Disyunción** | No soporta disyunciones directamente en hipótesis individuales | Soporte nativo secuencial | Soporte implícito mediante bifurcaciones del árbol |
| **Complejidad de Reglas** | Mínima si converge; sensible a ruido (colapso de versión) | Moderada y legible (complejos estrella) | Puede generar fragmentación excesiva sin poda |
| **Solapamiento** | No asigna clase a regiones no cubiertas | Los complejos pueden solaparse en fronteras amplias | Cobertura total exhaustiva sin solapamientos |
| **F1 y Sesgo Inductivo** | Sesgo restrictivo hacia conjunciones puras | Sesgo de generalidad por estrellas maximales | Sesgo de partición ortogonal codiciosa |

---

## 4. Preguntas de Reflexión

1. **¿Por qué el complejo de 40 kW clasifica un evento de 60 kW como 40 kW si no hay ejemplos en 60 kW?**
   Porque el negativo superior más cercano es 88 kW. Al maximizar la generalidad del complejo en ausencia de negativos intermedios, la regla cubre toda la brecha entre 42 y 88 kW.
2. **¿Qué sucede si introducimos un contraejemplo negativo en $\Delta P = 50\text{ kW}$?**
   El complejo para 40 kW se especializa a $16 < \Delta P < 50$, dejando 60 kW fuera de su cobertura.
3. **¿Cuál es la ventaja de una regla AQ frente a un árbol CART profundo?**
   La regla AQ es interpretable directamente por operarios de planta como rangos nominales de operación de cada máquina, sin anidar condiciones dependientes de otras variables.
