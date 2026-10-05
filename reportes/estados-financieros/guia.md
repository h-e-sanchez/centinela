# Guía: Del libro diario a los EEFF

> Reporte de contabilidad y finanzas en Power BI que recorre el ciclo completo de tres empresas: cada hecho económico registrado en partida doble, y el balance, el estado de resultados y el flujo de efectivo que salen de esos asientos, con sus indicadores y las cuadraturas de cierre. Todos los datos son sintéticos.

## Qué resuelve

El reporte Presupuesto vs. Real se queda en el resultado operacional. Este reporte baja al libro diario y sube hasta los estados financieros. Responde cuatro preguntas:
- ¿cómo queda registrado cada hecho (venta, cobranza, compra, remuneraciones, depreciación, deuda, impuesto) en partida doble?
- ¿qué dicen el balance, el estado de resultados y el flujo de efectivo, y **cómo cuadran entre sí**?
- ¿qué tan líquida, endeudada y rentable es cada empresa, y en cuántos días gira su capital de trabajo?
- ¿cómo se cierra el año?

**Alcance:** cada empresa lleva su propia contabilidad. **No hay consolidación.** Los montos van sin IVA.

## Datos

Son las **mismas tres empresas de los otros reportes de la vitrina**. Ingresos, costos y gastos operacionales son exactamente los **Real del reporte Presupuesto vs. Real**, por sucursal y cuenta. Por eso, el EBITDA de este reporte es el resultado operacional de aquel.

| Archivo | Grano | Para qué |
|---|---|---|
| `lineas_asiento.csv` | línea del libro diario | cuenta, sucursal (en las de resultados), debe y haber |
| `asientos.csv` | asiento | fecha, tipo y glosa |
| `plan_cuentas.csv` | cuenta × empresa | tipo, clasificación, línea del EERR o del balance y naturaleza |
| `eerr_reporte1.csv` | versión × mes × sucursal × cuenta | Real y Presupuesto del #1, para cuadrar y comparar |
| `empresas.csv` | empresa | segmentador |

Se generan con `data/generar_estados_financieros.py` (semilla fija), que lee `data/escenarios/montos.csv`.

**Qué se registra cada mes:**
- **Ventas, consumo de materiales, servicios y remuneraciones:** salen del Real del #1.
- **Cobranza:** cada industria cobra con su patrón de días.
- **Compras de materiales:** pasan por inventario.
- **Pagos:** a proveedores, con su plazo; las remuneraciones, al mes siguiente.
- **Inversión y depreciación del activo fijo.**
- **Deuda:** intereses y cuotas, más una **línea de crédito** de corto plazo que se gira cuando la caja baja del mínimo.
- **Impuesto a la renta (27%):** se devenga cada mes y se paga en abril siguiente.
- **Cierre:** el 31 de diciembre se cierran los resultados, y en enero se traspasan a resultados acumulados.

**Las tres historias:**
- **Salud:** las aseguradoras pagan lento y la clínica cobra a **95 días**. Tiene la liquidez más justa de las tres y gira la línea de crédito siete veces para pagar remuneraciones y proveedores.
- **Energía:** es intensiva en activo fijo (**81% del activo**). Tiene la mayor depreciación sobre ingresos y el mayor endeudamiento (pasivo 1,5 veces el patrimonio).
- **Manufactura:** en su año flojo de ventas siguió comprando según presupuesto. El inventario sube de ~60 a **117 días** de consumo en 2025 y baja en 2026.

## Modelo

- **Power Query** lee los CSV desde GitHub con la misma función `LeerCsv` de los otros reportes.
- **Sin caminos ambiguos:**
  - `empresas → asientos → lineas_asiento ← plan_cuentas`;
  - `Calendario → asientos`;
  - `eerr_reporte1` cuelga de `empresas`, `plan_cuentas` y `Calendario`.
- **Saldos de balance acumulados:** el saldo de una cuenta es la suma de todo lo cargado y abonado desde la apertura hasta el último día del periodo (`FILTER(ALL(Calendario[Date]), …)`).
- **El estado de resultados y el flujo excluyen la apertura, el cierre y el traspaso.** Si no, el cierre del 31 de diciembre dejaría los resultados del año en cero.
- **Flujo de efectivo como cascada:** una tabla desconectada de escalones y una medida con `SWITCH`. El total de la cascada es la variación de caja.

## Medidas clave

