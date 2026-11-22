# Material de enseñanza — identificación de cargas con datos reales

Material para el módulo «Procesamiento de Aprendizaje Automático»: aprendizaje supervisado y no supervisado,
validación y verificación de modelos, sobre un problema real (identificar las cargas de una planta a partir de la
potencia total de su acometida, NILM).

## Estado: solo con datos sintéticos

> **Condición bloqueante.** No se entregan datos reales, ni anonimizados, a estudiantes hasta contar con el
> consentimiento escrito de la empresa para ese uso. Mientras tanto, todo el material se practica con el tablero
> **sintético** que genera `./run.sh simulate`. Los contenidos de este directorio que sí dependen de datos reales
> (el caso de estudio) están marcados como no compartibles.

## Qué hay en este directorio

| Archivo | Para quién | Contenido |
|---|---|---|
| `mapa-contenido.md` | docente y estudiantes | Qué temario cubre cada archivo del repo, y qué ejercicio lo usa |
| `ejercicios.md` | estudiantes | Ejercicios por bloque, con datos sintéticos |
| `practicas/practica_kmeans_dbscan.py` | estudiantes | Práctica de comparación k-medias frente a DBSCAN sobre los mismos escalones |
| `rubrica.md` | docente | Rúbrica referida a los referenciales para la evaluación del módulo |
| `caso-de-estudio.md` | docente | Situación real con resultados agregados. **No compartir** sin consentimiento |

Las guías previas del repo se reutilizan, no se duplican:
- `docs/cuaderno-alumno.md`: cuaderno de trabajo. Contiene referencias a datos reales en algunas actividades; esas
  actividades se hacen con el tablero sintético hasta el consentimiento.
- `docs/guia-docente.md`: guía docente **con respuestas. No es publicable a estudiantes.**
- `docs/guia-andamiaje-proyectos.md`: pautas de andamiaje para proyectos.

## Cómo regenerar los datos sintéticos

```bash
./run.sh install          # una vez
./run.sh simulate         # genera data/input/sintetico.csv y data/verdad/sintetico.csv
```

La verdad de terreno del tablero sintético (qué carga se encendió y cuándo) está en `data/verdad/`. Solo se usa
para evaluar; los estudiantes no la ven hasta la evaluación.

## Cómo se entregan los datos reales (cuando haya consentimiento)

1. El dueño genera el conjunto con `scripts/seudonimizar_mediciones.py`: reemplaza el nombre de la empresa y los
   identificadores de medidor, y verifica que instantes y potencias queden idénticos. La configuración vive fuera del
   repo.
2. La salida va a una carpeta **fuera de cualquier repositorio git**. El script se niega a escribir dentro de un repo.
3. El conjunto se entrega por fuera de git, con una nota de no redistribución (ver el README del repo, sección
   «Uso docente»).
4. Los datos reales nunca se suben a git, a un issue, a un PR, a un notebook ni a un log.

## No redistribuir

Los datos reales anonimizados son del cliente. Quien los reciba no los copia, no los publica y no los sube a
ningún servicio. Las potencias, las fechas y el sector se conservan a propósito: quien conozca el sector y la región
puede inferir de qué planta se trata, por eso la condición de consentimiento sigue vigente.
