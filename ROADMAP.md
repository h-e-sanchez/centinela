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

## Camino C — Modelo Power BI — pendiente (manual)

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
