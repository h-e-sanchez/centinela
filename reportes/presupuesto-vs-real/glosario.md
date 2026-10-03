# Glosario: Presupuesto vs. Real por industria

> Qué significa cada concepto del reporte y cómo se calcula. La primera parte lo explica con palabras; la segunda lista **todas** las medidas DAX del modelo, leídas del proyecto PBIP con `herramientas/generar_glosario.py`, así que coinciden con lo que calcula Power BI.

## Conceptos

### Las tres versiones del monto

**Presupuesto.** Lo que la empresa planificó gastar e ingresar en el año, mes a mes y cuenta por cuenta. Es la vara contra la que se mide todo lo demás. En los datos es la versión `Presupuesto` de `montos.csv`.

**Real.** Lo que efectivamente se ejecutó: ingresos facturados y gastos contabilizados. En el reporte, *real* siempre se refiere a la ejecución, nunca a una proyección.

**Forecast 3+9.** Una re-proyección del año hecha en abril, con 3 meses reales y 9 proyectados:
- enero a marzo copia el real;
- abril a diciembre toma el presupuesto de cada mes y lo multiplica por el **run-rate** del primer trimestre de su componente.

El run-rate es real ÷ presupuesto de enero a marzo. Si un componente gastó 10% más de lo presupuestado en el trimestre, el forecast supone que seguirá 10% arriba el resto del año. Sirve para separar dos preguntas: *¿nos desviamos del plan?* (contra presupuesto) y *¿lo vimos venir?* (contra forecast).

### Desviación y cumplimiento

**Desviación $** = real − presupuesto. El signo se lee según el tipo de cuenta:
- en **gastos**, positivo es sobregasto (malo);
- en **ingresos**, positivo es sobreventa (bueno).

Por eso, para saber si una desviación es buena o mala, conviene mirar el **impacto en el resultado** (más abajo) y no solo su signo.

**Desviación %** = desviación $ ÷ presupuesto. Usa `DIVIDE`, que devuelve vacío si el presupuesto es cero en vez de un error. Un 8% en una cuenta chica y un 8% en la nómina son muy distintos en pesos, así que se lee junto a la desviación $.

**% Cumplimiento** = real ÷ presupuesto. Es la misma información que la desviación % vista como avance: 108% equivale a +8%.

**Desviación vs. forecast.** Real − forecast, en $ y en %. Es lo que *ni siquiera el forecast de marzo* anticipó: si es grande, el problema no era un mal presupuesto sino algo que cambió durante el año. Ejemplo de los datos: en Salud, el real queda −32,9% contra el forecast, porque el run-rate del primer trimestre no anticipó la campaña de invierno.

**Forecast vs. presupuesto %.** Cuánto corrigió el forecast al presupuesto original: la señal temprana de que el plan quedó desactualizado.

### Semáforo

Cada **línea** (una cuenta, en una sucursal y un mes: una fila de la tabla `desviacion`) se clasifica según el **valor absoluto** de su desviación %. Lo hace la columna calculada `Estado Semáforo`, fila por fila:

| Estado | Regla | Color |
|---|---|---|
| OK | hasta 5% | verde |
| Alerta | sobre 5% | ámbar |
| Crítica | sobre 15%, o gasto real en una cuenta sin presupuesto | rojo |

Los umbrales son los mismos que usa el motor en Python (`src/main.py`, opciones `--umbral` y `--umbral-critico`), y un test verifica que el modelo y el motor coincidan. El color sale de la medida `Color Semáforo`, que alimenta el formato condicional de las barras y matrices: si cambia el umbral, cambia en un solo lugar.

**Líneas en alerta / en crítica / % de líneas en alerta.** Cuentan cuántas líneas superan cada umbral. Responden *¿la desviación está concentrada en pocas cuentas o repartida?*: cuatro líneas críticas se investigan una por una, cuarenta piden revisar el presupuesto completo.

### Estado de Resultados

Las cuentas se agrupan en tres **grupos**: Ingresos, Costos y Gastos Operacionales.

**Resultado Operacional (RO)** = ingresos − costos − gastos operacionales. Es la utilidad de la operación antes de impuestos, intereses y partidas no operacionales. Existe en versión real, presupuesto, forecast y año anterior.

**Desviación RO %** = (RO real − RO presupuesto) ÷ |RO presupuesto|. Divide por el **valor absoluto** porque el RO puede ser negativo: si se presupuestó −100 y se logró −50, la mejora debe leerse +50%, no −50%.

