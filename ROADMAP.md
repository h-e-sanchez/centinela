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
- [ ] Reporte #4: Del libro diario a los EEFF / capital de trabajo (en espera)

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
