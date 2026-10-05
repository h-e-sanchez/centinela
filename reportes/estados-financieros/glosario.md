# Glosario: Del libro diario a los EEFF

> Qué significa cada concepto del reporte y cómo se calcula. La primera parte lo explica con palabras; la segunda lista **todas** las medidas DAX del modelo, leídas del proyecto PBIP con `herramientas/generar_glosario.py`, así que coinciden con lo que calcula Power BI.

## Conceptos

### La partida doble

**Asiento.** El registro de un hecho económico en el libro diario. Tiene fecha, glosa y dos o más líneas.

**Debe y haber.** Las dos columnas de cada línea. En cada asiento, lo que va al debe suma lo mismo que lo que va al haber: es la partida doble.
- **Al debe** aumentan los activos y los gastos, y disminuyen los pasivos, el patrimonio y los ingresos.
- **Al haber** pasa lo contrario.

**Plan de cuentas.** La lista de cuentas de la empresa, ordenada por tipo: activo, pasivo, patrimonio, ingreso, costo y gasto.

**Naturaleza.** Si la cuenta suele tener saldo deudor (activos y gastos) o acreedor (pasivos, patrimonio e ingresos).

### Del libro a los estados

**Libro diario.** Todos los asientos en orden de fecha.

**Balance de comprobación.** Por cuenta, lo cargado, lo abonado y el saldo. Si el libro está bien, el total del debe es igual al total del haber.

**Estado de resultados (EERR).** Ingresos menos costos y gastos del periodo: muestra si la empresa ganó o perdió.

**EBITDA.** Resultado antes de depreciación, intereses e impuestos. Aquí es el resultado operacional del reporte Presupuesto vs. Real.

**Balance general.** Lo que la empresa tiene (activo) y cómo lo financia (pasivo y patrimonio) en una fecha. Siempre: activo = pasivo + patrimonio.

**Flujo de efectivo (método indirecto).** Parte del resultado, le suma lo que no movió caja (la depreciación) y resta lo que absorbieron el capital de trabajo, la inversión y la deuda. El total es la variación de la caja.

### Cuentas del ciclo

**Deudores por ventas.** Ventas facturadas que aún no se cobran.

**Inventarios.** Materiales comprados que todavía no se consumen.

**Proveedores.** Compras y servicios recibidos que todavía no se pagan.

**Activo fijo y depreciación.** Lo invertido en planta y equipos, que se reconoce como gasto en el tiempo a medida que se desgasta.

**Línea de crédito de corto plazo.** Un préstamo que se gira cuando falta caja y se abona cuando sobra.

**Impuesto a la renta.** Se devenga cada mes sobre el resultado (27%) y se paga al año siguiente.

### Cierre e indicadores

**Cierre del ejercicio.** Al 31 de diciembre, las cuentas de ingresos y gastos se dejan en cero contra «Resultado del ejercicio». En enero, ese resultado se traspasa a «Resultados acumulados».

**Asiento de apertura.** El primer asiento: carga los saldos iniciales del balance.

**Liquidez corriente** = activo corriente / pasivo corriente. **Prueba ácida:** lo mismo, sin inventarios.

**Endeudamiento** = pasivo / patrimonio.

**ROE** = resultado / patrimonio: la rentabilidad para los dueños.

**Días de cobro, de inventario y de pago.** En cuántos días de actividad se cobra, se consume el inventario y se paga a proveedores. **Ciclo de caja** = cobro + inventario − pago.

## Medidas del modelo

El modelo tiene 60 medidas, agrupadas por carpeta como aparecen en el panel de datos de Power BI. Las de *portada* y *tarjetas* solo dan formato de texto a otras medidas.

### 0. Auxiliares

#### Días del periodo

Días calendario del periodo filtrado.

```dax
DATEDIFF(MIN(Calendario[Date]), MIN(MAX(Calendario[Date]), DATE(2026, 12, 31)), DAY) + 1
```

*Tabla `lineas_asiento` · formato `0`*

### 0. Portada

#### Portada ingresos

Ingresos abreviados.

```dax
VAR v = [Ingresos]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(v), BLANK(),
        ABS(v) >= 1000000000, FORMAT(v / 1000000000, "$ #,0.0") & " mil M",
        ABS(v) >= 1000000, FORMAT(v / 1000000, "$ #,0.0") & " M",
        FORMAT(v, "$ #,0")
    )
```

