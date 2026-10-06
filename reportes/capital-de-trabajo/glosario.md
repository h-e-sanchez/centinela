# Glosario: Capital de trabajo y ciclo de caja

> Qué significa cada concepto del reporte y cómo se calcula. La primera parte lo explica con palabras; la segunda lista **todas** las medidas DAX del modelo, leídas del proyecto PBIP con `herramientas/generar_glosario.py`, así que coinciden con lo que calcula Power BI.

## Conceptos

### Capital de trabajo

**Capital de trabajo neto** = cuentas por cobrar + inventario − cuentas por pagar. Es la plata que la operación tiene "amarrada" mientras espera cobrar.

**Fecha de corte.** El día al que se miden los saldos. Por defecto es el último día del periodo filtrado; el segmentador permite mirar un cierre de mes anterior.

**Ventana.** Los tres meses que terminan en la fecha de corte. DSO, DIO y DPO comparan el saldo al corte con el flujo de esa ventana.

### Cobranza

**Cuentas por cobrar.** Facturas de venta emitidas hasta la fecha de corte y que a esa fecha no estaban pagadas.

**DSO** (*days sales outstanding*) = cuentas por cobrar / ventas de la ventana × días de la ventana. Cuántos días de venta están todavía por cobrar.

**Cartera vencida.** La parte de las cuentas por cobrar cuyo vencimiento ya pasó.

**Antigüedad de cartera.** La cartera repartida en tramos según los días desde el vencimiento: al día, 1 a 30, 31 a 60, 61 a 90 y más de 90.

**Cumplimiento de cobranza** = cobrado en el periodo / lo que vencía en el periodo. Bajo 100% significa que la cartera crece.

**Pareto de deudores.** Clientes ordenados por cartera vencida, con el acumulado: suele mostrar que pocos clientes concentran la mayor parte de lo vencido.

### Pagos e inventario

**Cuentas por pagar.** Facturas de compra recibidas hasta la fecha de corte y no pagadas a esa fecha.

**DPO** (*days payables outstanding*) = cuentas por pagar / compras de la ventana × días. Cuántos días de compras se le deben a los proveedores.

**Pronto pago.** Pagar antes del vencimiento a cambio de un descuento. Acorta el DPO.

**DIO** (*days inventory outstanding*) = inventario al corte / consumo de la ventana × días. Cuántos días de consumo cubre el inventario.

**Rotación de inventario** = 365 / DIO. Cuántas veces al año se renueva.

**Sobrestock y quiebre.** Sobrestock es el saldo por sobre 1,3 veces la cobertura objetivo. Quiebre es cerrar un mes con menos de 5 días de cobertura.

### Ciclo y flujo de caja

**Ciclo de conversión de caja** = DSO + DIO − DPO. Los días que pasan entre pagarle al proveedor y cobrarle al cliente. Si es negativo, la empresa cobra antes de pagar y los proveedores financian su operación.

**Flujo de caja a 13 semanas.** La proyección semanal de cobros y pagos para el próximo trimestre: los vencimientos abiertos al corte, con el atraso típico de cada cliente, más la actividad del mismo mes del año anterior. Es la herramienta habitual de tesorería para anticipar estrecheces.

**Saldo mínimo.** El colchón de caja que la empresa quiere mantener. Se elige con un parámetro y marca las semanas en que la caja queda bajo ese nivel.

**Desembolsos no operacionales.** Dividendos e inversión en equipos: salen de la caja, pero no aparecen en el estado de resultados del reporte Presupuesto vs. Real.

## Medidas del modelo

El modelo tiene 58 medidas, agrupadas por carpeta como aparecen en el panel de datos de Power BI. Las de *portada* y *tarjetas* solo dan formato de texto a otras medidas.

### 0. Corte

#### Fecha de corte

Fecha a la que se miden saldos y antigüedad: el último día del periodo filtrado o el corte elegido, si es anterior.

```dax
MIN(MAX(Calendario[Date]), SELECTEDVALUE('Fechas de corte'[Corte], DATE(2026, 12, 31)))
```

*Tabla `facturas_venta` · formato `dd-mm-yyyy`*

#### Inicio de la ventana

