# Glosario: Pricing y márgenes por canal

> Qué significa cada concepto del reporte y cómo se calcula. La primera parte lo explica con palabras; la segunda lista **todas** las medidas DAX del modelo, leídas del proyecto PBIP con `herramientas/generar_glosario.py`, así que coinciden con lo que calcula Power BI.

## Conceptos

### Del precio de lista al bolsillo

**Precio de lista.** El precio publicado de cada producto o prestación, antes de cualquier descuento.

**Descuento comercial.** La rebaja negociada que aparece en la factura.

**Rappel.** Un descuento por volumen que se devuelve al cliente cuando cumple metas de compra, típico del retail.

**Bonificación.** Aportes al cliente fuera de la factura: promociones, exhibición o material de punto de venta.

**Ingreso neto.** Lo que de verdad se cobra: precio de lista menos los tres descuentos. Es la cifra que cuadra con el reporte Presupuesto vs. Real.

**% de realización** = ingreso neto / ingreso de lista. Parte del precio de lista que llega a la caja.

**Cascada de precios.** El gráfico que muestra cuánto se queda en cada escalón entre la lista y el margen final (en inglés, *price waterfall* o *pocket price*).

### Márgenes

**Costo variable.** El costo directo de lo vendido: materia prima, energía comprada o insumos clínicos.

**Margen bruto** = ingreso neto − costo variable.

**Costo de servir.** Lo que cuesta atender a un canal además de producir: logística, comisiones, trade marketing y atención. Retail y postventa son caros de servir; un cliente industrial grande, barato.

**Margen de contribución** = margen bruto − costo de servir. Es la medida justa para comparar canales: lo que cada uno aporta a cubrir los costos fijos.

### Precio, volumen y mezcla

**Efecto precio.** Cuánto cambió el ingreso porque cambió el precio de cada producto, a las cantidades de 2026.

**Efecto volumen.** Cuánto cambió porque se vendió más o menos en total, al precio promedio de 2025.

**Efecto mezcla.** Cuánto cambió porque se vendieron productos más caros o más baratos que antes, con el mismo volumen total.

Los tres efectos suman exactamente la variación de ingresos. Solo tiene sentido dentro de una industria, donde las unidades son comparables.

### Política comercial y clientes

**Política de descuentos.** El descuento total máximo que la empresa autoriza en cada canal.

**Fuga** (descuento fuera de política). El descuento dado por sobre ese máximo. Suele concentrarse en pocos clientes que negocian fuerte.

**Curva ballena.** Clientes ordenados del más al menos rentable, con el margen acumulado. Sube sobre 100% mientras los clientes suman margen y baja al final por los que lo restan: muestra cuánto margen se pierde en la cola.

**Elasticidad precio.** Cuánto cambia el volumen (en %) por cada 1% de cambio de precio. En el simulador es un supuesto por canal: retail reacciona mucho; el mercado spot y los peajes, nada.

## Medidas del modelo

El modelo tiene 45 medidas, agrupadas por carpeta como aparecen en el panel de datos de Power BI. Las de *portada* y *tarjetas* solo dan formato de texto a otras medidas.

### 0. Portada

#### Portada ingreso

Ingreso neto abreviado.

```dax
VAR v = [Ingreso neto]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(v), BLANK(),
        ABS(v) >= 1000000000, FORMAT(v / 1000000000, "$ #,0.0") & " mil M",
        ABS(v) >= 1000000, FORMAT(v / 1000000, "$ #,0.0") & " M",
        FORMAT(v, "$ #,0")
    )
```

*Tabla `transacciones`*

#### Portada realización

% de realización para la tarjeta.

```dax
FORMAT([% de realización], "0.0%")
```

*Tabla `transacciones`*

#### Portada margen

Margen de contribución % para la tarjeta.

```dax
FORMAT([Margen de contribución %], "0.0%")
```

*Tabla `transacciones`*

#### Portada frase 1

Primera frase: el canal con menor margen de contribución y su peso en el ingreso.

