# centinela

> Vitrina de reportes Power BI de control de gestión: cada reporte trae su versión
> interactiva, datos sintéticos descargables (CSV, Excel, .pbix y el proyecto PBIP como
> código) y una guía corta del modelo. Detrás, un motor de desviación Presupuesto vs. Real
> en Python, sin dependencias externas.

**Vitrina:** <https://h-e-sanchez.github.io/centinela/>

Parte del portafolio **Control de gestión, construido como software**: `centinela` es la
vitrina (lo que ve quien decide) y [`consulta`](https://github.com/h-e-sanchez/consulta) es el
taller (SQL, perfilado y gráficos sobre cualquier tabla, en el navegador). El manual es
[`cartilla`](https://h-e-sanchez.github.io/cartilla/): Python y pandas para quien viene de Excel.

## Vitrina

- `reportes/catalogo.json` describe cada reporte (resumen, habilidades, URL de Publicar en la
  Web, descargas, carpeta de datos y proyecto PBIP). `index.html` y `ficha.html?r=<slug>` se
  arman desde ahí: agregar un reporte es crear `reportes/<slug>/` (con `guia.md` y
  `diccionario.json`) y `powerbi/<slug>/`, sin escribir HTML. Un reporte con
  `"estado": "en-preparacion"` se muestra con su guía y descargas mientras no se publica.
- `herramientas/empaquetar_descargas.py [--reporte <slug>]` genera los zip (reproducibles) y
  el Excel de cada reporte desde sus CSV y su proyecto PBIP. El `.pbix` se exporta a mano
  desde Power BI Desktop.
- `tests/test_vitrina.py` verifica, reporte por reporte, que el catálogo esté completo, que
  las descargas estén al día con sus fuentes, que la guía solo cite medidas de su modelo y
  que la web no publique datos de contacto.

## Diseño

- **Modelo tidy/long** (año, mes, centro de costo, componente, monto) para presupuesto
  y real por separado — trivial de pivotear en Excel, Power BI o pandas sin transformar
  nada primero.
- **Motor puro** (`src/motor.py`): cruza ambas tablas por clave compuesta, calcula
  desviación en $ y % por línea, y clasifica cada una en `ok` / `alerta` / `critica`
  según un umbral configurable — la comparación es estricta (`>`, no `>=`): una línea en
  exactamente el umbral no dispara.
- **Jerarquía de cuentas mínima**: cada línea declara un `grupo_cuenta` (Ingresos / Costos
  / Gastos Operacionales), lo que permite calcular un subtotal real de Estado de
  Resultados — **Resultado Operacional = Ingresos − Costos − Gastos Operacionales** —
  con su propio semáforo de desviación, no solo una lista plana de líneas
  (`--estado-resultados`, ver [demo interactiva](https://h-e-sanchez.github.io/centinela/datos.html)).
- **Completitud de grilla**: ninguna celda se omite. Una línea presupuestada sin gasto
  real (o viceversa) se completa con monto `0` explícito — evita el sesgo de subconteo
  típico al agregar eventos poco frecuentes.
- **Parámetros separados de la lógica**: el umbral de alerta y el umbral crítico son
  argumentos del CLI, no valores fijos en el código — los "diales" que quien controla el
  presupuesto ajusta sin tocar una línea de Python.
- **Generador de datos sintéticos reproducible** (semilla fija): genera presupuesto y
  real con ruido controlado más un porcentaje de desviaciones grandes inyectadas a
  propósito, para que el motor tenga algo real que clasificar.
- **Escenarios por industria** (`data/generar_escenarios.py`): tres empresas sintéticas
  con estructura de cuentas y estacionalidad propias, cada una con una historia sobre el
  Resultado Operacional: Manufactura positiva (+20%), Energía neutra (+0,3%) y Salud en
  rojo (−72%, con resultado negativo en la campaña de invierno). Los tests verifican que
  cada escenario cumpla su historia. Son la fuente del modelo de Power BI y de
  `reporte.html`.
- **Cero dependencias de runtime** — solo librería estándar. Dev deps (`pytest`, `ruff`)
  separadas en `requirements-dev.txt`.

## Uso

```bash
pip install -r requirements.txt -r requirements-dev.txt

# Regenerar los descargables de la vitrina (requiere openpyxl, en requirements-dev.txt)
python herramientas/empaquetar_descargas.py

# Glosario de cada reporte (conceptos + todas las medidas DAX, leídas del TMDL) para la web y Power BI
python herramientas/generar_glosario.py

# Datos sintéticos del reporte Workforce (red de clínicas ficticia, 2025-2026 y pronóstico 2027)
python data/generar_workforce.py

# Datos sintéticos del reporte de contratistas (OT y estados de pago) + reglas SQL de auditoría
python data/generar_contratistas.py
python sql/auditar.py   # solo recalcula observaciones.csv desde los CSV

# Datos sintéticos del reporte de proyectos de TI (historial estilo Jira + pronóstico Monte Carlo)
python data/generar_proyectos_ti.py

# Datos sintéticos del reporte de compensaciones (lee las personas de Workforce)
python data/generar_compensaciones.py

# Generar presupuesto.csv y real.csv sintéticos
python data/generar_datos_sinteticos.py

# Correr el motor con el umbral por defecto (alerta >5%, crítica >15%)
python -m src.main

# Umbral propio + exportar el detalle a CSV
python -m src.main --umbral 0.08 --umbral-critico 0.20 --salida reporte_desviacion.csv

# Estado de Resultados por mes (Ingresos / Costos / Gastos Operacionales / Resultado Operacional)
python -m src.main --estado-resultados

# Tests
python -m pytest tests/ -q
```

## Modelo

La misma lógica, como **proyecto de Power BI versionado en texto** en
[`powerbi/presupuesto-vs-real/`](powerbi/presupuesto-vs-real/) (formato PBIP): modelo semántico en TMDL, con Power Query que lee
los CSV de este repo desde GitHub, tabla de fechas, la columna `Estado Semáforo` y 15
medidas DAX (montos, desviación, semáforo, Estado de Resultados y time intelligence), más
el reporte en PBIR. [`reporte.html`](https://h-e-sanchez.github.io/centinela/reporte.html)
recalcula ese reporte en el navegador y muestra la medida DAX de cada visual, leída en vivo
desde el TMDL. El reporte interactivo se publica con "Publicar en la Web" (solo datos
sintéticos) y queda incrustado en esa misma página. Detalle y pasos en
[`docs/how-to-pbi.md`](docs/how-to-pbi.md).

El reporte #2, **Workforce** ([`powerbi/workforce/`](powerbi/workforce/)), aplica el mismo
enfoque a People Analytics: dotación y rotación, los tres índices de ausentismo de la Dipres,
Factor Bradford, costo de cobertura con un piloto evaluado contra un grupo de control y
pronóstico 2027 con credibilidad de Bühlmann-Straub. Guía en
[`reportes/workforce/guia.md`](reportes/workforce/guia.md).

El reporte #3, **Contratistas y mantenimiento** ([`powerbi/contratistas/`](powerbi/contratistas/)),
cruza los estados de pago de los contratistas con las órdenes de trabajo y las tarifas. Las
reglas de auditoría viven en SQL versionado ([`sql/reglas_auditoria.sql`](sql/reglas_auditoria.sql),
CTE y `ROW_NUMBER` sobre `sqlite3`), con tests que exigen encontrar exactamente las anomalías
inyectadas. Suma cumplimiento del plan preventivo, backlog, MTBF y MTTR. Guía en
[`reportes/contratistas/guia.md`](reportes/contratistas/guia.md).

El reporte #4, **Proyectos tecnológicos** ([`powerbi/proyectos-ti/`](powerbi/proyectos-ti/)), lleva
el control de gestión a la cartera de TI desde el historial de un Jira ágil: velocidad y
previsibilidad por sprint, tiempo de ciclo por percentil, carga de los equipos, horas bloqueadas
por dependencias entre equipos y fecha de término pronosticada con Monte Carlo. Guía en
[`reportes/proyectos-ti/guia.md`](reportes/proyectos-ti/guia.md).

El reporte #6, **Equidad salarial y bandas** ([`powerbi/compensaciones/`](powerbi/compensaciones/)),
toma las mismas personas del reporte Workforce y mide bandas, compa-ratio, equidad interna por
persona y por servicio, brecha de género en cargos equivalentes y competitividad de mercado. Calcula
el costo de corregir, con un parámetro de reajuste negociado y seguridad por fila por servicio. Guía
en [`reportes/compensaciones/guia.md`](reportes/compensaciones/guia.md).

## Demo

[`h-e-sanchez.github.io/centinela`](https://h-e-sanchez.github.io/centinela/) — página
estática (sin build). [`/datos.html`](https://h-e-sanchez.github.io/centinela/datos.html)
deja explorar 3 corridas del motor con datos sintéticos y ajustar el umbral de alerta en vivo — la
clasificación se recalcula en el navegador con la misma aritmética que `src/motor.py`,
pero los datos en sí no se generan ahí (el RNG de JS no reproduce el de Python). El
reporte de Power BI está publicado con "Publicar en la Web" e incrustado en la página
principal y en [`/reporte.html`](https://h-e-sanchez.github.io/centinela/reporte.html). Relato,
mapa de páginas y backlog en [`ROADMAP.md`](ROADMAP.md).

## English

A dependency-free Python engine that reconciles a planned budget against actual spend
per cost center, computes the deviation in absolute and percentage terms, and flags each
line as ok / warning / critical against a configurable threshold. No cell is silently
dropped — a budgeted line with no matching actual (or vice versa) is filled with an
explicit zero, which avoids undercounting bias in sparse aggregations. Each line also
carries a minimal account hierarchy (Revenue / Cost of Sales / Operating Expenses), so
the engine can roll up a real P&L subtotal — Operating Result — with its own deviation
threshold, not just a flat list of line items. The same logic is modeled in Power BI (DAX
measures documented in `docs/how-to-pbi.md`) and published publicly via Power BI's
"Publish to Web" feature — synthetic data only.