Primer día de los tres meses que terminan en la fecha de corte: la ventana de DSO, DPO y DIO.

```dax
VAR c = [Fecha de corte]
RETURN DATE(YEAR(EDATE(c, -2)), MONTH(EDATE(c, -2)), 1)
```

*Tabla `facturas_venta` · formato `dd-mm-yyyy`*

#### Días de la ventana

Días de la ventana de tres meses.

```dax
INT([Fecha de corte] - [Inicio de la ventana]) + 1
```

*Tabla `facturas_venta` · formato `0`*

### 0. Portada

#### Portada ciclo

Ciclo de conversión de caja para la tarjeta.

```dax
FORMAT([Ciclo de conversión de caja], "0") & " días"
```

*Tabla `facturas_venta`*

#### Portada DSO

DSO para la tarjeta.

```dax
FORMAT([DSO], "0") & " días"
```

*Tabla `facturas_venta`*

#### Portada capital

Capital de trabajo neto abreviado.

```dax
VAR v = [Capital de trabajo neto]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(v), BLANK(),
        ABS(v) >= 1000000000, FORMAT(v / 1000000000, "$ #,0.0") & " mil M",
        ABS(v) >= 1000000, FORMAT(v / 1000000, "$ #,0.0") & " M",
        FORMAT(v, "$ #,0")
    )
```

*Tabla `facturas_venta`*

#### Portada frase 1

Primera frase: DSO, DPO y lo que significa el ciclo.

```dax
VAR ciclo = [Ciclo de conversión de caja]
RETURN
    "Cobra a " & FORMAT([DSO], "0") & " días y paga a " & FORMAT([DPO], "0") & ": "
        & IF(ciclo < 0, "los proveedores financian la operación", "la caja espera " & FORMAT(ciclo, "0") & " días")
```

*Tabla `facturas_venta`*

#### Portada frase 2

Segunda frase: cómo termina la proyección de caja a 13 semanas.

```dax
VAR semanas = CALCULATE([Semanas bajo el mínimo], caja_semanal[tipo] = "Proyectado")
VAR saldo = [Saldo en 13 semanas]
RETURN
    "Próximas 13 semanas: "
        & IF(semanas > 0, FORMAT(semanas, "0") & " bajo el saldo mínimo",
             "saldo proyectado de " & FORMAT(saldo / 1000000, "$ #,0") & " M")
```

*Tabla `facturas_venta`*

### 1. Cobranza

#### Ventas

Facturas de venta emitidas en el periodo: cuadran con los ingresos Real del reporte Presupuesto vs. Real.

```dax
CALCULATE(SUM(facturas_venta[monto]), KEEPFILTERS(facturas_venta[emision] >= DATE(2025, 1, 1)))
```

*Tabla `facturas_venta` · formato `\$ #,##0`*

#### Ventas de la ventana

Ventas de los tres meses que terminan en la fecha de corte.

```dax
VAR c = [Fecha de corte]
VAR i = [Inicio de la ventana]
RETURN
    CALCULATE(
        SUM(facturas_venta[monto]),
        REMOVEFILTERS(Calendario),
        facturas_venta[emision] >= i,
        facturas_venta[emision] <= c
    )
```

*Tabla `facturas_venta` · formato `\$ #,##0`*

#### Cuentas por cobrar

Facturas de venta emitidas hasta la fecha de corte y no pagadas a esa fecha.

```dax
VAR c = [Fecha de corte]
RETURN
    CALCULATE(
        SUM(facturas_venta[monto]),
        REMOVEFILTERS(Calendario),
        facturas_venta[emision] <= c,
    ISBLANK(facturas_venta[pago]) || facturas_venta[pago] > c
    )
```

*Tabla `facturas_venta` · formato `\$ #,##0`*

#### DSO

Días de venta pendientes de cobro: cuentas por cobrar sobre las ventas de la ventana, por sus días.

```dax
DIVIDE([Cuentas por cobrar], [Ventas de la ventana]) * [Días de la ventana]
```

*Tabla `facturas_venta` · formato `0`*

#### Cartera vencida

Cuentas por cobrar con el vencimiento ya pasado a la fecha de corte.

