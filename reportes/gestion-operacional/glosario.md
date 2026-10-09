# Glosario: Gestión operacional clínica

> Qué significa cada concepto del reporte y cómo se calcula. La primera parte lo explica con palabras; la segunda lista **todas** las medidas DAX del modelo, leídas del proyecto PBIP con `herramientas/generar_glosario.py`, así que coinciden con lo que calcula Power BI.

## Conceptos

### Hospitalizado

**Día cama disponible.** Una cama dotada durante un día. Treinta camas en un mes de 30 días son 900 días cama disponibles.

**Día cama ocupado (día paciente).** Una cama con un paciente durante un día.

**Ocupación de camas** = días cama ocupados / días cama disponibles. Sobre 85–90%, cualquier alza de demanda se transforma en espera en urgencia o en cirugías suspendidas por falta de cama.

**Egreso.** Un paciente que deja el servicio: alta, traslado o fallecimiento.

**Estada media (ALOS).** Días de estada / egresos. Cuántos días se queda en promedio cada paciente.

**Estada esperada y GRD.** Los Grupos Relacionados por el Diagnóstico agrupan pacientes con consumo de recursos parecido y les asignan una estada de referencia. Aquí se usa una norma simplificada por servicio.

**Índice de estada (IEMA).** Estada real / estada esperada. Sobre 1, los pacientes se quedan más de lo que indica la norma: esperando exámenes, interconsultas, traslados o un cupo de cuidado en casa. Esos días sobre la norma son capacidad inmovilizada.

**Índice de rotación.** Egresos por cama en el periodo. Mide cuántos pacientes pasan por cada cama.

**Reingreso a 30 días.** Paciente que vuelve a hospitalizarse antes de 30 días del alta. Un alta apresurada para liberar camas suele aparecer aquí.

### Pabellones

**Horas habilitadas.** Pabellones × horas de funcionamiento por día hábil. Es la capacidad instalada.

**Utilización de pabellón** = horas utilizadas / habilitadas. Incluye el recambio entre cirugías (aseo y preparación).

**Suspensión de cirugía.** Una cirugía programada que no se hace el día previsto. Es una hora de pabellón y de equipo pagada que no produce.

**Suspensión evitable.** Todas las causas que la gestión puede prevenir: paciente no preparado, atraso de la cirugía anterior, falta de cama, de insumo o de equipo, problemas administrativos e inasistencia. Solo la causa médica del paciente no se cuenta como evitable.

**Primera cirugía a la hora.** Si la primera cirugía del día parte tarde, toda la tabla se corre y las últimas terminan suspendidas.

**Pareto de causas.** Ordenar las causas de mayor a menor muestra que unas pocas explican la mayoría de las suspensiones. Por ahí parte la mejora continua.

### Urgencia

**Categorización (triage) C1 a C5.** Clasificación por gravedad al llegar. C1 es riesgo vital y se atiende de inmediato; C5 es consulta no urgente. Cada categoría tiene una espera máxima hasta la atención médica: 5, 30, 90, 180 y 240 minutos.

**Atenciones en meta de espera.** Parte de las atenciones que se cumplen dentro de la espera máxima de su categoría.

**Abandono.** Paciente que se va sin ser atendido. Sube cuando la espera de las categorías C4 y C5 se alarga.

**Espera de cama.** Horas que un paciente con indicación de hospitalización espera en urgencia hasta tener cama. Es el punto donde la ocupación hospitalaria y la urgencia se tocan.

### Ambulatorio y apoyo

**Utilización de box** = horas de agenda abiertas / horas de box disponibles.

**Ocupación de agenda** = horas con paciente agendado / horas ofertadas.

**Inasistencia (no-show).** Paciente agendado que no llega. La hora se pierde aunque haya lista de espera.

**Tercer cupo.** Días hasta la tercera hora disponible. Mide el acceso real mejor que la primera hora, que suele ser una anulación de última hora.

**TAT (turnaround time).** Tiempo desde la orden del examen hasta el informe. La meta depende del origen: urgencia necesita respuesta en una o dos horas; ambulatorio, en uno o dos días.

### Resultado y capacidad

**Previsión.** Quién paga: Fonasa, isapres, convenios con empresas o el paciente particular. El mismo día cama vale distinto según la previsión.

