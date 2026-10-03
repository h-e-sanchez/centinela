# Glosario: Contratistas y mantenimiento: del estado de pago a la orden de trabajo

> Qué significa cada concepto del reporte y cómo se calcula. La primera parte lo explica con palabras; la segunda lista **todas** las medidas DAX del modelo, leídas del proyecto PBIP con `herramientas/generar_glosario.py`, así que coinciden con lo que calcula Power BI.

## Conceptos

### Los documentos que se cruzan

**Orden de trabajo (OT).** El registro, en el sistema de mantenimiento (por ejemplo, SAP PM), de un trabajo sobre un activo: qué se hizo, cuándo, cuántas horas y si está cerrado. Hay dos clases:
- **preventiva:** sale del plan de mantención; tiene una fecha programada;
- **correctiva:** nace de una falla avisada; su fecha programada es la del aviso.

Una OT **cerrada** es trabajo terminado y respaldado. Una **abierta** todavía no debería cobrarse.

**Estado de pago (EP).** El cobro mensual que presenta el contratista. Cada **línea** dice qué servicio cobra, la cantidad, el precio unitario y qué OT lo respalda.

**Tarifa.** El precio unitario pactado en el contrato por cada servicio: la visita preventiva y la hora correctiva.

**Facturado** = suma de todas las líneas de EP. Incluye lo legítimo y lo que después se observa.

### Las cinco reglas de auditoría

Cada regla es una consulta SQL (`sql/reglas_auditoria.sql`) que cruza la línea del EP con su OT y con la tarifa. Una línea puede pasar todas las reglas o incumplir una.

| Regla | Qué detecta | Monto observado |
|---|---|---|
| **Cobro sin OT** | la línea no cita OT, o cita una que no existe en el sistema | la línea completa |
| **OT abierta** | se cobra trabajo no terminado: la OT sigue abierta o se cerró después del mes cobrado | la línea completa |
| **Cantidad sobre lo ejecutado** | se cobran más horas o visitas que las registradas en la OT, sobre una tolerancia de 5% | solo el exceso × precio |
| **Precio sobre tarifa** | el precio unitario supera el del contrato | solo el exceso × cantidad |
| **Doble cobro** | la misma OT y servicio ya se cobró antes | la línea completa |

**Por qué a veces se observa solo el exceso.** Si un contratista cobra 12 horas y la OT registra 8, las 8 horas se deben igual: lo discutible son las 4 de más. Por eso el monto observado mide lo que el control de verdad ahorra, no el total de líneas con problemas.

**Tolerancia de cantidad.** Hasta 5% sobre lo ejecutado no se observa, para no discutir redondeos. Es un parámetro del SQL, no una constante escondida.

**Doble cobro con `ROW_NUMBER`.** La consulta numera los cobros de cada OT y servicio en orden de periodo. El primero es legítimo; el segundo en adelante, doble cobro.

### Monto observado y resolución

**Observado** = suma del monto observado de todas las reglas. **% Observado** = observado ÷ facturado.

**El control.** Hasta junio de 2025 nadie cruzaba el EP con las OT. Desde el 1 de julio de 2025, lo observado se rechaza antes de pagar. La misma medida se lee distinto según la fecha:
- **Pagado de más:** observado antes del control. Ya salió de la caja; recuperarlo exige negociar con el contratista.
- **Monto evitado:** observado con control. Nunca se pagó.

**% observado antes y con control.** El control no solo rechaza: también **disuade**. Cuando los contratistas saben que cada línea se cruza con su OT, cobran menos de más. Por eso el % observado baja de ~9,5% a ~3,5%.

**Facturado sin observaciones** = facturado − observado: lo que pasa todas las reglas.

### Plan preventivo

**Preventivas programadas.** Mantenciones del plan con fecha en el periodo. La frecuencia depende de la **criticidad** del activo: A mensual, B bimestral y C trimestral.