```dax
VAR menor = TOPN(1, FILTER(VALUES(canales[canal]), NOT ISBLANK([Ingreso neto])), [Margen de contribución %], ASC)
VAR canal = MAXX(menor, canales[canal])
RETURN
    canal & ": " & FORMAT(CALCULATE([Ingreso neto], canales[canal] = canal) / [Ingreso neto], "0%")
        & " del ingreso, " & FORMAT(CALCULATE([Margen de contribución %], canales[canal] = canal), "0.0%") & " de margen"
```

*Tabla `transacciones`*

#### Portada frase 2

Segunda frase: cuánto de la variación de ingresos explica el precio.

```dax
"2026 vs. 2025: el precio explica " & FORMAT([Efecto precio % de la variación], "0%") & " de la variación"
```

*Tabla `transacciones`*

### 1. Ingresos

#### Precio de lista

Precio de lista del producto en el año.

```dax
AVERAGE(lista_precios[precio_lista])
```

*Tabla `lista_precios` · formato `\$ #,##0`*

#### Ingreso de lista

Lo que se habría facturado a precio de lista.

```dax
SUM(transacciones[ingreso_lista])
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Ingreso neto

Ingreso después de todos los descuentos: cuadra con el Real del reporte Presupuesto vs. Real.

```dax
SUM(transacciones[ingreso_neto])
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Unidades vendidas

Unidades vendidas (unidades, meses de contrato, MWh o prestaciones según el producto).

```dax
SUM(transacciones[cantidad])
```

*Tabla `transacciones` · formato `#,##0`*

#### Precio neto unitario

Ingreso neto por unidad vendida.

```dax
DIVIDE([Ingreso neto], [Unidades vendidas])
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Ingreso presupuestado

Ingreso del Presupuesto del reporte #1.

```dax
SUM(presupuesto_ingresos[monto])
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Variación vs. presupuesto %

Ingreso neto sobre el presupuestado, menos 1.

```dax
DIVIDE([Ingreso neto], [Ingreso presupuestado]) - 1
```

*Tabla `transacciones` · formato `0.0%`*

### 2. Cascada

#### Descuento comercial

Descuento negociado en la factura.

```dax
SUM(transacciones[descuento_comercial])
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Rappel otorgado

Descuento por volumen que se devuelve al cliente al cumplir metas.

```dax
SUM(transacciones[rappel])
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Bonificación otorgada

Aportes al cliente fuera de la factura (promociones, exhibición).

```dax
SUM(transacciones[bonificacion])
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### % de realización

Parte del precio de lista que de verdad se cobra.

```dax
DIVIDE([Ingreso neto], [Ingreso de lista])
```

*Tabla `transacciones` · formato `0.0%`*

#### Monto de la cascada

Cada escalón de la cascada de precio a bolsillo; el total es el margen de contribución.

```dax
SWITCH(
    SELECTEDVALUE('Cascada de precios'[Escalón]),
    "Ingreso de lista", [Ingreso de lista],
    "Descuento comercial", -[Descuento comercial],
    "Rappel", -[Rappel otorgado],
    "Bonificación", -[Bonificación otorgada],
    "Costo variable", -[Costo variable],
    "Costo de servir", -[Costo de servir]
)
```

*Tabla `transacciones` · formato `\$ #,##0`*

### 3. Márgenes

#### Costo variable

Costo directo de lo vendido.

```dax
SUM(transacciones[costo_variable])
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Costo de servir

Logística, comisiones y atención propios del canal.

```dax
SUM(transacciones[costo_servir])
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Margen bruto

Ingreso neto menos costo variable.

```dax
[Ingreso neto] - [Costo variable]
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Margen bruto %

Margen bruto sobre ingreso neto.

```dax
DIVIDE([Margen bruto], [Ingreso neto])
```

*Tabla `transacciones` · formato `0.0%`*

#### Margen de contribución

Lo que deja la venta después del costo variable y del costo de servir al canal.

```dax
[Margen bruto] - [Costo de servir]
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Margen de contribución %