**Impacto en resultado $.** Traduce cualquier desviación a su efecto en el RO: la sobreventa de ingresos suma y el sobregasto en costos o gastos resta. Es la medida que alimenta el **puente del resultado**: una cascada que parte del RO presupuestado, suma y resta el impacto de cada centro de costo y llega al RO real.

### Tiempo

**YTD (year to date).** Acumulado desde enero hasta el último mes visible. Se calcula con `DATESYTD` sobre la tabla `Calendario`.

**Mes anterior y variación MoM %.** El mismo monto del mes previo y su variación (*month over month*). Sirven para ver tendencia, no cumplimiento.

**Real AA (año anterior).** El real del mismo periodo de 2025 (`SAMEPERIODLASTYEAR`). **Var. interanual %** = (real − real AA) ÷ real AA: el crecimiento contra el año pasado, que no depende de qué tan bien se presupuestó.

**Móvil 12 meses.** Suma de los últimos 12 meses hasta el periodo visible. Suaviza la estacionalidad: una campaña de invierno no infla un mes aislado.

**Grupo de cálculo «Inteligencia de tiempo».** En vez de crear YTD, año anterior y móvil 12 meses para *cada* medida, un grupo de cálculo aplica esa transformación a la medida que esté en el visual. En la matriz de la hoja *2026 vs. 2025*, las columnas son los ítems del grupo (Periodo, YTD, Año anterior, Var. interanual % y Móvil 12m).

### Estructura del gasto

**Gasto fijo y variable.** Cada cuenta de gasto se clasifica como **fija** (no cambia con la actividad: arriendos, sueldos base) o **variable** (se mueve con el volumen: insumos, comisiones). **Gasto variable %** = gasto variable ÷ gasto total. Un sobregasto en gasto variable acompañado de sobreventa es sano; un sobregasto en gasto fijo no tiene esa explicación.

### Herramientas del modelo

**Parámetro de campo «Comparar por».** Una segmentación que cambia la dimensión de un gráfico: el mismo visual compara por industria, sucursal, centro de costo, tipo de gasto o grupo de cuenta, sin duplicar gráficos.

**Segmentación «Medida».** Una tabla desconectada con cuatro opciones (presupuesto, forecast, real y real del año anterior). La medida `Monto por medida` lee la opción elegida con `SWITCH` y devuelve el monto que corresponde; con varias elegidas, cada una es una serie del gráfico.

**Árbol de descomposición.** Parte del total y deja abrir, nivel por nivel, por industria, sucursal, grupo, centro de costo, cuenta y tipo de gasto, siguiendo la rama que más pesa.

## Medidas del modelo

El modelo tiene 47 medidas, agrupadas por carpeta como aparecen en el panel de datos de Power BI. Las de *portada* y *tarjetas* solo dan formato de texto a otras medidas.

### 0. Portada

#### Portada presupuesto

Resultado Operacional presupuestado, abreviado para la tarjeta (ingresos y gastos no se suman entre sí).

```dax
VAR v = [Resultado Operacional Presupuesto]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(v), BLANK(),
        ABS(v) >= 1000000000, FORMAT(v / 1000000000, "$ #,0.0") & " mil M",
        ABS(v) >= 1000000, FORMAT(v / 1000000, "$ #,0") & " M",
        FORMAT(v, "$ #,0")
    )
```

*Tabla `desviacion`*

#### Portada real

Resultado Operacional real, abreviado para la tarjeta.

```dax
VAR v = [Resultado Operacional]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(v), BLANK(),
        ABS(v) >= 1000000000, FORMAT(v / 1000000000, "$ #,0.0") & " mil M",
        ABS(v) >= 1000000, FORMAT(v / 1000000, "$ #,0") & " M",
        FORMAT(v, "$ #,0")
    )
```

*Tabla `desviacion`*

#### Portada resultado

Resultado Operacional contra presupuesto, con signo.

```dax
FORMAT([Desviación RO %], "+0.0%;-0.0%")
```

*Tabla `desviacion`*

#### Portada frase 1

Primera frase de la portada: cómo terminó el resultado.

```dax
"Resultado " & [Portada resultado] & " vs. presupuesto"
```

*Tabla `desviacion`*

#### Portada frase 2

Segunda frase: el centro de costo que más pesa en la desviación.

