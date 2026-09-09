# Cómo construir el modelo en Power BI

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
| Tarjeta / cascada | `Resultado Operacional` | `grupo_cuenta` (Ingresos/Costos/Gastos Operacionales), estilo Estado de Resultados — ver [demo](https://h-e-sanchez.github.io/centinela/estado-resultados.html) |
| Tabla detalle | todas las columnas de `desviacion` + `Estado Semáforo` | filtrada a `Estado Semáforo <> "OK"` |

## Publicar como modelo público

Para que quede algo visible en `h-e-sanchez.github.io/centinela` (GitHub Pages no puede
alojar un `.pbix` — es un formato de escritorio), se publica el reporte con la función
gratuita de Power BI **"Publicar en la Web"**:

1. Subir el `.pbix` al Power BI Service (powerbi.com), a un workspace propio.
2. Abrir el reporte publicado → Archivo → **Publicar en la Web** (no "Compartir" — ese
   requiere que el destinatario tenga cuenta; "Publicar en la Web" genera un link
   público sin login).
3. Copiar el `<iframe>` que entrega el asistente y pegarlo en `index.html`, reemplazando
   el placeholder marcado `<!-- PENDIENTE: iframe de Power BI -->`.

**⚠️ Nota de privacidad — leer antes de publicar cualquier reporte con esta función:**
"Publicar en la Web" hace el reporte **realmente público**: cualquier persona con el
link lo ve, sin necesidad de iniciar sesión, y Microsoft puede indexarlo. Es aceptable
acá porque **todos los datos son 100% sintéticos** (generados por
`data/generar_datos_sinteticos.py`, sin ningún dato real de ningún empleador). **Nunca
usar "Publicar en la Web" con datos reales de una empresa** — para eso existe
"Compartir" (acceso restringido) o incrustación con Power BI Embedded.

## Pendiente (candidato, manual)

1. Generar los CSV: `python data/generar_datos_sinteticos.py`.
2. Abrir Power BI Desktop, cargar `presupuesto.csv` y `real.csv`.
3. Combinar en Power Query según el paso 2 de "Modelo de datos" arriba.
4. Crear la tabla `Calendario` y la relación.
5. Crear la columna calculada `Estado Semáforo` y las 9 medidas.
6. Armar el layout con los visuales sugeridos.
7. Publicar en la Web (ver sección anterior) y pegar el `<iframe>` en `index.html`.
8. Exportar 1-2 capturas de pantalla del reporte para el README (opcional).
