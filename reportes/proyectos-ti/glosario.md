# Glosario: Proyectos tecnológicos: entrega, capacidad y colaboración entre equipos

> Qué significa cada concepto del reporte y cómo se calcula. La primera parte lo explica con palabras; la segunda lista **todas** las medidas DAX del modelo, leídas del proyecto PBIP con `herramientas/generar_glosario.py`, así que coinciden con lo que calcula Power BI.

## Conceptos

### Cómo se trabaja en un Jira ágil

**Issue.** La unidad de trabajo en Jira. Hay cuatro tipos:
- **épica:** agrupa el trabajo de un tema grande; no lleva puntos;
- **historia:** una funcionalidad que se puede entregar;
- **tarea:** trabajo técnico sin valor visible para el usuario;
- **bug:** un defecto que hay que corregir.

**Puntos de historia.** La estimación relativa del esfuerzo de una issue, en una escala tipo Fibonacci (1, 2, 3, 5, 8). No son horas: sirven para comparar y para medir cuánto entrega un equipo.

**Sprint.** Un ciclo fijo de dos semanas. Al inicio, el equipo compromete lo que espera terminar; al final, se mide qué terminó.

**Estados.** Una issue avanza por por hacer, en curso, en revisión y hecho. Si a mitad del trabajo falta algo de otro equipo, pasa a **bloqueado** hasta que puede seguir.

### Medir la entrega

**Comprometido y completado.** Comprometido son los puntos que el equipo planificó al inicio del sprint (lo que arrastraba en curso más lo que empezó la primera semana). Completado es la parte de eso que llegó a «hecho» dentro del mismo sprint.

**Previsibilidad** = completado / comprometido. Mide si se puede confiar en lo que el equipo promete. Un equipo puede terminar mucho y aun así ser poco previsible.

**Velocidad.** Puntos terminados por sprint. Sirve para planificar el sprint siguiente; no sirve para comparar equipos, porque cada equipo estima con su propia vara.

**Throughput.** Issues terminadas por semana o por mes. Es la base del pronóstico, porque contar issues es más estable que sumar estimaciones.

### Medir el flujo

**Tiempo de ciclo.** Días corridos entre que una issue entra a «en curso» y llega a «hecho». Incluye la revisión y los bloqueos.

**Percentil 85 (P85).** El valor que no supera el 85% de los casos. En tiempos de ciclo es el plazo que conviene prometer: el promedio queda corto porque unas pocas issues bloqueadas tardan mucho.

**WIP (trabajo en curso).** Issues empezadas y no terminadas a una fecha, incluidas las bloqueadas. Mucho WIP con poco throughput es señal de trabajo atascado.

**Diagrama de flujo acumulado.** Para cada semana, cuántas issues hay en cada estado. Si la banda de «en curso» o de «bloqueado» se ensancha, el trabajo entra más rápido de lo que sale.

### Capacidad y colaboración

**Capacidad.** Horas de jornada disponibles: la dedicación de cada persona a cada equipo por 40 horas a la semana. Quien reparte la semana entre dos equipos aporta media capacidad a cada uno.

**Carga** = horas registradas en proyectos / capacidad. Bajo 100% hay días de soporte u holgura; sobre 100%, sobretiempo.

**Dependencia.** Una issue que necesita algo de otro equipo para terminar. Las horas que espera bloqueada se atribuyen al equipo del que esperaba (el **equipo que bloquea**).

**Traspaso.** El tiempo entre que el equipo que bloquea termina y la issue bloqueada vuelve a avanzar. Un traspaso lento (por ejemplo, desplegar solo en ventanas semanales) alarga los bloqueos aunque el otro equipo trabaje rápido.

### Pronóstico y presupuesto

**Monte Carlo.** Para cada proyecto abierto se simulan 10.000 futuros: cada semana se toma al azar el throughput de una de las últimas 12 semanas, hasta agotar las issues pendientes. La distribución de las semanas de término da las fechas P50, P85 y P95.

