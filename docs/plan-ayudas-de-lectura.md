# Plan: ayudas de lectura en los reportes de la vitrina

> Que cualquier visitante entienda cada cifra sin salir del reporte: qué mide, cómo se lee, de dónde sale el número y dónde está la definición.

**Estado:** planificado el 2026-10-06. El piloto está en el #6 Compensaciones (PR #45 y #48); los otros siete reportes no tienen ayudas.

## 1. Qué probó el piloto

Probamos en el #6 cuatro piezas, y las cuatro funcionaron en Desktop:

| Pieza | Qué hace | Cómo se arma en PBIR |
|---|---|---|
| **Ícono ⓘ** | Al pasar el mouse por el encabezado del visual: qué mide, cómo leerlo, un ejemplo con cifras del reporte y el término del glosario | `visualContainerObjects.visualHeaderTooltip.text` + `visualHeader.showTooltipButton` |
| **Tooltip con cifras** | Al pasar el mouse sobre un dato: una ficha de 320 × 240 que explica ese dato con sus propias cifras | Página `type: Tooltip`, `visibility: HiddenInViewMode`, `pageBinding` Tooltip; en el visual, `visualTooltip` con `type 'Canvas'` y `section` |
| **Botón «Glosario →»** | Lleva a la página del glosario del reporte. En Desktop se activa con Ctrl + clic; en la web, con clic normal | `actionButton` con `visualLink` de tipo `PageNavigation` |
| **Ficha «Cómo se calcula»** | Muestra la operación de una cifra con los números de la selección: personas, promedio y multiplicación | Tarjeta clásica (`card`) con ajuste de línea y una medida de texto |

Las medidas de texto viven en la carpeta **«7. Ayudas»** de cada modelo, con su descripción `///`. Por eso entran solas al glosario.