```dax
VAR mayorDesvio = TOPN(1, VALUES(desviacion[centro_costo]), ABS([Desviación $]), DESC)
VAR centro = MAXX(mayorDesvio, desviacion[centro_costo])
VAR d = CALCULATE([Desviación %], desviacion[centro_costo] = centro)
RETURN "Mayor desvío: " & centro & " " & FORMAT(d, "+0.0%;-0.0%")
```

*Tabla `desviacion`*

### 0. Tarjetas ejecutivas

#### KPI Presupuesto

Texto para tarjetas: millones con un decimal, sin escalado automático del visual.

```dax
FORMAT([Monto Presupuesto] / 1000000, "$ #,0.0") & " MM"
```

*Tabla `desviacion`*

#### KPI Real

Texto para tarjetas.

```dax
FORMAT([Monto Real] / 1000000, "$ #,0.0") & " MM"
```

*Tabla `desviacion`*

#### KPI Resultado Operacional

Texto para tarjetas.

```dax
FORMAT([Resultado Operacional] / 1000000, "$ #,0.0;-$ #,0.0") & " MM"
```

*Tabla `desviacion`*

#### KPI Resultado Operacional Presupuesto

Texto para tarjetas.

```dax
FORMAT([Resultado Operacional Presupuesto] / 1000000, "$ #,0.0;-$ #,0.0") & " MM"
```

*Tabla `desviacion`*

#### KPI Real YTD

Texto para tarjetas.

```dax
FORMAT([Real YTD] / 1000000, "$ #,0.0") & " MM"
```

*Tabla `desviacion`*

#### KPI Presupuesto YTD

Texto para tarjetas.

```dax
FORMAT([Presupuesto YTD] / 1000000, "$ #,0.0") & " MM"
```

*Tabla `desviacion`*

#### KPI Forecast

Texto para tarjetas.

```dax
FORMAT([Monto Forecast] / 1000000, "$ #,0.0") & " MM"
```

*Tabla `desviacion`*

#### KPI Real AA

Texto para tarjetas.

```dax
FORMAT([Real AA] / 1000000, "$ #,0.0") & " MM"
```

*Tabla `desviacion`*

#### KPI Impacto en Resultado

Texto para tarjetas.

```dax
FORMAT([Impacto en Resultado $] / 1000000, "$ #,0.0;-$ #,0.0") & " MM"
```

*Tabla `desviacion`*

### 1. Montos

#### Monto Presupuesto

Suma del presupuesto en el contexto de filtro.

```dax
SUM(desviacion[monto_presupuesto])
```

*Tabla `desviacion` · formato `\$ #,##0`*

#### Monto Real

Suma de la ejecución real.

```dax
SUM(desviacion[monto_real])
```

*Tabla `desviacion` · formato `\$ #,##0`*

#### Monto Forecast

Forecast 3+9: enero a marzo real, abril a diciembre re-proyectado con el run-rate del trimestre.

```dax
SUM(desviacion[monto_forecast])
```

*Tabla `desviacion` · formato `\$ #,##0`*

#### Gasto Real

Costos y gastos operacionales ejecutados (todo lo que no es ingreso).

```dax
CALCULATE([Monto Real], desviacion[grupo_cuenta] <> "Ingresos")
```

*Tabla `desviacion` · formato `\$ #,##0`*

#### Monto por medida

Monto de la versión elegida en la segmentación «Medida»; con varias elegidas, cada una es una serie del gráfico.

```dax
SWITCH(
    SELECTEDVALUE(Medida[Medida Orden]),
    0, [Monto Presupuesto],
    1, [Monto Forecast],
    2, [Monto Real],
    3, [Real AA]
)
```

*Tabla `desviacion` · formato `\$ #,##0`*

### 2. Desviación

#### Desviación $

Real menos presupuesto: positivo = sobregasto (o sobreventa en Ingresos).

```dax
[Monto Real] - [Monto Presupuesto]
```

*Tabla `desviacion` · formato `\$ #,##0;-\$ #,##0`*

#### Desviación %

Desviación relativa; DIVIDE evita el error por presupuesto cero.

```dax
DIVIDE([Desviación $], [Monto Presupuesto])
```

*Tabla `desviacion` · formato `0.0%;-0.0%`*

#### % Cumplimiento

Real sobre presupuesto.

```dax
DIVIDE([Monto Real], [Monto Presupuesto])
```

