# Guía: Gestión operacional clínica

> Reporte de gestión operacional en Power BI para una red de tres clínicas: capacidad y uso de camas, pabellones, urgencia, ambulatorio y apoyo diagnóstico; un tablero de 13 indicadores contra su meta; la capacidad que se recupera sin invertir y el margen de cada línea. Todos los datos son sintéticos.

## Qué resuelve

Los otros reportes miran la empresa de Salud desde las finanzas y las personas. Este la mira desde **la operación**, y responde cinco preguntas:
- ¿cuánta capacidad hay y cuánta se usa: camas, pabellones y box?
- ¿dónde se pierde capacidad sin que nadie la use: estada sobre la norma, cirugías suspendidas, primeras cirugías tarde o inasistencias?
- ¿cumple la urgencia sus tiempos y cuánto espera cama un paciente que ya debe hospitalizarse?
- ¿responde a tiempo el laboratorio y la imagenología cuando los pide urgencia?
- ¿qué línea y qué previsión dejan margen, y cuánto margen se recupera si se libera capacidad?

## Datos

Es la empresa de Salud de la vitrina, **Red Asistencial Ejemplo S.A.**, con sus tres clínicas (Oriente, Centro y Poniente), de enero de 2025 a septiembre de 2026. Las clínicas tienen volúmenes de tamaño real: 396 camas, 18 pabellones y unas 18.000 atenciones de urgencia al mes. Por eso los ingresos **no cuadran con el reporte Presupuesto vs. Real**, donde la empresa de Salud está a escala de ejemplo. Lo que sí cuadra es la **producción con la operación**: los días cama facturados son los ocupados, las cirugías son las realizadas, y lo mismo con atenciones, consultas y exámenes.

| Archivo | Grano | Para qué |
|---|---|---|
| `camas.csv` | clínica × servicio × mes | camas, días cama, egresos, estada real y esperada, reingresos |
| `pabellones.csv` | clínica × especialidad × mes | horas habilitadas y utilizadas, cirugías programadas, realizadas y suspendidas, puntualidad |
| `suspensiones.csv` | clínica × causa × mes | por qué se suspende y si era evitable |
| `urgencia.csv` | clínica × categoría de triage × mes | atenciones, espera frente a la meta, abandonos y espera de cama |
| `ambulatorio.csv` | clínica × especialidad × mes | box, agenda, consultas, inasistencias, lista de espera y tercer cupo |
| `apoyo.csv` | clínica × unidad × origen × mes | exámenes y tiempo de respuesta (TAT) |
| `produccion.csv` | clínica × línea × previsión × mes | prestaciones, ingreso y costos directos (personal, insumos y honorarios) |
| `metas.csv`, `lineas.csv`, `sucursales.csv` | dimensión | metas de los indicadores, líneas con su área, clínicas |

Se generan con `data/generar_gestion_operacional.py` (semilla fija).

**Las tres historias:**
- **Invierno:** en julio de 2026 la ocupación llega a **92%**, con UCI y pediatría en 97%. La espera de cama en urgencia sube a **6,2 horas**, casi el triple que en enero, y las atenciones en meta caen a 67%.
- **Pabellones de la Clínica Poniente:** suspende el **15,4%** de sus cirugías, el doble que Oriente. Más de 9 de cada 10 suspensiones son evitables (paciente no preparado, atraso de la cirugía anterior) y solo el 45% de las primeras cirugías del día parte a la hora.
- **Estada en la Clínica Centro:** médico-quirúrgico tiene un **IEMA de 1,26**: los pacientes se quedan 26% más de lo que indica la norma. Esas camas inmovilizadas se notan en la espera de cama más alta de la red, y su imagenología de urgencia cae a 69% en meta durante el invierno.

Además, Fonasa queda con margen de contribución levemente negativo, pediatría pierde plata fuera del invierno porque su dotación es fija y dermatología tiene 22% de inasistencia.

## Modelo

- **Power Query** lee los CSV desde GitHub con la misma función `LeerCsv` de los otros reportes.
- **Estrella sin caminos ambiguos:**
  - `sucursales` y `Calendario` filtran las siete tablas de hechos;
  - `lineas` filtra `camas` y `produccion`, así un servicio clínico se ve igual en la ocupación y en la rentabilidad.
- **Tablero de metas desconectado:** `metas` trae cada indicador con su meta y su sentido («mayor» o «menor»). Una medida con `SWITCH` calcula el valor de cada fila y otra decide el color del semáforo.
- **Dos parámetros what-if:** `Reducción de estada` y `Reducción de suspensiones`, de 0% a 100%. Por defecto abren en 30% y 50%.

## Medidas clave

```dax
Ocupación de camas % = DIVIDE([Días cama ocupados], [Días cama disponibles])

Índice de estada (IEMA) = DIVIDE(SUM(camas[dias_estada]), SUM(camas[dias_estada_esperados]))

Días de estada sobre la norma = SUMX(camas, MAX(0, camas[dias_estada] - camas[dias_estada_esperados]))

Suspensión de cirugías % = DIVIDE([Cirugías suspendidas], [Cirugías programadas])

Margen variable = [Ingreso total] - [Costo de insumos] - [Costo de honorarios]

Margen por cirugías recuperadas = [Cirugías recuperables] * CALCULATE([Margen variable por prestación], lineas[linea] = "Pabellón")
```

Algunas decisiones de diseño:
- **Días sobre la norma fila a fila:** con `SUMX` y `MAX(0, …)`, un servicio que se queda bajo la norma no compensa a otro que se pasa. Lo que se mide es capacidad inmovilizada, no un promedio.
- **El simulador valoriza al margen variable, no al de contribución:** la dotación ya está pagada. Una cama liberada o una cirugía recuperada suma ingreso menos insumos y honorarios. Usar el margen de contribución subestimaría el valor de la capacidad.
- **Margen por estada servicio a servicio:** `Margen por estada recuperada` recorre los servicios con `SUMX`, porque un día de UCI no vale lo mismo que uno de maternidad.
- **Lista de espera al cierre:** es un saldo, no un flujo. Se lee en el último mes del periodo; sumarla mes a mes la inflaría.
- **Tablero con semáforo:** el color sale de una medida (`Color del estado`) aplicada como fondo condicional. Cambiar una meta es editar una fila de `metas.csv`, sin tocar el modelo.

## Cómo leerlo

1. **Portada:** el mes más exigido y la clínica que más suspende, en dos frases calculadas.
2. **Tablero de indicadores:** qué está en rojo, en el periodo y la clínica elegidos.
3. **Páginas por área:** abren cada rojo. Hospitalizado (estada), pabellones (causas), urgencia (categorías), ambulatorio (especialidades) y apoyo (unidad y origen).
4. **Capacidad liberable:** con los valores por defecto (30% de la estada sobre la norma y 50% de las suspensiones evitables) se liberan unas **7 camas equivalentes** y **1.664 cirugías**, con **$2.643 millones** de margen variable en los 21 meses.
5. **Rentabilidad:** qué línea y qué previsión sostienen el margen.
