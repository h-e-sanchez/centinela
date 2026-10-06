# Guía: Capital de trabajo y ciclo de caja

> Reporte de finanzas operativas en Power BI que muestra cuándo llega a la caja lo que gana la empresa: cuánto tarda en cobrar, cuánto en pagar, cuánto inventario mantiene, cuántos días espera la caja entre pagar y cobrar, y cómo viene el saldo de las próximas 13 semanas. Todos los datos son sintéticos.

## Qué resuelve

El reporte Presupuesto vs. Real dice si la empresa gana lo que presupuestó. Este reporte dice **cuándo llega esa plata a la caja**, y responde cuatro preguntas:
- ¿cuántos días pasan entre pagarle al proveedor y cobrarle al cliente?
- ¿qué clientes concentran la cartera vencida y a quién conviene cobrar primero?
- ¿se les paga a los proveedores a tiempo, antes de plazo o con atraso?
- ¿cuánta caja habrá en las próximas 13 semanas y en qué semanas queda bajo el mínimo?

## Datos

Son las **mismas tres empresas y nueve sucursales del reporte Presupuesto vs. Real**, y los **mismos clientes del reporte de pricing**. Las facturas de 2025 y 2026 **cuadran exactamente con el Real** de ese reporte, por industria, sucursal, mes y cuenta:
- las facturas de venta, con las cuentas de ingreso;
- las facturas de compra, con las cuentas de Costos que se compran a proveedores (materiales, combustibles, energía, mantención, medicamentos y honorarios).

Remuneraciones y gastos operacionales no pasan por facturas: se pagan en el mes y entran directo a la caja.

| Industria | Clientes y condición de pago | Inventario |
|---|---|---|
| Manufactura | retail a 60 días, distribuidores a 45, industriales y postventa a 30, exportación a 60 | materias primas y producto terminado |
| Energía | clientes libres a 20 días, distribuidoras a 30, mercado spot y peajes a 15 | combustibles |
| Salud | Fonasa a 60 días, isapres a 45, convenios a 30 y particulares al contado | medicamentos y material clínico |

| Archivo | Grano | Para qué |
|---|---|---|
| `facturas_venta.csv` | factura | emisión, vencimiento, pago y monto: cuentas por cobrar, antigüedad y cobranza |
| `facturas_compra.csv` | factura | lo mismo para los proveedores: cuentas por pagar y pagos |
| `inventario_mensual.csv` | sucursal × familia × mes | saldo, consumo y cobertura objetivo |
| `caja_semanal.csv` | empresa × semana | saldo inicial, cobros, pagos y saldo final, real y proyectado |
| `clientes.csv`, `proveedores.csv`, `sucursales.csv`, `empresas.csv` | dimensión | condición de pago, límite de crédito y perfil de pago |

Se generan con `data/generar_capital_de_trabajo.py` (semilla fija), que lee `data/escenarios/montos.csv`.

**Cómo se arman:**
- **Pagos:** cada factura vence según la condición de su canal. Se paga con el atraso típico del canal y del cliente; cuatro clientes morosos concentran la cartera vencida. La **fecha de corte es el 27 de diciembre de 2026**: lo que no estaba pagado a esa fecha queda con el pago vacío.
- **Apertura:** facturas de octubre a diciembre de 2024 que seguían abiertas el 1 de enero de 2025, para que la cobranza de 2025 parta con cartera. No cuentan en la cuadratura.
- **Caja:** los cobros y pagos reales salen de las mismas facturas, más remuneraciones a fin de mes y gastos los días 10 y 25. Se suman los desembolsos que no están en el estado de resultados: dividendos de Manufactura y Energía en mayo, y una compra de equipos de Salud en abril de 2026.
- **Proyección:** las 13 semanas siguientes al corte cobran las facturas abiertas con el atraso típico de cada cliente, pagan las compras a su vencimiento y repiten la actividad del mismo mes de 2026.

**Las tres historias:**
- **Salud:** Fonasa y las isapres pagan casi dos meses después del vencimiento. El **DSO llega a 93 días**, el ciclo de conversión de caja es el más largo de las tres empresas (77 días) y la caja cae **bajo $60 M en 7 semanas, entre abril y noviembre de 2026**. Las causas son la compra de equipos y el invierno, que sube la actividad y los pagos antes de que lleguen los cobros. En esos meses Salud también estira a sus proveedores: el 16% de sus facturas se paga con más de 7 días de atraso.
- **Manufactura:** el año flojo de ventas de 2025 deja **sobrestock de producto terminado en Antofagasta**. Cierra 2025 con unos 25 días más de inventario que Santiago y Concepción, y 2026 liquida ese stock.
- **Energía:** cobra a 23 días y paga combustibles y mantención a 60. El **ciclo es de −15 días**: los proveedores financian la operación y el capital de trabajo neto es negativo.

## Modelo

- **Power Query** lee los CSV desde GitHub con la misma función `LeerCsv` de los otros reportes.
- **Sin caminos ambiguos:**
  - `empresas → sucursales → facturas_venta`, `facturas_compra` e `inventario_mensual`;
  - `empresas → caja_semanal`;
  - `clientes → facturas_venta` y `proveedores → facturas_compra`.
