# Guía: Pricing y márgenes por canal

> Reporte de control de gestión comercial en Power BI que abre la venta del reporte Presupuesto vs. Real: a qué precio se vendió, cuánto del precio de lista se pierde en descuentos, qué canal deja margen después de su costo de servir y si la variación de ingresos vino del precio, del volumen o de la mezcla. Todos los datos son sintéticos.

## Qué resuelve

El reporte Presupuesto vs. Real dice cuánto se vendió. Este reporte dice **cómo**, y responde cinco preguntas:
- ¿cuánto del precio de lista se queda en descuentos antes de llegar a la caja?
- ¿qué canal deja más margen **después** de su costo de servir?
- ¿la variación de ingresos de 2026 vino del precio, del volumen o de la mezcla de productos?
- ¿quién recibe descuentos por sobre la política comercial?
- ¿qué clientes venden mucho y dejan poco, o pierden plata?

## Datos

Son las **mismas tres empresas y nueve sucursales del reporte Presupuesto vs. Real**. Sus ingresos netos **cuadran exactamente con las cuentas de ingreso Real** de ese reporte, por industria, sucursal, mes y cuenta, en 2025 y 2026.

| Industria | Canales | Unidad |
|---|---|---|
| Manufactura | retail, distribuidores, industrial nacional, exportación y postventa | unidades de producto y meses de contrato |
| Energía | clientes libres, distribuidoras, mercado spot y peajes | MWh |
| Salud | Fonasa, isapres, convenios con empresas y particulares | prestaciones (consultas, exámenes, días cama, cirugías) |

| Archivo | Grano | Para qué |
|---|---|---|
| `transacciones.csv` | línea de venta (mes, sucursal, cuenta, cliente y producto) | ingreso de lista, descuento comercial, rappel, bonificación, ingreso neto, costo variable y costo de servir |
| `canales.csv` | canal | descuento máximo de la política, costo de servir y elasticidad supuesta |
| `clientes.csv`, `productos.csv`, `lista_precios.csv`, `sucursales.csv`, `empresas.csv` | dimensión | quién compra, qué se vende y a qué precio de lista |
| `presupuesto_ingresos.csv` | sucursal × mes × cuenta | el Presupuesto de ingresos del #1, para comparar |

Se generan con `data/generar_pricing.py` (semilla fija), que lee `data/escenarios/montos.csv`.

**Cómo se arman:**
- **Cuadratura:** cada cuenta de ingreso del #1 se reparte entre canales y clientes. Cada línea parte del precio de lista y descuenta según la política del canal y la propensión del cliente a negociar. Al final, las cantidades se escalan para cuadrar con el Real.
- **Energía:** el volumen en MWh es casi el mismo los dos años y lo que se ajusta es el precio, como en un mercado donde el precio lo fija el sistema.

**Las tres historias:**
- **Manufactura:** retail mueve el mayor volumen, pero con rappel, bonificaciones y su costo de servir deja apenas **4,3%** de margen de contribución, contra más de 30% en industrial y exportación.
- **Energía:** la variación de ingresos de 2026 frente a 2025 (+$29 M) se explica **100% por el precio**. El volumen no cambió.
- **Salud:** tres convenios con empresas negocian descuentos sobre la política. El **21%** de las líneas de convenios queda fuera de política, y dos de esos convenios terminan con margen negativo.

## Modelo

- **Power Query** lee los CSV desde GitHub con la misma función `LeerCsv` de los otros reportes.
- **Sin caminos ambiguos:**
  - `empresas → sucursales → transacciones` (y `presupuesto_ingresos`);
  - `canales → clientes → transacciones`;
  - `productos → transacciones` (y `lista_precios`);
  - `Calendario` filtra ambas tablas de hechos.
- **Tablas desconectadas** para las dos cascadas: `Cascada de precios` (de lista a margen) y `Escalones PVM` (de 2025 a 2026). Una medida con `SWITCH` le da a cada escalón su monto, y el gráfico de cascada calcula el total.
- **Parámetro what-if `Cambio de precio`:** de −10% a +10%. El volumen reacciona según la elasticidad supuesta del canal.

## Medidas clave