**Atraso P85.** Días entre la fecha P85 y la comprometida. Negativo es holgura. El semáforo es verde si no hay atraso, ámbar hasta 30 días y rojo sobre 30.

**Presupuesto y consumo.** El presupuesto son las horas planificadas por la tarifa de cada equipo. Consumo = costo acumulado (horas registradas × tarifa) / presupuesto. Si el consumo supera al avance, el proyecto gasta más rápido de lo que entrega.

**Alcance agregado.** Puntos que entran al proyecto después de aprobarlo. Es la causa más común de atraso que no se ve en la velocidad: el equipo rinde igual, pero la meta se aleja.

## Medidas del modelo

El modelo tiene 51 medidas, agrupadas por carpeta como aparecen en el panel de datos de Power BI. Las de *portada* y *tarjetas* solo dan formato de texto a otras medidas.

### 0. Auxiliares

#### Color atraso

Fondo del semáforo: rojo sobre 30 días de atraso, ámbar hasta 30, verde a tiempo.

```dax
VAR d = [Atraso P85 (días)]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(d), BLANK(),
        d > 30, "#F2D4CC",
        d > 0, "#F3E3C3",
        "#D9E8DA"
    )
```

*Tabla `pronostico_termino`*

### 0. Portada

#### Portada en curso

Proyectos en curso al corte sobre el total de la cartera.

```dax
FORMAT(CALCULATE(COUNTROWS(pronostico_termino), pronostico_termino[estado] = "En curso"), "0") & " de " & FORMAT([Proyectos], "0")
```

*Tabla `issues`*

#### Portada avance

Avance de la cartera, para la tarjeta.

```dax
FORMAT([Avance %], "0%")
```

*Tabla `issues`*

#### Portada bloqueo

Parte del tiempo que el trabajo pasa bloqueado, para la tarjeta.

```dax
FORMAT([% del tiempo en bloqueo], "0.0%")
```

*Tabla `issues`*

#### Portada frase 1

Primera frase: el proyecto cuyo pronóstico P85 queda más lejos de la fecha comprometida.

```dax
VAR mayor = TOPN(1, FILTER(VALUES(proyectos[nombre]), [Atraso P85 (días)] <> BLANK()), [Atraso P85 (días)], DESC)
VAR nombre = MAXX(mayor, proyectos[nombre])
VAR dias = CALCULATE([Atraso P85 (días)], proyectos[nombre] = nombre)
RETURN
    IF(
        dias > 0,
        nombre & ": P85 " & FORMAT(dias, "0") & " días después de lo comprometido",
        "Toda la cartera termina, al P85, dentro de lo comprometido"
    )
```

*Tabla `issues`*

#### Portada frase 2

Segunda frase: el equipo del que más se espera.

```dax
VAR mayor = TOPN(1, VALUES(dependencias[equipo_bloqueante]), [Horas bloqueadas por dependencia], DESC)
VAR equipo = MAXX(mayor, dependencias[equipo_bloqueante])
VAR parte = DIVIDE(CALCULATE([Horas bloqueadas por dependencia], dependencias[equipo_bloqueante] = equipo), [Horas bloqueadas por dependencia])
RETURN equipo & " genera el " & FORMAT(parte, "0%") & " de las horas bloqueadas"
```

*Tabla `issues`*

### 1. Cartera

#### Puntos totales

Alcance actual en puntos de historia (incluye lo agregado después del inicio).

```dax
CALCULATE(SUM(issues[puntos]), issues[tipo] <> "epica")
```

*Tabla `issues` · formato `#,##0`*

#### Puntos hechos

Puntos de las issues terminadas al corte.

```dax
CALCULATE(SUM(issues[puntos]), issues[estado_al_corte] = "hecho")
```

*Tabla `issues` · formato `#,##0`*

#### Avance %

Puntos hechos sobre el alcance actual, al corte.

```dax
DIVIDE([Puntos hechos], [Puntos totales])
```