**Costo directo.** Personal, insumos y honorarios de la línea. El personal es fijo en el mes; insumos y honorarios son variables.

**Margen de contribución** = ingreso − costo directo. Lo que deja la línea para cubrir los gastos generales.

**Margen variable** = ingreso − insumos − honorarios. Lo que suma una prestación adicional cuando la dotación ya está pagada.

**Capacidad liberable.** Camas y horas de pabellón que se recuperan sin invertir: acortando la estada sobre la norma y evitando suspensiones. Se valoriza al margen variable porque la dotación no cambia.

## Medidas del modelo

El modelo tiene 79 medidas, agrupadas por carpeta como aparecen en el panel de datos de Power BI. Las de *portada* y *tarjetas* solo dan formato de texto a otras medidas.

### 0. Portada

#### Portada ocupación

Ocupación de camas para la tarjeta.

```dax
FORMAT([Ocupación de camas %], "0.0%")
```

*Tabla `produccion`*

#### Portada suspensión

Suspensión de cirugías para la tarjeta.

```dax
FORMAT([Suspensión de cirugías %], "0.0%")
```

*Tabla `produccion`*

#### Portada urgencia

Atenciones de urgencia en meta para la tarjeta.

```dax
FORMAT([Atenciones en meta de espera %], "0.0%")
```

*Tabla `produccion`*

#### Portada margen

Margen de contribución para la tarjeta.

```dax
FORMAT([Margen de contribución %], "0.0%")
```

*Tabla `produccion`*

#### Portada frase 1

Primera frase: el mes de mayor ocupación y la espera de cama en urgencia de ese mes.

```dax
VAR meses = ADDCOLUMNS(VALUES(camas[fecha]), "@ocupacion", [Ocupación de camas %])
VAR pico = TOPN(1, meses, [@ocupacion], DESC)
VAR mes = MAXX(pico, camas[fecha])
VAR espera = CALCULATE([Espera de cama promedio (h)], REMOVEFILTERS(Calendario), urgencia[fecha] = mes)
RETURN
    "Mes más exigido: " & FORMAT(mes, "mmm yyyy") & ", con " & FORMAT(MAXX(pico, [@ocupacion]), "0%")
        & " de ocupación y " & FORMAT(espera, "0.0") & " h de espera de cama en urgencia"
```

*Tabla `produccion`*

#### Portada frase 2

Segunda frase: la clínica que más suspende y cuánto de eso era evitable.

```dax
VAR peor = TOPN(1, VALUES(sucursales[sucursal]), [Suspensión de cirugías %], DESC)
VAR clinica = MAXX(peor, sucursales[sucursal])
RETURN
    clinica & " suspende " & FORMAT(CALCULATE([Suspensión de cirugías %], sucursales[sucursal] = clinica), "0.0%")
        & " de sus cirugías; " & FORMAT(CALCULATE([Suspensiones evitables %], sucursales[sucursal] = clinica), "0%")
        & " por causas evitables"
```

*Tabla `produccion`*

### 1. Hospitalizado

#### Días cama disponibles

Camas dotadas por los días del mes.

```dax
SUM(camas[dias_cama_disponibles])
```

*Tabla `camas` · formato `#,##0`*

#### Días cama ocupados

Días paciente: camas ocupadas cada día, sumadas en el periodo.

```dax
SUM(camas[dias_cama_ocupados])
```

*Tabla `camas` · formato `#,##0`*

#### Ocupación de camas %

Índice ocupacional: días cama ocupados sobre disponibles.

```dax
DIVIDE([Días cama ocupados], [Días cama disponibles])
```

*Tabla `camas` · formato `0.0%`*

#### Egresos hospitalarios

Pacientes que dejan el servicio (altas, traslados y fallecidos).

```dax
SUM(camas[egresos])
```

*Tabla `camas` · formato `#,##0`*

#### Estada media (días)

Promedio de días de estada por egreso (ALOS).

```dax
DIVIDE(SUM(camas[dias_estada]), [Egresos hospitalarios])
```

*Tabla `camas` · formato `0.0`*

#### Estada esperada (días)

Estada que correspondería según la norma por diagnóstico (GRD simplificado).

