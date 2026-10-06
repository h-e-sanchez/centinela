# Guía: Equidad salarial y bandas · por persona y por servicio

> Reporte de People Analytics en Power BI sobre la estructura salarial de tres empresas: quién está fuera de su banda, qué servicio paga distinto por el mismo grado, si hay brecha de género entre cargos equivalentes, cómo se compara con el mercado y cuánto cuesta corregir. Todos los datos son sintéticos.

## Qué resuelve

Una gerencia de personas sabe cuánto paga; lo difícil es saber si paga **de forma coherente**. El reporte responde cinco preguntas:
- ¿quién está bajo el mínimo o sobre el máximo de su banda?
- ¿hay **servicios** que pagan sistemáticamente distinto por el mismo grado?
- ¿existe brecha entre mujeres y hombres **en cargos equivalentes**?
- ¿la empresa paga sobre o bajo el mercado?
- ¿cuánto cuesta corregir, y cuánto un reajuste general?

La mirada **por servicio** importa tanto como la mirada **por persona**. Una brecha individual se corrige caso a caso, pero una brecha de servicio suele revelar una práctica de contratación o de jefatura.

## Datos

Son **las mismas personas del reporte Workforce**, con sus mismos IDs, sede, servicio, estamento, sexo, ingreso y egreso. Así, un mismo ID se puede seguir en dotación, ausentismo y renta. El servicio es la unidad de Workforce (en Salud: urgencia, hospitalización, pabellón, UCI, ambulatorio y apoyo).

| Archivo | Grano | Para qué |
|---|---|---|
| `remuneraciones.csv` | persona × mes (2025-2026) | sueldo base, su equivalente a 44 horas, variable y la banda que le corresponde |
| `bandas.csv` | empresa × grado × año | mínimo, punto medio y máximo, y el P25, P50 y P75 de la encuesta de mercado |
| `personas.csv` | persona | la ficha de Workforce más el cargo y el grado |
| `cargos.csv`, `grados.csv`, `servicios.csv`, `empresas.csv` | dimensión | estructura de cargos, siete grados, servicios y empresas |

Se generan con `data/generar_compensaciones.py` (semilla fija), que lee `data/workforce/personas.csv`.

**Cómo se arman:**
- **Grados:** siete grados por empresa: directivos; profesionales y técnicos, senior si llevan 6 años o más; administrativos; y operarios o auxiliares.
- **Bandas:** van de 80% a 120% del punto medio y suben 4,5% en 2026.
- **Sueldo:** es el punto medio por un compa-ratio individual, que crece con la antigüedad y tiene ruido.
- **Jornadas de 22 horas:** cobran en proporción. El compa-ratio se mide sobre el equivalente a 44 horas.

**Las tres prácticas que el reporte destapa:**
- **Salud:** la UCI paga sobre la banda para retener técnicos (compa-ratio 1,11), mientras ambulatorio queda en 0,90 por el mismo grado.
- **Energía:** contrata en Zona Norte bajo el mínimo de la banda desde mediados de 2024. Hoy el 8,6% de su dotación está bajo el mínimo, y corregirlo cuesta $49 M al año.
- **Manufactura:** la brecha cruda engaña. En el agregado, las mujeres parecen ganar **9,7% más**, porque los hombres se concentran en los grados de operarios. Dentro de la misma banda, ganan **4,3% menos**.

## Modelo

- **Power Query** lee los CSV desde GitHub con la misma función `LeerCsv` de los otros reportes, y traduce el sexo a «Mujer» y «Hombre».
- **Copo de nieve, sin caminos ambiguos:**
  - `empresas → servicios → personas → remuneraciones`;
  - `cargos → personas`;
  - `bandas`, `grados` y `Calendario` filtran `remuneraciones`.
- **Foto al último mes:** las medidas de estructura (dotación, compa-ratio, fuera de banda, brecha y costo) miran el último mes con remuneraciones del periodo filtrado. Con el segmentador de año se compara diciembre de 2025 con diciembre de 2026.
- **Parámetro what-if `Reajuste negociado`:** de 0% a 10%, para simular una negociación colectiva. Sin elegir, usa 4,5%.
- **Seguridad por fila:** un rol por servicio (`Jefatura UCI`, `Jefatura Ambulatorio`, etc.) filtra `servicios`, y con eso a sus personas y remuneraciones. Cada jefatura ve solo su servicio. Se prueba en Desktop con **Modelado → Ver como**. La versión publicada en la web no lleva los roles, porque Power BI no permite publicar en la web un modelo con seguridad por fila: muestra todos los servicios. Los roles están en el proyecto PBIP.

## Medidas clave

```dax
Compa-ratio =
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        DIVIDE(SUM(remuneraciones[sueldo_base_44h]), SUMX(remuneraciones, RELATED(bandas[punto_medio]))),
        remuneraciones[fecha] = ultimo
    )

% fuera de banda = DIVIDE([Bajo el mínimo] + [Sobre el máximo], [Dotación])

Brecha de género cruda = DIVIDE([Mediana hombres] - [Mediana mujeres], [Mediana hombres])

Posición vs. mercado =
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        DIVIDE(SUM(remuneraciones[sueldo_base_44h]), SUMX(remuneraciones, RELATED(bandas[mercado_p50]))),
        remuneraciones[fecha] = ultimo
    )

Costo anual de llevar al mínimo = [Costo de llevar al mínimo (mes)] * 12

Impacto anual del reajuste = [Sueldo base del mes] * 12 * [Reajuste negociado %]
```