*Tabla `issues` · formato `0%`*

#### Proyectos

Proyectos de la cartera en el filtro.

```dax
COUNTROWS(proyectos)
```

*Tabla `proyectos` · formato `#,##0`*

#### Presupuesto

Presupuesto aprobado de los proyectos: horas planificadas por la tarifa de cada equipo.

```dax
SUM(proyectos[presupuesto_monto])
```

*Tabla `proyectos` · formato `\$ #,##0`*

#### Fin comprometido

Fecha de término comprometida del proyecto.

```dax
MAX(proyectos[fin_comprometido])
```

*Tabla `proyectos` · formato `d mmm yyyy`*

#### Alcance agregado %

Puntos agregados después de aprobar el proyecto, sobre los planificados al inicio.

```dax
DIVIDE(SUM(proyectos[puntos_agregados]), SUM(proyectos[puntos_planificados]))
```

*Tabla `proyectos` · formato `0%`*

#### Costo

Horas registradas por la tarifa de cada persona.

```dax
SUMX(worklogs, worklogs[horas] * RELATED(personas_ti[tarifa_hora]))
```

*Tabla `worklogs` · formato `\$ #,##0`*

#### Consumo de presupuesto %

Costo acumulado al corte sobre el presupuesto aprobado del proyecto.

```dax
DIVIDE(CALCULATE([Costo], REMOVEFILTERS(Calendario)), [Presupuesto])
```

*Tabla `worklogs` · formato `0%`*

#### Costo por punto

Costo del periodo sobre los puntos terminados en el periodo.

```dax
DIVIDE([Costo], [Puntos terminados])
```

*Tabla `worklogs` · formato `\$ #,##0`*

### 2. Entrega

#### Comprometido

Puntos comprometidos al inicio del sprint.

```dax
SUM(compromisos[puntos])
```

*Tabla `compromisos` · formato `#,##0`*

#### Completado

Puntos comprometidos que llegaron a «hecho» dentro del mismo sprint.

```dax
CALCULATE(SUM(compromisos[puntos]), compromisos[completada] = 1)
```

*Tabla `compromisos` · formato `#,##0`*

#### Previsibilidad %

Completado sobre comprometido: qué tan confiable es lo que el equipo promete.

```dax
DIVIDE([Completado], [Comprometido])
```

*Tabla `compromisos` · formato `0%`*

#### Issues terminadas

Throughput: issues (sin épicas) que llegan a «hecho» en el periodo.

```dax
CALCULATE(COUNTROWS(issues), issues[tipo] <> "epica", NOT ISBLANK(issues[fecha_fin]), USERELATIONSHIP(Calendario[Date], issues[fecha_fin]))
```

*Tabla `issues` · formato `#,##0`*

#### Puntos terminados

Puntos de las issues que llegan a «hecho» en el periodo.

```dax
CALCULATE(SUM(issues[puntos]), issues[tipo] <> "epica", NOT ISBLANK(issues[fecha_fin]), USERELATIONSHIP(Calendario[Date], issues[fecha_fin]))
```

*Tabla `issues` · formato `#,##0`*

#### Velocidad

Puntos terminados por sprint (cada issue cuenta en el sprint en que llega a «hecho»).

```dax
CALCULATE([Puntos terminados], TREATAS(VALUES(sprints[sprint]), issues[sprint]), REMOVEFILTERS(Calendario))
```

*Tabla `issues` · formato `#,##0`*

### 3. Flujo

#### Issues en el estado

Issues en cada estado al cierre de la semana.

```dax
SUM(flujo_semanal[issues])
```

*Tabla `flujo_semanal` · formato `#,##0`*

#### Tiempo de ciclo P50 (días)

Mediana de días corridos entre «en curso» y «hecho», de las issues terminadas en el periodo.