```dax
DIVIDE(SUM(camas[dias_estada_esperados]), [Egresos hospitalarios])
```

*Tabla `camas` · formato `0.0`*

#### Índice de estada (IEMA)

Estada real sobre la esperada: sobre 1, los pacientes se quedan más de lo que indica la norma.

```dax
DIVIDE(SUM(camas[dias_estada]), SUM(camas[dias_estada_esperados]))
```

*Tabla `camas` · formato `0.00`*

#### Días de estada sobre la norma

Días cama usados por sobre la estada esperada: capacidad inmovilizada.

```dax
SUMX(camas, MAX(0, camas[dias_estada] - camas[dias_estada_esperados]))
```

*Tabla `camas` · formato `#,##0`*

#### Camas dotadas (promedio)

Camas dotadas promedio de los meses del periodo.

```dax
AVERAGEX(VALUES(camas[fecha]), CALCULATE(SUM(camas[camas_dotadas])))
```

*Tabla `camas` · formato `#,##0`*

#### Días del periodo

Días calendario de los meses del periodo.

```dax
SUMX(VALUES(camas[fecha]), DAY(EOMONTH(camas[fecha], 0)))
```

*Tabla `camas` · formato `#,##0`*

#### Índice de rotación

Egresos por cama en el periodo: cuántos pacientes pasan por cada cama.

```dax
DIVIDE([Egresos hospitalarios], [Camas dotadas (promedio)])
```

*Tabla `camas` · formato `0.0`*

#### Reingresos a 30 días %

Egresos que vuelven a hospitalizarse antes de 30 días.

```dax
DIVIDE(SUM(camas[reingresos_30d]), [Egresos hospitalarios])
```

*Tabla `camas` · formato `0.0%`*

### 2. Pabellones

#### Horas habilitadas

Horas de pabellón disponibles (pabellones × horas por día hábil).

```dax
SUM(pabellones[horas_habilitadas])
```

*Tabla `pabellones` · formato `#,##0`*

#### Horas utilizadas

Horas de pabellón con paciente, incluido el recambio.

```dax
SUM(pabellones[horas_utilizadas])
```

*Tabla `pabellones` · formato `#,##0`*

#### Horas ociosas

Horas habilitadas que no se usaron.

```dax
[Horas habilitadas] - [Horas utilizadas]
```

*Tabla `pabellones` · formato `#,##0`*

#### Utilización de pabellón %

Horas utilizadas sobre habilitadas.

```dax
DIVIDE([Horas utilizadas], [Horas habilitadas])
```

*Tabla `pabellones` · formato `0.0%`*

#### Cirugías programadas

Cirugías en la tabla quirúrgica.

```dax
SUM(pabellones[cirugias_programadas])
```

*Tabla `pabellones` · formato `#,##0`*

#### Cirugías realizadas

Cirugías programadas que se hicieron.

```dax
SUM(pabellones[cirugias_realizadas])
```

*Tabla `pabellones` · formato `#,##0`*

#### Cirugías suspendidas

Cirugías programadas que no se hicieron el día previsto.

```dax
SUM(pabellones[cirugias_suspendidas])
```

*Tabla `pabellones` · formato `#,##0`*

#### Suspensión de cirugías %

Cirugías suspendidas sobre programadas.

```dax
DIVIDE([Cirugías suspendidas], [Cirugías programadas])
```

*Tabla `pabellones` · formato `0.0%`*

#### Primera cirugía a la hora %

Primeras cirugías del día que parten a la hora programada: si la primera parte tarde, toda la tabla se corre.

```dax
DIVIDE(SUM(pabellones[primeras_a_la_hora]), SUM(pabellones[primeras_del_dia]))
```

*Tabla `pabellones` · formato `0.0%`*

#### Suspensiones por causa

Cirugías suspendidas, para abrir por causa.

```dax
SUM(suspensiones[suspendidas])
```

*Tabla `suspensiones` · formato `#,##0`*

#### Suspensiones evitables

Suspensiones por causas que la gestión puede evitar (todas menos la causa médica del paciente).

```dax
CALCULATE([Suspensiones por causa], suspensiones[evitable] = 1)
```

*Tabla `suspensiones` · formato `#,##0`*

#### Suspensiones evitables %

Parte de las suspensiones que era evitable.

