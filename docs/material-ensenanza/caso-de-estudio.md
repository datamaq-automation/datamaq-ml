# Caso de estudio — identificar las cargas de una planta papelera a partir de su acometida

> **NO COMPARTIR con estudiantes.** Este documento contiene resultados derivados de mediciones reales de una planta.
> Solo puede compartirse con estudiantes cuando conste el consentimiento escrito de la empresa para ese uso
> (ver `README.md`). Hasta entonces, es material del docente. Los ejercicios de los estudiantes se hacen con el
> tablero sintético.

## 1. La situación

Una planta papelera tiene dos acometidas de transformador (medidores **Trafo 1** y **Trafo 2**, nombres seudonimizados).
Cada una mide la potencia activa total cada 5 minutos. Ninguna tiene el detalle de qué equipos se encienden: el
tablero general mezcla las cargas de la preparación de pasta y de la máquina papelera continua.

La pregunta de la planta: **¿qué equipos hay detrás de esta curva, cuándo arrancan y cuánto tiempo trabajan?** Con esa
respuesta se puede planificar el mantenimiento y medir la disponibilidad de cada equipo sin instrumentarlo uno por uno.

## 2. Los datos

- Tres semanas de mediciones por acometida (21 días completos analizados).
- Solo **potencia activa**. No hay potencia reactiva en este conjunto, y eso cambia qué se puede concluir (sección 5).
- Muestreo de 5 minutos: 288 muestras por día en condiciones normales. Algunos días tienen brechas de más de 5 minutos.

## 3. Lo que se hizo

1. **Detectar los escalones.** Un escalón es un cambio de potencia entre dos muestras consecutivas. El umbral se elige
   con el método de Otsu, que separa el ruido de los cambios grandes. Resultado: entre 23 y 65 escalones por día con
   el umbral automático; con un umbral de 5 kW aparecen entre 110 y 250.
2. **Buscar candidatos a equipos sin etiquetas.** DBSCAN sobre las magnitudes de los escalones. Con el umbral
   automático, cada acometida da un grupo principal: uno de unos 91 kW en la primera y uno de unos 75 kW en la segunda.
   Con un umbral fijo de 5 kW aparecen grupos más pequeños, pero cambian al mover el umbral: no son estables.
3. **Atribuir intervalos.** Cada encendido se empareja con su apagado cuando la firma coincide, y el intervalo se mide
   con las mediciones reales (no con la potencia nominal del equipo).
4. **Validar sin verdad de terreno.** No hay forma de saber qué equipo se encendió. Se miden consistencia, cierres y
   plausibilidad.

## 4. Resultados agregados

Energía medida del día (integral de la potencia): **mediana de unos 5 500 kWh** en la primera acometida y **unos
3 500 kWh** en la segunda. En fin de semana baja a unos 2 500 a 3 900 kWh.

| Medida | Trafo 1 | Trafo 2 |
|---|---|---|
| Porcentaje de energía atribuida a la carga candidata (catálogo automático) | 3 % a 18 % | −8 % a 18 % |
| Escalones sin atribuir (catálogo automático) | 17 % a 53 % (mediana 32 %) | 36 % a 64 % (mediana 48 %) |
| Días con energía atribuida mayor que la medida | 0 de 21 | 0 de 21 |
| Intervalos abiertos al final del día | 0 o 1 por día | 0 o 1 por día |
| Intervalos cortados por un escalón ajeno | 0 a 2 por día | 0 a 3 por día |

Hallazgo que vale contar en clase: al principio, algunos intervalos daban **energía negativa** (hasta
−1 600 kWh en un día), porque se cerraban con un apagado que no era de su equipo. Se corrigió el motor: un apagado que
deja la potencia por debajo de la base cierra el intervalo en ese punto. Después de la corrección, la primera
acometida no tiene intervalos negativos y la segunda tiene dos, de muy baja confianza.

Plausibilidad de una carga: en fin de semana, la carga de 91 kW de la primera acometida aparece en 9 intervalos que
suman unas 8 horas y 608 kWh. Eso da una potencia media de unos 74 kW, coherente con una carga de ese tamaño.

## 5. Qué se puede concluir y qué no

**Sí se puede concluir**:
- La energía atribuida nunca supera la medida: el motor no inventa consumo.
- Los intervalos se cierran donde corresponde, incluso al final del día (no a las 23:59:59).
- Hay al menos una carga grande que arranca y para de forma repetible.
- El catálogo es incompleto: la mitad o más de los escalones no se explican con él.

**No se puede concluir**:
- **Qué equipo es cada grupo.** Con potencia activa sola, equipos de potencia parecida se mezclan.
- **Exactitud, precisión ni F1.** No hay verdad de terreno: la spec pide F1 ≥ 0,90, y con estos datos ese criterio
  no se puede verificar.
- **Los clusters de motores IEC** del análisis previo: dependían de la reactiva, que no está en este conjunto.
- **Ciclos de menos de 5 minutos**: el muestreo no los ve.
- **Si la hora de las mediciones es UTC o local**: el análisis supone UTC. Un corrimiento de horas cambia qué día es
  cada día.

## 6. Preguntas para el estudiante (cuando el caso esté habilitado)

1. El porcentaje atribuido es bajo. ¿Eso es un problema del motor, del catálogo o de los datos? ¿Cómo lo distinguirían?
2. Una carga de 91 kW con 8 horas de marcha a 74 kW de potencia media. ¿Qué les llamaría la atención, y qué dato
   pedirían para confirmarlo?
3. ¿Qué cambiarían primero: la tolerancia del grupo, el umbral, o agregar la reactiva? Justifiquen con la práctica
   E7 (k-medias frente a DBSCAN) sobre el tablero sintético.
4. Diseñen una prueba de consistencia nueva que habría detectado la energía negativa antes de que llegara a un informe.
