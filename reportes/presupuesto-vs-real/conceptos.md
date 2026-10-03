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
