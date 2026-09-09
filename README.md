# centinela

> Motor de seguimiento de desviación Presupuesto vs. Real por centro de costo, con
> alertas por umbral configurable — completamente en Python, sin dependencias externas.

## Diseño

- **Modelo tidy/long** (año, mes, centro de costo, componente, monto) para presupuesto
  y real por separado — trivial de pivotear en Excel, Power BI o pandas sin transformar
  nada primero.
- **Motor puro** (`src/motor.py`): cruza ambas tablas por clave compuesta, calcula
  desviación en $ y % por línea, y clasifica cada una en `ok` / `alerta` / `critica`
  según un umbral configurable — la comparación es estricta (`>`, no `>=`): una línea en
  exactamente el umbral no dispara.
- **Completitud de grilla**: ninguna celda se omite. Una línea presupuestada sin gasto
  real (o viceversa) se completa con monto `0` explícito — evita el sesgo de subconteo
  típico al agregar eventos poco frecuentes.
- **Parámetros separados de la lógica**: el umbral de alerta y el umbral crítico son
  argumentos del CLI, no valores fijos en el código — los "diales" que un Analista de
  Control de Gestión ajusta sin tocar una línea de Python.
- **Generador de datos sintéticos reproducible** (semilla fija): genera presupuesto y
  real con ruido controlado más un porcentaje de desviaciones grandes inyectadas a
  propósito, para que el motor tenga algo real que clasificar.
- **Cero dependencias de runtime** — solo librería estándar. Dev deps (`pytest`, `ruff`)
  separadas en `requirements-dev.txt`.

## Uso

```bash
pip install -r requirements.txt -r requirements-dev.txt

# Generar presupuesto.csv y real.csv sintéticos
python data/generar_datos_sinteticos.py

# Correr el motor con el umbral por defecto (alerta >5%, crítica >15%)
python -m src.main

# Umbral propio + exportar el detalle a CSV
python -m src.main --umbral 0.08 --umbral-critico 0.20 --salida reporte_desviacion.csv

# Tests
python -m pytest tests/ -q
```

## Modelo

Las mismas medidas, documentadas para reconstruirlas en Power BI (medidas DAX, modelo
de datos, visuales sugeridos) en [`docs/how-to-pbi.md`](docs/how-to-pbi.md). La
construcción del `.pbix` es un paso manual — Power BI Desktop es una aplicación de
escritorio, no algo que se pueda automatizar desde este repo. El modelo resultante se
publica con la función gratuita "Publicar en la Web" de Power BI (siempre sobre datos
sintéticos, nunca datos reales de un empleador) y queda incrustado en la demo.

## Demo

[`h-e-sanchez.github.io/centinela`](https://h-e-sanchez.github.io/centinela/) — página
estática (sin build), con un ejemplo de la salida del motor y el modelo de Power BI
incrustado una vez publicado.

## English

A dependency-free Python engine that reconciles a planned budget against actual spend
per cost center, computes the deviation in absolute and percentage terms, and flags each
line as ok / warning / critical against a configurable threshold. No cell is silently
dropped — a budgeted line with no matching actual (or vice versa) is filled with an
explicit zero, which avoids undercounting bias in sparse aggregations. The same logic is
modeled in Power BI (DAX measures documented in `docs/how-to-pbi.md`) and published
publicly via Power BI's "Publish to Web" feature — synthetic data only.