**Cumplimiento preventivo %** = preventivas iniciadas a tiempo ÷ programadas. *A tiempo* significa a más tardar 7 días después de la fecha programada. Una preventiva atrasada no es solo un incumplimiento de contrato: aumenta la probabilidad de falla.

**Backlog (OT).** Preventivas vencidas y sin iniciar al cierre del periodo, incluidas las de meses anteriores. Es trabajo atrasado que se acumula.

**Backlog (semanas)** = backlog ÷ preventivas que el plan programa en una semana promedio. Dice cuántas semanas de trabajo preventivo están pendientes: 1 semana se recupera; 6 semanas indican que el contratista no da abasto.

**% Correctivo** = OT correctivas ÷ OT totales. Una operación sana es mayoritariamente preventiva; si lo correctivo crece, se está reparando lo que no se mantuvo.

### Confiabilidad de los activos

**Falla.** Cada OT correctiva.

**MTBF (tiempo medio entre fallas)** = días-activo de operación ÷ fallas. Con 10 activos durante 365 días y 40 fallas: 10 × 365 ÷ 40 ≈ 91 días entre fallas. Más alto es mejor. El reporte lo compara con el **MTBF objetivo** de diseño de cada tipo de activo.

**MTTR (tiempo medio de reparación)** = horas promedio de trabajo de las correctivas cerradas. Más bajo es mejor.

**Detención media** = horas promedio que el activo está detenido por falla: el **tiempo de respuesta** del contratista (desde el aviso hasta que llega) más la reparación. La diferencia entre detención y MTTR es la espera. Un contratista puede reparar rápido y aun así dejar el activo detenido medio día por llegar tarde.

**Disponibilidad %** = 1 − horas detenidas por falla ÷ horas totales de los activos. Un 98,7% parece alto, pero en una flota de 78 activos durante dos años son miles de horas sin operar.

### Contratistas

**Perfil limpio / riesgoso.** Es la etiqueta de la simulación: los riesgosos concentran las anomalías y también cumplen peor el plan y responden más lento. En datos reales esta columna no existiría. Lo que el reporte muestra es cómo el ranking los **revela** sin saberlo de antemano: los mismos nombres arriba en % observado y abajo en cumplimiento preventivo.

**Facturado por OT** = facturado ÷ OT del periodo: el costo medio de cada intervención, útil para comparar contratistas de la misma especialidad.

## Medidas del modelo

El modelo tiene 32 medidas, agrupadas por carpeta como aparecen en el panel de datos de Power BI. Las de *portada* y *tarjetas* solo dan formato de texto a otras medidas.

### 0. Auxiliares

#### Días del periodo

Días calendario del periodo filtrado.

```dax
COUNTROWS(Calendario)
```

*Tabla `ordenes_trabajo` · formato `#,##0`*

### 0. Portada

#### Portada facturado

Facturado abreviado para la tarjeta.

```dax
VAR v = [Facturado]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(v), BLANK(),
        ABS(v) >= 1000000000, FORMAT(v / 1000000000, "$ #,0.0") & " mil M",
        ABS(v) >= 1000000, FORMAT(v / 1000000, "$ #,0") & " M",
        FORMAT(v, "$ #,0")
    )
```

*Tabla `estados_pago`*

#### Portada observado

Observado abreviado para la tarjeta.

```dax
VAR v = [Observado]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(v), BLANK(),
        ABS(v) >= 1000000000, FORMAT(v / 1000000000, "$ #,0.0") & " mil M",
        ABS(v) >= 1000000, FORMAT(v / 1000000, "$ #,0") & " M",
        FORMAT(v, "$ #,0")
    )
```

*Tabla `estados_pago`*

#### Portada evitado

Monto evitado abreviado para la tarjeta.

```dax
VAR v = [Monto evitado]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(v), BLANK(),
        ABS(v) >= 1000000000, FORMAT(v / 1000000000, "$ #,0.0") & " mil M",
        ABS(v) >= 1000000, FORMAT(v / 1000000, "$ #,0") & " M",
        FORMAT(v, "$ #,0")
    )
```

*Tabla `estados_pago`*