```dax
DIVIDE([Suspensiones evitables], [Suspensiones por causa])
```

*Tabla `suspensiones` · formato `0%`*

### 3. Urgencia

#### Atenciones de urgencia

Pacientes atendidos en urgencia.

```dax
SUM(urgencia[atenciones])
```

*Tabla `urgencia` · formato `#,##0`*

#### Atenciones en meta de espera %

Atenciones cuya espera hasta el médico quedó dentro de la meta de su categoría.

```dax
DIVIDE(SUM(urgencia[atenciones_en_meta]), [Atenciones de urgencia])
```

*Tabla `urgencia` · formato `0.0%`*

#### Espera hasta la atención (min)

Minutos promedio desde la llegada hasta la atención médica.

```dax
DIVIDE(SUM(urgencia[minutos_espera]), [Atenciones de urgencia])
```

*Tabla `urgencia` · formato `#,##0`*

#### Meta de espera (min)

Espera máxima de la categoría de triage.

```dax
MAX(urgencia[meta_minutos])
```

*Tabla `urgencia` · formato `#,##0`*

#### Abandono de urgencia %

Pacientes que se van sin ser atendidos.

```dax
DIVIDE(SUM(urgencia[abandonos]), [Atenciones de urgencia])
```

*Tabla `urgencia` · formato `0.0%`*

#### Hospitalización desde urgencia %

Atenciones que terminan en hospitalización.

```dax
DIVIDE(SUM(urgencia[hospitalizados]), [Atenciones de urgencia])
```

*Tabla `urgencia` · formato `0.0%`*

#### Espera de cama promedio (h)

Horas que un paciente con indicación de hospitalización espera cama en urgencia.

```dax
DIVIDE(SUM(urgencia[horas_espera_cama]), SUM(urgencia[hospitalizados]))
```

*Tabla `urgencia` · formato `0.0`*

### 4. Ambulatorio

#### Horas de box

Horas de box disponibles (boxes × horario de atención).

```dax
SUM(ambulatorio[horas_box])
```

*Tabla `ambulatorio` · formato `#,##0`*

#### Horas ofertadas

Horas de agenda médica abiertas.

```dax
SUM(ambulatorio[horas_ofertadas])
```

*Tabla `ambulatorio` · formato `#,##0`*

#### Utilización de box %

Horas de agenda abiertas sobre horas de box disponibles.

```dax
DIVIDE([Horas ofertadas], [Horas de box])
```

*Tabla `ambulatorio` · formato `0.0%`*

#### Ocupación de agenda %

Horas con paciente agendado sobre horas ofertadas.

```dax
DIVIDE(SUM(ambulatorio[horas_agendadas]), [Horas ofertadas])
```

*Tabla `ambulatorio` · formato `0.0%`*

#### Consultas agendadas

Horas tomadas por pacientes.

```dax
SUM(ambulatorio[consultas_agendadas])
```

*Tabla `ambulatorio` · formato `#,##0`*

#### Consultas realizadas

Consultas agendadas a las que el paciente llegó.

```dax
SUM(ambulatorio[consultas_realizadas])
```

*Tabla `ambulatorio` · formato `#,##0`*

#### Inasistencia %

Pacientes agendados que no llegan (no-show).

```dax
DIVIDE(SUM(ambulatorio[inasistencias]), [Consultas agendadas])
```

*Tabla `ambulatorio` · formato `0.0%`*

#### Lista de espera (último mes)

Pacientes esperando hora al cierre del último mes del periodo.

```dax
VAR ultimo = MAX(ambulatorio[fecha])
RETURN CALCULATE(SUM(ambulatorio[lista_espera]), ambulatorio[fecha] = ultimo)
```

*Tabla `ambulatorio` · formato `#,##0`*

#### Días al tercer cupo

Días hasta la tercera hora disponible en el último mes: mide el acceso sin el ruido de las anulaciones.

```dax
VAR ultimo = MAX(ambulatorio[fecha])
RETURN CALCULATE(AVERAGE(ambulatorio[dias_tercer_cupo]), ambulatorio[fecha] = ultimo)
```

*Tabla `ambulatorio` · formato `0`*

### 5. Apoyo

#### Total de exámenes

Exámenes informados.

```dax
SUM(apoyo[examenes])
```

