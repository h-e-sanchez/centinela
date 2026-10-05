# Guía: Proyectos tecnológicos · entrega, capacidad y colaboración entre equipos

> Reporte de control de gestión en Power BI sobre la cartera de TI de tres empresas, armado desde el historial de un Jira ágil: cuándo termina de verdad cada proyecto, qué equipo está cargado y dónde se traba el trabajo cuando pasa de un equipo a otro. Todos los datos son sintéticos.

## Qué resuelve

Una oficina de proyectos o una gerencia de TI suele ver la cartera como porcentajes de avance escritos a mano. Este reporte la ve desde lo que registra Jira (estados con fecha y hora, puntos y horas) y responde tres preguntas:
- ¿qué proyectos van a tiempo y dentro del presupuesto, y **cuándo terminan de verdad**?
- ¿qué equipo está sobrecargado y cuál tiene holgura?
- ¿**dónde se traba el trabajo** cuando necesita algo de otro equipo?

## Datos

Son las **mismas tres empresas ficticias de los otros reportes de la vitrina**. Cada una tiene un área de TI con cinco equipos (Datos, Integraciones, Plataforma, Producto y QA; unas 22 personas) que ejecutan cuatro proyectos con sprints de dos semanas. La simulación corre día hábil a día hábil desde enero de 2025 hasta la **fecha de corte, el 30 de septiembre de 2026**; lo posterior se pronostica.

| Industria | Empresa | Proyectos |
|---|---|---|
| Manufactura | Manufacturas Ejemplo S.A. | migración de ERP, trazabilidad de lotes en planta, portal de distribuidores, mantenimiento predictivo |
| Energía | Energía Ejemplo S.A. | telemetría de centrales, despacho en tiempo real, facturación de clientes libres, ciberseguridad OT |
| Salud | Red Asistencial Ejemplo S.A. | ficha clínica electrónica, agenda en línea, integración con laboratorio, tablero de camas |

| Archivo | Grano | Para qué |
|---|---|---|
| `issues.csv` | issue (épica, historia, tarea o bug) | puntos, equipo, fechas de inicio y fin, estado al corte, días de ciclo y horas bloqueada |
| `transiciones.csv` | cambio de estado | el changelog de Jira: `por_hacer → en_curso → en_revision → hecho`, con `bloqueado` entremedio |
| `worklogs.csv` | persona × día × issue | horas registradas |
| `compromisos.csv` | sprint × issue | lo que el equipo comprometió y si lo terminó dentro del sprint |
| `dependencias.csv` | par de issues | qué issue esperó a cuál de otro equipo, y cuántas horas |
| `flujo_semanal.csv` | semana × proyecto × equipo × estado | la foto semanal para el diagrama de flujo acumulado |
| `capacidad_semanal.csv` | semana × equipo | horas de jornada disponibles |
| `pronostico_termino.csv`, `pronostico_distribucion.csv` | proyecto (y semana) | fechas P50, P85 y P95 del Monte Carlo y su distribución |
| `proyectos.csv`, `equipos.csv`, `empresas.csv`, `sprints.csv`, `personas_ti.csv`, `asignaciones.csv` | dimensión | fecha comprometida, presupuesto, tarifas y dedicación (algunas personas reparten la semana entre dos equipos) |

Se generan con `data/generar_proyectos_ti.py` (semilla fija) y se pueden reproducir.

**Cómo se simula:**
- **Alcance:** cada proyecto planifica sus puntos para calzar con la capacidad de sus equipos entre el inicio y la fecha comprometida.
- **Trabajo:** cada persona toma la siguiente issue de la cola de su equipo y la trabaja según su dedicación; algunos días se van en soporte.
- **Dependencias:** si a mitad del trabajo falta algo de otro equipo, la issue pasa a «bloqueado» y la persona toma otra cosa. Vuelve a la cola de uno a tres días hábiles después de que el otro equipo termina: es el traspaso.

**Las tres historias:**
- **Salud:** la ficha clínica crece un 28% en alcance en diciembre de 2025, y su P85 queda 75 días después de lo comprometido.
- **Energía:** Integraciones tiene un equipo corto, tareas subestimadas y despliega en ventanas semanales, así que concentra el 39% de las horas bloqueadas de la empresa.
- **Manufactura:** parte las historias grandes (máximo 5 puntos) y compromete con prudencia; el ERP cumple el 90% de lo comprometido y su P50 cae antes de la fecha comprometida.

## Modelo

- **Power Query** lee los CSV desde GitHub con la misma función `LeerCsv` de los otros reportes, y traduce los códigos de estado a nombres ordenados (Por hacer → Hecho).
- **Copo de nieve, sin caminos ambiguos:**
  - `empresas → proyectos → issues`, y desde `issues` cuelgan `worklogs`, `transiciones`, `compromisos` y `dependencias` (por la issue bloqueada). Así un filtro de industria o de proyecto llega a todo por un solo camino.
  - `equipos` filtra `issues`, `flujo_semanal`, `capacidad_semanal` y `asignaciones`.
  - `Calendario` filtra `worklogs`, `flujo_semanal`, `capacidad_semanal` y `sprints`. La relación con `issues[fecha_fin]` queda **inactiva**: si estuviera activa, habría dos caminos de `Calendario` a `worklogs`. Las medidas de throughput la activan con `USERELATIONSHIP`.
- **Segmentador dependiente:** el de proyecto lleva un filtro de visual `Puntos totales > 0`, así que solo muestra los de la empresa elegida.
- **El Monte Carlo se precalcula en Python.** DAX solo lee sus percentiles: un cálculo aleatorio dentro del modelo cambiaría con cada clic.