#### Portada frase 1

Primera frase: cuánto se observaba antes y después de instalar el control.

```dax
"Observado: " & FORMAT([% Observado antes del control], "0.0%") & " → " & FORMAT([% Observado con control], "0.0%") & " con control"
```

*Tabla `estados_pago`*

#### Portada frase 2

Segunda frase: el contratista con más monto observado.

```dax
VAR mayorObservado = TOPN(1, VALUES(contratistas[contratista]), [Observado], DESC)
VAR nombre = MAXX(mayorObservado, contratistas[contratista])
VAR monto = CALCULATE([Observado], contratistas[contratista] = nombre)
VAR corto = SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(nombre, " Ltda.", ""), " S.A.", ""), " SpA", "")
RETURN corto & ": " & FORMAT(monto / 1000000, "$ #,0") & " M observado"
```

*Tabla `estados_pago`*

### 1. Estados de pago

#### Facturado

Todo lo que los contratistas cobran en sus estados de pago.

```dax
SUM(estados_pago[monto])
```

*Tabla `estados_pago` · formato `\$ #,##0`*

#### Líneas de EP

Líneas cobradas.

```dax
COUNTROWS(estados_pago)
```

*Tabla `estados_pago` · formato `#,##0`*

#### Facturado por OT

Facturado sobre órdenes de trabajo del periodo: costo unitario del servicio.

```dax
DIVIDE([Facturado], [OT])
```

*Tabla `estados_pago` · formato `\$ #,##0`*

### 2. Auditoría

#### Observado

Monto que las reglas dejan observado: la línea completa o solo el exceso, según la regla.

```dax
SUM(observaciones[monto_observado])
```

*Tabla `observaciones` · formato `\$ #,##0`*

#### % Observado

Observado sobre facturado.

```dax
DIVIDE([Observado], [Facturado])
```

*Tabla `observaciones` · formato `0.0%`*

#### Líneas observadas

Líneas de EP con al menos una regla incumplida.

```dax
DISTINCTCOUNT(observaciones[id_linea])
```

*Tabla `observaciones` · formato `#,##0`*

#### Pagado de más

Observado antes de julio de 2025: se pagó porque nadie cruzaba el EP con las OT.

```dax
CALCULATE([Observado], observaciones[resolucion] = "Pagada sin control")
```

*Tabla `observaciones` · formato `\$ #,##0`*

#### Monto evitado

Observado desde julio de 2025: el control lo rechaza antes de pagar.

```dax
CALCULATE([Observado], observaciones[resolucion] = "Rechazada")
```

*Tabla `observaciones` · formato `\$ #,##0`*

#### Facturado sin observaciones

Lo que pasa todas las reglas.

```dax
[Facturado] - [Observado]
```

*Tabla `observaciones` · formato `\$ #,##0`*

#### Observado promedio mensual

Monto observado de un mes típico del periodo.

```dax
AVERAGEX(VALUES(Calendario[Periodo Num]), [Observado])
```

*Tabla `observaciones` · formato `\$ #,##0`*

#### % Observado antes del control

Enero a junio de 2025, sin control.

```dax
CALCULATE([% Observado], Calendario[Date] < DATE(2025, 7, 1))
```

*Tabla `observaciones` · formato `0.0%`*

#### % Observado con control

Desde julio de 2025: el control disuade y las anomalías bajan.

```dax
CALCULATE([% Observado], Calendario[Date] >= DATE(2025, 7, 1))
```

*Tabla `observaciones` · formato `0.0%`*

### 3. Mantenimiento

#### Activos

Activos mantenidos en el filtro.

```dax
COUNTROWS(activos)
```

*Tabla `activos` · formato `#,##0`*

#### MTBF objetivo (días)

MTBF de diseño del tipo de activo, para comparar con el observado.

```dax
AVERAGE(activos[mtbf_objetivo_dias])
```

*Tabla `activos` · formato `#,##0`*

#### OT

Órdenes de trabajo programadas (preventivas) o avisadas (correctivas) en el periodo.

