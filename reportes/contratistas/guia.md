# Guía: Contratistas y mantenimiento · del estado de pago a la orden de trabajo

> Reporte de control de gestión en Power BI que cruza lo que cobran los contratistas de mantenimiento con lo que de verdad ejecutaron. Las reglas de auditoría están escritas en SQL versionado y tienen tests. Todos los datos son sintéticos.

## Qué resuelve

Una empresa que externaliza el mantenimiento recibe cada mes un estado de pago (EP) por contratista. Si nadie lo cruza con las órdenes de trabajo (OT) del sistema de mantenimiento, se pagan cosas que no pasaron:
- cobros sin OT;
- OT que siguen abiertas;
- horas o visitas de más;
- precios fuera de contrato;
- la misma OT cobrada dos veces.

El reporte responde tres preguntas:
- ¿cuánto se cobra sin respaldo y quién lo cobra?
- ¿cuánto se evita desde que existe el control?
- ¿esos mismos contratistas cumplen el plan preventivo y reparan a tiempo?

## Datos

Son las **mismas tres empresas ficticias y nueve sedes de los otros reportes de la vitrina**. Cada empresa mantiene sus activos con cuatro contratistas, uno por especialidad, y les paga unos $210 millones al mes, entre 2025 y 2026:

| Industria | Activos mantenidos | Contratistas riesgosos |
|---|---|---|
| Manufactura | líneas de envasado, compresores, calderas, montacargas | el de montacargas |
| Energía | estanques granel, red de distribución, subestaciones, válvulas y reguladores | los de estanques y de válvulas |
| Salud | climatización, equipos clínicos, grupos electrógenos, ascensores | el de climatización |

| Archivo | Grano | Para qué |
|---|---|---|
| `ordenes_trabajo.csv` | OT | preventivas del plan y correctivas por falla, con fechas, horas y detención (como una extracción de OT de SAP PM) |
| `estados_pago.csv` | línea de EP | lo que cobra cada contratista cada mes, con la OT que cita |
| `observaciones.csv` | línea × regla incumplida | salida de las reglas SQL, con el monto observado y su resolución |
| `tarifas.csv` | contratista × servicio | precio del contrato: visita preventiva y hora correctiva |
| `sedes.csv`, `contratistas.csv`, `activos.csv` | dimensión | segmentadores; el activo trae su criticidad y su MTBF de diseño |

Se generan con `data/generar_contratistas.py` (semilla fija) y se pueden reproducir.

**La historia del control:** hasta junio de 2025 nadie cruza el EP con las OT, y las anomalías llegan a ~9,5% de lo facturado, con un pico de $26,5 millones en Energía. Desde julio de 2025 el control rechaza lo observado antes de pagar y, como los contratistas lo saben, las anomalías bajan a ~3,5%. Los contratistas riesgosos concentran más de la mitad del monto observado y además cumplen peor el plan preventivo (70% a tiempo, contra 92% de los demás).

## Reglas de auditoría en SQL

`sql/reglas_auditoria.sql` cruza cada línea con su OT y con la tarifa, usando una CTE por regla. `sql/auditar.py` lo ejecuta tal cual sobre `sqlite3` de la biblioteca estándar, sin dependencias:

| Regla | Condición | Monto observado |
|---|---|---|
| Cobro sin OT | la línea no cita OT o cita una que no existe | la línea completa |
| OT abierta | la OT no está cerrada o se cerró después del mes cobrado | la línea completa |
| Cantidad sobre lo ejecutado | cobra más de 5% sobre lo registrado en la OT | el exceso × precio |
| Precio sobre tarifa | el precio unitario supera el del contrato | el exceso × cantidad |
| Doble cobro | `ROW_NUMBER() OVER (PARTITION BY id_ot, servicio ORDER BY periodo, id_linea) > 1` | la línea completa |

El generador inyecta las anomalías con una etiqueta (`anomalia_inyectada`). `tests/test_contratistas.py` exige que las reglas encuentren **exactamente** las líneas etiquetadas, sin falsos positivos ni negativos. La tolerancia de cantidad y la fecha de inicio del control son parámetros en una CTE (`parametros`), no constantes escondidas.

## Modelo

- **Power Query** lee los CSV desde GitHub con la misma función `LeerCsv` de los otros reportes.
  - `ordenes_trabajo` calcula los días de atraso de cada OT.
  - `observaciones` traduce el código de la regla a un nombre legible.
- **Dos estrellas que comparten dimensiones:**
  - `estados_pago` y `observaciones` cuelgan directo de `sedes`, `contratistas` y `Calendario` (por el mes del EP).
  - `ordenes_trabajo` llega a `sedes` y `contratistas` a través de `activos`, en copo de nieve, para que haya un solo camino de filtro, y a `Calendario` por la fecha programada.
- **Segmentador dependiente:** el de contratista lleva un filtro de visual `Facturado > 0`, así que solo muestra los de la empresa elegida.
- **`Calendario`** es una tabla calculada de 2025 a 2026.

## Medidas clave

