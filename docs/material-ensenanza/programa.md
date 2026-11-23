# Programa del Módulo: Procesamiento de Aprendizaje Automático (ISFT 199)

Planificación curricular, cronograma semestral de 16 semanas y balance de carga horaria.

---

## 1. Fundamentación y Supuestos

El módulo «Procesamiento de Aprendizaje Automático» de la Tecnicatura Superior (ISFT 199) se estructura en torno a un problema tecnológico e industrial concreto: **la desagregación no intrusiva de cargas eléctricas (NILM)** en plantas productivas a partir de la potencia de su transformador de cabecera.

### Supuestos de Planificación
- **Duración del Semestre:** 16 semanas académicas efectivas.
- **Carga Horaria Presencial:** 4 horas reloj semanales en aula/laboratorio informático (64 horas reloj cátedra en total).
- **Carga Horaria Asincrónica:** 1 a 2 horas semanales de lectura previa, ejercitación autónoma y consolidación de proyectos (22 horas reloj en total).
- **Carga Total Estimada:** 86 horas de dedicación integral del estudiante (coherente con el rango de 65 a 87 horas calculado en ↗ [docs/ejemplos/ejemplo_issue_22.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_22.py)).

> **Análisis de Presupuesto Horario:**
> Si se limitara el módulo estrictamente a las 64 horas de clase presencial sin trabajo autónomo, el contenido demandaría entre 16.2 y 21.8 semanas, superando el calendario. La estrategia pedagógica adoptada es el **modelo híbrido o aula invertida**: la teoría base y la lectura de conceptos se realizan como preparación previa, dedicando las 4 horas de clase al trabajo sobre código, análisis de datos y discusión guiada.

---

## 2. Cronograma Semanal (16 Semanas)

| Semana | Bloque Temático | Contenidos Centrales | Práctica / Ejercicio | Horas Aula | Horas Asinc. | Issue |
|---|---|---|---|---|---|---|
| **1** | Introducción al NILM | Telemetría eléctrica, potencia activa y reactiva, transitorios | Instalación, `./run.sh simulate` | 4 h | 0 h | #29 |
| **2** | Fundamentos de AA | Aprendizaje inductivo vs. deductivo, generalización | E10 (comparación y contraste) | 4 h | 1 h | #12 |
| **3** | Supervisado: Árboles | Clasificación CART, pureza de nodos, extracción de reglas | E1 (`./run.sh supervise`) | 4 h | 1 h | #12 |
| **4** | Espacio de Versiones | Límite específico S y límite general G, reglas conjuntivas | E3 y E4 (espacio de versiones) | 4 h | 2 h | #13 |
| **5** | Inducción de Reglas | Algoritmo AQ, cobertura de complejos y clases múltiples | Práctica AQ sobre saltos sintéticos | 4 h | 2 h | #13 |
| **6** | Lógica Inductiva | Programación lógica inductiva (ILP) y algoritmo FOIL | Cláusulas de primer orden sobre eventos | 4 h | 2 h | #14 |
| **7** | Evaluación Supervisada | Matrices de confusión, precisión, sensibilidad, sobreajuste | E5 (`./run.sh evaluate`) | 4 h | 2 h | #16 |
| **8** | Regresión y Pronóstico | Modelado de demanda, series de tiempo, partición temporal | Predicción de potencia a 15 min | 4 h | 2 h | #15 |
| **9** | Clustering: Densidad | DBSCAN, radio epsilon, densidad mínima, ruido | E6 (`./run.sh train`) | 4 h | 1 h | #17 |
| **10** | Clustering Jerárquico | Estrategia aglomerativa, enlaces, dendrograma | E7 (comparación k-means vs. DBSCAN) | 4 h | 1 h | #17 |
| **11** | Aprendizaje por Refuerzo | Entorno MDP simplificado, Q-learning tabular, recompensas | Optimización de encendidos y picos | 4 h | 2 h | #18 |
| **12** | Algoritmos Genéticos | Poblaciones, operadores genéticos, optimización de horarios | Aplanamiento de curva de carga | 4 h | 2 h | #19 |
| **13** | Validación sin Verdad | Protocolo de validación, balance de energía, residuo | ↗ [protocolo-validacion.md](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/material-ensenanza/protocolo-validacion.md), E10 | 4 h | 1 h | #20 |
| **14** | Secuencias de Análisis | Librerías estándar (scikit-learn) vs. adaptadores propios | Benchmarking y acoplamiento | 4 h | 2 h | #21 |
| **15** | Integración Real | Aplicación del protocolo sobre datos anonimizados T1 y T2 | Análisis de acometidas reales | 4 h | 1 h | #20 |
| **16** | Cierre y Evaluación | Presentación de proyectos y aplicación de rúbrica | Evaluación final por rúbrica | 4 h | 1 h | #22 |
| **TOTAL** | — | — | — | **64 h** | **22 h** | — |

---

## 3. Estrategia de Recorte ante Contingencias

Si por razones de calendario institucional (feriados, mesas de examen) el período lectivo se redujera a 14 semanas o menos, la prioridad curricular mantendrá el núcleo industrial:
1. **Módulos Preservados (Núcleo Indispensable):** Semanas 1 a 5 (Supervisado y Reglas), 7 (Evaluación), 9 (DBSCAN) y 13-15 (Validación y Casos Reales).
2. **Módulos de Ajuste:** Algoritmos genéticos (#19) y Aprendizaje por refuerzo (#18) pasan a seminarios optativos o talleres de profundización sin comprometer la aprobación del módulo básico.
