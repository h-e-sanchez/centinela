# Roadmap — centinela

Estado al **2026-09-09**. El sitio está en vivo
([`h-e-sanchez.github.io/centinela`](https://h-e-sanchez.github.io/centinela/)): motor
Python completo, sitio estático de 2 páginas, modelo de Power BI documentado y pendiente
de publicar (paso manual, ver Camino C). Este archivo se edita a mano.

---

## Relato — la empresa de ejemplo

Los datos sintéticos de este repo no son números al azar sin contexto: representan una
empresa ficticia, **"Manufacturera Ejemplo S.A."** — genérica a propósito, sin ninguna
relación con un empleador real.

- **~100 personas**, una manufacturera de tamaño medio con **dos líneas de producto
  propio** más un componente de **servicios de postventa** (mantenimiento/soporte sobre lo
  vendido). Esto mapea directo a `CENTROS["Ingresos"]` en
  [`data/generar_datos_sinteticos.py`](data/generar_datos_sinteticos.py):
  `ventas_producto_a`, `ventas_producto_b`, `ventas_servicios`.
- **Costos** = `Operaciones` (materiales, producción) — el costo directo de fabricar lo que
  se vende.
- **Gastos Operacionales** = `Comercial`, `Administración y Finanzas`, `Personas`,
  `Tecnología` — la estructura de soporte típica de una PYME industrial, no una lista
  inventada: es la misma taxonomía Ingresos/Costos/Gastos Operacionales que aparece en
  cualquier Estado de Resultados exportado de SAP FI/CO, generalizada sin ningún dato de
  un empleador específico.

**Por qué este arquetipo y no otro:** un relevamiento del mercado laboral chileno de roles
de Control de Gestión/FP&A que piden Power BI (búsqueda propia del autor, no publicada en
este repo) muestra que las publicaciones reales vienen mayoritariamente de **empresas
manufactureras/industriales de tamaño medio que venden por línea de producto** — papel,
alimentos, vino — todas pidiendo "Presupuesto y Forecast" + Power BI con DAX avanzado como
requisito central. El relato de `centinela` sigue ese mismo perfil porque es el que mejor
explica una herramienta de seguimiento Presupuesto vs. Real: no se copia ninguna empresa
puntual, solo se elige el arquetipo de negocio que el mercado real demuestra que es común
para este rol.

### Reporte #2 — las mismas tres empresas, vistas desde las personas

Las tres empresas ficticias del reporte #1 (Manufactura, Energía y Salud), con sus sucursales
como sedes, seis unidades por empresa y unas 1.400 personas, simuladas día hábil a día hábil
en 2025-2026 ([`data/generar_workforce.py`](data/generar_workforce.py)). En Salud, la
calibración sigue en orden de magnitud a la Dipres (*Radiografía del ausentismo laboral en el
sector público*, 2024), al NHS y a la SUSESO, a escala de clínica privada; Energía y
Manufactura, con plantillas más masculinas, quedan más abajo. Desde julio de 2025 una sede de
cada empresa (Concepción, Zona Norte y Clínica Oriente) cubre ausencias con un pool interno, y
las otras dos sirven de grupo de control. Ningún parámetro sale de un empleador real: el
método (simulación y credibilidad) es genérico.

### Reportes #4 a #7 — las mismas tres empresas, cuatro miradas más

Especificados el 2026-10-05, antes de construir. Cada especificación fija datos, páginas,
medidas, historias sembradas y tests, y todos abren con **portada y resumen** y cierran con
**glosario**, como el #2.

- **#4 Proyectos tecnológicos** ([especificación](docs/especificaciones/04-proyectos-ti.md)):
  la cartera de TI de cada empresa, ejecutada por cinco equipos compartidos con un flujo ágil
  estilo Jira. Mide velocidad, flujo, carga por equipo y dependencias entre equipos, y
  pronostica la fecha de término con Monte Carlo.
- **#5 Capital de trabajo y ciclo de caja** ([especificación](docs/especificaciones/05-capital-de-trabajo.md)):
  cobranza, pagos e inventario con DSO, DPO, DIO y ciclo de conversión de caja, más un flujo
  de caja a 13 semanas. Sus facturas cuadran con los montos del #1.
- **#6 Equidad salarial y bandas** ([especificación](docs/especificaciones/06-compensaciones.md)):
  las mismas personas del #2, con bandas por grado, compa-ratio y brecha de género, mirado
  **por persona y por servicio**, con seguridad por fila por servicio.
- **#7 Pricing y márgenes por canal** ([especificación](docs/especificaciones/07-pricing-margenes.md)):
  cascada de precios, margen de contribución por canal, efecto precio-volumen-mezcla y curva
  ballena de clientes. Sus ingresos cuadran con el #1.

---

## Camino A — Motor (Python) — hecho

- **Generador de datos sintéticos**
  ([`data/generar_datos_sinteticos.py`](data/generar_datos_sinteticos.py)) — semilla fija
  (reproducible), ruido controlado por centro de costo/componente más un porcentaje de
  desviaciones grandes inyectadas a propósito (`TASA_DESVIACION_GRANDE`) para que el motor
  tenga algo real que clasificar. Es la única fuente de datos del repo: nada se
  reimplementa en otro lenguaje (ver Camino B).
- **Motor de cruce y clasificación** ([`src/motor.py`](src/motor.py)) — desviación $/%
  por línea, umbral estricto configurable, `resumen_por_grupo` para el subtotal de
  Resultado Operacional.
- **CLI** ([`src/main.py`](src/main.py)) — `--umbral`, `--umbral-critico`,
  `--estado-resultados`, exportación a CSV.
- **Suite de tests** ([`tests/`](tests/)) — motor, generador, exportador web.

Detalle completo del diseño en [`README.md`](README.md) § Diseño — no se repite aquí.

## Camino B — Sitio estático — hecho

Despliegue estático (GitHub Pages), sin paso de build.

**Mapa de páginas — qué ve el visitante:**

| Página | Qué muestra |
|---|---|
| [`index.html`](index.html) | resumen del motor (tabla de ejemplo real), sección Modelo (Power BI — placeholder pendiente de iframe), sección Portafolio (link a [`consulta`](https://github.com/h-e-sanchez/consulta)) |
| [`datos.html`](datos.html) | selector de ejemplo (3 semillas) + mes + umbral de alerta/crítico ajustable en vivo; tabla de Estado de Resultados y tabla de detalle, recalculadas en el navegador |
| [`docs/how-to-pbi.md`](docs/how-to-pbi.md) | documentación técnica del modelo DAX — visitable desde GitHub, no forma parte del sitio estático |

`datos.html` **no genera datos en el navegador** — carga 3 corridas reales del motor
Python embebidas como JSON estático
([`data/exportar_ejemplos_web.py`](data/exportar_ejemplos_web.py) →
`data/ejemplos-web.json`) y solo reimplementa en JS la aritmética simple y determinista
(clasificación ok/alerta/crítica, sumas por grupo) — ver "No hacer" más abajo para el
porqué.

## Camino C — Modelo Power BI — hecho

**2026-10-01 — hecho como código:** proyecto PBIP en [`powerbi/presupuesto-vs-real/`](powerbi/presupuesto-vs-real/) (modelo TMDL
completo, reporte PBIR con una página vacía) y [`reporte.html`](reporte.html), que recalcula
el reporte en el navegador con el DAX leído del TMDL. **Pendiente, manual:** abrir el PBIP
en Desktop, armar los visuales, guardar (commit de los `visual.json`) y publicar con un
tenant propio (dominio `cimad.net`). Los pasos de abajo quedan como referencia del modelo;
la ruta vigente está en [`docs/how-to-pbi.md`](docs/how-to-pbi.md) § Proyecto PBIP.

Power BI Desktop es una aplicación de escritorio: este paso no se puede automatizar desde
el repo. Ruta resumida (idéntica a los 8 pasos de
[`docs/how-to-pbi.md`](docs/how-to-pbi.md) § "Pendiente (candidato, manual)" — ese
documento tiene el detalle completo, las fórmulas DAX y el modelo de datos; acá solo la
secuencia):

1. Generar los CSV (`python data/generar_datos_sinteticos.py`).
2. Abrir Power BI Desktop, cargar `presupuesto.csv` y `real.csv`.
3. Combinar en Power Query (join por `anio`+`mes`+`centro_costo`+`componente`, completitud
   de grilla con ceros explícitos).
4. Crear la tabla `Calendario` y su relación.
5. Crear la columna calculada `Estado Semáforo` y las 9 medidas DAX.
6. Armar el layout con los visuales sugeridos.
7. **Publicar en la Web** y pegar el `<iframe>` resultante en `index.html`.
8. Exportar 1-2 capturas de pantalla del reporte para el README (opcional).

**⚠️ Recordatorio de privacidad:** "Publicar en la Web" hace el reporte genuinamente
público e indexable — usar **solo** con los datos sintéticos generados por este repo,
nunca con datos reales de un empleador.

---

## Camino D — Vitrina de reportes — en curso

La web pasa a ser una vitrina de reportes Power BI para reclutadores: portada con
presentación breve y tarjetas, ficha por reporte (`ficha.html?r=<slug>`) con reporte
interactivo, descargas y guía `.md`, y una sección secundaria "Cómo está hecho".

- [x] Reporte #1: Presupuesto vs. Real por industria (catálogo, guía, descargas CSV, Excel y PBIP)
- [ ] `.pbix` exportado desde Desktop y captura `portada.png` (manual)
- [x] Reporte #2: Workforce (dotación, ausentismo y cobertura): datos, modelo PBIP con 6 páginas, guía y descargas
- [x] Reporte #2: abierto en Desktop sin errores y publicado en la web (tenant `cimad.net`)
- [ ] Reporte #2: `.pbix` exportado y captura `portada.png` (manual)
- [x] Reporte #3: Contratistas y mantenimiento: datos, reglas SQL con tests, modelo PBIP con 6 páginas, guía y descargas
- [x] Reporte #3: abierto en Desktop sin errores y publicado en la web (tenant `cimad.net`)
- [ ] Reporte #3: `.pbix` exportado y captura `portada.png` (manual)
- [x] Glosario por reporte: conceptos escritos a mano + todas las medidas DAX leídas del TMDL, en la ficha web y como página «Glosario» en cada PBIP
- [ ] Glosario: abrir los 3 PBIP en Desktop, revisar la página y volver a publicar (manual)
- [x] Reportes #4 a #7: especificación en [`docs/especificaciones/`](docs/especificaciones/) y tarjetas «En preparación» en la vitrina (`proximos` del catálogo)
- [x] Reporte #4 · Proyectos tecnológicos: generador y tests, PBIP de 8 páginas, guía, glosario y descargas (catálogo «en preparación»)
- [ ] Reporte #4: abierto en Desktop, publicado en la web y `.pbix` exportado (manual)
- [x] Reporte #5 · Capital de trabajo y ciclo de caja: generador cuadrado con el #1, PBIP de 8 páginas, guía, glosario y descargas (catálogo «en preparación»)
- [x] Reporte #5: abierto en Desktop y publicado en la web (falta `.pbix` exportado, manual)
- [x] Reporte #6 · Equidad salarial y bandas: generador sobre las personas del #2, PBIP de 9 páginas con RLS por servicio, guía, glosario y descargas (catálogo «en preparación»)
- [x] Reporte #6: abierto en Desktop y publicado en la web, en una copia sin roles: Power BI no publica en la web un modelo con RLS (faltan probar los roles con «Ver como» y exportar el `.pbix`, manual)
- [x] Reporte #7 · Pricing y márgenes por canal: generador cuadrado con el #1, PBIP de 9 páginas, guía, glosario y descargas (catálogo «en preparación»)
- [ ] Reporte #7: abierto en Desktop, publicado en la web y `.pbix` exportado (manual)
- [x] Reporte #8 · Del libro diario a los EEFF: especificación, libro diario en partida doble cuadrado con el #1, PBIP de 10 páginas, guía, glosario y descargas (catálogo «en preparación»; sin consolidación)
- [ ] Reporte #8: abierto en Desktop, publicado en la web y `.pbix` exportado (manual)

## Backlog P1 — robustez

- **CI bloqueada.** `.github/workflows/ci.yml` existe en el working tree pero no está
  commiteado — falta el scope OAuth `workflow` (`gh auth refresh -s workflow`). Ver
  Bitácora.
- Cobertura de tests para `src/main.py` (hoy solo se prueban `motor.py` y los
  generadores).

## Backlog P2 — alcance

- Capturas del reporte Power BI para el README, una vez publicado (Camino C, paso 8).
- Toggle ES/EN del copy de la interfaz — misma idea que el backlog P2 de `consulta`,
  anotada acá para mantener los dos roadmaps del portafolio alineados.
- Permitir que el visitante cargue su propio CSV en `datos.html` sin que el archivo salga
  del navegador — mismo compromiso de privacidad client-side que ya aplica `consulta`.
- Más de un año de datos en los ejemplos (hoy cada semilla cubre un año calendario).

## No hacer (por ahora)

- **Generar datos en el navegador.** El RNG de JS no reproduce `random.Random` de
  Python — la misma semilla daría números *distintos*, lo cual sería engañoso. Los
  ejemplos de `datos.html` siempre vienen de una corrida real del CLI.
- **Datos reales de un empleador**, en cualquier forma — ni en el motor, ni en el sitio,
  ni en el modelo de Power BI. Sin excepciones.

---

## Nota técnica de deploy

GitHub Pages sirve `main` `/` directo, sin build. A diferencia de `consulta`, `centinela`
todavía no tiene `?v=N` de cache-busting en `style.css`/`datos.js` — si esos archivos
empiezan a cambiar con frecuencia, agregar el mismo patrón (bumpear `?v=N` en el HTML en
cada cambio) para evitar que Pages sirva la versión vieja unos minutos.

---

## English

This roadmap documents `centinela`'s three build paths (Python engine, static site, Power
BI model) and the fictional company behind its example data — a mid-size manufacturer
selling two product lines plus after-sales service, an archetype chosen because it
matches what real Control de Gestión/FP&A job postings with Power BI most commonly
describe. The engine and static site are done; the Power BI model is documented in full
in `docs/how-to-pbi.md` and pending the one manual step Power BI Desktop requires
(publish to the web with synthetic data only, then embed the iframe). No real employer's
name or data appears anywhere in this repo.

---

## Bitácora

### 2026-10-06 — Reporte #5: Capital de trabajo y ciclo de caja

Generador `data/generar_capital_de_trabajo.py`: facturas de venta a los mismos clientes del #7 y
facturas de compra a proveedores ficticios, con condición de pago por canal y atraso por cliente.
Cuadran al peso con los ingresos Real y las cuentas de Costos compradas a proveedores del #1. Suma
inventario mensual por familia y caja semanal real hasta el corte (27-12-2026), con 13 semanas
proyectadas. `tests/test_capital_de_trabajo.py` verifica la cuadratura, las fechas, que la caja
sume semana a semana y que sus cobros sean las facturas pagadas, y tres historias:
- Salud con DSO de 93 días, el ciclo más largo y 7 semanas bajo $60 M en 2026;
- Antofagasta cierra 2025 con unos 25 días más de inventario que las otras sucursales;
- Energía con ciclo de −15 días.

Proyecto PBIP `powerbi/capital-de-trabajo/`: 14 tablas (relaciones inactivas por vencimiento y
pago, fecha de corte, tramos de antigüedad, cascada del ciclo y parámetro de saldo mínimo) y 8
páginas, como en la especificación.

### 2026-10-05 — Reporte #6: Equidad salarial y bandas

Generador `data/generar_compensaciones.py` sobre las mismas personas de Workforce: siete grados,
bandas por empresa y año con encuesta de mercado, y remuneraciones mensuales 2025-2026.
`tests/test_compensaciones.py` verifica que sean las mismas personas, que solo cobren mientras
están vigentes, la jornada parcial, un rol de seguridad por servicio y las tres historias:
- la UCI con compa-ratio de 1,11;
- el 8,6% de Energía bajo el mínimo;
- en Manufactura, la brecha cruda negativa frente al 4,3% en la misma banda.

Proyecto PBIP `powerbi/compensaciones/`: 10 tablas, un parámetro what-if de reajuste negociado,
18 roles (uno por servicio) y 9 páginas, que suman a la especificación la de competitividad de
mercado.

### 2026-10-05 — Reporte #7: Pricing y márgenes por canal

Generador `data/generar_pricing.py`: líneas de venta con cascada de lista a neto, costo variable y
costo de servir. Los ingresos netos cuadran al peso con las cuentas de ingreso Real del #1.
`tests/test_pricing.py` verifica la cuadratura, la cascada, que precio + volumen + mezcla sumen la
variación, y tres historias:
- Retail queda con 4,3% de margen de contribución;
- en Energía, el precio explica el 100% de la variación;
- en Salud, el 21% de los convenios está fuera de política.

Proyecto PBIP `powerbi/pricing-margenes/`: 13 tablas (dos cascadas desconectadas y un parámetro de
cambio de precio) y 9 páginas, que suman a la especificación el simulador de precio.

### 2026-10-05 — Reporte #8: Del libro diario a los EEFF

Sale de la espera con un alcance acotado: contabilidad por empresa, sin consolidación.
Especificación en `docs/especificaciones/08-estados-financieros.md`. El generador
`data/generar_estados_financieros.py` lleva el Real del #1 a un libro diario en partida doble y le
suma cobranza, inventario, pagos, depreciación, deuda (con una línea de crédito automática),
impuesto, cierre y traspaso. `tests/test_estados_financieros.py` verifica:
- debe = haber en cada asiento;
- el balance cuadrado en los 24 meses;
- el EBITDA igual al #1;
- el cierre y el traspaso;
- que el flujo indirecto explique la variación de caja;
- tres historias: Salud cobra a 95 días, Energía tiene 81% de activo fijo y Manufactura llega a 117 días de inventario.

Proyecto PBIP `powerbi/estados-financieros/` de 10 páginas, con saldos acumulados, cascada del flujo y
página de cuadraturas.

### 2026-10-05 — Reporte #4: Proyectos tecnológicos

Generador `data/generar_proyectos_ti.py`: simulación día hábil a día hábil de la cartera de TI de
las tres empresas (cinco equipos compartidos, dependencias entre equipos, bloqueos y traspasos) y
pronóstico de Monte Carlo con 10.000 simulaciones. `tests/test_proyectos_ti.py` verifica la
coherencia del historial y las tres historias:
- la ficha clínica de Salud termina 75 días tarde al P85;
- Integraciones concentra el 39% del bloqueo en Energía;
- el ERP de Manufactura tiene una previsibilidad de 90%.

Proyecto PBIP `powerbi/proyectos-ti/`: 17 tablas en copo de nieve, con la relación del calendario
con la fecha de fin inactiva y activada con `USERELATIONSHIP`, y 8 páginas (portada, resumen,
sprints, flujo, capacidad, colaboración, pronóstico y glosario). Catálogo en «en preparación»
hasta abrirlo en Desktop y publicarlo.

### 2026-10-05 — Reportes #4 a #7 especificados

Cuatro especificaciones en `docs/especificaciones/`, con un mismo contrato: datos tidy con
semilla fija, páginas (portada, resumen y glosario incluidos), medidas DAX clave, tres
historias sembradas y tests. Son Proyectos tecnológicos (ágil, estilo Jira),
Capital de trabajo y ciclo de caja, Equidad salarial y bandas (por persona y por servicio)
y Pricing y márgenes por canal. Los cuatro aparecen en la vitrina como «En preparación».
El #5 absorbe el capital de trabajo que estaba en espera en el #4; «Del libro diario a los
EEFF» pasa a ser el #8.

### 2026-10-02 — Workforce publicado

Desktop abrió el modelo y las 6 páginas sin errores; al guardar normalizó el PBIP (metadatos
lingüísticos es-CL, nombres sin comillas, schema de un visual). Publicado con "Publicar en la
Web" desde el tenant propio y registrado en el catálogo: la ficha ya muestra el reporte
interactivo.

### 2026-10-02 — Reporte #2: Workforce

Generador `data/generar_workforce.py` (personas, episodios, ausencia diaria, disponibilidad,
cobertura y pronóstico 2027 con Bühlmann-Straub y simulación de episodios) y
`tests/test_workforce.py`, que verifica la calibración y la historia del piloto. Proyecto PBIP
`powerbi/workforce/` con 12 tablas, parámetro de campo «Comparar por» y 6 páginas (resumen,
dotación, ausentismo, patrones individuales, cobertura y pronóstico) con los visuales ya
definidos en PBIR. Ficha y descargas publicadas como «en preparación» hasta publicarlo desde
Desktop.

### 2026-10-02 — Vitrina con varios reportes

El proyecto PBIP del reporte #1 pasa a `powerbi/presupuesto-vs-real/` para que cada reporte
tenga su carpeta. El catálogo suma `modelo`, `datos` y `prefijo` por reporte; el diccionario
de columnas vive en `reportes/<slug>/diccionario.json`. `empaquetar_descargas.py --reporte`
arma los descargables de cualquier reporte y escribe el Excel según los encabezados (antes
era posicional). Los tests de vitrina y de Power BI se parametrizan por reporte, y un reporte
con `"estado": "en-preparacion"` se muestra con guía y descargas mientras no se publica.

### 2026-10-01 — Vitrina de reportes

`index.html` se reescribe como vitrina (presentación, destacado con el reporte publicado,
tarjetas desde `reportes/catalogo.json`, "Cómo está hecho" y portafolio). Nueva ficha genérica
`ficha.html` + `ficha.js` con guía renderizada (`marked`, cdnjs) y descargas que solo se
muestran si el archivo existe. Empaquetador reproducible y `tests/test_vitrina.py`.

### 2026-10-01 — Reporte de Power BI publicado e incrustado

Publicado con "Publicar en la Web" desde un tenant propio (dominio `cimad.net`, nunca el de un
empleador) e incrustado en `index.html` (sección Modelo) y en `reporte.html`
(`PBI_EMBED_URL`). Solo datos sintéticos.

### 2026-10-01 — Escenarios por industria

`data/generar_escenarios.py` crea tres industrias con historias distintas sobre el Resultado
Operacional: Manufactura positiva (+20,4%), Energía neutra (+0,3%) y Salud en rojo (−72,1%,
negativa de junio a agosto). El modelo de Power BI pasa a leer `data/escenarios/`, con columna
`industria`, las medidas `Desviación RO %` y `Color Resultado`, un segmentador Industria en
Resumen y Estado de Resultados, y la página nueva **Escenarios**. `reporte.html` suma el
selector de industria y la tabla de escenarios. El motor CLI y `datos.html` siguen con los
datos originales (semillas 42, 7 y 123).

### 2026-10-01 — Power BI como código + `reporte.html`

Proyecto PBIP (TMDL + PBIR) en `powerbi/` con Power Query que lee los CSV desde GitHub, tabla
de fechas calculada, `Estado Semáforo` y 15 medidas DAX. Nueva página `reporte.html`
(KPI, tendencia, desviación por centro de costo, matriz con semáforo y Estado de
Resultados) con el DAX de cada visual leído en vivo desde el TMDL; verificada contra
`python -m src.main --estado-resultados` (diciembre: Resultado Operacional real
$9.738.194, −12,5%, alerta). Test nuevo que impide que la página cite medidas que no
existen en el modelo.

### 2026-09-09 — Roadmap inicial

Primer `ROADMAP.md` del repo, homologado con el formato de `consulta/ROADMAP.md`. Agrega
el relato de la empresa de ejemplo (ligado a evidencia real del `/rank` del día), el mapa
de páginas, la ruta resumida de Power BI y el cierre en inglés.

### 2026-09-09 — `datos.html`: explorar el dataset completo (PR #3)

Reemplaza el enlace estático de `index.html` por una página interactiva: 3 ejemplos reales
del motor embebidos como JSON, umbral de alerta/crítico ajustable en vivo, tabla de
Estado de Resultados y tabla de detalle recalculadas en el navegador con la misma
aritmética de `src/motor.py`.

### 2026-09-09 — Jerarquía de cuentas y Estado de Resultados (PR #2)

Cada línea gana un `grupo_cuenta` (Ingresos / Costos / Gastos Operacionales), lo que
permite un subtotal real de Estado de Resultados (`Resultado Operacional = Ingresos −
Costos − Gastos Operacionales`) vía `--estado-resultados`. `docs/how-to-pbi.md` documenta
la medida DAX equivalente.

### 2026-09-08 — Scaffold inicial (PR #1)

Motor de desviación Presupuesto vs. Real (`src/motor.py`, `src/main.py`), generador de
datos sintéticos con semilla fija, sitio estático (`index.html`, `style.css`), y
`docs/how-to-pbi.md` con el modelo DAX completo. Publicado como repo público + GitHub
Pages.