Margen de contribución sobre ingreso neto.

```dax
DIVIDE([Margen de contribución], [Ingreso neto])
```

*Tabla `transacciones` · formato `0.0%`*

#### Clientes con margen negativo

Clientes cuyo margen de contribución es negativo en el periodo.

```dax
COUNTROWS(FILTER(VALUES(clientes[cliente]), [Margen de contribución] < 0))
```

*Tabla `transacciones` · formato `#,##0`*

#### Margen acumulado %

Curva ballena: margen acumulado desde el cliente más rentable hasta este, sobre el margen total.

```dax
VAR propio = [Margen de contribución]
VAR total = CALCULATE([Margen de contribución], ALLSELECTED(clientes[cliente]))
RETURN
    DIVIDE(
        SUMX(FILTER(ALLSELECTED(clientes[cliente]), [Margen de contribución] >= propio), [Margen de contribución]),
        total
    )
```

*Tabla `transacciones` · formato `0%`*

### 4. Descuentos

#### Descuento máximo de la política

Descuento total máximo que permite la política comercial del canal.

```dax
MAX(canales[descuento_maximo])
```

*Tabla `canales` · formato `0%`*

#### Descuento total %

Descuento comercial, rappel y bonificación sobre el ingreso de lista.

```dax
1 - [% de realización]
```

*Tabla `transacciones` · formato `0.0%`*

#### Descuento fuera de política

Descuento dado por sobre el máximo de la política del canal: la fuga.

```dax
SUMX(
    transacciones,
    MAX(0, transacciones[ingreso_lista] - transacciones[ingreso_neto] - transacciones[ingreso_lista] * RELATED(canales[descuento_maximo]))
)
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Líneas fuera de política

Líneas de venta con descuento total sobre el máximo de la política.

```dax
COUNTROWS(
    FILTER(
        transacciones,
        1 - DIVIDE(transacciones[ingreso_neto], transacciones[ingreso_lista]) > RELATED(canales[descuento_maximo])
    )
)
```

*Tabla `transacciones` · formato `#,##0`*

#### Líneas de venta

Líneas de venta.

```dax
COUNTROWS(transacciones)
```

*Tabla `transacciones` · formato `#,##0`*

#### % de líneas fuera de política

Parte de las líneas con descuento sobre la política.

```dax
DIVIDE([Líneas fuera de política], [Líneas de venta])
```

*Tabla `transacciones` · formato `0.0%`*

### 5. Precio, volumen y mezcla

#### Ingreso 2025

Ingreso neto de 2025 (no depende del segmentador de año).

```dax
CALCULATE([Ingreso neto], REMOVEFILTERS(Calendario), transacciones[anio] = 2025)
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Ingreso 2026

Ingreso neto de 2026 (no depende del segmentador de año).

```dax
CALCULATE([Ingreso neto], REMOVEFILTERS(Calendario), transacciones[anio] = 2026)
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Variación de ingresos

Ingreso 2026 menos ingreso 2025.

```dax
[Ingreso 2026] - [Ingreso 2025]
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Efecto precio

Lo que cambió el ingreso por el precio, a los volúmenes de 2026.

```dax
SUMX(
    VALUES(productos[producto]),
    VAR q1 = CALCULATE(SUM(transacciones[cantidad]), REMOVEFILTERS(Calendario), transacciones[anio] = 2026)
    VAR q0 = CALCULATE(SUM(transacciones[cantidad]), REMOVEFILTERS(Calendario), transacciones[anio] = 2025)
    VAR r1 = CALCULATE(SUM(transacciones[ingreso_neto]), REMOVEFILTERS(Calendario), transacciones[anio] = 2026)
    VAR r0 = CALCULATE(SUM(transacciones[ingreso_neto]), REMOVEFILTERS(Calendario), transacciones[anio] = 2025)
    RETURN IF(q0 > 0 && q1 > 0, (DIVIDE(r1, q1) - DIVIDE(r0, q0)) * q1)
)
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Efecto volumen y mezcla

