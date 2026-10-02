# Cómo construir el modelo en Power BI

> **Desde 2026-10-01 el modelo ya está construido como código** en
> [`powerbi/presupuesto-vs-real/`](../powerbi/presupuesto-vs-real/), en formato **PBIP** (Power BI Project): el modelo semántico en
> TMDL y el reporte en PBIR, todo como texto versionado. Este documento sigue siendo la
> especificación de referencia; la sección [Proyecto PBIP](#proyecto-pbip-en-el-repo) explica
> qué falta hacer a mano y cómo publicarlo.

## Proyecto PBIP en el repo

```
powerbi/presupuesto-vs-real/
├── centinela.pbip                     ← abrir este archivo en Power BI Desktop
├── centinela.SemanticModel/
│   ├── definition.pbism
│   └── definition/                    ← TMDL: un archivo por tabla
│       ├── model.tmdl  database.tmdl  expressions.tmdl  relationships.tmdl
│       └── tables/desviacion.tmdl  tables/Calendario.tmdl
└── centinela.Report/
    ├── definition.pbir                ← apunta al modelo con byPath
    ├── definition/                    ← PBIR: una página "Resumen", sin visuales todavía
    └── StaticResources/               ← tema base CY24SU10 + tema «técnico cálido»
```

Qué ya está resuelto en el código:

- **Origen de datos:** el parámetro `UrlDatos` apunta a la carpeta `data/` de este repo en
  GitHub (`raw.githubusercontent.com`). El modelo carga `presupuesto.csv` y `real.csv` sin
  rutas locales, y el refresco en el Power BI Service funciona con credencial anónima.
- **Escenarios:** desde 2026-10-01 el modelo lee `data/escenarios/presupuesto.csv` y
  `real.csv` (tres industrias, columna `industria`). El reporte tiene un segmentador Industria
  ("Todas" = consolidado) y una página **Escenarios** que compara el Resultado Operacional de
  cada industria con la medida `Color Resultado` (verde sobre +2%, rojo bajo −2%, gris neutro).
- **Power Query:** une ambos archivos con `Table.Combine` + `Table.Group` (completitud de
  grilla: cada línea queda con presupuesto y real, 0 explícito si falta uno) y agrega `fecha`.
  Los montos se leen con cultura `en-US` porque vienen con punto decimal.
- **Modelo:** hecho `desviacion` + dimensión `Calendario` (tabla calculada en DAX, marcada
  como tabla de fechas) con relación por fecha.
- **DAX:** la columna `Estado Semáforo` y 15 medidas en carpetas (Montos, Desviación,
  Semáforo, Estado de Resultados, Tiempo con `TOTALYTD` y `DATEADD`), con formato y
  descripción. `discourageImplicitMeasures` obliga a usar las medidas.

Qué falta, a mano (Power BI Desktop de octubre de 2024 o posterior, por el formato PBIR del reporte):

1. Abrir `powerbi/presupuesto-vs-real/centinela.pbip`. Si Desktop pide credenciales para `raw.githubusercontent.com`,
   elegir **Anónimo**. Luego **Actualizar** para cargar los datos.
2. Armar los visuales de la tabla [Visuales sugeridos](#visuales-sugeridos) en la página
   "Resumen". Para la matriz, usar formato condicional sobre `Desviación %` con las reglas
   5% y 15% (las mismas del semáforo).
3. **Guardar.** Desktop escribe los visuales como archivos `visual.json` dentro de
   `centinela.Report/definition/pages/`: se hace commit de esos archivos como de cualquier
   otro cambio. `.pbi/cache.abf` y `localSettings.json` quedan fuera por el `.gitignore`.

La página [`reporte.html`](../reporte.html) recalcula el mismo reporte en el navegador y
muestra cada medida leyéndola desde `tables/desviacion.tmdl`, así que cualquier cambio de
DAX que se haga en Desktop y se guarde aparece ahí sin tocar el JavaScript.

> Especificación del modelo y las medidas DAX, documentadas antes de construir el
> `.pbix` en Power BI Desktop (paso manual — Claude Code no puede operar esa GUI, ver
> README.md § Modelo). Fuente de datos: `data/presupuesto.csv` y `data/real.csv`
> generados por `python data/generar_datos_sinteticos.py`.

## Modelo de datos

1. **Origen de datos**: importar `presupuesto.csv` y `real.csv` como dos consultas
   separadas en Power Query (Obtener datos → Texto/CSV).
2. **Combinar en una sola tabla `desviacion`** (Power Query → Combinar consultas →
   Combinación externa completa) uniendo por `anio` + `mes` + `centro_costo` +
   `componente`. Renombrar la columna `monto` de cada origen a `monto_presupuesto` y
   `monto_real` respectivamente. Reemplazar los valores nulos resultantes por `0` en
   ambas columnas (Transformar → Reemplazar valores) — esto replica en Power Query la
   misma "completitud de grilla" que aplica el motor Python: una celda sin dato real
   nunca desaparece de la agregación, se cuenta como `0` explícito. La columna
   `grupo_cuenta` (Ingresos / Costos / Gastos Operacionales) viene igual en ambos
   orígenes — quedarse con una sola copia tras la combinación, no duplicarla.
3. **Agregar una columna de fecha** en `desviacion` vía Power Query
   (`= #date([anio], [mes], 1)`) para poder relacionarla con el calendario.
4. **Tabla `Calendario`** (dimensión de fechas, para que funcione time intelligence):
   ```dax
   Calendario = CALENDAR(DATE(2026, 1, 1), DATE(2026, 12, 31))
   ```
   Marcarla explícitamente como tabla de fechas (Herramientas de tabla → Marcar como
   tabla de fechas).
5. **Relación**: `Calendario[Date]` (1) → `desviacion[fecha]` (*).

## Columna calculada

```dax
Estado Semáforo =
VAR pct = DIVIDE(desviacion[monto_real] - desviacion[monto_presupuesto], desviacion[monto_presupuesto])
RETURN
    SWITCH(
        TRUE(),
        desviacion[monto_presupuesto] = 0 && desviacion[monto_real] <> 0, "Crítica",
        // umbrales estrictos (>), no inclusivos — igual que el motor Python
        ABS(pct) > 0.15, "Crítica",
        ABS(pct) > 0.05, "Alerta",
        "OK"
    )
```

## Medidas

```dax
Monto Presupuesto = SUM(desviacion[monto_presupuesto])
```

```dax
Monto Real = SUM(desviacion[monto_real])
```

```dax
Desviación $ = [Monto Real] - [Monto Presupuesto]
```

```dax
Desviación % = DIVIDE([Desviación $], [Monto Presupuesto])
```

```dax
Líneas en Alerta = CALCULATE(COUNTROWS(desviacion), desviacion[Estado Semáforo] <> "OK")
```

```dax
Líneas en Crítica = CALCULATE(COUNTROWS(desviacion), desviacion[Estado Semáforo] = "Crítica")
```

```dax
% Líneas en Alerta = DIVIDE([Líneas en Alerta], COUNTROWS(desviacion))
```

```dax
% Cumplimiento = DIVIDE([Monto Real], [Monto Presupuesto])
```

```dax
// Subtotal de Estado de Resultados — el mismo Resultado Operacional que calcula
// `python -m src.main --estado-resultados`, expresado en DAX filtrando por grupo_cuenta.
Resultado Operacional =
CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Ingresos")
    - CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Costos")
    - CALCULATE([Monto Real], desviacion[grupo_cuenta] = "Gastos Operacionales")
```

## Visuales sugeridos

| Visual | Medidas | Corte |
|---|---|---|
| Tarjetas KPI | `Monto Presupuesto`, `Monto Real`, `Desviación %`, `% Cumplimiento` | (sin corte, totales del período) |
| Matriz condicional (formato por `Estado Semáforo`) | `Monto Presupuesto`, `Monto Real`, `Desviación %` | `centro_costo` × `componente` |
| Línea de tiempo | `Monto Presupuesto`, `Monto Real` | `Calendario[Mes]` |
| Barras apiladas | `Líneas en Alerta`, `Líneas en Crítica` | `centro_costo` |
| Tarjeta / cascada | `Resultado Operacional` | `grupo_cuenta` (Ingresos/Costos/Gastos Operacionales), estilo Estado de Resultados — ver [demo interactiva](https://h-e-sanchez.github.io/centinela/datos.html) |
| Tabla detalle | todas las columnas de `desviacion` + `Estado Semáforo` | filtrada a `Estado Semáforo <> "OK"` |

## Publicar como modelo público

GitHub Pages no puede alojar un reporte de Power BI: se publica en el Power BI Service con
**"Publicar en la Web"**, que entrega un `<iframe>` público sin login.

### Cuenta: tenant propio, nunca la del empleador

- Power BI **no acepta correos personales** (Gmail, Hotmail): exige un correo de trabajo o
  de institución educativa.
- **Nunca usar la cuenta de un empleador** para el portafolio: el reporte quedaría en su
  tenant y "Publicar en la Web" suele estar bloqueado por su administrador.
- Con un **dominio propio** (por ejemplo `cimad.net`), registrarse en
  [powerbi.com](https://powerbi.com) con ese correo crea un tenant nuevo. Si nadie lo
  administra, se toma el rol de administrador con el
  [proceso de *admin takeover*](https://learn.microsoft.com/en-us/entra/identity/users/domains-admin-takeover)
  (verificando el dominio con un registro TXT en el DNS).
- Según la [documentación de Publicar en la Web](https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-publish-to-web),
  publicar desde **Mi área de trabajo** requiere una licencia de Power BI (la gratuita
  sirve) y que el administrador habilite la opción del tenant; desde un área de trabajo
  compartida se necesita Pro o PPU.

### Pasos

1. **Habilitar la opción en el tenant** (como administrador): Portal de administración →
   Configuración del inquilino → Configuración de exportación y uso compartido →
   **Publicar en la web** → Habilitado.
2. **Publicar desde Desktop:** Inicio → Publicar → **Mi área de trabajo**.
3. En el Service, configurar la credencial del origen web como **Anónima** (Configuración
   del modelo semántico → Credenciales del origen de datos).
4. Abrir el reporte → Archivo → Insertar informe → **Publicar en la web (público)** →
   Crear código para insertar.
5. Copiar la URL del `src` del `<iframe>` (`https://app.powerbi.com/view?r=...`) y pegarla en
   `PBI_EMBED_URL`, al inicio de [`reporte.js`](../reporte.js). La misma URL se puede usar en
   el `<iframe>` de la sección Modelo de `index.html`, reemplazando el placeholder.

**⚠️ Nota de privacidad — leer antes de publicar cualquier reporte con esta función:**
"Publicar en la Web" hace el reporte **realmente público**: cualquier persona con el
link lo ve, sin iniciar sesión, puede acceder a los datos del modelo aunque el reporte no
los muestre, y Microsoft puede indexarlo. Es aceptable acá porque **todos los datos son
100% sintéticos** (generados por `data/generar_datos_sinteticos.py`). **Nunca usar
"Publicar en la Web" con datos reales de una empresa.**

## Pendiente (candidato, manual)

Los pasos 2 a 5 de la versión anterior (cargar CSV, Power Query, Calendario, DAX) ya están
en el código de `powerbi/presupuesto-vs-real/`. Queda:

1. Abrir `powerbi/presupuesto-vs-real/centinela.pbip` en Power BI Desktop y **Actualizar** (credencial anónima).
2. Armar el layout con los visuales sugeridos en la página "Resumen" y **guardar**; hacer
   commit de los `visual.json` que escribe Desktop.
3. Crear el tenant propio y publicar en la Web (sección anterior); pegar la URL en
   `PBI_EMBED_URL` de `reporte.js`.
4. Exportar 1 o 2 capturas del reporte para el README (opcional).