```dax
COUNTROWS(ordenes_trabajo)
```

*Tabla `ordenes_trabajo` · formato `#,##0`*

#### Preventivas programadas

Mantenciones del plan con fecha programada en el periodo.

```dax
CALCULATE(COUNTROWS(ordenes_trabajo), ordenes_trabajo[clase] = "Preventiva")
```

*Tabla `ordenes_trabajo` · formato `#,##0`*

#### Preventivas a tiempo

Preventivas iniciadas a más tardar 7 días después de lo programado.

```dax
CALCULATE(COUNTROWS(ordenes_trabajo), ordenes_trabajo[clase] = "Preventiva", ordenes_trabajo[dias_atraso] <= 7)
```

*Tabla `ordenes_trabajo` · formato `#,##0`*

#### Cumplimiento preventivo %

Preventivas a tiempo sobre programadas.

```dax
DIVIDE([Preventivas a tiempo], [Preventivas programadas])
```

*Tabla `ordenes_trabajo` · formato `0.0%`*

#### Backlog (OT)

Preventivas vencidas y sin iniciar al cierre del periodo (también las de meses anteriores).

```dax
VAR fin = MAX(Calendario[Date])
RETURN
    COUNTROWS(
        FILTER(
            CALCULATETABLE(ordenes_trabajo, REMOVEFILTERS(Calendario)),
            ordenes_trabajo[clase] = "Preventiva"
                && ordenes_trabajo[fecha_programada] <= fin
                && (ISBLANK(ordenes_trabajo[fecha_inicio]) || ordenes_trabajo[fecha_inicio] > fin)
        )
    ) + 0
```

*Tabla `ordenes_trabajo` · formato `#,##0`*

#### Backlog (semanas)

Backlog expresado en semanas del plan: cuántas semanas de trabajo preventivo están atrasadas.

```dax
VAR semanal = DIVIDE(CALCULATE([Preventivas programadas], REMOVEFILTERS(Calendario)), 104)
RETURN DIVIDE([Backlog (OT)], semanal)
```

*Tabla `ordenes_trabajo` · formato `0.0`*

#### Fallas

OT correctivas: cada una es una falla avisada.

```dax
CALCULATE(COUNTROWS(ordenes_trabajo), ordenes_trabajo[clase] = "Correctiva")
```

*Tabla `ordenes_trabajo` · formato `#,##0`*

#### % Correctivo

Parte del trabajo que es reacción a fallas y no plan.

```dax
DIVIDE([Fallas], [OT])
```

*Tabla `ordenes_trabajo` · formato `0.0%`*

#### MTTR (h)

Tiempo medio de reparación de las correctivas cerradas, en horas.

```dax
CALCULATE(AVERAGE(ordenes_trabajo[horas_ejecutadas]), ordenes_trabajo[clase] = "Correctiva", ordenes_trabajo[estado] = "Cerrada")
```

*Tabla `ordenes_trabajo` · formato `0.0`*

#### Detención media (h)

Horas detenido por falla: tiempo de respuesta del contratista más reparación.

```dax
CALCULATE(AVERAGE(ordenes_trabajo[horas_detencion]), ordenes_trabajo[clase] = "Correctiva", ordenes_trabajo[estado] = "Cerrada")
```

*Tabla `ordenes_trabajo` · formato `0.0`*

#### MTBF (días)

Días-activo de operación por cada falla.

```dax
DIVIDE([Activos] * [Días del periodo], [Fallas])
```

*Tabla `ordenes_trabajo` · formato `#,##0`*

#### Disponibilidad %

Horas disponibles sobre horas totales de los activos, descontando la detención por fallas.

```dax
VAR horas = [Activos] * [Días del periodo] * 24
VAR detenido = CALCULATE(SUM(ordenes_trabajo[horas_detencion]), ordenes_trabajo[clase] = "Correctiva")
RETURN IF(horas > 0, 1 - DIVIDE(detenido, horas))
```

*Tabla `ordenes_trabajo` · formato `0.00%`*
