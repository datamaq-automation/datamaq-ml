# datamaq-ml

Motor de Machine Learning para **Monitoreo No Intrusivo de Cargas (NILM Industrial)** de DataMaq.

A partir del consumo general de un transformador o acometida de planta (TGBT), detecta automáticamente qué equipos se encienden y se apagan, agrupando escalones de potencia ($\Delta P, \Delta Q$) mediante **DBSCAN** y clasificándolos con árboles de decisión CART y aprendizaje en espacio de versiones (*Version Space Learner*).

## Cómo funciona

1. **Datos:** Potencia activa total ($P$) y reactiva ($Q$) en intervalos de 5 minutos (300 segundos).
2. **Eventos:** Detección de escalones $|\Delta P| \ge \text{umbral}$ entre muestras consecutivas (encendidos $\uparrow$ y apagados $\downarrow$).
3. **Clustering:** DBSCAN agrupa los eventos por densidad de potencia. Cada cluster resultante representa una máquina candidata con su potencia típica y firma reactiva.
4. **Asignación y Explicabilidad:** Extracción de reglas conjuntivas y clasificación supervisada para actualizar el catálogo de máquinas inferidas y horómetros digitales.

## Puesta en marcha

Requisitos: Python 3.10 o superior.

```bash
./run.sh install                  # crea .venv y sincroniza dependencias
cp .env.example .env              # opcional: solo para sobreescribir valores por defecto
```

El archivo `.env` es local y **no se versiona**. No pongas secretos en el repo: el acceso a la VPS se configura en `~/.ssh/config`.

## Datos de mediciones

> **Los datos reales no se versionan.** `data/input/` y `data/verdad/` están ignorados por Git,
> salvo el dataset sintético (`sintetico.csv`), que se genera con `./run.sh simulate`.
> Las mediciones de planta (`planta_*.csv`, symlinks de `data/input`) quedan solo en el equipo que las usa.

En modo local (`MEDICIONES_SOURCE=local`, valor por defecto), cada medidor es un archivo `data/input/<medidor>.csv`
con columnas `instante,potencia_kw`.

> **Nombre exacto del medidor:** el nombre distingue mayúsculas, minúsculas y espacios.
> Para la planta es **`Trafo arriba`** (con espacio) y **`Trafo abajo`**. Usar `Trafo_arriba` no funciona:
> el repositorio busca `data/input/<medidor>.csv` tal cual y devuelve `LookupError: Medidor desconocido`.

## Comandos principales (`run.sh`)

```bash
./run.sh dev          # Servidor FastAPI con reload automático en puerto 8000
./run.sh start prod   # Servidor FastAPI con datos desde la VPS (ver docs/PRODUCCION.md)
./run.sh train        # Identifica las cargas de data/input/ y exporta resultados a data/output/
./run.sh simulate     # Genera tablero simulado con cargas conocidas para benchmarking
./run.sh evaluate     # Evalúa precisión y sensibilidad contra la verdad conocida
./run.sh supervise    # Entrena clasificador supervisado CART
./run.sh disaggregate # Desagrega eventos y calcula horas de marcha por máquina (batch diario)
./run.sh test         # Suite completa de pruebas unitarias, de integración, e2e y de arquitectura
./run.sh gauntlet     # 11 reglas de arquitectura (tests/test_architecture.py)
./run.sh audit        # Código muerto y componentes Dios
./run.sh lint         # Estilo y formato con ruff
```

### Desagregación batch diaria (`disaggregate`)

```bash
./run.sh disaggregate "Trafo arriba" --fecha 2026-09-20 --potencia 91.0 --nombre "Compresor 1"
./run.sh disaggregate "Trafo arriba" --fecha 2026-09-20 --firmas config/firmas.json
```

- `medidor` (obligatorio): nombre exacto del medidor, por ejemplo `"Trafo arriba"`.
- `--fecha YYYY-MM-DD`: día cerrado a procesar. **Pasalo siempre**: si se omite, usa la fecha de hoy.
- `--firmas ARCHIVO.json`: catálogo de firmas confirmadas (lista de objetos con `machine_id`, `nombre`, `potencia_nominal_kw`, y opcionalmente `reactiva_tipica_kvar`, `tolerancia_kw`, `umbral_marcha_kw`).
- `--potencia`, `--reactiva`, `--nombre`, `--machine-id`: firma rápida para una sola máquina, sin archivo.

Estado actual: el comando **imprime el resumen en el log y no persiste resultados** (horas, ciclos y energía por máquina). Pendientes conocidos: lectura de la potencia reactiva Q desde la fuente, energía medida (hoy se usa la potencia nominal de la firma) y persistencia de los resultados.
Si `--firmas` apunta a un archivo inexistente, el comando no falla: procesa cero firmas y sale con código 0.

## Configuración

Las variables están centralizadas en `src/infrastructure/settings/config.py` con valores por defecto.
`.env.example` documenta las que suelen cambiar.

## Arquitectura

Implementado bajo **Clean Architecture** estricta:
- `src/domain/cargas/`: Entidades puras, reglas de negocio, simulación y Version Space Learner.
- `src/application/cargas/`: Casos de uso de identificación, inducción de reglas, atribución batch y DTOs fuertemente tipados.
- `src/infrastructure/`: Scikit-learn (DBSCAN, CART, Naive Bayes, KNN), FastAPI REST endpoints, repositorios CSV y SSH, y CLI.

Documentación de producción (modo SSH, VPS, systemd): `docs/PRODUCCION.md`.