*Tabla `desviacion` · formato `0.0%`*

### 3. Semáforo

#### Líneas en Alerta

Líneas en Alerta o Crítica (umbral 5%).

```dax
CALCULATE(COUNTROWS(desviacion), desviacion[Estado Semáforo] <> "OK")
```

*Tabla `desviacion` · formato `0`*

#### Líneas en Crítica

Líneas sobre el umbral crítico (15%).

```dax
CALCULATE(COUNTROWS(desviacion), desviacion[Estado Semáforo] = "Crítica")
```

*Tabla `desviacion` · formato `0`*

#### % Líneas en Alerta

Proporción de líneas fuera de umbral.

```dax
DIVIDE([Líneas en Alerta], COUNTROWS(desviacion))
```

*Tabla `desviacion` · formato `0.0%`*

#### Color Semáforo

Color hex del semáforo para formato condicional (barras y matriz): 5% alerta, 15% crítica.

```dax
VAR d = [Desviación %]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(d), "#978F7E",
        ABS(d) > 0.15, "#B23C26",
        ABS(d) > 0.05, "#A67A2E",
        "#4F7A52"
    )
```

*Tabla `desviacion`*

### 4. Estado de Resultados

#### Resultado Operacional

Ingresos − Costos − Gastos Operacionales, ejecución real.

```dax
VAR ingresos = CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Ingresos")
VAR costos = CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Costos")
VAR gastos = CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Gastos Operacionales")
RETURN ingresos - costos - gastos
```

*Tabla `desviacion` · formato `\$ #,##0;-\$ #,##0`*

#### Resultado Operacional Presupuesto

El mismo subtotal sobre el presupuesto.

```dax
VAR ingresos = CALCULATE([Monto Presupuesto], desviacion[grupo_cuenta] = "Ingresos")
VAR costos = CALCULATE([Monto Presupuesto], desviacion[grupo_cuenta] = "Costos")
VAR gastos = CALCULATE([Monto Presupuesto], desviacion[grupo_cuenta] = "Gastos Operacionales")
RETURN ingresos - costos - gastos
```

*Tabla `desviacion` · formato `\$ #,##0;-\$ #,##0`*

#### Desviación RO %

Desviación del Resultado Operacional contra su presupuesto (base: valor absoluto del presupuesto).

```dax
DIVIDE([Resultado Operacional] - [Resultado Operacional Presupuesto], ABS([Resultado Operacional Presupuesto]))
```

*Tabla `desviacion` · formato `0.0%;-0.0%`*

#### Color Resultado

Color del escenario según el Resultado Operacional: verde sobre +2%, rojo bajo -2%, gris si es neutro.

```dax
VAR d = [Desviación RO %]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(d), "#978F7E",
        d >= 0.02, "#4F7A52",
        d <= -0.02, "#B23C26",
        "#978F7E"
    )
```

*Tabla `desviacion`*

#### Impacto en Resultado $

Efecto de la desviación en el Resultado Operacional: más ingreso suma, más gasto resta.

```dax
VAR ingresos = CALCULATE([Desviación $], desviacion[grupo_cuenta] = "Ingresos")
VAR egresos = CALCULATE([Desviación $], desviacion[grupo_cuenta] <> "Ingresos")
RETURN ingresos - egresos
```

*Tabla `desviacion` · formato `\$ #,##0;-\$ #,##0`*

#### Resultado Operacional Forecast

El mismo subtotal sobre el forecast.

```dax
VAR ingresos = CALCULATE([Monto Forecast], desviacion[grupo_cuenta] = "Ingresos")
VAR costos = CALCULATE([Monto Forecast], desviacion[grupo_cuenta] = "Costos")
VAR gastos = CALCULATE([Monto Forecast], desviacion[grupo_cuenta] = "Gastos Operacionales")
RETURN ingresos - costos - gastos
```

*Tabla `desviacion` · formato `\$ #,##0;-\$ #,##0`*

### 5. Tiempo

#### Real YTD

Acumulado del año (time intelligence sobre la tabla Calendario).

```dax
TOTALYTD([Monto Real], Calendario[Date])
```

*Tabla `desviacion` · formato `\$ #,##0`*

#### Presupuesto YTD

Presupuesto acumulado del año.

```dax
TOTALYTD([Monto Presupuesto], Calendario[Date])
```

*Tabla `desviacion` · formato `\$ #,##0`*

