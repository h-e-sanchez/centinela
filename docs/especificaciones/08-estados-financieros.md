# Reporte #8 · Del libro diario a los EEFF

> Especificación del reporte. Define datos, páginas y medidas para que el generador, el modelo PBIP
> y la guía se construyan contra un mismo contrato.

**Estado:** construido el 2026-10-05 (pendiente Desktop y publicación) · **Slug:** `estados-financieros` · **Tema:** Finanzas · Contabilidad

## Qué resuelve

El reporte #1 muestra el resultado operacional frente al presupuesto. Este reporte recorre el camino completo de la contabilidad de cada empresa, desde el asiento hasta los tres estados financieros:

- ¿cómo se registra cada hecho económico (venta, cobranza, compra, remuneraciones, depreciación, deuda, impuesto) en partida doble?
- ¿qué dicen el balance, el estado de resultados y el flujo de efectivo, y cómo cuadran entre sí?
- ¿qué indicadores de liquidez, endeudamiento, rentabilidad y capital de trabajo salen de ellos?
- ¿cómo se cierra el año?

**Alcance:** contabilidad por empresa, **sin consolidación**. El reporte estaba en espera justamente por la consolidación, que queda fuera. Montos sin IVA.

## Datos

Son las **mismas tres empresas** de los otros reportes. Ingresos, costos y gastos operacionales son los **Real del #1** por sucursal y cuenta, así que el EBITDA de este reporte es exactamente el resultado operacional del #1.

Generador: `data/generar_estados_financieros.py` (`SEMILLA = 42`) → `data/estados-financieros/`.

| Archivo | Grano | Columnas principales |
|---|---|---|
| `plan_cuentas.csv` | cuenta × empresa | `cuenta_codigo, industria, cuenta, tipo, clasificacion, linea, naturaleza, componente, inventariable` |
| `asientos.csv` | asiento | `asiento, fecha, industria, tipo, glosa`. Tipos: apertura, venta, cobranza, compra, consumo, gasto, remuneraciones, pagos, inversión, depreciación, intereses, amortización, impuesto, crédito de corto plazo, cierre y traspaso |
| `lineas_asiento.csv` | línea | `asiento, linea, industria, cuenta_codigo, sucursal, debe, haber` |
| `eerr_reporte1.csv` | versión × mes × sucursal × cuenta | Real y Presupuesto del #1, para comparar y cuadrar |

**Cómo se simula el capital de trabajo:**
- **Cobranza:** cada industria cobra con su patrón de días. Salud cobra a más de 90 días porque las aseguradoras pagan lento.
- **Materiales:** pasan por inventario.
- **Proveedores:** se pagan con su propio plazo.
- **Remuneraciones:** se pagan al mes siguiente.
- **Impuesto a la renta:** el impuesto de cada año se paga en abril del siguiente.
- **Línea de crédito de corto plazo:** se gira cuando la caja baja del mínimo.

## Páginas

| # | Página | Qué muestra |
|---|---|---|
| 1 | **Portada** | Título, pregunta del reporte, las tres empresas y cómo navegar |
| 2 | **Resumen** | Ingresos, EBITDA, resultado, liquidez y endeudamiento; los tres hallazgos |
| 3 | Libro diario | Asientos con sus líneas al debe y al haber, filtrables por tipo y mes |
| 4 | Balance de comprobación | Por cuenta: debe y haber del periodo y saldo al cierre |
| 5 | Estado de resultados | Mensual y acumulado, frente al Presupuesto del #1 |
| 6 | Balance general | Activo, pasivo y patrimonio al cierre del periodo |
| 7 | Flujo de efectivo | Método indirecto en cascada: del resultado a la variación de caja |
| 8 | Indicadores | Liquidez, prueba ácida, endeudamiento, ROE, días de cobro, inventario y pago, y ciclo de caja |
| 9 | Cierre | Cuadraturas (debe = haber, balance, EBITDA vs. #1, flujo vs. caja) y asientos de ajuste y cierre |
| 10 | **Glosario** | Conceptos y medidas, generado desde el TMDL |

## Medidas DAX clave

- `Saldo deudor` acumulado hasta el último día del periodo, con `FILTER(ALL(Calendario[Date]), …)`.
- `Activo`, `Pasivo` y `Patrimonio` (incluye el resultado aún no cerrado) y `Diferencia de balance`, que siempre es 0.
- Líneas del estado de resultados sin los asientos de apertura, cierre y traspaso; `EBITDA`, `Resultado del ejercicio` y márgenes.
- Flujo de efectivo indirecto como `SWITCH` sobre una tabla de escalones; el total es la variación de caja.
- Ratios: `Liquidez corriente`, `Prueba ácida`, `Endeudamiento`, `ROE anualizado`, `Días de cobro`, `Días de inventario`, `Días de pago` y `Ciclo de caja`.

## Historias sembradas en los datos

| Industria | Resultado | Historia |
|---|---|---|
| Salud | 95 días de cobro | Las aseguradoras pagan lento: tiene la liquidez más justa de las tres y gira la línea de crédito de corto plazo para pagar remuneraciones y proveedores |
| Energía | 81% de activo fijo | Intensiva en activo fijo: la mayor depreciación sobre ingresos y el mayor endeudamiento de las tres |
| Manufactura | 117 días de inventario | En su año flojo de ventas (2025) siguió comprando según presupuesto: el inventario sube de ~60 a 117 días y baja en 2026 |

## Tests (`tests/test_estados_financieros.py`)

- Reproducibilidad con la misma semilla.
- **Partida doble:** debe = haber en cada asiento.
- **Balance cuadrado** al cierre de cada uno de los 24 meses, por empresa.
- **EBITDA = resultado operacional Real del #1**, por empresa y año.
- **Cierre:** las cuentas de resultados quedan en cero y la utilidad se traspasa a resultados acumulados.
- **Flujo de efectivo:** resultado menos las variaciones de las demás cuentas de balance = variación de caja.
- Las tres historias.

## Pasos manuales en Power BI Desktop

Iguales a los de los reportes anteriores ([`../how-to-pbi.md`](../how-to-pbi.md)). Al trabajar en el PBIP:
- cerrar Desktop antes de que se edite el proyecto como código;
- descartar los cambios solo de CRLF;
- dejar `activePageName` en `portada`;
- no usar `top` como nombre de `VAR`.
