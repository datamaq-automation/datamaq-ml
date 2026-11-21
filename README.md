# datamaq-ml

Motor de Machine Learning para **Monitoreo No Intrusivo de Cargas (NILM Industrial)** de DataMaq.

A partir del consumo general de un transformador o acometida de planta (TGBT), detecta automáticamente qué equipos se encienden y se apagan, agrupando escalones de potencia ($\Delta P, \Delta Q$) mediante **DBSCAN** y clasificándolos con árboles de decisión CART y aprendizaje en espacio de versiones (*Version Space Learner*).

## Cómo funciona

1. **Datos:** Potencia activa total ($P$) y reactiva ($Q$) en intervalos de 5 minutos (300 segundos).
2. **Eventos:** Detección de escalones $|\Delta P| \ge \text{umbral}$ entre muestras consecutivas (encendidos $\uparrow$ y apagados $\downarrow$).
3. **Clustering:** DBSCAN agrupa los eventos por densidad de potencia. Cada cluster resultante representa una máquina candidata con su potencia típica y firma reactiva.
4. **Asignación y Explicabilidad:** Extracción de reglas conjuntivas y clasificación supervisada para actualizar el catálogo de máquinas inferidas y horómetros digitales.

## Comandos Principales (`run.sh`)

```bash
./run.sh dev         # Levanta el servidor FastAPI con reload automático en puerto 8000
./run.sh train       # Identifica las cargas de data/input/ y exporta resultados
./run.sh simulate    # Genera tablero simulado con cargas conocidas para benchmarking
./run.sh evaluate    # Evalúa precisión y sensibilidad contra la verdad conocida
./run.sh supervise   # Entrena clasificador supervisado CART
./run.sh test        # Ejecuta suite completa de pruebas unitarias y de arquitectura
./run.sh lint        # Comprueba estilo y formato con ruff
```

## Arquitectura

Implementado bajo **Clean Architecture** estricta:
- `src/domain/cargas/`: Entidades puras, reglas de negocio, simulación y Version Space Learner.
- `src/application/cargas/`: Casos de uso de identificación, inducción de reglas y DTOs fuertemente tipados.
- `src/infrastructure/`: Scikit-learn (DBSCAN, CART, Naive Bayes, KNN), FastAPI REST endpoints y repositorios CSV/SSH.