#### Desviación YTD %

Desviación acumulada del año.

```dax
DIVIDE([Real YTD] - [Presupuesto YTD], [Presupuesto YTD])
```

*Tabla `desviacion` · formato `0.0%;-0.0%`*

#### Real Mes Anterior

Ejecución real del mes previo.

```dax
CALCULATE([Monto Real], DATEADD(Calendario[Date], -1, MONTH))
```

*Tabla `desviacion` · formato `\$ #,##0`*

#### Variación MoM %

Variación contra el mes anterior.

```dax
DIVIDE([Monto Real] - [Real Mes Anterior], [Real Mes Anterior])
```

*Tabla `desviacion` · formato `0.0%;-0.0%`*

#### Real AA

Real del mismo periodo del año anterior.

```dax
CALCULATE([Monto Real], SAMEPERIODLASTYEAR(Calendario[Date]))
```

*Tabla `desviacion` · formato `\$ #,##0`*

#### Var. interanual %

Crecimiento contra el mismo periodo del año anterior.

```dax
DIVIDE([Monto Real] - [Real AA], [Real AA])
```

*Tabla `desviacion` · formato `0.0%;-0.0%`*

#### Real Móvil 12m

Suma de los últimos 12 meses hasta el periodo visible.

```dax
CALCULATE([Monto Real], DATESINPERIOD(Calendario[Date], MAX(Calendario[Date]), -12, MONTH))
```

*Tabla `desviacion` · formato `\$ #,##0`*

#### Resultado Operacional AA

Resultado Operacional del mismo periodo del año anterior.

```dax
CALCULATE([Resultado Operacional], SAMEPERIODLASTYEAR(Calendario[Date]))
```

*Tabla `desviacion` · formato `\$ #,##0;-\$ #,##0`*

#### Var. RO interanual %

Variación interanual del Resultado Operacional (base: valor absoluto del año anterior).

```dax
DIVIDE([Resultado Operacional] - [Resultado Operacional AA], ABS([Resultado Operacional AA]))
```

*Tabla `desviacion` · formato `0.0%;-0.0%`*

### 6. Forecast

#### Desviación vs Forecast $

Real menos forecast: lo que ni siquiera el forecast de marzo anticipó.

```dax
[Monto Real] - [Monto Forecast]
```

*Tabla `desviacion` · formato `\$ #,##0;-\$ #,##0`*

#### Desviación vs Forecast %

Desviación relativa contra el forecast.

```dax
DIVIDE([Desviación vs Forecast $], [Monto Forecast])
```

*Tabla `desviacion` · formato `0.0%;-0.0%`*

#### Forecast vs Presupuesto %

Cuánto corrigió el forecast al presupuesto original.

```dax
DIVIDE([Monto Forecast] - [Monto Presupuesto], [Monto Presupuesto])
```

*Tabla `desviacion` · formato `0.0%;-0.0%`*

#### Desviación RO vs Forecast %

Resultado Operacional real contra el del forecast.

```dax
DIVIDE([Resultado Operacional] - [Resultado Operacional Forecast], ABS([Resultado Operacional Forecast]))
```

*Tabla `desviacion` · formato `0.0%;-0.0%`*

### 7. Estructura de gasto

#### Gasto variable %

Parte del gasto ejecutado que se mueve con la actividad.

```dax
DIVIDE(CALCULATE([Monto Real], desviacion[tipo_gasto] = "Variable"), [Gasto Real])
```

*Tabla `desviacion` · formato `0.0%`*

## Grupo de cálculo «Inteligencia de tiempo»

Cada ítem se aplica sobre la medida que esté en el visual (`SELECTEDMEASURE()`), así que una sola definición sirve para todas las medidas.

#### Periodo

```dax
SELECTEDMEASURE()
```

#### YTD

```dax
CALCULATE(SELECTEDMEASURE(), DATESYTD(Calendario[Date]))
```

#### Año anterior

```dax
CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR(Calendario[Date]))
```

#### Var. interanual %

```dax
VAR aa = CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR(Calendario[Date]))
RETURN DIVIDE(SELECTEDMEASURE() - aa, aa)
```

*Formato propio: `0.0%;-0.0%`*

#### Móvil 12m

```dax
CALCULATE(SELECTEDMEASURE(), DATESINPERIOD(Calendario[Date], MAX(Calendario[Date]), -12, MONTH))
```