```dax
CALCULATE(PERCENTILEX.INC(FILTER(issues, NOT ISBLANK(issues[dias_ciclo])), issues[dias_ciclo], 0.5), issues[tipo] <> "epica", NOT ISBLANK(issues[fecha_fin]), USERELATIONSHIP(Calendario[Date], issues[fecha_fin]))
```

*Tabla `issues` · formato `0`*

#### Tiempo de ciclo P85 (días)

El 85% de las issues terminadas en el periodo tardó a lo más estos días: sirve para prometer plazos.

```dax
CALCULATE(PERCENTILEX.INC(FILTER(issues, NOT ISBLANK(issues[dias_ciclo])), issues[dias_ciclo], 0.85), issues[tipo] <> "epica", NOT ISBLANK(issues[fecha_fin]), USERELATIONSHIP(Calendario[Date], issues[fecha_fin]))
```

*Tabla `issues` · formato `0`*

#### WIP

Trabajo en curso al cierre del periodo (o al corte): issues empezadas y no terminadas, incluidas las bloqueadas.

```dax
VAR fin = MIN(MAX(Calendario[Date]), DATE(2026, 9, 30))
RETURN COUNTROWS(
    FILTER(
        issues,
        issues[tipo] <> "epica"
            && NOT ISBLANK(issues[fecha_inicio])
            && issues[fecha_inicio] <= fin
            && (ISBLANK(issues[fecha_fin]) || issues[fecha_fin] > fin)
    ))
```

*Tabla `issues` · formato `#,##0`*

#### Antigüedad del WIP (días)

Días promedio que lleva abierto el trabajo en curso al cierre del periodo.

```dax
VAR fin = MIN(MAX(Calendario[Date]), DATE(2026, 9, 30))
RETURN
    AVERAGEX(
        FILTER(
            issues,
            issues[tipo] <> "epica"
                && NOT ISBLANK(issues[fecha_inicio])
                && issues[fecha_inicio] <= fin
                && (ISBLANK(issues[fecha_fin]) || issues[fecha_fin] > fin)
        ),
        fin - issues[fecha_inicio]
    )
```

*Tabla `issues` · formato `0`*

#### Transiciones

Cambios de estado registrados.

```dax
COUNTROWS(transiciones)
```

*Tabla `transiciones` · formato `#,##0`*

### 4. Capacidad

#### Personas-equivalentes

Personas a tiempo completo equivalentes: suma de la dedicación de cada asignación.

```dax
SUM(asignaciones[dedicacion])
```

*Tabla `asignaciones` · formato `#,##0.0`*

#### Con dedicación partida

Asignaciones de personas que reparten la semana entre dos equipos.

```dax
CALCULATE(COUNTROWS(asignaciones), asignaciones[dedicacion] < 1)
```

*Tabla `asignaciones` · formato `#,##0`*

#### Capacidad (h)

Horas de jornada disponibles en el periodo.

```dax
SUM(capacidad_semanal[horas_capacidad])
```

*Tabla `capacidad_semanal` · formato `#,##0`*

#### Carga %

Horas registradas en proyectos sobre capacidad: bajo 100% hay soporte u holgura; sobre 100%, sobretiempo.

```dax
DIVIDE([Horas registradas], [Capacidad (h)])
```

*Tabla `capacidad_semanal` · formato `0%`*

#### Personas

Personas de TI en el filtro.

```dax
COUNTROWS(personas_ti)
```

*Tabla `personas_ti` · formato `#,##0`*

#### Horas registradas

Horas trabajadas en issues de proyectos (el soporte no se registra).

```dax
SUM(worklogs[horas])
```

*Tabla `worklogs` · formato `#,##0`*

### 5. Colaboración

#### Dependencias

Issues que necesitan algo de otro equipo para terminar.

```dax
COUNTROWS(dependencias)
```

*Tabla `dependencias` · formato `#,##0`*

#### Horas bloqueadas por dependencia

Horas de espera atribuidas al equipo bloqueante (si hay dos bloqueantes, se reparten).

```dax
SUM(dependencias[horas_bloqueado])
```

