# Reporte #6 · Equidad salarial y bandas: por persona y por servicio

> Especificación previa a la construcción. Define datos, páginas y medidas del reporte para
> que el generador, el modelo PBIP y la guía se construyan contra un mismo contrato.

**Estado:** especificado el 2026-10-05 · **Slug:** `compensaciones` · **Tema:** People Analytics · Compensaciones

## Qué resuelve

Una gerencia de personas necesita saber si paga de forma coherente, y no solo cuánto paga:

- ¿quién está fuera de su banda salarial, por debajo del mínimo o sobre el máximo?
- ¿hay **servicios o unidades** que pagan sistemáticamente distinto por el mismo cargo?
- ¿existe brecha entre mujeres y hombres en el mismo grado?
- ¿cuánto cuesta corregir, y en qué servicio conviene empezar?

La mirada **por servicio** es tan importante como la mirada por persona: una brecha
individual se corrige caso a caso, pero una brecha de servicio suele revelar una práctica
de contratación o de jefatura.

## Datos

Las **mismas personas del reporte #2 Workforce**, con sus mismos IDs, industria, sede,
unidad, estamento, sexo, edad y antigüedad. Así un mismo ID se puede seguir en dotación,
ausentismo y remuneración. El **servicio** es la unidad de `workforce` (en Salud: urgencia,
hospitalización, pabellón, UCI, ambulatorio y apoyo).

Generador previsto: `data/generar_compensaciones.py` (`SEMILLA = 42`). Lee
`data/workforce/personas.csv` y escribe `data/compensaciones/`.

| Archivo | Grano | Columnas principales |
|---|---|---|
| `cargos.csv` | cargo | `cargo, industria, estamento, grado, familia` |
| `bandas.csv` | grado × industria × año | `grado, industria, anio, minimo, punto_medio, maximo` |
| `asignacion_cargo.csv` | persona × periodo | `persona, cargo, desde, hasta` |
| `remuneraciones.csv` | persona × mes | `persona, anio, mes, sueldo_base, variable, jornada_horas` |
| `servicios.csv` | servicio | `servicio, industria, area` |

Los montos son **sintéticos y en orden de magnitud**: ninguna banda ni sueldo sale de un
empleador real.

## Páginas

| # | Página | Qué muestra |
|---|---|---|
| 1 | **Portada** | Título, pregunta del reporte, las tres empresas y cómo navegar |
| 2 | **Resumen** | Compa-ratio por empresa, % fuera de banda, brecha de género ajustada, costo de corregir y los tres hallazgos |
| 3 | Bandas y posición | Sueldo base vs. grado, con mínimo, punto medio y máximo superpuestos; distribución dentro de la banda |
| 4 | **Por persona** | Tabla con compa-ratio, posición en la banda y alerta de fuera de banda, ordenable y filtrable. Solo IDs sintéticos, sin nombres |
| 5 | **Por servicio** | Mapa de calor servicio × grado del compa-ratio promedio, % fuera de banda por servicio y dispersión del mismo cargo entre servicios |
| 6 | Brecha de género | Brecha dentro del mismo grado y cargo, por servicio, con el tamaño de cada grupo visible (sin conclusiones con grupos chicos) |
| 7 | Costo de corregir | Parámetro what-if para llevar a todos al mínimo o al P25 de su banda; costo mensual y anual por servicio y empresa |
| 8 | **Glosario** | Conceptos y medidas, generado desde el TMDL |

**Seguridad por fila (RLS):** un rol por servicio, para que cada jefatura vea solo su
servicio y el promedio de la empresa como referencia. Se documenta en la guía cómo probarlo
con "Ver como" en Desktop.

## Medidas DAX clave

- `Compa-ratio` = sueldo base ÷ punto medio de la banda.
- `Posición en banda` = (sueldo − mínimo) ÷ (máximo − mínimo).
- `% bajo el mínimo` y `% sobre el máximo`.
- `Brecha de género en el grado`: diferencia de la mediana del sueldo base entre mujeres y
  hombres del mismo grado, promediada con el peso de la dotación.
- `Dispersión del cargo entre servicios`: coeficiente de variación del sueldo base de un mismo
  cargo entre servicios.
- `Costo de corregir`, sobre el parámetro what-if (mínimo o P25).

## Historias sembradas en los datos

| Industria | Resultado | Historia |
|---|---|---|
| Salud | UCI con compa-ratio 1,12 | La UCI paga sobre la banda para retener técnicos, mientras ambulatorio queda bajo el punto medio por el mismo cargo |
| Energía | 9% bajo el mínimo | Las incorporaciones de 2026 en Zona Norte entraron bajo el mínimo de su banda: corregirlas cuesta poco y se concentra en un solo servicio |
| Manufactura | Brecha de 4% en el grado | La brecha de género cruda es grande por la composición de los estamentos, pero dentro del mismo grado se reduce a cerca de 4% |

## Habilidades para el catálogo

Bandas salariales y compa-ratio · Equidad interna por persona y por servicio · Brecha de
género ajustada por grado · Parámetros what-if · Seguridad por fila (RLS) · Modelo que
reutiliza las personas del reporte #2 · Proyecto PBIP versionado en Git

## Tests previstos (`tests/test_compensaciones.py`)

- Reproducibilidad con la misma semilla.
- **Mismas personas que `workforce`:** todo ID de `remuneraciones` existe en
  `personas.csv`, y solo hay remuneración en los meses en que la persona está vigente.
- Bandas válidas: `minimo < punto_medio < maximo` en cada grado y año.
- Calibración de las tres historias.
- RLS: la expresión de cada rol filtra solo su servicio (test sobre el TMDL).

## Pasos manuales en Power BI Desktop

Iguales a los de los reportes anteriores ([`../how-to-pbi.md`](../how-to-pbi.md)), más la
prueba de los roles con "Ver como". Al trabajar en el PBIP:
- cerrar Desktop antes de que se edite el proyecto como código;
- descartar los cambios solo de CRLF;
- dejar `activePageName` en `portada`;
- no usar `top` como nombre de `VAR`.