- **Tres fechas por factura:** `Calendario` filtra por emisión (relación activa). Vencimiento y pago tienen relaciones **inactivas**, que `USERELATIONSHIP` activa en las medidas de cobrado, pagado y calendario de vencimientos.
- **Saldos a una fecha de corte:** las cuentas por cobrar, la antigüedad y el inventario se calculan con `REMOVEFILTERS(Calendario)` y filtros sobre emisión y pago. Así una factura emitida en marzo sigue contando como abierta en junio si no se ha pagado.
- **Tablas desconectadas:** `Fechas de corte` (cierres de mes), `Tramos de antigüedad` y `Escalones del ciclo` (la cascada DSO + DIO − DPO).
- **Parámetro what-if `Saldo mínimo`:** de $20 M a $150 M, para marcar las semanas en que la caja queda bajo ese colchón.

## Medidas clave

```dax
Fecha de corte = MIN(MAX(Calendario[Date]), SELECTEDVALUE('Fechas de corte'[Corte], DATE(2026, 12, 31)))

Cuentas por cobrar =
VAR c = [Fecha de corte]
RETURN
    CALCULATE(
        SUM(facturas_venta[monto]),
        REMOVEFILTERS(Calendario),
        facturas_venta[emision] <= c,
        ISBLANK(facturas_venta[pago]) || facturas_venta[pago] > c
    )

DSO = DIVIDE([Cuentas por cobrar], [Ventas de la ventana]) * [Días de la ventana]

Ciclo de conversión de caja = [DSO] + [DIO] - [DPO]

Capital de trabajo neto = [Cuentas por cobrar] + [Inventario al corte] - [Cuentas por pagar]

Cobrado = CALCULATE(SUM(facturas_venta[monto]), USERELATIONSHIP(facturas_venta[pago], Calendario[Date]))
```

Algunas decisiones de diseño:
- **DSO, DIO y DPO sobre la misma ventana:** los tres comparan el saldo al corte con el flujo de los tres meses previos, así el ciclo suma días comparables. Un DSO calculado sobre el año completo esconde la estacionalidad de Salud.
- **La antigüedad se mide desde el vencimiento, no desde la emisión:** una factura de Fonasa a 60 días no está atrasada a los 50.
- **Atraso con tolerancia de 7 días:** pagar uno o dos días tarde es normal en tesorería. Lo que se marca es lo que pasa de una semana.
- **La proyección no inventa precisión:** usa el atraso promedio de cada cliente y repite la actividad del año anterior. Sirve para ver estrecheces con anticipación, no para fijar el saldo exacto.

## Cómo leerlo

| Medida | Qué significa |
|---|---|
| **DSO** | Días de venta todavía por cobrar. |
| **DPO** | Días de compras que se les deben a los proveedores. |
| **DIO** | Días de consumo que cubre el inventario. |
| **Ciclo de conversión de caja** | DSO + DIO − DPO: los días que la caja espera. Negativo es bueno para la caja. |
| **Cartera vencida acumulada %** | Pareto de deudores: qué parte de lo vencido concentran los primeros clientes. |
| **Semanas bajo el mínimo** | Cuántas semanas la caja queda bajo el saldo mínimo elegido. |

El reporte abre en **Energía**, la misma industria con que abren los demás reportes de la vitrina. Valores de control al corte (31 de diciembre de 2026, sin otros filtros):

| Indicador | Energía (al abrir) | Las tres empresas (sin filtro) |
|---|---|---|
| Ventas 2025-2026 | $1.820 M | $5.516 M |
| Cuentas por cobrar | $55,7 M (9,3% vencido) | $464,0 M (32,7% vencido) |
| DSO / DIO / DPO | 23 / 13 / 51 días | 58 / 26 / 49 días |
| Ciclo de conversión de caja | −15 días | 35 días |
| Capital de trabajo neto | −$6,9 M | $393,9 M |
| Saldo de caja al corte / en 13 semanas | $256,8 M / $300,9 M | $669,3 M / $784,9 M |
| Semanas bajo $60 M | 0 | 7 (todas de Salud) |

## Cómo abrirlo

- **`.pbix`:** doble clic con Power BI Desktop.
- **Proyecto PBIP:** descomprimir, abrir `capital-de-trabajo.pbip` y pulsar **Actualizar**. Los datos se leen desde GitHub; si pide credenciales, elegir Anónimo.
- **Solo los datos:** el zip de CSV o el Excel, con una hoja por tabla y un diccionario de columnas.

## Gobierno de datos

Clientes, proveedores, facturas y saldos de caja son ficticios.
- **Datos reales:** la cartera por cliente y la caja proyectada son información sensible. El reporte se publicaría solo para la gerencia de finanzas y tesorería.
- **Lo que no publicamos:** ninguna factura, deuda ni saldo bancario de un empleador real.

## Qué demuestra

- Finanzas operativas: DSO, DIO, DPO y ciclo de conversión de caja medidos a una fecha de corte, con antigüedad de cartera y Pareto de deudores.
- Un flujo de caja a 13 semanas con saldo mínimo ajustable, que conecta la cartera con la tesorería.
- Un modelo con relaciones inactivas (`USERELATIONSHIP`) y saldos a fecha de corte, que cuadra con el reporte Presupuesto vs. Real y está versionado como proyecto PBIP en Git.
