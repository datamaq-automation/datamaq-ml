# Guía de Integración: Secuencias de Análisis y Contratos entre Etapas

Un sistema de desagregación energética o de Machine Learning industrial está estructurado como una **cadena secuencial de etapas** (*pipeline*), donde la salida de cada fase alimenta de forma determinista la entrada de la fase subsiguiente.

---

## 1. La Necesidad de Contratos Fuertemente Tipados

En proyectos colaborativos o al integrar bibliotecas externas (como `scikit-learn`), pasar estructuras débiles como `dict` genéricos o tuplas anónimas introduce **fallas silenciosas**:
- Un error de formato o unidad (ej. pasar segundos en vez de minutos, o $\text{W}$ en vez de $\text{kW}$) no se manifiesta en la etapa culpable, sino muchas etapas después, distorsionando la estimación de energía y diagnóstico de fallas.
- **Principio Fail-Fast:** Cada etapa debe validar explícitamente sus precondiciones y postcondiciones mediante DTOs inmutables (`dataclass(frozen=True)` o `BaseModel` de Pydantic), lanzando `ContratoVioladoError` de inmediato ante cualquier discrepancia.

---

## 2. Las Cuatro Etapas de Análisis NILM

| Etapa | Componente | Entrada (Precondición) | Salida (Postcondición / Contrato) | Responsabilidad |
|---|---|---|---|---|
| **1. Diferencias** | `DiferenciasContrato` | `Sequence[float]` ($\text{kW}$ por minuto, longitud $\ge 2$) | `list[float]` ($\Delta P$ en $\text{kW}$) | Computa gradientes discretos adyacentes $\Delta P_t = P_t - P_{t-1}$. |
| **2. Detección** | `DeteccionEventosContrato` | `Sequence[float]` ($\Delta P$) + `umbral_kw > 0` | `list[EventoDetectadoDTO]` | Aísla transitorios significativos preservando el índice temporal exacto. |
| **3. Agrupamiento** | `AgrupamientoContrato` | `Sequence[EventoDetectadoDTO]` | `dict[float, list[EventoDetectadoDTO]]` | Agrupa los eventos por magnitud de potencia $|\Delta P|$. |
| **4. Resumen** | `ResumenContrato` | `dict[float, list[EventoDetectadoDTO]]` | `ResumenCargasDTO` | Consolida el conteo total de eventos y catálogo de magnitudes de carga. |

---

## 3. Integración Híbrida: Código Propio, de Pares y Externo

En una arquitectura limpia:
1. **Librería Propia de Dominio:** Implementa las reglas matemáticas y de negocio (`EventoDetectadoDTO`, `ResumenCargasDTO`, invariantes físicas).
2. **Componente de un Compañero:** Puede implementar un detector alternativo (ej. basado en estadísticos móviles o filtro CUSUM). Siempre que devuelva `list[EventoDetectadoDTO]`, la cadena continúa operando sin alteración.
3. **Librería Externa (ej. `scikit-learn`):** Puede reemplazar la etapa 3 utilizando `DBSCAN(eps=...)` o `KMeans`. El adaptador de infraestructura es responsable de transformar los `EventoDetectadoDTO` a matrices NumPy para `sklearn` y mapear las etiquetas resultantes nuevamente al contrato esperado por la Etapa 4.

---

## 4. Rúbrica de Colaboración e Integración en Equipo

| Nivel | Definición de Contratos | Manejo de Excepciones | Integración de Componentes |
|---|---|---|---|
| **Inicial** | Se intercambian diccionarios planos sin validación; los errores ocurren en tiempo de ejecución avanzado. | El código ignora fallas o lanza `KeyError`/`IndexError` genéricos sin contexto. | Cada integrante trabaja en ramas aisladas sin tests de integración comunes. |
| **Competente** | Contratos tipados documentados; se verifican tipos básicos en las funciones principales. | Se emiten excepciones personalizadas ante valores fuera de rango. | Se combinan etapas de diferentes miembros corriendo un script de prueba conjunto. |
| **Avanzado** | DTOs inmutables tipados y validados con pre/postcondiciones estrictas. | Errores semánticos de contrato (`ContratoVioladoError`) con mensajes claros y trazabilidad. | Suite automatizada de integración CI/CD que simula rotura de contratos y valida interoperabilidad con `scikit-learn`. |