*Tabla `apoyo` · formato `#,##0`*

#### TAT en meta %

Exámenes informados dentro del tiempo de respuesta comprometido para su origen.

```dax
DIVIDE(SUM(apoyo[examenes_en_meta]), [Total de exámenes])
```

*Tabla `apoyo` · formato `0.0%`*

#### TAT promedio (min)

Minutos promedio desde la toma u orden hasta el informe.

```dax
DIVIDE(SUM(apoyo[minutos_respuesta]), [Total de exámenes])
```

*Tabla `apoyo` · formato `#,##0`*

#### Exámenes de urgencia en meta %

TAT en meta de los exámenes pedidos desde urgencia, donde el tiempo de respuesta frena el alta o la hospitalización.

```dax
CALCULATE([TAT en meta %], apoyo[origen] = "Urgencia")
```

*Tabla `apoyo` · formato `0.0%`*

### 6. Resultado

#### Total de prestaciones

Días cama, cirugías, atenciones, consultas o exámenes, según la línea.

```dax
SUM(produccion[prestaciones])
```

*Tabla `produccion` · formato `#,##0`*

#### Ingreso total

Ingreso facturado a la previsión y al paciente.

```dax
SUM(produccion[ingreso])
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Costo de personal

Dotación propia de la línea: es fijo en el mes, no cambia con el volumen.

```dax
SUM(produccion[costo_personal])
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Costo de insumos

Medicamentos e insumos clínicos: variable con las prestaciones.

```dax
SUM(produccion[costo_insumos])
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Costo de honorarios

Honorarios médicos por acto: variable con el ingreso.

```dax
SUM(produccion[costo_honorarios])
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Costo directo

Personal, insumos y honorarios de la línea.

```dax
[Costo de personal] + [Costo de insumos] + [Costo de honorarios]
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Margen de contribución

Lo que deja la línea después de sus costos directos, para cubrir gastos generales.

```dax
[Ingreso total] - [Costo directo]
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Margen de contribución %

Margen de contribución sobre ingreso.

```dax
DIVIDE([Margen de contribución], [Ingreso total])
```

*Tabla `produccion` · formato `0.0%`*

#### Margen variable

Ingreso menos costos variables: lo que suma una prestación más con la dotación ya pagada.

```dax
[Ingreso total] - [Costo de insumos] - [Costo de honorarios]
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Ingreso por prestación

Ingreso promedio de cada prestación.

```dax
DIVIDE([Ingreso total], [Total de prestaciones])
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Costo directo por prestación

Costo directo promedio de cada prestación.

```dax
DIVIDE([Costo directo], [Total de prestaciones])
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Margen variable por prestación

Margen variable promedio de cada prestación.

```dax
DIVIDE([Margen variable], [Total de prestaciones])
```

*Tabla `produccion` · formato `\$ #,##0`*

### 7. Capacidad

#### Días liberables

Días de estada sobre la norma que se recuperan con la reducción elegida.

```dax
[Días de estada sobre la norma] * [Reducción de estada %]
```

*Tabla `produccion` · formato `#,##0`*

#### Camas equivalentes liberadas

Días liberables expresados en camas disponibles todo el periodo.

```dax
DIVIDE([Días liberables], [Días del periodo])
```

*Tabla `produccion` · formato `#,##0.0`*

#### Egresos adicionales posibles

Pacientes más que caben en los días liberados, a la estada esperada.

```dax
DIVIDE([Días liberables], [Estada esperada (días)])
```

*Tabla `produccion` · formato `#,##0`*

#### Margen por estada recuperada

Margen variable de ocupar los días liberados con pacientes nuevos, servicio por servicio.

```dax
SUMX(
    VALUES(lineas[linea]),
    [Días liberables] * CALCULATE([Margen variable por prestación], lineas[area] = "Hospitalizado")
)
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Cirugías recuperables

Suspensiones evitables que se recuperan con la reducción elegida.

```dax
[Suspensiones evitables] * [Reducción de suspensiones %]
```

*Tabla `produccion` · formato `#,##0`*

#### Margen por cirugías recuperadas

Margen variable de las cirugías recuperadas, al margen variable promedio de pabellón.

