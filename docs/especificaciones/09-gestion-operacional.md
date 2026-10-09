# Reporte #9 · Gestión operacional clínica

> Especificación del reporte. Define datos, páginas y medidas para que el generador, el modelo
> PBIP y la guía se construyan contra un mismo contrato.

**Estado:** construido el 2026-10-09 (pendiente Desktop y publicación) · **Slug:** `gestion-operacional` · **Tema:** Gestión operacional · Salud

## Qué resuelve

Los reportes #1 a #8 miran la empresa de Salud desde las finanzas y las personas. Este reporte la
mira desde **la operación**: lo que hace una Gerencia de Gestión Operacional en una clínica.

- ¿Cuánta capacidad tenemos y cuánta usamos (camas, pabellones, box)?
- ¿Dónde se pierde capacidad sin que nadie la use: estada sobre la norma, cirugías suspendidas,
  primeras cirugías tarde, inasistencias?
- ¿Cumple la urgencia sus tiempos? ¿Cuánto espera cama un paciente que ya debe hospitalizarse?
- ¿Responde a tiempo el apoyo diagnóstico, sobre todo cuando lo pide urgencia?
- ¿Qué línea y qué previsión dejan margen después de sus costos directos?
- ¿Cuánta capacidad y margen se recuperan sin invertir, actuando sobre la estada y las suspensiones?

## Datos

Solo la empresa de Salud de la vitrina, **Red Asistencial Ejemplo S.A.**, con sus tres clínicas
(Oriente, Centro y Poniente), de enero de 2025 a septiembre de 2026 (los meses con Real en el #1).
Las clínicas tienen **volúmenes de tamaño real**: 396 camas, 18 pabellones y unas 18.000 atenciones
de urgencia al mes. Por eso los ingresos **no cuadran con el #1**, donde la empresa de Salud está a
escala de ejemplo. Lo que sí cuadra es la producción con la operación: los días cama facturados son
los ocupados, las cirugías son las realizadas, y lo mismo con atenciones, consultas y exámenes.

Generador: `data/generar_gestion_operacional.py` (`SEMILLA = 42`) → `data/gestion-operacional/`.

| Archivo | Grano | Columnas principales |
|---|---|---|
| `sucursales.csv` | clínica | `sucursal, empresa, orden` |
| `lineas.csv` | línea de producción | `linea, area, unidad, orden` |
| `metas.csv` | indicador | `indicador, area, meta, sentido, formato, orden` |
| `camas.csv` | clínica × servicio × mes | `camas_dotadas, dias_cama_disponibles, dias_cama_ocupados, egresos, dias_estada, dias_estada_esperados, reingresos_30d` |
| `pabellones.csv` | clínica × especialidad × mes | `horas_habilitadas, horas_programadas, horas_utilizadas, cirugias_programadas, cirugias_realizadas, cirugias_suspendidas, primeras_del_dia, primeras_a_la_hora` |
| `suspensiones.csv` | clínica × causa × mes | `causa, evitable, suspendidas` |
| `urgencia.csv` | clínica × categoría de triage × mes | `meta_minutos, atenciones, atenciones_en_meta, minutos_espera, abandonos, hospitalizados, horas_espera_cama` |
| `ambulatorio.csv` | clínica × especialidad × mes | `horas_box, horas_ofertadas, horas_agendadas, consultas_agendadas, consultas_realizadas, inasistencias, lista_espera, dias_tercer_cupo` |
| `apoyo.csv` | clínica × unidad × origen × mes | `meta_minutos, examenes, examenes_en_meta, minutos_respuesta` |
| `produccion.csv` | clínica × línea × previsión × mes | `prestaciones, ingreso, costo_personal, costo_insumos, costo_honorarios` |

**Costos:**
- El **personal** es fijo en el mes, porque la dotación se paga igual con la cama vacía.
- Los **insumos** son variables con las prestaciones.
- Los **honorarios** son variables con el ingreso.

Por eso el simulador valoriza la capacidad recuperada al **margen variable**.

## Modelo

Estrella sin caminos ambiguos:
- `sucursales` y `Calendario` filtran las siete tablas de hechos;
- `lineas` filtra `camas` y `produccion`;
- `metas` y los dos parámetros what-if (`Reducción de estada` y `Reducción de suspensiones`) quedan desconectados.

## Páginas

| # | Página | Qué muestra |
|---|---|---|
| 1 | **Portada** | Cuatro KPI, la ocupación y la urgencia por mes, y dos frases calculadas (mes más exigido; clínica que más suspende) |
| 2 | **Tablero de indicadores** | 13 indicadores contra su meta, con semáforo, y el corte por clínica |
| 3 | Hospitalizado | Ocupación, estada media, IEMA, rotación y reingresos por servicio y mes |
| 4 | Pabellones | Utilización, suspensiones (Pareto de causas), primera cirugía a la hora, por clínica y especialidad |
| 5 | Urgencias | Espera por categoría de triage, abandono, hospitalización y espera de cama |
| 6 | Ambulatorio | Utilización de box, ocupación de agenda, inasistencia, lista de espera y tercer cupo |
| 7 | Apoyo diagnóstico | Laboratorio e imagenología por origen: volumen y TAT en meta |
| 8 | Capacidad liberable | What-if: reducir la estada sobre la norma y las suspensiones evitables; camas equivalentes y margen recuperado |
| 9 | Rentabilidad por línea | Ingreso, costo directo y margen de contribución por área, línea y previsión |
| 10 | **Glosario** | Conceptos y medidas, generado desde el TMDL |

## Medidas DAX clave

- `Ocupación de camas %` = días cama ocupados ÷ disponibles.
- `Índice de estada (IEMA)` = días de estada ÷ días esperados según la norma.
- `Días de estada sobre la norma`: suma, fila a fila, de los días de estada sobre los esperados.
- `Suspensión de cirugías %` y `Suspensiones evitables %`.
- `Atenciones en meta de espera %` según la meta de cada categoría de triage.
- `Espera de cama promedio (h)`.
- `Margen de contribución` y `Margen variable por prestación`.
- `Valor del indicador`: un `SWITCH` sobre la fila de `metas` que alimenta el semáforo.
- `Margen por estada recuperada`: un `SUMX` por servicio, porque cada servicio tiene su propio margen por día cama.

## Historias sembradas en los datos

| Tema | Resultado | Historia |
|---|---|---|
| Invierno | 92% de ocupación en jul 2026 | UCI y pediatría llegan a 97%. La espera de cama en urgencia sube a 6,2 h y las atenciones en meta caen a 67% |
| Pabellones | 15,4% de suspensión en Poniente | Es el doble que en Oriente. Más de 9 de cada 10 suspensiones son evitables y solo el 45% de las primeras cirugías parte a la hora |
| Estada | IEMA 1,26 en médico-quirúrgico de Centro | Los pacientes se quedan 26% más de lo que indica la norma. Centro tiene la espera de cama más alta y su imagenología de urgencia cae a 69% en meta en invierno |

Otros hallazgos del dato:
- Fonasa queda con un margen de contribución levemente negativo.
- Pediatría pierde plata fuera del invierno, porque su dotación es fija.
- Dermatología tiene 22% de inasistencia.
- La lista de espera de oftalmología crece todos los meses.

## Habilidades para el catálogo

Indicadores hospitalarios (ocupación, IEMA, rotación) · Eficiencia de pabellones y Pareto de
suspensiones · Tiempos de urgencia por categoría de triage · Tablero de metas con semáforo ·
What-if de capacidad liberable · Margen de contribución por línea y previsión · Proyecto PBIP
versionado en Git