```dax
Ingreso neto = SUM(transacciones[ingreso_neto])

% de realización = DIVIDE([Ingreso neto], [Ingreso de lista])

Margen de contribución = [Margen bruto] - [Costo de servir]

Margen de contribución % = DIVIDE([Margen de contribución], [Ingreso neto])

Efecto mezcla = [Efecto volumen y mezcla] - [Efecto volumen]

Descuento fuera de política = SUMX(
    transacciones,
    MAX(0, transacciones[ingreso_lista] - transacciones[ingreso_neto] - transacciones[ingreso_lista] * RELATED(canales[descuento_maximo]))
)
```

Algunas decisiones de diseño:
- **Margen de contribución, no solo margen bruto:** comparar canales sin su costo de servir premia a los que más cuestan atender. Retail se ve razonable en margen bruto y casi en cero en contribución.
- **Precio-volumen-mezcla por producto:**
  - el efecto precio valoriza el cambio de precio a las cantidades de 2026;
  - el efecto volumen y mezcla valoriza el cambio de cantidades a los precios de 2025;
  - la mezcla es lo que queda al separar el volumen total.

  Los tres suman exactamente la variación. Mezclar industrias (unidades con MWh) no tiene sentido, así que se lee con una industria elegida.
- **Curva ballena con `ALLSELECTED`:** el margen acumulado se ordena del cliente más rentable al menos rentable, dentro de lo que el visitante filtró.
- **Simulador honesto:** la elasticidad es un supuesto declarado por canal, no una estimación. El simulador sirve para ver la sensibilidad del margen, no para predecir.

## Cómo leerlo

| Medida | Qué significa |
|---|---|
| **% de realización** | Parte del precio de lista que de verdad se cobra. |
| **Margen de contribución %** | Lo que deja la venta después del costo variable y del costo de servir al canal. |
| **Efecto precio / volumen / mezcla** | De dónde viene la variación de ingresos de 2026 frente a 2025. |
| **Descuento fuera de política** | La fuga: descuento dado por sobre el máximo del canal. |
| **Margen acumulado %** | Curva ballena: sobre 100% mientras los clientes suman margen; baja al final por los que lo restan. |

El reporte abre en **Energía**, la misma industria con que abren los demás reportes de la vitrina. Valores de control para revisar al abrir el reporte (2025 y 2026 juntos):

| Indicador | Energía (al abrir) | Las tres empresas (sin filtro) |
|---|---|---|
| Ingreso neto | $1.820 M | $5.516 M |
| % de realización | 95,5% | 85,3% |
| Margen bruto / de contribución | 46,7% / 45,3% | 34,4% / 30,6% |
| Variación vs. presupuesto | +0,6% | −0,1% |
| Variación 2026 vs. 2025 | +$29,4 M (100% precio) | +$179,5 M |
| Descuento fuera de política | $0 | $13,4 M (7,5% de las líneas) |
| Canal con menor margen de contribución | Distribuidoras, 39,3% | Retail, 4,4% |
| Clientes con margen negativo | 0 | 2 |

## Cómo abrirlo

- **`.pbix`:** doble clic con Power BI Desktop.
- **Proyecto PBIP:** descomprimir, abrir `pricing-margenes.pbip` y pulsar **Actualizar**. Los datos se leen desde GitHub; si pide credenciales, elegir Anónimo.
- **Solo los datos:** el zip de CSV o el Excel, con una hoja por tabla y un diccionario de columnas.

## Gobierno de datos

Clientes, precios, descuentos y costos son ficticios.
- **Datos reales:** las condiciones comerciales por cliente son información sensible. El reporte se publicaría solo para la gerencia comercial y la de finanzas.
- **Lo que no publicamos:** ninguna lista de precios, descuento ni margen de un empleador real.

## Qué demuestra

- Control de gestión comercial: cascada de precios, margen de contribución por canal y fugas de descuento.
- Análisis precio-volumen-mezcla que cuadra al peso con la variación de ingresos.
- Un modelo que cuadra con el reporte Presupuesto vs. Real, tablas desconectadas para cascadas y un simulador what-if, versionado como proyecto PBIP en Git.
