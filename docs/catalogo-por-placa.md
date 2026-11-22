# Catálogo por placa: firma esperada de cada motor

El catálogo por placa dice qué debería ver el medidor de cada motor, antes de que `train` descubra nada.
Sirve para comparar: si train encuentra un modo donde la placa dice que debe haber un motor, el hallazgo tiene
respaldo; si no lo encuentra, hay un motor que no se ve.

## Formato del CSV

| Columna | Obligatoria | Qué es |
|---|---|---|
| `etiqueta` | sí | Nombre del motor en el catálogo. Única en el archivo. |
| `potencia_nominal_kw` | sí | Potencia de placa, mayor que cero. |
| `trafo` | sí | Trafo o medidor al que alimenta. |
| `tipo_proceso` | sí | Proceso (bombeo, mezcla, transporte…). Informativo. |
| `forma_arranque` | sí | Una de: `directo`, `estrella_triangulo`, `variador`, `arranque_suave`. |
| `cos_phi` | no | Factor de potencia típico. Si falta, 0,85. Debe estar en (0, 1]. |

Un ejemplo sintético está en `docs/ejemplos/placas_sinteticas.csv`. El catálogo real de motores **no** se versiona:
se lee desde una ruta local.

## Qué se espera ver según la forma de arranque

La potencia de placa y el cos φ dan la reactiva esperada: `Q = P · tan(arccos cos φ)`. Con cos φ 0,85, la
relación ΔQ/ΔP es 0,62. La forma de arranque cambia qué escalón ve el medidor:

| Forma de arranque | Escalón visible | Cómo se compara |
|---|---|---|
| `directo` | Un escalón de P al arrancar. | Un modo de train debe caer en P (± tolerancia). |
| `estrella_triangulo` | Dos escalones: P/3 en estrella y 2P/3 al pasar a triángulo. | Un modo debe caer en P/3 o en 2P/3. Un modo en P no es este motor. |
| `variador` | Rampa de frecuencia, sin escalón único. | No se compara como escalón: el resultado es `sin_escalon`. |
| `arranque_suave` | Rampa de tensión, sin escalón único. | Igual que el variador: `sin_escalon`. |

La reactiva también depende de la forma: en estrella el motor toma menos corriente, así que el escalón de P/3
trae una Q de la misma forma (la relación ΔQ/ΔP se mantiene); en variador y arranque suave, la relación
depende del control y no se puede fijar desde la placa. Esta tabla es una hipótesis de trabajo: hay que
validarla con los arranques medidos.

## Comparar contra train

```bash
python -m src.infrastructure.cli.comparar_placas \
  --placas <ruta local al catálogo>.csv \
  --cargas output/cargas_<medidor>.csv \
  --tolerancia-kw 5 \
  --salida-json output/comparacion.json
```

El log da solo conteos: motores, coinciden, forma distinta, sin modo, sin escalón. El JSON da el detalle por
motor: el modo que coincidió, su ΔQ/ΔP observada, la esperada y la nota de la forma de arranque.

Estados posibles:
- `coincide`: hay un modo en la potencia (o en un escalón) y su ΔQ/ΔP está a ±0,15 de la esperada.
- `coincide_forma_distinta`: hay modo, pero la relación de reactiva no es la esperada.
- `sin_modo`: no hay ningún modo a menos de la tolerancia.
- `sin_escalon`: la forma de arranque no deja un escalón que se pueda emparejar.