```dax
VAR c = [Fecha de corte]
RETURN
    CALCULATE(
        SUM(facturas_venta[monto]),
        REMOVEFILTERS(Calendario),
        facturas_venta[emision] <= c,
    ISBLANK(facturas_venta[pago]) || facturas_venta[pago] > c,
        facturas_venta[vencimiento] < c
    )
```

*Tabla `facturas_venta` · formato `\$ #,##0`*

#### % vencido

Parte de las cuentas por cobrar que ya venció.

```dax
DIVIDE([Cartera vencida], [Cuentas por cobrar])
```

*Tabla `facturas_venta` · formato `0.0%`*

#### Cartera por tramo

Cuentas por cobrar del tramo de antigüedad: días desde el vencimiento a la fecha de corte.

```dax
VAR c = [Fecha de corte]
VAR tramo = SELECTEDVALUE('Tramos de antigüedad'[Orden])
RETURN
    CALCULATE(
        SUMX(
            facturas_venta,
            VAR d = INT(c - facturas_venta[vencimiento])
            RETURN
                IF(
                    SWITCH(tramo, 1, d <= 0, 2, d >= 1 && d <= 30, 3, d >= 31 && d <= 60, 4, d >= 61 && d <= 90, 5, d > 90, TRUE()),
                    facturas_venta[monto]
                )
        ),
        REMOVEFILTERS(Calendario),
        facturas_venta[emision] <= c,
    ISBLANK(facturas_venta[pago]) || facturas_venta[pago] > c
    )
```

*Tabla `facturas_venta` · formato `\$ #,##0`*

#### % de la cartera

Peso del tramo en las cuentas por cobrar.

```dax
DIVIDE([Cartera por tramo], [Cuentas por cobrar])
```

*Tabla `facturas_venta` · formato `0.0%`*

#### Cobrado

Facturas de venta pagadas en el periodo (por fecha de pago).

```dax
CALCULATE(SUM(facturas_venta[monto]), USERELATIONSHIP(facturas_venta[pago], Calendario[Date]))
```

*Tabla `facturas_venta` · formato `\$ #,##0`*

#### Vencimientos de clientes

Facturas de venta que vencían en el periodo (por fecha de vencimiento).

```dax
CALCULATE(SUM(facturas_venta[monto]), USERELATIONSHIP(facturas_venta[vencimiento], Calendario[Date]))
```

*Tabla `facturas_venta` · formato `\$ #,##0`*

#### Cumplimiento de cobranza

Cobrado sobre lo que vencía en el periodo.

```dax
DIVIDE([Cobrado], [Vencimientos de clientes])
```

*Tabla `facturas_venta` · formato `0%`*

#### Cartera vencida acumulada %

Pareto de deudores: cartera vencida acumulada desde el cliente que más debe hasta este, sobre el total.

```dax
VAR propio = [Cartera vencida]
VAR total = CALCULATE([Cartera vencida], ALLSELECTED(clientes[cliente]))
RETURN
    IF(
        propio > 0,
        DIVIDE(SUMX(FILTER(ALLSELECTED(clientes[cliente]), [Cartera vencida] >= propio), [Cartera vencida]), total)
    )
```

*Tabla `facturas_venta` · formato `0%`*

#### Clientes con cartera vencida

Clientes con al menos una factura vencida a la fecha de corte.

```dax
COUNTROWS(FILTER(VALUES(clientes[cliente]), [Cartera vencida] > 0))
```

*Tabla `facturas_venta` · formato `#,##0`*

#### Clientes sobre su límite

Clientes cuyas cuentas por cobrar superan su límite de crédito.

```dax
COUNTROWS(
    FILTER(VALUES(clientes[cliente]), [Cuentas por cobrar] > CALCULATE(MAX(clientes[limite_credito])))
)
```

*Tabla `facturas_venta` · formato `#,##0`*

### 2. Pagos

#### Compras

Facturas de compra emitidas en el periodo: cuadran con las cuentas de Costos compradas a proveedores del reporte #1.

```dax
CALCULATE(SUM(facturas_compra[monto]), KEEPFILTERS(facturas_compra[emision] >= DATE(2025, 1, 1)))
```

