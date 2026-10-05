# Reporte #5 · Capital de trabajo y ciclo de caja

> Especificación previa a la construcción. Define datos, páginas y medidas del reporte para
> que el generador, el modelo PBIP y la guía se construyan contra un mismo contrato.

**Estado:** especificado el 2026-10-05 · **Slug:** `capital-de-trabajo` · **Tema:** Finanzas operativas

## Qué resuelve

El reporte #1 muestra si la empresa gana lo que presupuestó. Este reporte muestra **cuándo
llega esa plata a la caja**. Una gerencia de finanzas necesita responder:

- ¿cuántos días pasan entre pagarle al proveedor y cobrarle al cliente?
- ¿qué clientes concentran la cartera vencida y a quién conviene cobrar primero?
- ¿cuánta caja tendremos en las próximas 13 semanas?

## Datos

Las **mismas tres empresas** y sucursales del reporte #1. Las ventas y los costos de las
facturas **cuadran con `data/escenarios/montos.csv`** por industria, sucursal y mes, de modo
que el #1 y el #5 cuentan la misma historia desde el resultado y desde la caja.

| Industria | Clientes típicos | Inventario |
|---|---|---|
| Manufactura | Distribuidores, retail e industriales; condiciones de 30 a 90 días | Materias primas y producto terminado |
| Energía | Clientes libres con contrato y distribuidoras; cobro mensual predecible | Combustibles |
| Salud | Fonasa, isapres, convenios y particulares; las aseguradoras pagan lento | Insumos médicos |

Generador previsto: `data/generar_capital_de_trabajo.py` (`SEMILLA = 42`) → `data/capital-de-trabajo/`.

| Archivo | Grano | Columnas principales |
|---|---|---|
| `clientes.csv` | cliente (ficticio) | `cliente, industria, segmento, condicion_dias, limite_credito` |
| `proveedores.csv` | proveedor (ficticio) | `proveedor, industria, categoria, condicion_dias` |
| `facturas_venta.csv` | factura | `factura, industria, sucursal, cliente, emision, vencimiento, pago, monto` (`pago` vacío si está abierta) |
| `facturas_compra.csv` | factura | `factura, industria, sucursal, proveedor, emision, vencimiento, pago, monto` |
| `inventario_mensual.csv` | industria × sucursal × familia × mes | `anio, mes, industria, sucursal, familia, saldo, consumo` |
| `caja_semanal.csv` | industria × semana | `semana, industria, saldo_inicial, cobros, pagos, saldo_final, tipo (real o proyectado)` |

## Páginas

| # | Página | Qué muestra |
|---|---|---|
| 1 | **Portada** | Título, pregunta del reporte, las tres empresas y cómo navegar |
| 2 | **Resumen** | Ciclo de conversión de caja (CCC) por empresa y su tendencia, capital de trabajo neto y los tres hallazgos |
| 3 | Cobranza y cartera | DSO, cartera por tramo de antigüedad (al día, 1-30, 31-60, 61-90, +90), Pareto de deudores y cumplimiento de la cobranza |
| 4 | Pagos a proveedores | DPO, calendario de vencimientos, pagos atrasados y pagados antes de plazo |
| 5 | Inventario | DIO, rotación por familia, sobrestock y quiebres |
| 6 | Ciclo de caja | Cascada DSO + DIO − DPO = CCC por empresa y comparación entre las tres |
| 7 | Flujo de caja a 13 semanas | Saldo real y proyectado, semanas con saldo bajo el mínimo y su causa (cobro o pago) |
| 8 | **Glosario** | Conceptos y medidas, generado desde el TMDL |

## Medidas DAX clave

- `DSO` = cuentas por cobrar ÷ ventas del período × días; `DPO` y `DIO` con la misma lógica
  sobre compras y costo.
- `Ciclo de conversión de caja` = DSO + DIO − DPO.
- `Cartera vencida` y `% vencido`, con tramos de antigüedad calculados a una fecha de corte
  (parámetro).
- `Capital de trabajo neto` = cuentas por cobrar + inventario − cuentas por pagar.
- `Cumplimiento de cobranza` = cobrado ÷ vencido en el período.
- `Saldo proyectado` y `Semanas bajo el mínimo`, con un parámetro what-if de saldo mínimo.

## Historias sembradas en los datos

| Industria | Resultado | Historia |
|---|---|---|
| Salud | DSO > 90 días | Las aseguradoras pagan lento y el CCC es el más largo de las tres; la caja se estrecha en invierno, cuando sube la actividad |
| Manufactura | DIO +25 días | El año flojo de ventas del #1 deja sobrestock de producto terminado en Antofagasta y alarga el ciclo |
| Energía | CCC negativo | Cobra antes de pagar: contratos con facturación mensual y proveedores de combustible a 60 días |

## Habilidades para el catálogo

Capital de trabajo (DSO, DIO, DPO, CCC) · Antigüedad de cartera con fecha de corte ·
Parámetros what-if · Flujo de caja proyectado · Modelo coherente con el reporte #1 ·
Proyecto PBIP versionado en Git

## Tests previstos (`tests/test_capital_de_trabajo.py`)

- Reproducibilidad con la misma semilla.
- **Cuadratura con el #1:** facturas de venta y compra por industria, sucursal y mes igual a
  `montos.csv`, dentro de una tolerancia de redondeo.
- Coherencia de fechas: `emision ≤ vencimiento` y `emision ≤ pago`.
- Caja: `saldo_final = saldo_inicial + cobros − pagos` en cada semana.
- Calibración de las tres historias.

## Pasos manuales en Power BI Desktop

Iguales a los de los reportes anteriores ([`../how-to-pbi.md`](../how-to-pbi.md)). Al
trabajar en el PBIP:
- cerrar Desktop antes de que se edite el proyecto como código;
- descartar los cambios solo de CRLF;
- dejar `activePageName` en `portada`;
- no usar `top` como nombre de `VAR`.

**Relación con el #8:** el libro diario y los estados financieros están en el reporte #8
(`08-estados-financieros.md`). El #5 profundiza en la cobranza, los pagos y el flujo a 13 semanas.
