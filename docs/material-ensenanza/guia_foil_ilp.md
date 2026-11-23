# Guía Didáctica: Programación Lógica Inductiva (ILP) y Algoritmo FOIL (Quinlan, 1990)

El **Algoritmo FOIL** (*First Order Inductive Learner*) extiende el aprendizaje inductivo de reglas al paradigma de **primer orden (lógica de predicados)**.

A diferencia del aprendizaje proposicional (donde cada ejemplo es un vector fijo de valores numéricos o categóricos como $[\Delta P, \Delta Q]$), el aprendizaje relacional induce definiciones lógicas generales sobre **hechos extensionales de fondo** (*background knowledge*) y relaciones arbitrarias entre entidades.

---

## 1. Cláusulas de Horn y Representación de Conocimiento

Una **cláusula definida de Horn** tiene la forma:

$$\text{Cabeza}(X, Y) \leftarrow L_1 \land L_2 \land \dots \land L_k$$

- **Cabeza:** El predicado objetivo que queremos aprender a deducir (ej. `dependiente(X, Y)`).
- **Cuerpo:** Conjunción de literales que pueden introducir variables intermedias ligadas ($Z, W, \dots$) para representar relaciones de tránsito o composición:
  $$\text{dependiente}(X, Y) \leftarrow \text{despues}(X, Z) \land \text{despues}(Z, Y)$$
  *Interpretación industrial:* "La máquina $X$ depende operativamente de $Y$ si existe un equipo intermedio $Z$ que arranca después de $Y$ y antes de $X$".

---

## 2. Ganancia de Información FOIL (Quinlan, 1990)

FOIL construye el cuerpo de cada cláusula agregando literales de forma codiciosa (*greedy top-down*), guiado por una función de ganancia basada en teoría de la información:

$$\text{Ganancia}(L) = t \cdot \left( \log_2 \frac{p_1}{p_1 + n_1} - \log_2 \frac{p_0}{p_0 + n_0} \right)$$

Donde:
- $p_0, n_0$: número de tuplas positivas y negativas cubiertas por la cláusula actual antes de añadir el literal $L$.
- $p_1, n_1$: número de tuplas positivas y negativas que continúan cubiertas tras añadir el literal $L$.
- $t$: número de tuplas positivas cubiertas por la cláusula anterior que se mantienen cubiertas por el nuevo cuerpo ($t \le p_1$).

### Intuición de la fórmula:
- $\log_2 \frac{p}{p + n}$ mide la información requerida para certificar que un ejemplo cubierto es verdaderamente positivo (relacionado con el cociente de pureza).
- Si la cláusula especializada excluye muchos negativos ($n_1 \ll n_0$) sin perder demasiados positivos, la ganancia es fuertemente positiva.
- Si no cubre ningún positivo restante ($p_1 = 0$), la ganancia es estrictamente $0.0$.

---

## 3. Ejemplo Numérico Resuelto: Secuencias de Arranque en Sala de Máquinas

Consideremos 4 equipos de planta:
- $A$: Compresor principal.
- $B$: Bomba de alimentación.
- $C$: Ventilador de tiro.
- $D$: Luminaria de línea.

Hechos extensionales observados (`despues(X, Y)`):
$$\{ (A, B), (C, A), (D, C) \}$$

Se desea aprender el concepto `dependiente(X, Y)` (cierre transitivo de dependencias).
Pares positivos ($P$, 6 casos):
$$\{ (A, B), (C, A), (C, B), (D, C), (D, A), (D, B) \}$$
Pares negativos ($N$, 6 casos): todos los pares ordenados restantes entre los 4 equipos.

### Paso 1: Primera Cláusula Directa
- Hipótesis: `dependiente(X, Y) :- despues(X, Y)`.
- Cubre: $(A, B), (C, A), (D, C)$. ($p_1 = 3, n_1 = 0$).
- $p_0 = 6, n_0 = 6$.
- $\text{Ganancia} = 3 \cdot (\log_2(3/3) - \log_2(6/12)) = 3 \cdot (0 - (-1)) = \mathbf{3.00}$.
- Positivos restantes por cubrir: $\{ (C, B), (D, A), (D, B) \}$.

### Paso 2: Segunda Cláusula (Salto de Longitud 2)
- Hipótesis: `dependiente(X, Y) :- despues(X, Z), despues(Z, Y)`.
- Cubre: $(C, B)$ vía $C \rightarrow A \rightarrow B$ y $(D, A)$ vía $D \rightarrow C \rightarrow A$. ($p_1 = 2, n_1 = 0$).
- Con respecto a los 3 positivos restantes y 6 negativos ($p_0 = 3, n_0 = 6$):
- $\text{Ganancia} = 2 \cdot (\log_2(2/2) - \log_2(3/9)) = 2 \cdot (0 - (-1.58496)) = \mathbf{3.17}$.
- Positivo restante por cubrir: $\{ (D, B) \}$.

### Paso 3: Tercera Cláusula (Salto de Longitud 3)
- Hipótesis: `dependiente(X, Y) :- despues(X, Z), despues(Z, W), despues(W, Y)`.
- Cubre: $(D, B)$ vía $D \rightarrow C \rightarrow A \rightarrow B$. ($p_1 = 1, n_1 = 0$).
- Con respecto al positivo restante y 6 negativos ($p_0 = 1, n_0 = 6$):
- $\text{Ganancia} = 1 \cdot (\log_2(1/1) - \log_2(1/7)) = 1 \cdot (0 - (-2.80735)) = \mathbf{2.81}$.

El programa final disyuntivo de 3 cláusulas cubre el 100% de los positivos y 0% de los negativos.

---

## 4. Preguntas para el Estudiante

1. **¿Por qué un árbol de decisión proposicional estándar (como CART) no puede aprender este concepto sin preprocesar todas las combinaciones de pares?**
2. **¿Cómo se expresaría este concepto de forma recursiva con solo 2 cláusulas en lógica de primer orden?**
   - Base: `dependiente(X, Y) :- despues(X, Y).`
   - Paso inductivo: `dependiente(X, Y) :- despues(X, Z), dependiente(Z, Y).`
3. **¿Qué impacto tendría un falso positivo en los hechos observados de `despues`?**