*Tabla `facturas_compra` · formato `\$ #,##0`*

#### Compras de la ventana

Compras de los tres meses que terminan en la fecha de corte.

```dax
VAR c = [Fecha de corte]
VAR i = [Inicio de la ventana]
RETURN
    CALCULATE(
        SUM(facturas_compra[monto]),
        REMOVEFILTERS(Calendario),
        facturas_compra[emision] >= i,
        facturas_compra[emision] <= c
    )
```

*Tabla `facturas_compra` · formato `\$ #,##0`*

#### Cuentas por pagar

Facturas de compra recibidas hasta la fecha de corte y no pagadas a esa fecha.

```dax
VAR c = [Fecha de corte]
RETURN
    CALCULATE(
        SUM(facturas_compra[monto]),
        REMOVEFILTERS(Calendario),
        facturas_compra[emision] <= c,
    ISBLANK(facturas_compra[pago]) || facturas_compra[pago] > c
    )
```

*Tabla `facturas_compra` · formato `\$ #,##0`*

#### DPO

Días de compra pendientes de pago: cuentas por pagar sobre las compras de la ventana, por sus días.

```dax
DIVIDE([Cuentas por pagar], [Compras de la ventana]) * [Días de la ventana]
```

*Tabla `facturas_compra` · formato `0`*

#### Pagado a proveedores

Facturas de compra pagadas en el periodo (por fecha de pago).

```dax
CALCULATE(SUM(facturas_compra[monto]), USERELATIONSHIP(facturas_compra[pago], Calendario[Date]))
```

*Tabla `facturas_compra` · formato `\$ #,##0`*

#### Vencimientos de proveedores

Facturas de compra que vencían en el periodo: el calendario de pagos.

```dax
CALCULATE(SUM(facturas_compra[monto]), USERELATIONSHIP(facturas_compra[vencimiento], Calendario[Date]))
```

*Tabla `facturas_compra` · formato `\$ #,##0`*

#### Facturas pagadas

Facturas de compra pagadas en el periodo.

```dax
CALCULATE(
    COUNTROWS(FILTER(facturas_compra, NOT ISBLANK(facturas_compra[pago]))),
    USERELATIONSHIP(facturas_compra[pago], Calendario[Date])
)
```

*Tabla `facturas_compra` · formato `#,##0`*

#### Facturas pagadas con atraso

Facturas pagadas más de 7 días después de su vencimiento.

```dax
CALCULATE(
    COUNTROWS(FILTER(facturas_compra, NOT ISBLANK(facturas_compra[pago]) && facturas_compra[pago] > facturas_compra[vencimiento] + 7)),
    USERELATIONSHIP(facturas_compra[pago], Calendario[Date])
)
```

*Tabla `facturas_compra` · formato `#,##0`*

#### Monto pagado con atraso

Monto de las facturas pagadas más de 7 días después de su vencimiento.

```dax
CALCULATE(
    SUMX(FILTER(facturas_compra, NOT ISBLANK(facturas_compra[pago]) && facturas_compra[pago] > facturas_compra[vencimiento] + 7), facturas_compra[monto]),
    USERELATIONSHIP(facturas_compra[pago], Calendario[Date])
)
```

*Tabla `facturas_compra` · formato `\$ #,##0`*

#### % pagado con atraso

Parte de las facturas pagadas con más de 7 días de atraso.

```dax
DIVIDE([Facturas pagadas con atraso], [Facturas pagadas])
```

*Tabla `facturas_compra` · formato `0.0%`*

#### Facturas pagadas antes de plazo

Facturas pagadas 7 días o más antes del vencimiento (por descuento de pronto pago).

```dax
CALCULATE(
    COUNTROWS(FILTER(facturas_compra, NOT ISBLANK(facturas_compra[pago]) && facturas_compra[pago] <= facturas_compra[vencimiento] - 7)),
    USERELATIONSHIP(facturas_compra[pago], Calendario[Date])
)
```

*Tabla `facturas_compra` · formato `#,##0`*

#### Atraso promedio de pago

Días promedio entre el vencimiento y el pago (negativo: se pagó antes).

