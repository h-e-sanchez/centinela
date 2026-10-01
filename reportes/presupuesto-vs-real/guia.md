# Guía: Presupuesto vs. Real por industria

> Reporte de control de gestión en Power BI que muestra, en una sola vista, dónde y cuándo la ejecución se aleja del presupuesto y qué efecto tiene en el Resultado Operacional. Todos los datos son sintéticos.

## Qué resuelve

Un controller necesita responder tres preguntas cada mes: ¿cuánto nos desviamos?, ¿en qué centro de costo? y ¿cómo pega en el resultado? El reporte responde las tres con tarjetas ejecutivas, un semáforo y el Estado de Resultados acumulado, y permite comparar tres empresas con historias distintas.

## Datos

Tres empresas ficticias, una por industria, con 12 meses de 2026 y su propia estructura de centros de costo:

| Industria | Resultado Operacional vs. presupuesto | Historia |
|---|---|---|
| Manufactura | +20,4% | Ingresos sobre el presupuesto, peak en el cuarto trimestre |
| Energía | +0,3% | Invierno bien presupuestado: neutro |
| Salud | −72,1% | Campaña de invierno (junio a agosto) con resultado negativo |

Columnas, en formato tidy: `industria`, `anio`, `mes`, `centro_costo`, `componente`, `grupo_cuenta` (Ingresos, Costos o Gastos Operacionales) y `monto`. Se generan con `data/generar_escenarios.py` (semilla fija), así que cualquiera puede reproducirlos.

## Modelo

- **Power Query** lee los dos CSV desde GitHub y los une con `Table.Combine` + `Table.Group`, de modo que cada línea queda con presupuesto y real (0 explícito si falta uno).
- **Hecho `desviacion`** + **dimensión `Calendario`** (tabla calculada en DAX, marcada como tabla de fechas), relacionadas por fecha.
- Las medidas implícitas están desactivadas: todo pasa por medidas DAX explícitas.

## Medidas clave

```dax
Desviación % = DIVIDE([Desviación $], [Monto Presupuesto])

Resultado Operacional =
VAR ingresos = CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Ingresos")
VAR costos = CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Costos")
VAR gastos = CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Gastos Operacionales")
RETURN ingresos - costos - gastos

Real YTD = TOTALYTD([Monto Real], Calendario[Date])

Desviación RO % = DIVIDE([Resultado Operacional] - [Resultado Operacional Presupuesto], ABS([Resultado Operacional Presupuesto]))

Color Semáforo =
VAR d = [Desviación %]
RETURN SWITCH(TRUE(), ISBLANK(d), "#978F7E", ABS(d) > 0.15, "#B23C26", ABS(d) > 0.05, "#A67A2E", "#4F7A52")
```

`Color Semáforo` alimenta el formato condicional de las barras y de la matriz: el color sale de una medida, no de reglas fijas en cada visual.

## Cómo leerlo

- **Semáforo por línea:** verde hasta 5% de desviación, ámbar sobre 5% y rojo sobre 15%.
- **Resultado Operacional por industria:** verde sobre +2%, gris si es neutro y rojo bajo −2%.
- **Segmentador Industria:** "Todas" muestra el consolidado de las tres empresas.

## Cómo abrirlo

- **`.pbix`:** doble clic con Power BI Desktop.
- **Proyecto PBIP:** descomprimir, abrir `centinela.pbip` y pulsar **Actualizar** (los datos se leen desde GitHub; si pide credenciales, elegir Anónimo). Es el mismo reporte, guardado como código (TMDL y PBIR).
- **Solo los datos:** el zip de CSV o el Excel, para armar tu propia versión en Power BI o Excel.

## Qué demuestra

Modelado en Power Query, modelo estrella con tabla de fechas, DAX con time intelligence, formato condicional por medida, diseño ejecutivo y un proyecto de Power BI versionado y probado en Git, con tests que verifican que el reporte y los datos cuenten la misma historia.
