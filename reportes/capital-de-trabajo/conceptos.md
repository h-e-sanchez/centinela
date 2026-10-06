## Conceptos

### Capital de trabajo

**Capital de trabajo neto** = cuentas por cobrar + inventario − cuentas por pagar. Es la plata que la operación tiene "amarrada" mientras espera cobrar.

**Fecha de corte.** El día al que se miden los saldos. Por defecto es el último día del periodo filtrado; el segmentador permite mirar un cierre de mes anterior.

**Ventana.** Los tres meses que terminan en la fecha de corte. DSO, DIO y DPO comparan el saldo al corte con el flujo de esa ventana.

### Cobranza

**Cuentas por cobrar.** Facturas de venta emitidas hasta la fecha de corte y que a esa fecha no estaban pagadas.

**DSO** (*days sales outstanding*) = cuentas por cobrar / ventas de la ventana × días de la ventana. Cuántos días de venta están todavía por cobrar.

**Cartera vencida.** La parte de las cuentas por cobrar cuyo vencimiento ya pasó.

**Antigüedad de cartera.** La cartera repartida en tramos según los días desde el vencimiento: al día, 1 a 30, 31 a 60, 61 a 90 y más de 90.

**Cumplimiento de cobranza** = cobrado en el periodo / lo que vencía en el periodo. Bajo 100% significa que la cartera crece.

**Pareto de deudores.** Clientes ordenados por cartera vencida, con el acumulado: suele mostrar que pocos clientes concentran la mayor parte de lo vencido.

### Pagos e inventario

**Cuentas por pagar.** Facturas de compra recibidas hasta la fecha de corte y no pagadas a esa fecha.

**DPO** (*days payables outstanding*) = cuentas por pagar / compras de la ventana × días. Cuántos días de compras se le deben a los proveedores.

**Pronto pago.** Pagar antes del vencimiento a cambio de un descuento. Acorta el DPO.

**DIO** (*days inventory outstanding*) = inventario al corte / consumo de la ventana × días. Cuántos días de consumo cubre el inventario.

**Rotación de inventario** = 365 / DIO. Cuántas veces al año se renueva.

**Sobrestock y quiebre.** Sobrestock es el saldo por sobre 1,3 veces la cobertura objetivo. Quiebre es cerrar un mes con menos de 5 días de cobertura.

### Ciclo y flujo de caja

**Ciclo de conversión de caja** = DSO + DIO − DPO. Los días que pasan entre pagarle al proveedor y cobrarle al cliente. Si es negativo, la empresa cobra antes de pagar y los proveedores financian su operación.

**Flujo de caja a 13 semanas.** La proyección semanal de cobros y pagos para el próximo trimestre: los vencimientos abiertos al corte, con el atraso típico de cada cliente, más la actividad del mismo mes del año anterior. Es la herramienta habitual de tesorería para anticipar estrecheces.

**Saldo mínimo.** El colchón de caja que la empresa quiere mantener. Se elige con un parámetro y marca las semanas en que la caja queda bajo ese nivel.

**Desembolsos no operacionales.** Dividendos e inversión en equipos: salen de la caja, pero no aparecen en el estado de resultados del reporte Presupuesto vs. Real.