## Medidas clave

```dax
Puntos totales = CALCULATE(SUM(issues[puntos]), issues[tipo] <> "epica")

Avance % = DIVIDE([Puntos hechos], [Puntos totales])

Issues terminadas = CALCULATE(COUNTROWS(issues), issues[tipo] <> "epica", NOT ISBLANK(issues[fecha_fin]), USERELATIONSHIP(Calendario[Date], issues[fecha_fin]))

Previsibilidad % = DIVIDE([Completado], [Comprometido])

Tiempo de ciclo P85 (días) = CALCULATE(PERCENTILEX.INC(FILTER(issues, NOT ISBLANK(issues[dias_ciclo])), issues[dias_ciclo], 0.85), issues[tipo] <> "epica", NOT ISBLANK(issues[fecha_fin]), USERELATIONSHIP(Calendario[Date], issues[fecha_fin]))

Carga % = DIVIDE([Horas registradas], [Capacidad (h)])

Costo = SUMX(worklogs, worklogs[horas] * RELATED(personas_ti[tarifa_hora]))

% del tiempo en bloqueo = DIVIDE([Horas bloqueadas], [Horas bloqueadas] + [Horas registradas])

Atraso P85 (días) = MAX(pronostico_termino[atraso_p85_dias])
```

Algunas decisiones de diseño:
- **Previsibilidad sobre lo comprometido, no sobre lo terminado:** un equipo que termina mucho pero no lo que prometió no es previsible. Lo que se suma a mitad de sprint no cuenta como comprometido.
- **Percentiles en vez de promedios:** el tiempo de ciclo tiene cola larga (las issues bloqueadas). El P85 es el plazo que conviene prometer; el promedio lo subestima.
- **WIP a una fecha:** `WIP` y `Antigüedad del WIP (días)` miran el último día del periodo filtrado (o el corte), así que el mismo visual sirve para cualquier mes.
- **Pronóstico con throughput y no con puntos:** el Monte Carlo cuenta issues terminadas por semana, porque contar issues es más estable que sumar estimaciones.

## Cómo leerlo

| Medida | Qué significa |
|---|---|
| **Avance %** | Puntos hechos sobre el alcance actual, que incluye lo agregado después del inicio. |
| **Consumo de presupuesto %** | Costo acumulado al corte sobre el presupuesto aprobado. Si supera al avance, el proyecto gasta más rápido de lo que entrega. |
| **Previsibilidad %** | Parte de lo comprometido al inicio del sprint que llegó a «hecho» dentro del sprint. |
| **Tiempo de ciclo P50 / P85** | Días corridos de «en curso» a «hecho». El P85 es el plazo que se cumple en 85 de cada 100 issues. |
| **Carga %** | Horas registradas en proyectos sobre capacidad. Bajo 100% hay soporte u holgura; sobre 100%, sobretiempo. |
| **Horas bloqueadas** | Horas hábiles en «bloqueado». En la página de colaboración se atribuyen al equipo del que se esperaba. |
| **Fecha P85 / Atraso P85** | La fecha que el Monte Carlo cumple en el 85% de las simulaciones, y su distancia a la fecha comprometida. |

El reporte abre en **Energía**, la misma industria con que abren los demás reportes de la vitrina. Valores de control para revisar al abrir el reporte:

| Indicador | Energía (al abrir) | Las tres empresas (sin filtro) |
|---|---|---|
| Proyectos en curso al corte | 3 de 4 | 7 de 12 |
| Avance de la cartera | 91% | 89% |
| Costo / presupuesto | $2.348 M / $2.144 M (110%) | $7.340 M / $6.805 M (108%) |
| Previsibilidad | 72% | 79% |
| Tiempo de ciclo P50 / P85 (todas las terminadas) | 9 / 21 días | 9 / 18 días |
| WIP al corte | 42 issues | 114 issues |
| Tiempo en bloqueo | 35,2% | 26,5% |
| Equipo que más bloquea | Integraciones, 39% | Integraciones, 32% |
| Mayor atraso al P85 | Ciberseguridad OT, 61 días | Ficha clínica electrónica, 75 días |

## Cómo abrirlo

- **`.pbix`:** doble clic con Power BI Desktop.
- **Proyecto PBIP:** descomprimir, abrir `proyectos-ti.pbip` y pulsar **Actualizar**. Los datos se leen desde GitHub; si pide credenciales, elegir Anónimo.
- **Solo los datos:** el zip de CSV o el Excel, con una hoja por tabla y un diccionario de columnas.

## Gobierno de datos

Empresas, proyectos, personas, tarifas y fechas son ficticios.
- **Datos reales:** el historial saldría de la API de Jira (changelog y worklogs). Las horas por persona son datos sensibles, así que el reporte se publicaría agregado por equipo y no por persona.
- **Lo que no publicamos:** ninguna cartera, tarifa ni registro de un empleador real.

## Qué demuestra

- Control de gestión aplicado a una cartera de TI: avance, consumo de presupuesto y fechas pronosticadas en un mismo tablero.
- Métricas de flujo ágil: velocidad, previsibilidad, tiempo de ciclo por percentil, WIP y diagrama de flujo acumulado.
- Colaboración entre equipos medida con datos: quién bloquea a quién y cuánto cuesta esperar.
- Pronóstico probabilístico con Monte Carlo, y un modelo de Power BI en copo de nieve con una relación inactiva bien resuelta, versionado como proyecto PBIP en Git.