```dax
CALCULATE(
    AVERAGEX(FILTER(facturas_compra, NOT ISBLANK(facturas_compra[pago])), INT(facturas_compra[pago] - facturas_compra[vencimiento])),
    USERELATIONSHIP(facturas_compra[pago], Calendario[Date])
)
```

*Tabla `facturas_compra` · formato `0.0`*

### 3. Inventario

#### Inventario al corte

Saldo de inventario al cierre del mes de la fecha de corte.

```dax
VAR c = [Fecha de corte]
RETURN CALCULATE(SUM(inventario_mensual[saldo]), REMOVEFILTERS(Calendario), inventario_mensual[fecha] = DATE(YEAR(c), MONTH(c), 1))
```

*Tabla `inventario_mensual` · formato `\$ #,##0`*

#### Consumo de la ventana

Consumo de inventario de los tres meses que terminan en la fecha de corte.

```dax
VAR c = [Fecha de corte]
VAR i = [Inicio de la ventana]
RETURN CALCULATE(SUM(inventario_mensual[consumo]), REMOVEFILTERS(Calendario), inventario_mensual[fecha] >= i, inventario_mensual[fecha] <= c)
```

*Tabla `inventario_mensual` · formato `\$ #,##0`*

#### DIO

Días de inventario: saldo al corte sobre el consumo de la ventana, por sus días.

```dax
DIVIDE([Inventario al corte], [Consumo de la ventana]) * [Días de la ventana]
```

*Tabla `inventario_mensual` · formato `0`*

#### Rotación de inventario

Veces que el inventario se renueva en un año al ritmo de consumo de la ventana.

```dax
DIVIDE(365, [DIO])
```

*Tabla `inventario_mensual` · formato `0.0`*

#### Consumo del periodo