**Lecciones del piloto y de las correcciones del mismo día,** que ya tienen test:
- `filterConfig` va en el contenedor del `visual.json`, nunca dentro de `visual` (PR #41).
- La columna de un parámetro what-if no lleva `isNameInferred` con `sourceColumn: [Value]`, porque Desktop la renombra a «Value» (PR #42).
- Un segmentador what-if abre en el primer valor de la serie si no guarda uno. Hay que guardar el valor por defecto y generar la serie con enteros divididos (PR #45 y #46).
- Un visual que usa un parámetro de campo declara `fieldParameters` (PR #47).
- Una etiqueta no puede significar dos cosas: «P25» de la banda pasó a «primer cuartil» (PR #45).
- `tests/test_esquemas_pbir.py` valida cada archivo contra el esquema oficial. Se corre **antes** de pedir que se abra Desktop.

## 2. Reglas de redacción

Cada texto ⓘ tiene cuatro partes, en este orden, y no pasa de unos 300 caracteres:

1. **Qué mide**, con la fórmula en palabras: «Compa-ratio = sueldo base (44 h) / punto medio de la banda».
2. **Cómo leerlo:** el umbral o la dirección buena. «Bajo 0,90, mal pagado para su grado».
3. **Un ejemplo con una cifra verificada:** de la tabla de valores de control de la guía, o recalculada desde los CSV antes de escribirla. Por defecto se usa Energía, la industria con que abren los reportes, salvo que la historia del reporte esté en otra.
4. **El término del glosario:** «Glosario: Compa-ratio», con el nombre exacto que usa `conceptos.md`.

Los tooltips y las fichas usan medidas de texto. Esas medidas leen la selección (`SELECTEDVALUE`), toleran vacíos (`COALESCE`) y dicen «Toda la selección» cuando no hay un dato puntual.

## 3. Cómo se aplica según el estado del reporte

| Grupo | Reportes | Método |
|---|---|---|
| **Construidos por código** | #5 Capital de trabajo, #6 Compensaciones, #7 Pricing, #8 EEFF | El constructor agrega las ayudas. Antes de cada cambio se verifica que el constructor reproduce `main` sin diferencias |
| **Guardados por Desktop** | #1 Presupuesto vs. Real, #2 Workforce, #3 Contratistas, #4 Proyectos TI | Se edita el JSON con un script idempotente, sin regenerar, para no pisar lo que Desktop guardó |

**Propuesta para la tanda 0:** llevar el mecanismo al repo, para que no viva en un scratchpad.
- `reportes/<slug>/ayudas.json`: los textos de cada visual, con la página y la clave del visual (o su título), el texto ⓘ y la página de tooltip si tiene. Los textos quedan versionados como datos y se revisan en el PR.
- `herramientas/ayudas_pbir.py`: lee ese archivo y lo aplica a los `visual.json` (ⓘ, tooltip y botón). Es idempotente y sirve para los dos grupos.
- Un test de cobertura: todo visual de datos (no texto, segmentador ni botón) tiene ⓘ, y todo texto ⓘ nombra un término que existe en el glosario del reporte.

## 4. Inventario y propuesta por reporte

Hay 225 visuales de datos en los siete reportes pendientes, más los 27 del #6, que ya tiene ⓘ en 17.

| # | Reporte | Visuales de datos | Estado web | Tooltips con cifras (propuesta) | Fichas «Cómo se calcula» (propuesta) |
|---|---|---|---|---|---|
| 1 | Presupuesto vs. Real | 30 en 8 páginas | Publicado | Desviación ($ y %, con su semáforo); Forecast 3+9 frente al presupuesto | Resumen: desviación del resultado operacional |
| 2 | Workforce | 34 en 7 páginas | Publicado | Tasa global de ausentismo (días perdidos / disponibles); rotación de 12 meses | Cobertura y costo: ahorro del piloto. Pronóstico 2027: tasa con credibilidad = Z × observada + (1 − Z) × referencia |
| 3 | Contratistas | 24 en 6 páginas | Publicado | % observado por regla de auditoría; cumplimiento preventivo; MTBF y MTTR | Auditoría de EP: monto observado y su regla |
| 4 | Proyectos TI | 29 en 7 páginas | Publicado | Previsibilidad del sprint; tiempo de ciclo P85; atraso P85 | Pronóstico: cómo sale la fecha P85 de la simulación de Monte Carlo |
| 5 | Capital de trabajo | 27 en 7 páginas | Publicado | DSO, DIO y DPO con su ventana; cartera por tramo de antigüedad | Ciclo de caja: DSO + DIO − DPO. Flujo a 13 semanas: saldo final = inicial + cobros − pagos |
| 6 | Compensaciones | 27 en 8 páginas | Publicado | Hecho: compa-ratio y fuera de banda | Hecho: costo de corregir y reajuste |
| 7 | Pricing y márgenes | 27 en 8 páginas | Sin publicar | Margen de contribución % por canal; descuento fuera de política | Cascada: de lista a margen. Simulador: ingreso simulado con elasticidad |
| 8 | Del libro diario a los EEFF | 27 en 9 páginas | Sin publicar | Liquidez, endeudamiento, ROE y días de cobro, inventario y pago | EBITDA = resultado operacional + depreciación; flujo indirecto desde la utilidad |

Las fórmulas de la tabla son la propuesta. Al implementar se copian del TMDL de cada reporte, no de esta tabla.

## 5. Tandas

| Tanda | Alcance | PR | Esfuerzo de Claude Code | Esfuerzo del candidato |
|---|---|---|---|---|
| **0** | Script `ayudas_pbir.py`, `ayudas.json` del #6 (migrado desde el constructor) y test de cobertura | 1 | 1 sesión | Revisar el PR |
| **1** | Ícono ⓘ y botón «Glosario →» en los siete reportes | 1 por grupo: #1 a #4 y #5, #7 y #8 | 1 sesión | Abrir cada reporte en Desktop y volver a publicar los publicados |
| **2** | Tooltips con cifras y fichas «Cómo se calcula» | 1 por reporte, empezando por los publicados: #5, #1, #2, #3, #4, y después #7 y #8 | 1 sesión cada dos reportes | Revisar en Desktop cada PR y volver a publicar |

El #7 y el #8 conviene publicarlos **después** de la tanda 1, para publicarlos una sola vez.

## 6. Verificación de cada PR

- [ ] `pytest` en verde, incluidos `test_esquemas_pbir.py` y el test de cobertura de ayudas.
- [ ] Cada cifra de un texto ⓘ o de un ejemplo de la guía está recalculada desde los CSV, o sale de la tabla de valores de control de la guía.
- [ ] El constructor reproduce `main` antes del cambio (grupo por código), o el script solo toca las claves de ayuda (grupo Desktop): `git diff --ignore-cr-at-eol` lo confirma.
- [ ] Revisión en Desktop: ⓘ de un visual, tooltip sobre un dato, botón Glosario con Ctrl + clic y fichas con un filtro aplicado.
- [ ] Se vuelve a publicar el reporte, si ya estaba en la web. El #6 se publica desde la copia sin roles.

## 7. Riesgos y decisiones abiertas

- **¿Se ve el ícono ⓘ en «Publicar en la web»?** El encabezado de un visual aparece al pasar el mouse en la web. Se confirma con el primer reporte de la tanda 1 antes de seguir.
- **Densidad:** con siete visuales por página, los ⓘ no deben repetir la bajada de la página. Si una página ya explica una medida, el ⓘ aporta el ejemplo y no la definición.
- **Pantallas chicas:** las fichas «Cómo se calcula» ocupan alto. Solo se ponen donde la cifra no se entiende sin la operación.
- **Decisión del candidato:** ¿un PR por grupo en la tanda 1, o uno por reporte para revisar de a poco?
- **Decisión del candidato:** ¿fichas «Cómo se calcula» solo en las páginas propuestas, o también en el resumen de cada reporte?