```dax
Facturado = SUM(estados_pago[monto])

Observado = SUM(observaciones[monto_observado])

% Observado = DIVIDE([Observado], [Facturado])

Pagado de más = CALCULATE([Observado], observaciones[resolucion] = "Pagada sin control")

Monto evitado = CALCULATE([Observado], observaciones[resolucion] = "Rechazada")

Cumplimiento preventivo % = DIVIDE([Preventivas a tiempo], [Preventivas programadas])

Backlog (OT) =
VAR fin = MAX(Calendario[Date])
RETURN
    COUNTROWS(
        FILTER(
            CALCULATETABLE(ordenes_trabajo, REMOVEFILTERS(Calendario)),
            ordenes_trabajo[clase] = "Preventiva"
                && ordenes_trabajo[fecha_programada] <= fin
                && (ISBLANK(ordenes_trabajo[fecha_inicio]) || ordenes_trabajo[fecha_inicio] > fin)
        )
    ) + 0

MTBF (días) = DIVIDE([Activos] * [Días del periodo], [Fallas])

Disponibilidad % =
VAR horas = [Activos] * [Días del periodo] * 24
VAR detenido = CALCULATE(SUM(ordenes_trabajo[horas_detencion]), ordenes_trabajo[clase] = "Correctiva")
RETURN IF(horas > 0, 1 - DIVIDE(detenido, horas))
```

Algunas decisiones de diseño:
- **Observado ≠ facturado de la línea:** en cantidad y precio se observa solo el exceso, porque la parte legítima se paga igual. Así el monto observado es lo que de verdad se ahorra.
- **`Backlog (OT)` quita el filtro de `Calendario`:** el backlog de diciembre incluye preventivas vencidas en meses anteriores que siguen sin iniciar. Con el filtro del mes, solo vería las de diciembre.
- **MTBF en días-activo:** divide el tiempo de operación de todos los activos filtrados por las fallas. Comparado con el MTBF de diseño (`MTBF objetivo (días)`), muestra qué tipos fallan más de lo esperado.

## Cómo leerlo

| Medida | Qué significa |
|---|---|
| **% Observado** | Parte de lo facturado que no pasa las reglas. Antes del control, era plata pagada de más; con control, es plata rechazada. |
| **Pagado de más / Monto evitado** | La misma medida antes y después del 1 de julio de 2025. |
| **Cumplimiento preventivo** | Preventivas iniciadas a más tardar 7 días después de lo programado, sobre las programadas. |
| **Backlog (semanas)** | Preventivas vencidas sin iniciar, expresadas en semanas del ritmo del plan. |
| **MTTR / Detención media** | Horas de reparación, y horas detenido contando la respuesta del contratista. La diferencia entre ambas es el tiempo de respuesta. |

El reporte abre en **Energía**, la misma industria con que abren los demás reportes de la vitrina. Valores de control para revisar al abrir el reporte:

| Indicador | Energía (al abrir) | Las tres empresas (sin filtro) |
|---|---|---|
| Facturado 2025-2026 | $5.073 M | $15.159 M |
| Observado (% de lo facturado) | $272,9 M (5,4%) | $759,6 M (5,0%) |
| Pagado de más / Monto evitado | $133,9 M / $138,9 M | $356,8 M / $402,7 M |
| % observado sin control / con control | 10,3% / 3,7% | 9,5% / 3,5% |
| Mayor observado | Montajes Ejemplo Norte Ltda., $110 M | Clima Ejemplo Ltda., $172 M |
| Cumplimiento preventivo | 78,2% | 83,8% |
| MTBF / MTTR | 92 días / 7,4 h | 86 días / 7,8 h |
| Disponibilidad | 98,73% | 98,75% |

## Cómo abrirlo

- **`.pbix`:** doble clic con Power BI Desktop.
- **Proyecto PBIP:** descomprimir, abrir `contratistas.pbip` y pulsar **Actualizar**. Los datos se leen desde GitHub; si pide credenciales, elegir Anónimo.
- **Solo los datos:** el zip de CSV o el Excel, con una hoja por tabla y un diccionario de columnas.
- **Solo las reglas:** `python sql/auditar.py` vuelve a calcular `observaciones.csv` desde los CSV.

## Gobierno de datos

Contratistas, activos y montos son ficticios.
- **Datos reales:** las observaciones se revisarían con el administrador del contrato antes de rechazar, y la regla de cantidad usaría las mediciones aprobadas en terreno, no solo lo registrado en la OT.
- **Lo que no publicamos:** ninguna cifra, contrato, tarifa ni regla de un empleador real.

## Qué demuestra

- Control de gestión aplicado a contratistas: auditoría de estados de pago con reglas explícitas y el monto que evita el control.
- SQL versionado (CTE, `LEFT JOIN`, `ROW_NUMBER`) con tests de precisión y recall sobre anomalías etiquetadas.
- Indicadores de mantenimiento al estilo de SAP PM: cumplimiento del plan, backlog, MTBF, MTTR y disponibilidad.
- Un modelo de Power BI con dos estrellas que comparten dimensiones sin caminos ambiguos, y un proyecto PBIP versionado en Git.
