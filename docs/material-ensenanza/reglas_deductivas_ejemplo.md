# Reglas Deductivas de Identificación de Cargas (Ejemplo Experto)

Material pedagógico para el módulo «Procesamiento de Aprendizaje Automático» (ISFT 199).

---

## 1. Contexto: Conocimiento Experto vs. Inducción de Datos

En la desagregación no intrusiva de cargas (NILM), existen dos paradigmas fundamentales para formular reglas que clasifiquen un salto de potencia activa (`|ΔP|` en kW) en un equipo eléctrico concreto:

1. **Enfoque Deductivo (Reglas de Experto):** Un ingeniero electricista o especialista en planta formula las reglas a partir de las placas de características de los motores, el conocimiento de las caídas de tensión y las condiciones operativas de la fábrica.
2. **Enfoque Inductivo (Aprendizaje Automático):** Un algoritmo (como CART o particionado por puntos medios) observa ejemplos etiquetados históricos y deduce los cortes matemáticos óptimos que separan las clases observadas.

---

## 2. Las Tres Reglas Deductivas del Experto

Considerando el tablero sintético de tres cargas industriales:
- **Carga 15 kW:** Compresor auxiliar o bomba dosificadora pequeña.
- **Carga 40 kW:** Bomba de recirculación de pasta o ventilador de tiro.
- **Carga 90 kW:** Motor principal de accionamiento de la máquina papelera.

El experto formula deductivamente las siguientes tres reglas basadas en bandas de tolerancia y márgenes de seguridad:

```text
REGLA 1 (Carga Alta - 90 kW):
    SI |ΔP| >= 60.0 kW
    ENTONCES Carga = 90 kW
    Justificación experta: Ninguna otra carga del tablero supera los 50 kW en régimen
    ni con sobrecarga momentánea. Cualquier salto mayor o igual a 60 kW pertenece al motor principal.

REGLA 2 (Carga Media - 40 kW):
    SI 25.0 kW <= |ΔP| < 60.0 kW
    ENTONCES Carga = 40 kW
    Justificación experta: La carga de 40 kW oscila entre 30 kW (en vacío) y 55 kW (a plena carga).
    El límite inferior de 25 kW previene solapamiento con los picos del compresor de 15 kW.

REGLA 3 (Carga Baja - 15 kW):
    SI |ΔP| < 25.0 kW
    ENTONCES Carga = 15 kW
    Justificación experta: El compresor de 15 kW opera típicamente entre 12 kW y 22 kW.
```

---

## 3. Contraste Empírico: Inducción vs. Deducción

El modelo inductivo se entrena con tres casos prototípicos: `(15 kW, 15)`, `(40 kW, 40)` y `(90 kW, 90)`. Siguiendo el algoritmo inductivo estándar de árboles de decisión (Breiman et al., 1984), los cortes se sitúan en los puntos medios entre ejemplos contiguos:
- Corte 1: `(15 + 40) / 2 = 27.5 kW`
- Corte 2: `(40 + 90) / 2 = 65.0 kW`

Al evaluar ambos modelos sobre seis casos de prueba representativos de la operación real (`PRUEBA`):

| Salto |ΔP| (kW) | Verdad (kW) | Regla Experto | Regla Inducida | Diagnóstico Físico del Error |
|---|---|---|---|---|
| **55.0** | 40 | 40 ✔ | 40 ✔ | Bomba a plena carga: ambos aciertan. |
| **70.0** | 90 | 90 ✔ | 90 ✔ | Motor principal a baja carga: ambos aciertan. |
| **30.0** | 40 | 40 ✔ | 40 ✔ | Bomba en vacío: ambos aciertan. |
| **20.0** | 15 | 15 ✔ | 15 ✔ | Compresor a régimen nominal: ambos aciertan. |
| **62.0** | 90 | 90 ✔ | **40 ✘** | Motor arrancando con carga pesada: **la regla inducida falla** porque su corte (65 kW) quedó demasiado alto por falta de ejemplos intermedios. |
| **26.0** | 15 | **40 ✘** | 15 ✔ | Compresor con sobrepresión momentánea: **la regla del experto falla** porque fijó su umbral rígidamente en 25 kW. |

---

## 4. Análisis de Matrices de Confusión

Ambas reglas obtienen una **exactitud idéntica de 83.33 % (5/6)**, pero sus matrices de confusión revelan naturalezas operativas completamente distintas:

### Matriz de Confusión — Regla del Experto
```text
Verdad \ Predicho | 15 kW | 40 kW | 90 kW
------------------+-------+-------+-------
15 kW             |   1   |   1   |   0    (Confunde 15 con 40 en ΔP=26)
40 kW             |   0   |   2   |   0
90 kW             |   0   |   0   |   2
```

### Matriz de Confusión — Regla Inducida
```text
Verdad \ Predicho | 15 kW | 40 kW | 90 kW
------------------+-------+-------+-------
15 kW             |   2   |   0   |   0
40 kW             |   0   |   2   |   0
90 kW             |   0   |   1   |   1    (Confunde 90 con 40 en ΔP=62)
```

> **Lección Fundamental:** Dos modelos con la misma exactitud global pueden tener impactos operacionales radicalmente distintos. Para un sistema de mantenimiento preventivo, confundir un motor crítico de 90 kW con una bomba auxiliar de 40 kW (error de la regla inducida) es mucho más grave que subestimar un transitorio menor del compresor.

---

## 5. Script Reproducible

Para ejecutar y validar este análisis en consola:
```bash
python docs/ejemplos/ejemplo_issue_12.py
```
Código y tests automatizados: ↗ [docs/ejemplos/ejemplo_issue_12.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/docs/ejemplos/ejemplo_issue_12.py) y ↗ [tests/unit/test_aprendizaje_inductivo_deductivo.py](file:///home/agustin/proyectos_software/datamaq/datamaq-ml/tests/unit/test_aprendizaje_inductivo_deductivo.py).
