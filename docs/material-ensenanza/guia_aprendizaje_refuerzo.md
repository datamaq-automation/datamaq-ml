# Guía Didáctica: Aprendizaje por Refuerzo y Q-Learning Tabular

El **Aprendizaje por Refuerzo** (*Reinforcement Learning* - RL) es el paradigma de Machine Learning centrado en la **toma de decisiones secuenciales**.

A diferencia del aprendizaje supervisado (donde un maestro proporciona etiquetas correctas) y del no supervisado (donde se extraen patrones geométricos en los datos), en RL un **agente** aprende interactuando con un **entorno** mediante ensayo y error, buscando maximizar una señal escalar de **recompensa acumulada**.

---

## 1. El Proceso de Decisión de Markov (MDP)

Un problema de decisión secuencial se formaliza mediante una tupla $\langle S, A, P, R, \gamma \rangle$:
- **Estados ($S$):** Situaciones en las que puede encontrarse el sistema (ej. franjas de tarifa eléctrica: `valle` vs `pico`).
- **Acciones ($A$):** Decisiones operativas disponibles para el agente (ej. `arrancar` una bomba o `esperar`).
- **Recompensa ($R(s, a)$):** Retorno económico o energético inmediato de ejecutar la acción $a$ en el estado $s$.
- **Factor de Descuento ($\gamma \in [0, 1)$):** Determina el valor presente de las recompensas futuras. Un $\gamma = 0.9$ pondera el futuro lejano significativamente.

---

## 2. Ecuación y Actualización de Bellman (Q-Learning)

El valor $Q(s, a)$ representa el retorno esperado acumulado si el agente toma la acción $a$ en el estado $s$ y en adelante sigue una política óptima:

$$Q(s, a) \leftarrow Q(s, a) + \alpha \cdot \left[ r + \gamma \max_{a'} Q(s', a') - Q(s, a) \right]$$

Donde:
- $\alpha$: tasa de aprendizaje.
- $r + \gamma \max_{a'} Q(s', a') - Q(s, a)$: **Error de Diferencia Temporal (TD Error)**.

---

## 3. Ejemplo Industrial: Despacho de Cargas bajo Tarifa Horaria

Consideremos un proceso industrial cíclico determinista:
$$\text{valle} \longrightarrow \text{pico} \longrightarrow \text{valle} \dots$$

- **En Valle (Tarifa Baja):** Arrancar la máquina ahorra costos de parada ($r_{\text{valle}} = +2$).
- **En Pico (Tarifa Alta):** Arrancar tiene un costo o penalización ($r_{\text{pico}}$).
- **Acción Esperar:** Retorno neutro ($r = 0$).
- Factor de descuento $\gamma = 0.9$. Período del ciclo $T = 2$ pasos ($\gamma^2 = 0.81$).

### Caso 1: Pico Severamente Penalizado ($r_{\text{pico}} = -5$)
- Política óptima: arrancar en valle ($+2$), esperar en pico ($0$).
- Ecuación de Bellman analítica en estado valle:
  $$V(\text{valle}) = r_{\text{valle}} + \gamma^2 V(\text{valle}) \implies V(\text{valle}) = \frac{r_{\text{valle}}}{1 - \gamma^2} = \frac{2}{1 - 0.81} = \frac{2}{0.19} \approx \mathbf{10.53}$$
- Política aprendida: `{"valle": "arrancar", "pico": "esperar"}`.

### Caso 2: Pico Rentable o Moderado ($r_{\text{pico}} = +1$)
- Política óptima: arrancar en ambos estados (el beneficio productivo supera la tarifa pico).
- Ecuación de Bellman analítica en estado valle:
  $$V(\text{valle}) = \frac{r_{\text{valle}} + \gamma \cdot r_{\text{pico}}}{1 - \gamma^2} = \frac{2 + 0.9 \cdot 1}{0.19} = \frac{2.9}{0.19} \approx \mathbf{15.26}$$
- Política aprendida: `{"valle": "arrancar", "pico": "arrancar"}`.

> **Lección Central:** Modificar una única recompensa en el estado pico cambia instantáneamente la política óptima en el estado valle. El agente no aprende reglas estáticas, sino que evalúa el horizonte completo.

---

## 4. Preguntas de Reflexión

1. **¿Qué ocurre si el factor de descuento es $\gamma = 0$?**
   El agente se vuelve miope: solo optimiza la recompensa inmediata del paso actual ignorando el costo futuro del pico.
2. **¿Por qué se necesita una política $\epsilon$-greedy durante el entrenamiento?**
   Para garantizar exploración: si $\epsilon = 0$, el agente puede quedar atrapado en una acción subóptima sin descubrir que arrancar en valle reporta $+2$.