Consumo de inventario del periodo (cuentas de materiales del #1).

```dax
SUM(inventario_mensual[consumo])
```

*Tabla `inventario_mensual` · formato `\$ #,##0`*

#### Cobertura en días

Días de consumo que cubre el saldo del mes.

```dax
DIVIDE(SUM(inventario_mensual[saldo]), SUM(inventario_mensual[consumo])) * 30
```

*Tabla `inventario_mensual` · formato `0`*

#### Días objetivo

Cobertura objetivo de la familia, en días de consumo.

```dax
AVERAGE(inventario_mensual[cobertura_objetivo])
```

*Tabla `inventario_mensual` · formato `0`*

#### Sobrestock

Saldo sobre 1,3 veces la cobertura objetivo, al cierre del mes de corte.

```dax
VAR c = [Fecha de corte]
RETURN
    CALCULATE(
        SUMX(inventario_mensual, MAX(0, inventario_mensual[saldo] - inventario_mensual[consumo] / 30 * inventario_mensual[cobertura_objetivo] * 1.3)),
        REMOVEFILTERS(Calendario),
        inventario_mensual[fecha] = DATE(YEAR(c), MONTH(c), 1)
    )
```

*Tabla `inventario_mensual` · formato `\$ #,##0`*

#### Meses con quiebre

Familias y sucursales que cerraron un mes con menos de 5 días de cobertura.

```dax
COUNTROWS(FILTER(inventario_mensual, inventario_mensual[saldo] < inventario_mensual[consumo] / 30 * 5))
```

*Tabla `inventario_mensual` · formato `#,##0`*

### 4. Ciclo de caja

#### Ciclo de conversión de caja

Días entre pagarle al proveedor y cobrarle al cliente: DSO + DIO − DPO.

```dax
[DSO] + [DIO] - [DPO]
```

*Tabla `facturas_venta` · formato `0`*

#### Capital de trabajo neto

Cuentas por cobrar más inventario menos cuentas por pagar, a la fecha de corte.

```dax
[Cuentas por cobrar] + [Inventario al corte] - [Cuentas por pagar]
```

*Tabla `facturas_venta` · formato `\$ #,##0`*

#### Días del ciclo

Cada escalón de la cascada del ciclo; el total es el ciclo de conversión de caja.

```dax
SWITCH(
    SELECTEDVALUE('Escalones del ciclo'[Componente]),
    "DSO", [DSO],
    "DIO", [DIO],
    "DPO", -[DPO]
)
```

*Tabla `facturas_venta` · formato `0`*

### 5. Flujo de caja

#### Cobros en caja

Cobros de la semana (reales o proyectados).

```dax
SUM(caja_semanal[cobros])
```

*Tabla `caja_semanal` · formato `\$ #,##0`*

#### Pagos en caja

Pagos de la semana: proveedores, remuneraciones y gastos, inversiones y dividendos.

```dax
SUM(caja_semanal[pagos])
```

*Tabla `caja_semanal` · formato `\$ #,##0`*

#### Saldo real

Saldo de caja al cierre de la semana, hasta la fecha de corte.

```dax
CALCULATE(SUM(caja_semanal[saldo_final]), caja_semanal[tipo] = "Real")
```

*Tabla `caja_semanal` · formato `\$ #,##0`*

#### Saldo proyectado

Saldo de caja proyectado al cierre de cada una de las 13 semanas siguientes al corte.

```dax
CALCULATE(SUM(caja_semanal[saldo_final]), caja_semanal[tipo] = "Proyectado")
```

*Tabla `caja_semanal` · formato `\$ #,##0`*

#### Saldo al corte

Saldo de caja de la última semana real.

```dax
VAR s = CALCULATE(MAX(caja_semanal[semana]), caja_semanal[tipo] = "Real")
RETURN CALCULATE(SUM(caja_semanal[saldo_final]), caja_semanal[semana] = s)
```

*Tabla `caja_semanal` · formato `\$ #,##0`*

#### Saldo en 13 semanas

Saldo de caja proyectado al final de las 13 semanas.

```dax
VAR s = CALCULATE(MAX(caja_semanal[semana]), caja_semanal[tipo] = "Proyectado")
RETURN CALCULATE(SUM(caja_semanal[saldo_final]), caja_semanal[semana] = s)
```

*Tabla `caja_semanal` · formato `\$ #,##0`*

#### Cobros proyectados

Cobros de las 13 semanas proyectadas.

```dax
CALCULATE(SUM(caja_semanal[cobros]), caja_semanal[tipo] = "Proyectado")
```

*Tabla `caja_semanal` · formato `\$ #,##0`*

#### Pagos proyectados

Pagos de las 13 semanas proyectadas.

```dax
CALCULATE(SUM(caja_semanal[pagos]), caja_semanal[tipo] = "Proyectado")
```

*Tabla `caja_semanal` · formato `\$ #,##0`*

#### Bajo el mínimo

1 si el saldo de la semana queda bajo el saldo mínimo elegido.

```dax
IF(SUM(caja_semanal[saldo_final]) < [Saldo mínimo elegido], 1)
```

*Tabla `caja_semanal` · formato `0`*

#### Semanas bajo el mínimo

Semanas con saldo bajo el mínimo elegido.

```dax
VAR minimo = [Saldo mínimo elegido]
RETURN COUNTROWS(FILTER(VALUES(caja_semanal[semana]), CALCULATE(SUM(caja_semanal[saldo_final])) < minimo))
```

*Tabla `caja_semanal` · formato `#,##0`*

#### Causa

Qué explica la semana bajo el mínimo: una inversión o dividendo, pagos altos o cobros bajos.

```dax
VAR promedio = CALCULATE(AVERAGE(caja_semanal[pagos]), ALLEXCEPT(caja_semanal, caja_semanal[industria]))
RETURN
    IF(
        [Bajo el mínimo] = 1,
        SWITCH(
            TRUE(),
            SUM(caja_semanal[inversiones_dividendos]) > 0, "Inversión o dividendo",
            SUM(caja_semanal[pagos]) > promedio * 1.3, "Pagos altos (remuneraciones y proveedores)",
            "Cobros bajos"
        )
    )
```

*Tabla `caja_semanal`*

#### Saldo mínimo elegido

Saldo mínimo elegido en el segmentador; si no hay uno elegido, $60 M.

```dax
SELECTEDVALUE('Saldo mínimo'[Saldo mínimo], 60000000)
```

*Tabla `Saldo mínimo` · formato `\$ #,##0`*