Algunas decisiones de diseño:
- **Compa-ratio sobre el equivalente a 44 horas:** si no, una persona con media jornada aparecería bajo el mínimo sin estarlo.
- **Brecha en la banda, no en el total:** la brecha de género se calcula dentro de cada banda (empresa × grado) y se pondera por su dotación. Así compara cargos equivalentes y no mezcla la composición de los estamentos. La brecha cruda queda a la vista para mostrar cuánto engaña.
- **Medianas en vez de promedios:** unos pocos sueldos directivos mueven mucho el promedio.
- **Costo de corregir con dos metas:** el mínimo de la banda (lo indispensable) y el primer cuartil de la banda (una corrección más sana, que deja margen para el mérito; no es el P25 de mercado).

## Cómo leerlo

| Medida | Qué significa |
|---|---|
| **Compa-ratio** | 1,00 es el punto medio de la banda. Bajo 0,90, la persona o el servicio está mal pagado para su grado; sobre 1,10, sobre la banda. |
| **Posición en banda** | 0% es el mínimo y 100% el máximo. |
| **% fuera de banda** | Parte de la dotación bajo el mínimo o sobre el máximo. |
| **Dispersión entre servicios** | Cuánto varía el sueldo promedio del mismo grado entre servicios: sobre 5%, la equidad interna se resiente. |
| **Brecha de género en el grado** | Positiva: las mujeres ganan menos que los hombres en cargos equivalentes. |
| **Posición vs. mercado** | Sueldo sobre el P50 de mercado: bajo 1,00 la empresa paga menos que la mitad del mercado. |

**Ayudas de lectura:** cada visual tiene un ícono ⓘ en su encabezado con qué mide, cómo leerlo y un ejemplo con cifras del reporte. En el compa-ratio y el % fuera de banda, al pasar el mouse sobre un dato aparece un tooltip que explica ese dato con sus propias cifras. El botón **Glosario →** de cada página lleva a la página del glosario.

El reporte abre en **Energía**, la misma industria con que abren los demás reportes de la vitrina. Estos son los valores de control a diciembre de 2026, para revisar al abrir el reporte:

| Indicador | Energía (al abrir) | Las tres empresas (sin filtro) |
|---|---|---|
| Dotación | 370 | 1.419 |
| Masa salarial del mes | $688 M | $2.207 M |
| Compa-ratio | 0,97 | 0,97 |
| Fuera de banda | 9,2% (32 bajo el mínimo, 2 sobre el máximo) | 3,4% (38 bajo, 10 sobre) |
| Posición vs. mercado | 0,94 | 0,94 |
| Costo anual de llevar al mínimo / al primer cuartil | $48,9 M / $141,5 M | $52,4 M / $273,8 M |
| Brecha de género cruda / en el grado | 2,2% / 1,1% | −1,1% / 2,4% |
| Impacto anual de un reajuste de 4,5% | $348 M | $1.124 M |
| Servicio con mayor / menor compa-ratio | Transmisión 0,99 / Gestión corporativa 0,95 | UCI 1,11 / Ambulatorio 0,90 |

**Ejemplo de cálculo (Energía, diciembre de 2026).** La página «Costo de corregir» muestra esta operación con las cifras de cualquier selección:
- **Llevar al mínimo:** 32 personas están bajo el mínimo y les faltan en promedio $127.422 al mes. Son $4.077.500 al mes × 12 = **$48,9 M** al año.
- **Llevar al primer cuartil:** 65 personas están bajo el primer cuartil (las 32 anteriores y 33 que superan el mínimo). Les faltan en promedio $181.412 al mes: $11.791.750 al mes × 12 = **$141,5 M** al año. Cuesta casi el triple porque suma personas y porque la meta es más alta: el mínimo es 80% del punto medio y el primer cuartil, 90%.
- **Reajuste de 4,5%:** suma de sueldos base del mes, $644.083.000 × 12 × 4,5% = **$347,8 M** al año. Solo sueldo base, sin variable ni cargas.

## Cómo abrirlo

- **`.pbix`:** doble clic con Power BI Desktop.
- **Proyecto PBIP:** descomprimir, abrir `compensaciones.pbip` y pulsar **Actualizar**. Los datos se leen desde GitHub; si pide credenciales, elegir Anónimo.
- **Solo los datos:** el zip de CSV o el Excel, con una hoja por tabla y un diccionario de columnas.

## Gobierno de datos

Personas, bandas, sueldos y encuesta de mercado son ficticios.
- **Datos reales:** las remuneraciones individuales son datos personales sensibles. El reporte se publicaría con seguridad por fila y la página por persona solo para la gerencia de personas; el resto vería agregados por servicio.
- **Grupos chicos:** una brecha calculada con menos de 5 personas por sexo no permite conclusiones.
- **Lo que no publicamos:** ninguna banda, sueldo ni encuesta de un empleador real.

## Qué demuestra

- Compensaciones con criterio de control de gestión: bandas, compa-ratio, equidad interna por persona y por servicio, y el costo de cada corrección.
- Un análisis de brecha de género que distingue lo crudo de lo comparable.
- Competitividad frente a una encuesta de mercado y simulación de un reajuste negociado.
- Seguridad por fila por servicio y un modelo que reutiliza las personas del reporte Workforce, versionado como proyecto PBIP en Git.