*Tabla `lineas_asiento`*

#### Portada margen EBITDA

Margen EBITDA para la tarjeta.

```dax
FORMAT([Margen EBITDA %], "0.0%")
```

*Tabla `lineas_asiento`*

#### Portada liquidez

Liquidez corriente para la tarjeta.

```dax
FORMAT([Liquidez corriente], "0.00")
```

*Tabla `lineas_asiento`*

#### Portada frase 1

Primera frase: los días del ciclo de caja.

```dax
"Cobra en " & FORMAT([Días de cobro], "0") & " días, guarda " & FORMAT([Días de inventario], "0")
    & " días de inventario y paga en " & FORMAT([Días de pago], "0")
```

*Tabla `lineas_asiento`*

#### Portada frase 2

Segunda frase: estructura del balance.

```dax
"Activo fijo " & FORMAT(DIVIDE([Activo fijo neto], [Activo]), "0%") & " del activo; endeudamiento "
    & FORMAT([Endeudamiento], "0.00")
```

*Tabla `lineas_asiento`*

### 1. Libro diario

#### Asientos

Asientos registrados en el periodo.

```dax
COUNTROWS(asientos)
```

*Tabla `asientos` · formato `#,##0`*

#### Debe

Suma de cargos (debe).

```dax
SUM(lineas_asiento[debe])
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Haber

Suma de abonos (haber).

```dax
SUM(lineas_asiento[haber])
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Monto

Debe menos haber: positivo = saldo deudor.

```dax
[Debe] - [Haber]
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

### 2. Estado de resultados

#### Monto EERR

Ingresos en positivo y costos o gastos en negativo, sin los asientos de cierre.

```dax
CALCULATE([Haber] - [Debe], NOT asientos[tipo] IN {"Apertura", "Cierre", "Traspaso"}, plan_cuentas[tipo] IN {"Ingreso", "Costo", "Gasto"})
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Ingresos