```dax
Saldo deudor = CALCULATE([Monto], FILTER(ALL(Calendario[Date]), Calendario[Date] <= MAX(Calendario[Date])))

EBITDA = [Ingresos] + [Costos] + [Gastos operacionales]

Resultado del ejercicio = [Resultado antes de impuestos] + [Impuesto a la renta]

Diferencia de balance = [Activo] - [Pasivo] - [Patrimonio]

Liquidez corriente = DIVIDE([Activo corriente], [Pasivo corriente])

Ciclo de caja = [Días de cobro] + [Días de inventario] - [Días de pago]
```

Algunas decisiones de diseño:
- **Patrimonio con el resultado en curso:** mientras el año no se cierra, el resultado vive en las cuentas de ingresos y gastos. El patrimonio del balance lo incluye, así que el balance cuadra cualquier día del año, no solo el 31 de diciembre.
- **Flujo indirecto por diferencia de saldos:** el flujo parte del resultado y resta lo que cambió cada cuenta de balance distinta de la caja y el patrimonio. Como cada asiento cuadra, el total es exactamente la variación de caja, y la página de cierre lo verifica.
- **Cuadratura con el #1:** el EBITDA contable se compara con el resultado operacional Real del #1. La diferencia es 0, porque los dos reportes leen la misma fuente.

## Cómo leerlo

| Medida | Qué significa |
|---|---|
| **EBITDA** | Resultado antes de depreciación, intereses e impuestos: el resultado operacional del reporte Presupuesto vs. Real. |
| **Liquidez corriente / prueba ácida** | Cuántas veces el activo corriente (sin inventarios, en la prueba ácida) cubre el pasivo corriente. |
| **Endeudamiento** | Pasivo sobre patrimonio. |
| **Días de cobro / inventario / pago** | En cuántos días se cobra, se consume el inventario y se paga a proveedores. |
| **Ciclo de caja** | Días entre pagar al proveedor y cobrarle al cliente. |
| **Diferencias de cierre** | Debe vs. haber, balance, EBITDA vs. #1 y flujo vs. caja: todas deben ser 0. |

El reporte abre en **Energía**, la misma industria con que abren los demás reportes de la vitrina. Valores de control para revisar al abrir el reporte (resultados de 2025 y 2026; balance al 31 de diciembre de 2026):

| Indicador | Energía (al abrir) | Las tres empresas (sin filtro) |
|---|---|---|
| Ingresos / EBITDA | $1.820 M / $509 M (28,0%) | $5.516 M / $1.124 M (20,4%) |
| Depreciación / gastos financieros | $212 M / $114 M | $406 M / $160 M |
| Resultado del ejercicio | $134 M (7,3%) | $407 M (7,4%) |
| Activo / pasivo / patrimonio | $1.455 M / $867 M / $588 M | $2.963 M / $1.389 M / $1.574 M |
| Liquidez corriente / prueba ácida | 2,85 / 2,73 | 2,43 / 2,24 |
| Endeudamiento | 1,47 | 0,88 |
| Activo fijo sobre el activo | 81% | 61% |
| Días de cobro / inventario / pago | 31 / 26 / 41 | 66 / 57 / 47 |
| Variación de caja 2025-2026 | +$119 M | +$420 M |
| Diferencias de cierre | 0 | 0 |

## Cómo abrirlo

- **`.pbix`:** doble clic con Power BI Desktop.
- **Proyecto PBIP:** descomprimir, abrir `estados-financieros.pbip` y pulsar **Actualizar**. Los datos se leen desde GitHub; si pide credenciales, elegir Anónimo.
- **Solo los datos:** el zip de CSV o el Excel, con una hoja por tabla y un diccionario de columnas.

## Gobierno de datos

Empresas, cuentas y asientos son ficticios.
- **Datos reales:** el libro diario saldría del ERP (por ejemplo, SAP FI). El plan de cuentas real tendría más niveles y centros de costo, y los EEFF publicados seguirían IFRS con notas.
- **Lo que no publicamos:** ningún asiento, saldo ni estado financiero de un empleador real.

## Qué demuestra

- Contabilidad de punta a punta: partida doble, balance de comprobación, cierre anual y traspaso a resultados acumulados.
- Los tres estados financieros que cuadran entre sí, con un flujo de efectivo indirecto que explica la caja al peso.
- Indicadores de liquidez, endeudamiento, rentabilidad y capital de trabajo, y la cuadratura con el reporte Presupuesto vs. Real.
- Un modelo de Power BI con saldos acumulados, exclusión de asientos de cierre y cascadas desconectadas, versionado como proyecto PBIP en Git.