*Tabla `dependencias` · formato `#,##0`*

#### Espera media (días)

Días hábiles de espera promedio por dependencia.

```dax
DIVIDE([Horas bloqueadas por dependencia], [Dependencias] * 8)
```

*Tabla `dependencias` · formato `0.0`*

#### Dependencias abiertas al corte

Dependencias cuya issue bloqueante no estaba terminada al corte.

```dax
CALCULATE([Dependencias], ISBLANK(dependencias[resuelta]))
```

*Tabla `dependencias` · formato `#,##0`*

#### Horas bloqueadas

Horas hábiles que las issues pasaron en «bloqueado» esperando a otro equipo.

```dax
SUM(issues[horas_bloqueado])
```

*Tabla `issues` · formato `#,##0`*

#### % del tiempo en bloqueo

Horas bloqueadas sobre horas bloqueadas más horas trabajadas en las mismas issues.

```dax
DIVIDE([Horas bloqueadas], [Horas bloqueadas] + [Horas registradas])
```

*Tabla `issues` · formato `0.0%`*

#### Entradas a bloqueado

Veces que una issue pasó a «bloqueado» por una dependencia.

```dax
CALCULATE(COUNTROWS(transiciones), transiciones[estado_hasta] = "bloqueado")
```

*Tabla `transiciones` · formato `#,##0`*

### 6. Pronóstico

#### Probabilidad

Parte de las simulaciones que termina esa semana.

```dax
SUM(pronostico_distribucion[probabilidad])
```

*Tabla `pronostico_distribucion` · formato `0.0%`*

#### Probabilidad acumulada

Probabilidad de haber terminado a más tardar esa semana.

```dax
VAR semana = MAX(pronostico_distribucion[semana_termino])
RETURN
    CALCULATE(
        SUM(pronostico_distribucion[probabilidad]),
        pronostico_distribucion[semana_termino] <= semana,
        REMOVEFILTERS(pronostico_distribucion[semana_termino])
    )
```

*Tabla `pronostico_distribucion` · formato `0%`*

#### Estado

Terminado o en curso al corte.

```dax
SELECTEDVALUE(pronostico_termino[estado])
```

*Tabla `pronostico_termino`*

#### Fecha P50

Fecha de término con 50% de probabilidad (si terminó, la fecha real).

```dax
MAX(pronostico_termino[fecha_p50])
```

*Tabla `pronostico_termino` · formato `d mmm yyyy`*

#### Fecha P85

Fecha de término con 85% de probabilidad: la que conviene comprometer.

```dax
MAX(pronostico_termino[fecha_p85])
```

*Tabla `pronostico_termino` · formato `d mmm yyyy`*

#### Fecha P95

Fecha de término con 95% de probabilidad.

```dax
MAX(pronostico_termino[fecha_p95])
```

*Tabla `pronostico_termino` · formato `d mmm yyyy`*

#### Atraso P85 (días)

Días entre la fecha P85 y la comprometida (negativo = holgura).

```dax
MAX(pronostico_termino[atraso_p85_dias])
```

*Tabla `pronostico_termino` · formato `0`*

#### Issues pendientes

Issues sin terminar al corte, que el Monte Carlo reparte en semanas futuras.

```dax
SUM(pronostico_termino[issues_pendientes])
```

*Tabla `pronostico_termino` · formato `#,##0`*

#### Throughput semanal

Issues terminadas por semana en las últimas 12 semanas antes del corte.

```dax
AVERAGE(pronostico_termino[throughput_semanal])
```

*Tabla `pronostico_termino` · formato `0.0`*

#### Proyectos atrasados al P85

Proyectos abiertos cuyo P85 cae después de la fecha comprometida.

```dax
CALCULATE(COUNTROWS(pronostico_termino), pronostico_termino[estado] = "En curso", pronostico_termino[atraso_p85_dias] > 0)
```

*Tabla `pronostico_termino` · formato `#,##0`*