Ventas del periodo (las mismas del Real del #1).

```dax
CALCULATE([Monto EERR], plan_cuentas[linea] = "Ingresos")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Costos

Costos directos, en negativo.

```dax
CALCULATE([Monto EERR], plan_cuentas[linea] = "Costos")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Gastos operacionales

Gastos de administración y venta, en negativo.

```dax
CALCULATE([Monto EERR], plan_cuentas[linea] = "Gastos operacionales")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### EBITDA

Resultado antes de depreciación, intereses e impuestos: es el resultado operacional del #1.

```dax
[Ingresos] + [Costos] + [Gastos operacionales]
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Depreciación

Desgaste del activo fijo del periodo, en negativo.

```dax
CALCULATE([Monto EERR], plan_cuentas[linea] = "Depreciación")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Gastos financieros

Intereses de la deuda, en negativo.

```dax
CALCULATE([Monto EERR], plan_cuentas[linea] = "Gastos financieros")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Resultado antes de impuestos

EBITDA menos depreciación e intereses.

```dax
[EBITDA] + [Depreciación] + [Gastos financieros]
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Impuesto a la renta

Impuesto devengado (27%), en negativo.

```dax
CALCULATE([Monto EERR], plan_cuentas[linea] = "Impuesto a la renta")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Resultado del ejercicio

Utilidad o pérdida del periodo.

```dax
[Resultado antes de impuestos] + [Impuesto a la renta]
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Margen EBITDA %

EBITDA sobre ingresos.

```dax
DIVIDE([EBITDA], [Ingresos])
```

*Tabla `lineas_asiento` · formato `0.0%`*

#### Margen neto %

Resultado del ejercicio sobre ingresos.

```dax
DIVIDE([Resultado del ejercicio], [Ingresos])
```

*Tabla `lineas_asiento` · formato `0.0%`*

#### Presupuesto EERR

Mismas líneas del Presupuesto del #1 (hasta el EBITDA).

```dax
CALCULATE(
    SUMX(eerr_reporte1, eerr_reporte1[monto] * IF(RELATED(plan_cuentas[tipo]) = "Ingreso", 1, -1)),
    eerr_reporte1[version] = "Presupuesto"
)
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Variación vs. presupuesto

Real contable menos presupuesto, por línea.

```dax
[Monto EERR] - [Presupuesto EERR]
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

### 3. Balance

#### Saldo deudor

Saldo acumulado hasta el último día del periodo (debe menos haber, desde la apertura).

```dax
CALCULATE([Monto], FILTER(ALL(Calendario[Date]), Calendario[Date] <= MAX(Calendario[Date])))
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Saldo

Saldo con su signo natural: los activos y gastos en positivo, los pasivos, el patrimonio y los ingresos también.

```dax
SUMX(VALUES(plan_cuentas[naturaleza]), [Saldo deudor] * plan_cuentas[naturaleza])
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Activo

Total de activos al cierre.

```dax
CALCULATE([Saldo deudor], plan_cuentas[tipo] = "Activo")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Pasivo

Total de pasivos al cierre.

```dax
-CALCULATE([Saldo deudor], plan_cuentas[tipo] = "Pasivo")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Patrimonio

Capital, resultados acumulados y resultado del ejercicio (cerrado o en curso).

```dax
-CALCULATE([Saldo deudor], plan_cuentas[tipo] IN {"Patrimonio", "Ingreso", "Costo", "Gasto"})
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Resultado en curso

Resultado del año aún no cerrado: aparece en el patrimonio hasta el asiento de cierre.

```dax
-CALCULATE([Saldo deudor], plan_cuentas[tipo] IN {"Ingreso", "Costo", "Gasto"})
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Activo corriente

Caja, deudores e inventarios.

```dax
CALCULATE([Saldo deudor], plan_cuentas[clasificacion] = "Activo corriente")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Pasivo corriente

Proveedores, remuneraciones, crédito de corto plazo e impuestos por pagar.

```dax
-CALCULATE([Saldo deudor], plan_cuentas[clasificacion] = "Pasivo corriente")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Caja

Caja y bancos al cierre.

```dax
CALCULATE([Saldo deudor], plan_cuentas[linea] = "Efectivo")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Deudores por ventas

Ventas por cobrar al cierre.

```dax
CALCULATE([Saldo deudor], plan_cuentas[linea] = "Deudores por ventas")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Inventarios

Materiales en bodega al cierre.

```dax
CALCULATE([Saldo deudor], plan_cuentas[linea] = "Inventarios")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Proveedores

Compras y servicios por pagar al cierre.

```dax
-CALCULATE([Saldo deudor], plan_cuentas[linea] = "Proveedores")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Activo fijo neto

Propiedades, planta y equipo menos la depreciación acumulada.

```dax
CALCULATE([Saldo deudor], plan_cuentas[linea] = "Activo fijo neto")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Deuda financiera

Préstamos de corto y largo plazo.

```dax
-CALCULATE([Saldo deudor], plan_cuentas[linea] IN {"Deuda financiera de corto plazo", "Deuda financiera de largo plazo"})
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

### 4. Flujo de efectivo

#### Movimiento

Debe menos haber del periodo, sin apertura ni cierres.

```dax
CALCULATE([Monto], NOT asientos[tipo] IN {"Apertura", "Cierre", "Traspaso"})
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Variación de caja

Cuánto cambió la caja en el periodo.

```dax
CALCULATE([Movimiento], plan_cuentas[linea] = "Efectivo")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Monto del flujo

Cada escalón del flujo indirecto; el total es la variación de caja.

```dax
SWITCH(
    SELECTEDVALUE('Escalones del flujo'[Escalón]),
    "Resultado del ejercicio", [Resultado del ejercicio],
    "Depreciación", -CALCULATE([Movimiento], plan_cuentas[orden] = 1202),
    "Deudores por ventas", -CALCULATE([Movimiento], plan_cuentas[linea] = "Deudores por ventas"),
    "Inventarios", -CALCULATE([Movimiento], plan_cuentas[linea] = "Inventarios"),
    "Proveedores", -CALCULATE([Movimiento], plan_cuentas[linea] = "Proveedores"),
    "Remuneraciones e impuestos", -CALCULATE([Movimiento], plan_cuentas[linea] IN {"Remuneraciones por pagar", "Impuestos por pagar"}),
    "Inversión en activo fijo", -CALCULATE([Movimiento], plan_cuentas[orden] = 1201),
    "Deuda financiera", -CALCULATE([Movimiento], plan_cuentas[linea] IN {"Deuda financiera de corto plazo", "Deuda financiera de largo plazo"})
)
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Flujo operacional

Resultado más depreciación y menos el aumento del capital de trabajo.

```dax
[Resultado del ejercicio]
    - CALCULATE([Movimiento], plan_cuentas[orden] = 1202)
    - CALCULATE([Movimiento], plan_cuentas[linea] IN {"Deudores por ventas", "Inventarios", "Proveedores", "Remuneraciones por pagar", "Impuestos por pagar"})
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Flujo de inversión

Compras de activo fijo, en negativo.

```dax
-CALCULATE([Movimiento], plan_cuentas[orden] = 1201)
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Flujo de financiamiento

Préstamos recibidos menos amortizaciones.

```dax
-CALCULATE([Movimiento], plan_cuentas[linea] IN {"Deuda financiera de corto plazo", "Deuda financiera de largo plazo"})
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

### 5. Indicadores

#### Liquidez corriente

Activo corriente sobre pasivo corriente: cuántas veces se cubren las deudas de corto plazo.

```dax
DIVIDE([Activo corriente], [Pasivo corriente])
```

*Tabla `lineas_asiento` · formato `0.00`*

#### Prueba ácida

Liquidez sin contar inventarios.

```dax
DIVIDE([Activo corriente] - [Inventarios], [Pasivo corriente])
```

*Tabla `lineas_asiento` · formato `0.00`*

#### Endeudamiento

Pasivo sobre patrimonio: cuánto de lo que tiene la empresa está financiado por terceros.

```dax
DIVIDE([Pasivo], [Patrimonio])
```

*Tabla `lineas_asiento` · formato `0.00`*

#### Capital de trabajo neto

Activo corriente menos pasivo corriente.

```dax
[Activo corriente] - [Pasivo corriente]
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### ROE anualizado

Resultado del periodo llevado a un año, sobre el patrimonio al cierre.

```dax
DIVIDE([Resultado del ejercicio] * 365 / [Días del periodo], [Patrimonio])
```

*Tabla `lineas_asiento` · formato `0.0%`*

#### Días de cobro

Días de venta que están por cobrar (DSO).

```dax
DIVIDE([Deudores por ventas], [Ingresos]) * [Días del periodo]
```

*Tabla `lineas_asiento` · formato `0`*

#### Consumo de materiales

Costo de los materiales consumidos en el periodo.

```dax
CALCULATE([Debe], NOT asientos[tipo] IN {"Apertura", "Cierre", "Traspaso"}, plan_cuentas[inventariable] = 1)
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Días de inventario

Días de consumo que hay en bodega (DIO).

```dax
DIVIDE([Inventarios], [Consumo de materiales]) * [Días del periodo]
```

*Tabla `lineas_asiento` · formato `0`*

#### Compras y servicios

Lo que se compró a proveedores en el periodo.

```dax
CALCULATE([Haber], NOT asientos[tipo] IN {"Apertura", "Cierre", "Traspaso"}, plan_cuentas[linea] = "Proveedores")
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Días de pago

Días de compras que están por pagar (DPO).

```dax
DIVIDE([Proveedores], [Compras y servicios]) * [Días del periodo]
```

*Tabla `lineas_asiento` · formato `0`*

#### Ciclo de caja

Días entre pagar al proveedor y cobrarle al cliente.

```dax
[Días de cobro] + [Días de inventario] - [Días de pago]
```

*Tabla `lineas_asiento` · formato `0`*

### 6. Cierre

#### Diferencia debe - haber

En todo el libro debe ser 0: partida doble.

```dax
[Debe] - [Haber]
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Diferencia de balance

Activo menos pasivo y patrimonio: siempre 0.

```dax
[Activo] - [Pasivo] - [Patrimonio]
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Diferencia del flujo

Flujo de efectivo menos variación de caja: siempre 0.

```dax
[Flujo operacional] + [Flujo de inversión] + [Flujo de financiamiento] - [Variación de caja]
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### EBITDA Real del reporte 1

Resultado operacional Real del reporte Presupuesto vs. Real.

```dax
CALCULATE(
    SUMX(eerr_reporte1, eerr_reporte1[monto] * IF(RELATED(plan_cuentas[tipo]) = "Ingreso", 1, -1)),
    eerr_reporte1[version] = "Real"
)
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*

#### Diferencia con el reporte 1

EBITDA de la contabilidad menos el resultado operacional del #1: siempre 0.

```dax
[EBITDA] - [EBITDA Real del reporte 1]
```

*Tabla `lineas_asiento` · formato `\$ #,##0`*