Lo que cambió el ingreso por las cantidades, a los precios de 2025.

```dax
SUMX(
    VALUES(productos[producto]),
    VAR q1 = CALCULATE(SUM(transacciones[cantidad]), REMOVEFILTERS(Calendario), transacciones[anio] = 2026)
    VAR q0 = CALCULATE(SUM(transacciones[cantidad]), REMOVEFILTERS(Calendario), transacciones[anio] = 2025)
    VAR r1 = CALCULATE(SUM(transacciones[ingreso_neto]), REMOVEFILTERS(Calendario), transacciones[anio] = 2026)
    VAR r0 = CALCULATE(SUM(transacciones[ingreso_neto]), REMOVEFILTERS(Calendario), transacciones[anio] = 2025)
    RETURN IF(q0 > 0 && q1 > 0, (q1 - q0) * DIVIDE(r0, q0))
)
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Efecto volumen

Lo que cambió el ingreso por la cantidad total, al precio promedio de 2025. Tiene sentido dentro de una industria.

```dax
VAR q1 = CALCULATE(SUM(transacciones[cantidad]), REMOVEFILTERS(Calendario), transacciones[anio] = 2026)
VAR q0 = CALCULATE(SUM(transacciones[cantidad]), REMOVEFILTERS(Calendario), transacciones[anio] = 2025)
RETURN (q1 - q0) * DIVIDE([Ingreso 2025], q0)
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Efecto mezcla

Lo que cambió el ingreso porque se vendieron productos más caros o más baratos.

```dax
[Efecto volumen y mezcla] - [Efecto volumen]
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Efecto precio % de la variación

Parte de la variación de ingresos que explica el precio.

```dax
DIVIDE([Efecto precio], [Variación de ingresos])
```

*Tabla `transacciones` · formato `0%`*

#### Monto PVM

Escalones del puente de 2025 a 2026; el total es el ingreso 2026.

```dax
SWITCH(
    SELECTEDVALUE('Escalones PVM'[Efecto]),
    "Ingreso 2025", [Ingreso 2025],
    "Volumen", [Efecto volumen],
    "Mezcla", [Efecto mezcla],
    "Precio", [Efecto precio]
)
```

*Tabla `transacciones` · formato `\$ #,##0`*

### 6. Simulador

#### Cambio de precio %

Valor elegido en el segmentador; si no hay uno elegido, 0%.

```dax
SELECTEDVALUE('Cambio de precio'[Cambio de precio], 0)
```

*Tabla `Cambio de precio` · formato `0%`*

#### Elasticidad supuesta

Cambio porcentual de volumen por cada 1% de cambio de precio (supuesto del simulador).

```dax
MAX(canales[elasticidad])
```

*Tabla `canales` · formato `0.0`*

#### Ingreso simulado

Ingreso neto con el cambio de precio y la reacción del volumen según la elasticidad del canal.

```dax
VAR dp = [Cambio de precio %]
RETURN
    SUMX(
        VALUES(canales[canal]),
        VAR e = CALCULATE(MAX(canales[elasticidad]))
        VAR f = MAX(0, 1 + e * dp)
        RETURN [Ingreso neto] * (1 + dp) * f
    )
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Margen simulado

Margen de contribución con el cambio de precio y el volumen ajustado.

```dax
VAR dp = [Cambio de precio %]
RETURN
    SUMX(
        VALUES(canales[canal]),
        VAR e = CALCULATE(MAX(canales[elasticidad]))
        VAR f = MAX(0, 1 + e * dp)
        RETURN [Ingreso neto] * (1 + dp) * f - [Costo variable] * f - [Costo de servir] * (1 + dp) * f
    )
```

*Tabla `transacciones` · formato `\$ #,##0`*

#### Variación del margen simulada

Margen simulado menos margen actual.

```dax
[Margen simulado] - [Margen de contribución]
```

*Tabla `transacciones` · formato `\$ #,##0`*