```dax
[Cirugías recuperables] * CALCULATE([Margen variable por prestación], lineas[linea] = "Pabellón")
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Margen potencial

Margen variable que se recupera con las dos palancas.

```dax
[Margen por estada recuperada] + [Margen por cirugías recuperadas]
```

*Tabla `produccion` · formato `\$ #,##0`*

#### Reducción de estada %

Valor elegido en el segmentador; si no hay uno elegido, 30%.

```dax
SELECTEDVALUE('Reducción de estada'[Reducción de estada], 0.3)
```

*Tabla `Reducción de estada` · formato `0%`*

#### Reducción de suspensiones %

Valor elegido en el segmentador; si no hay uno elegido, 50%.

```dax
SELECTEDVALUE('Reducción de suspensiones'[Reducción de suspensiones], 0.5)
```

*Tabla `Reducción de suspensiones` · formato `0%`*

### 8. Indicadores

#### Valor del indicador

Valor del indicador de la fila, calculado con su medida.

```dax
SWITCH(
    SELECTEDVALUE(metas[indicador]),
    "Ocupación de camas", [Ocupación de camas %],
    "Índice de estada (IEMA)", [Índice de estada (IEMA)],
    "Reingresos a 30 días", [Reingresos a 30 días %],
    "Utilización de pabellón", [Utilización de pabellón %],
    "Suspensión de cirugías", [Suspensión de cirugías %],
    "Primera cirugía a la hora", [Primera cirugía a la hora %],
    "Atenciones de urgencia en meta", [Atenciones en meta de espera %],
    "Abandono de urgencia", [Abandono de urgencia %],
    "Espera de cama desde urgencia", [Espera de cama promedio (h)],
    "Inasistencia ambulatoria", [Inasistencia %],
    "Utilización de box", [Utilización de box %],
    "Exámenes de urgencia en meta", [Exámenes de urgencia en meta %],
    "Margen de contribución", [Margen de contribución %]
)
```

*Tabla `metas` · formato `0.00`*

#### Meta del indicador

Meta del indicador de la fila.

```dax
SELECTEDVALUE(metas[meta])
```

*Tabla `metas` · formato `0.00`*

#### Área del indicador

Área a la que pertenece el indicador.

```dax
SELECTEDVALUE(metas[area])
```

*Tabla `metas`*

#### Cumple la meta

Verdadero si el valor está del lado correcto de la meta (sobre ella si el sentido es «mayor», bajo ella si es «menor»).

```dax
VAR v = [Valor del indicador]
VAR objetivo = [Meta del indicador]
RETURN
    IF(
        NOT ISBLANK(v),
        IF(SELECTEDVALUE(metas[sentido]) = "mayor", v >= objetivo, v <= objetivo)
    )
```

*Tabla `metas`*

#### Valor (texto)

Valor del indicador con su formato (porcentaje, horas o índice).

```dax
VAR v = [Valor del indicador]
VAR f = SELECTEDVALUE(metas[formato])
RETURN
    IF(
        NOT ISBLANK(v),
        SWITCH(f, "pct", FORMAT(v, "0.0%"), "horas", FORMAT(v, "0.0") & " h", FORMAT(v, "0.00"))
    )
```

*Tabla `metas`*

#### Meta (texto)

Meta con su sentido: ≥ si hay que superarla, ≤ si no hay que pasarla.

```dax
VAR v = [Meta del indicador]
VAR f = SELECTEDVALUE(metas[formato])
RETURN
    IF(
        NOT ISBLANK(v),
        IF(SELECTEDVALUE(metas[sentido]) = "mayor", "≥ ", "≤ ") & SWITCH(f, "pct", FORMAT(v, "0.0%"), "horas", FORMAT(v, "0.0") & " h", FORMAT(v, "0.00"))
    )
```

*Tabla `metas`*

#### Estado del indicador

En meta o fuera de meta.

```dax
IF(NOT ISBLANK([Cumple la meta]), IF([Cumple la meta], "En meta", "Fuera de meta"))
```

*Tabla `metas`*

#### Color del estado

Color de fondo del estado: verde en meta, rojo fuera de meta.

```dax
IF(NOT ISBLANK([Cumple la meta]), IF([Cumple la meta], "#DCE8D5", "#F3D6CF"))
```

*Tabla `metas`*
