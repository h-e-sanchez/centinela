# Guía: Presupuesto vs. Real por industria

> Reporte de control de gestión en Power BI que muestra dónde y cuándo la ejecución se aleja del presupuesto y del forecast, qué efecto tiene en el Resultado Operacional y en qué sucursal y cuenta se origina. Todos los datos son sintéticos.

## Qué resuelve

Un controller necesita responder cuatro preguntas cada mes: ¿cuánto nos desviamos?, ¿en qué centro, sucursal y cuenta?, ¿cómo pega en el resultado? y ¿lo veíamos venir en el forecast? El reporte responde con tarjetas ejecutivas, un semáforo, el Estado de Resultados, un Forecast 3+9, la comparación contra el año anterior y un puente del resultado con drill hasta la cuenta.

## Datos

Tres empresas ficticias, una por industria, con 2025 y 2026, tres sucursales cada una y sus cuentas dentro de cada componente:

| Industria | Resultado Operacional 2026 vs. presupuesto | Historia |
|---|---|---|
| Manufactura | +20,4% | Ingresos sobre el presupuesto, peak en el cuarto trimestre. En 2025, en cambio, cerró −13,0% |
| Energía | +0,3% | Invierno bien presupuestado: neutro |
| Salud | −72,1% | Campaña de invierno (junio a agosto) con resultado negativo. El forecast de marzo no la anticipó (real −32,9% vs. forecast) y la mitad del sobregasto cae en la Clínica Poniente |

- **`montos.csv`** (lo que lee Power BI): `version` (Presupuesto, Forecast o Real), `industria`, `anio`, `mes`, `sucursal`, `centro_costo`, `componente`, `cuenta`, `tipo_gasto` (Ingreso, Fijo o Variable), `grupo_cuenta` y `monto`.
- **Forecast 3+9:** enero a marzo copia el real; abril a diciembre es el presupuesto multiplicado por el run-rate del primer trimestre (real / presupuesto) de cada componente.
- **`presupuesto.csv` y `real.csv`:** el 2026 agregado por componente. Suman exactamente lo mismo que el detalle, y un test lo verifica.

Se generan con `data/generar_escenarios.py` (semilla fija), así que cualquiera puede reproducirlos.

## Modelo

- **Power Query** lee `montos.csv` desde GitHub y lo pivotea por versión (`Table.Pivot`): cada línea queda con presupuesto, forecast y real, con 0 explícito si falta uno.
- **Hecho `desviacion`** + **dimensión `Calendario`** (tabla calculada en DAX, marcada como tabla de fechas), relacionadas por fecha.
- **Grupo de cálculo «Inteligencia de tiempo»:** Periodo, YTD, Año anterior, Var. interanual % y Móvil 12m sobre cualquier medida, sin duplicar medidas.
- **Parámetros de campo:** «Comparar por» (industria, sucursal, centro de costo, tipo de gasto o grupo de cuenta) y «Medida» (presupuesto, forecast, real o real del año anterior).
- Las medidas implícitas están desactivadas: todo pasa por medidas DAX explícitas.

## Medidas clave

```dax
Desviación % = DIVIDE([Desviación $], [Monto Presupuesto])

Resultado Operacional =
VAR ingresos = CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Ingresos")
VAR costos = CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Costos")
VAR gastos = CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Gastos Operacionales")
RETURN ingresos - costos - gastos

Impacto en Resultado $ =
VAR ingresos = CALCULATE([Desviación $], desviacion[grupo_cuenta] = "Ingresos")
VAR egresos = CALCULATE([Desviación $], desviacion[grupo_cuenta] <> "Ingresos")
RETURN ingresos - egresos

Desviación vs Forecast % = DIVIDE([Desviación vs Forecast $], [Monto Forecast])

Real AA = CALCULATE([Monto Real], SAMEPERIODLASTYEAR(Calendario[Date]))

Real Móvil 12m = CALCULATE([Monto Real], DATESINPERIOD(Calendario[Date], MAX(Calendario[Date]), -12, MONTH))

Color Semáforo =
VAR d = [Desviación %]
RETURN SWITCH(TRUE(), ISBLANK(d), "#978F7E", ABS(d) > 0.15, "#B23C26", ABS(d) > 0.05, "#A67A2E", "#4F7A52")
```

`Color Semáforo` alimenta el formato condicional de las barras y de las matrices: el color sale de una medida, no de reglas fijas en cada visual. En el grupo de cálculo, el ítem «Var. interanual %» trae su propio formato de porcentaje (`formatStringDefinition`).

## Hojas

1. **Resumen**, **Estado de Resultados** y **Escenarios:** la vista ejecutiva de 2026.
2. **Forecast 3+9:** presupuesto, forecast y real en 24 meses, y la brecha del resultado contra cada versión.
3. **2026 vs. 2025:** real contra el año anterior, comparación con el parámetro «Comparar por» y una matriz con el grupo de cálculo.
4. **Puente y drill:**
   - cascada del impacto en el resultado por centro de costo;
   - árbol de descomposición (industria, sucursal, grupo, centro, cuenta y tipo de gasto);
   - matriz con drill de grupo a cuenta.
5. **Sucursales y gasto:** desviación por sucursal, gasto fijo vs. variable por mes, mapa de calor y el parámetro «Medida».

## Cómo leerlo

- **Semáforo por línea:** verde hasta 5% de desviación, ámbar sobre 5% y rojo sobre 15%.
- **Resultado Operacional por industria:** verde sobre +2%, gris si es neutro y rojo bajo −2%.
- **Año:** las hojas de 2026 tienen un filtro de página editable en el panel de filtros. La hoja de forecast muestra los dos años y se filtra con su segmentador.
- **Industria:** todas las hojas abren en **Energía**, la misma industria con que abren los demás reportes de la vitrina; al quitar la selección se ve el consolidado de las tres empresas.

## Cómo abrirlo

- **`.pbix`:** doble clic con Power BI Desktop.
- **Proyecto PBIP:** descomprimir, abrir `centinela.pbip` y pulsar **Actualizar** (los datos se leen desde GitHub; si pide credenciales, elegir Anónimo). Es el mismo reporte, guardado como código (TMDL y PBIR).
- **Solo los datos:** el zip de CSV o el Excel, para armar tu propia versión en Power BI o Excel.

## Qué demuestra

Modelado en Power Query (pivoteo de versiones), modelo con tabla de fechas, DAX con time intelligence, grupo de cálculo, parámetros de campo, Forecast 3+9, cascada y árbol de descomposición, formato condicional por medida y un proyecto de Power BI versionado y probado en Git, con tests que verifican que el reporte y los datos cuenten la misma historia.
