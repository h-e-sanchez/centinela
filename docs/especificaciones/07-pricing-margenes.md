# Reporte #7 · Pricing y márgenes por canal

> Especificación previa a la construcción. Define datos, páginas y medidas del reporte para
> que el generador, el modelo PBIP y la guía se construyan contra un mismo contrato.

**Estado:** especificado el 2026-10-05 · **Slug:** `pricing-margenes` · **Tema:** Control de gestión · Comercial

## Qué resuelve

El reporte #1 muestra cuánto se vendió frente al presupuesto. Este reporte abre esa venta
para ver **a qué precio y con qué margen**:

- ¿cuánto del precio de lista se pierde en descuentos antes de llegar a la caja?
- ¿qué canal deja más margen después de su costo de servir?
- ¿la variación de ingresos vino del precio, del volumen o de la mezcla?
- ¿qué clientes venden mucho pero dejan poco o nada?

## Datos

Las **mismas tres empresas** y sucursales del reporte #1. Los ingresos de las transacciones
**cuadran con las cuentas de ingreso de `data/escenarios/montos.csv`** por industria, sucursal
y mes.

| Industria | Canales | Unidad de precio |
|---|---|---|
| Manufactura | Distribuidores, retail, industrial directo, e-commerce | $ por unidad de producto |
| Energía | Clientes libres con contrato, distribuidoras reguladas, mercado spot | $ por MWh |
| Salud | Fonasa, isapres, convenios con empresas, particular | $ por prestación (arancel) |

Generador previsto: `data/generar_pricing.py` (`SEMILLA = 42`) → `data/pricing-margenes/`.

| Archivo | Grano | Columnas principales |
|---|---|---|
| `canales.csv` | canal | `canal, industria, costo_servir_pct` |
| `productos.csv` | producto o prestación | `producto, industria, linea, costo_variable_unitario` |
| `clientes.csv` | cliente (ficticio) | `cliente, industria, canal, segmento` |
| `lista_precios.csv` | producto × vigencia | `producto, desde, hasta, precio_lista` |
| `transacciones.csv` | línea de venta | `fecha, industria, sucursal, cliente, producto, cantidad, precio_lista, descuento_comercial, rappel, bonificacion, precio_neto` |
| `costo_servir.csv` | canal × mes | `anio, mes, industria, canal, logistica, comisiones, otros` |

## Páginas

| # | Página | Qué muestra |
|---|---|---|
| 1 | **Portada** | Título, pregunta del reporte, las tres empresas y cómo navegar |
| 2 | **Resumen** | Precio neto realizado vs. lista, margen de contribución por canal, efecto precio-volumen-mezcla y los tres hallazgos |
| 3 | Cascada de precios | De precio de lista a precio de bolsillo: descuento comercial, rappel, bonificación y costo de servir |
| 4 | Margen por canal y producto | Margen bruto y de contribución por canal, línea y producto; matriz de volumen vs. margen |
| 5 | Precio, volumen y mezcla | Variación de ingresos y margen contra el año anterior y el presupuesto, separada en efecto precio, volumen y mezcla |
| 6 | Descuentos y fugas | Dispersión del descuento por cliente frente a la política del canal; clientes fuera de política |
| 7 | Rentabilidad por cliente | Curva ballena: margen acumulado por cliente ordenado de mayor a menor |
| 8 | **Glosario** | Conceptos y medidas, generado desde el TMDL |

## Medidas DAX clave

- `Precio neto realizado` y `% de realización` = precio neto ÷ precio de lista.
- `Margen bruto` = ingreso neto − costo variable; `Margen de contribución` = margen bruto −
  costo de servir.
- `Efecto precio`, `Efecto volumen` y `Efecto mezcla`, contra el año anterior o el
  presupuesto con un parámetro de campo de comparación.
- `Descuento fuera de política` = descuento sobre el máximo del canal.
- `Margen acumulado` por ranking de cliente, para la curva ballena.

## Historias sembradas en los datos

| Industria | Resultado | Historia |
|---|---|---|
| Manufactura | Retail 4% de contribución | Retail mueve el mayor volumen, pero con rappel y costo de logística queda con el margen de contribución más bajo; e-commerce es chico y rentable |
| Energía | Efecto precio +8% | En el año seco el ingreso crece por el precio spot, no por el volumen: el efecto precio explica casi toda la variación |
| Salud | 18% de convenios fuera de política | Los convenios con empresas acumulan descuentos sobre la política y cuatro clientes quedan con margen negativo en la curva ballena |

## Habilidades para el catálogo

Cascada de precios · Margen de contribución por canal · Análisis precio-volumen-mezcla ·
Parámetros de campo · Curva ballena de rentabilidad · Modelo coherente con el reporte #1 ·
Proyecto PBIP versionado en Git

## Tests previstos (`tests/test_pricing.py`)

- Reproducibilidad con la misma semilla.
- **Cuadratura con el #1:** el ingreso neto por industria, sucursal y mes es igual a las
  cuentas de ingreso de `montos.csv`, dentro de una tolerancia de redondeo.
- Cascada coherente: `precio_neto = precio_lista − descuentos` y nunca mayor que la lista.
- Precio-volumen-mezcla: la suma de los tres efectos es igual a la variación total.
- Calibración de las tres historias.

## Pasos manuales en Power BI Desktop

Iguales a los de los reportes anteriores ([`../how-to-pbi.md`](../how-to-pbi.md)). Al
trabajar en el PBIP:
- cerrar Desktop antes de que se edite el proyecto como código;
- descartar los cambios solo de CRLF;
- dejar `activePageName` en `portada`;
- no usar `top` como nombre de `VAR`.
