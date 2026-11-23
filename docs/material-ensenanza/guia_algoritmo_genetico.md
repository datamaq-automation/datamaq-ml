# Guía Didáctica: Algoritmos Genéticos y Optimización de Horarios (Holland, 1975; Goldberg, 1989)

La **optimización de horarios de demanda** (*peak shaving* o aplanamiento de curva de carga) busca distribuir el encendido de cargas eléctricas pesadas a lo largo de las franjas horarias de operación para minimizar la **demanda máxima simultánea** contratada en el transformador.

---

## 1. El Problema de Optimización Combinatoria

Dado:
- Un conjunto de $C$ cargas con potencias individuales $P = [p_1, p_2, \dots, p_C]$ (kW).
- Una demanda de base por hora $B = [b_0, b_1, \dots, b_{H-1}]$ (kW) para $H$ horas.
- Una asignación horaria (cromosoma) $X = [h_1, h_2, \dots, h_C]$, donde cada gen $h_i \in \{0, 1, \dots, H-1\}$ indica la hora de arranque de la carga $i$.

### Función Objetivo / Aptitud (*Fitness*)
La demanda en la hora $h$ es:
$$D(h) = b_h + \sum_{i: h_i = h} p_i$$

El objetivo es minimizar el pico máximo:
$$\min_{X} \max_{h \in \{0, \dots, H-1\}} D(h)$$

### Explosión Combinatoria y Búsqueda Exhaustiva
- El número total de configuraciones posibles es $H^C$.
- Para 4 cargas y 4 horas: $4^4 = 256$ combinaciones (perfectamente resoluble por fuerza bruta).
- Para 20 cargas en 24 horas: $24^{20} \approx 4 \times 10^{27}$ combinaciones. La fuerza bruta requeriría millones de años de cómputo; aquí es donde las heurísticas evolutivas resultan indispensables.

---

## 2. Componentes del Algoritmo Genético

1. **Individuo / Cromosoma:** Lista de enteros de longitud $C$, donde la posición $i$ es la carga y el valor es la hora asignada.
2. **Población:** Conjunto de $M$ individuos que evolucionan a lo largo de $G$ generaciones.
3. **Elitismo:** Los mejores $k$ individuos de cada generación se copian intactos a la siguiente, garantizando que la mejor aptitud encontrada nunca decrezca de forma monótona.
4. **Selección por Torneo:** Se eligen al azar $k_{\text{torneo}}$ individuos de la población y el que presente menor demanda máxima gana el derecho a reproducirse.
5. **Cruza en un Punto (*Single-Point Crossover*):** Se selecciona un índice de corte aleatorio y el hijo hereda los genes del padre hasta el corte y de la madre en adelante.
6. **Mutación:** Con probabilidad $p_{\text{mut}}$, un gen es reemplazado por una hora seleccionada al azar en $[0, H-1]$, permitiendo escapar de óptimos locales.

---

## 3. Ejemplo Numérico: 4 Cargas en 4 Horas

- Cargas: Horno (90 kW), Compresor (40 kW), Iluminación (25 kW), Bomba (15 kW).
- Base horaria: [20, 30, 50, 40] kW para las horas 0, 1, 2, 3.
- Sin optimizar (todas a la hora 0): $20 + 90 + 40 + 25 + 15 = \mathbf{190\text{ kW}}$.
- Con optimización (Fuerza Bruta y Genético): pico mínimo global de $\mathbf{110\text{ kW}}$.
  - Ejemplo de solución A (fuerza bruta): $(0, 1, 1, 1)$
    - Hora 0: $20 + 90 = 110\text{ kW}$
    - Hora 1: $30 + 40 + 25 + 15 = 110\text{ kW}$
    - Hora 2: $50 + 0 = 50\text{ kW}$
    - Hora 3: $40 + 0 = 40\text{ kW}$
  - Ejemplo de solución B (genético): $(0, 3, 2, 3)$
    - Hora 0: $20 + 90 = 110\text{ kW}$
    - Hora 1: $30 + 0 = 30\text{ kW}$
    - Hora 2: $50 + 25 = 75\text{ kW}$
    - Hora 3: $40 + 40 + 15 = 95\text{ kW}$

> **Observación para el Operario:** Existen múltiples configuraciones con el mismo pico óptimo (110 kW). En la práctica, el operador preferirá aquella que reparta el trabajo de forma más homogénea o que respete descansos de personal.
