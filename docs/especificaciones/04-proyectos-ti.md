# Reporte #4 · Proyectos tecnológicos: entrega, capacidad y colaboración entre equipos

> Especificación previa a la construcción. Define datos, páginas y medidas del reporte para
> que el generador, el modelo PBIP y la guía se construyan contra un mismo contrato.

**Estado:** construido el 2026-10-05 (pendiente Desktop y publicación) · **Slug:** `proyectos-ti` · **Tema:** Control de gestión · Proyectos TI

## Qué resuelve

Las tres empresas de la vitrina tienen una cartera de proyectos de tecnología que ejecutan
equipos compartidos, con un flujo ágil estilo Jira. Una oficina de proyectos o una gerencia
de TI necesita responder cada semana:

- ¿qué proyectos van a tiempo y dentro del presupuesto, y cuándo terminan de verdad?
- ¿qué equipo está sobrecargado y cuál tiene holgura?
- ¿dónde se traba el trabajo cuando pasa de un equipo a otro?

El reporte responde las tres con datos de flujo (estados con fecha y hora), no con
porcentajes de avance declarados a mano.

## Datos

Las **mismas tres empresas** de los reportes #1 y #2. Cada una tiene su área de TI con cinco
equipos (**Datos, Integraciones, Plataforma, Producto y QA**) y una cartera de 4 a 5
proyectos en 2025-2026:

| Empresa | Proyectos de ejemplo |
|---|---|
| Manufacturas Ejemplo S.A. | Migración de ERP, trazabilidad de lotes en planta, portal de distribuidores, mantenimiento predictivo |
| Energía Ejemplo S.A. | Telemetría de centrales, despacho en tiempo real, facturación de clientes libres, ciberseguridad OT |
| Red Asistencial Ejemplo S.A. | Ficha clínica electrónica, agenda en línea, integración con laboratorio, tablero de camas |

Generador previsto: `data/generar_proyectos_ti.py` (`SEMILLA = 42`, solo biblioteca estándar)
→ `data/proyectos-ti/`.

| Archivo | Grano | Columnas principales |
|---|---|---|
| `proyectos.csv` | proyecto | `proyecto, industria, nombre, sponsor_area, inicio, fin_comprometido, presupuesto_horas, presupuesto_monto` |
| `equipos.csv` | equipo × industria | `equipo, industria, capacidad_horas_semana` |
| `personas_ti.csv` | persona (ID sintético, sin nombre) | `persona_ti, industria, rol, tarifa_hora` |
| `asignaciones.csv` | persona × equipo × periodo | `persona_ti, equipo, desde, hasta, dedicacion` (una persona puede estar en dos equipos) |
| `sprints.csv` | sprint de 2 semanas | `sprint, industria, inicio, fin` |
| `issues.csv` | issue | `issue, proyecto, equipo, tipo (epica, historia, tarea, bug), epica_padre, puntos, sprint, creado` |
| `transiciones.csv` | cambio de estado | `issue, estado_desde, estado_hasta, fecha_hora` con estados `por_hacer → en_curso → en_revision → bloqueado → hecho` |
| `dependencias.csv` | par de issues | `issue_bloqueante, issue_bloqueado, creada, resuelta` (muchas cruzan equipos) |
| `worklogs.csv` | persona × issue × día | `persona_ti, issue, fecha, horas` |

Al construirlo sumamos cinco tablas que el modelo necesitaba:
- `empresas` (la dimensión de industria);
- `compromisos` (lo comprometido por sprint);
- `capacidad_semanal`;
- `flujo_semanal` (la foto para el diagrama de flujo acumulado);
- `pronostico_distribucion`.

El detalle está en la [guía del reporte](../../reportes/proyectos-ti/guia.md).

## Páginas

| # | Página | Qué muestra |
|---|---|---|
| 1 | **Portada** | Título, pregunta del reporte, las tres empresas y cómo navegar |
| 2 | **Resumen** | Semáforo de la cartera: avance en puntos, consumo de presupuesto, fecha de término P50/P85 frente a la comprometida y los tres hallazgos |
| 3 | Sprints y velocidad | Comprometido vs. completado por sprint, velocidad promedio y su variabilidad, burndown del sprint seleccionado |
| 4 | Flujo | Diagrama de flujo acumulado (CFD), tiempo de ciclo por percentil (dispersión), WIP por estado y antigüedad del trabajo en curso |
| 5 | Capacidad y carga | Horas registradas vs. capacidad por equipo y semana; personas con dedicación partida |
| 6 | Colaboración entre equipos | Matriz de dependencias equipo × equipo, horas en `bloqueado` por equipo que bloquea, traspasos por issue y tiempo de espera en cada traspaso |
| 7 | Pronóstico | Simulación de Monte Carlo sobre el throughput semanal histórico: distribución de la fecha de término por proyecto (P50, P85 y P95) |
| 8 | **Glosario** | Conceptos y medidas, generado desde el TMDL |

## Medidas DAX clave

- `Velocidad` (puntos completados por sprint) y `Previsibilidad` (completado ÷ comprometido).
- `Tiempo de ciclo P50` y `P85` (de `en_curso` a `hecho`), con `PERCENTILEX.INC`.
- `WIP` y `Antigüedad del WIP` al último día del periodo filtrado (o al corte).
- `Horas bloqueadas` y `% del tiempo de ciclo en bloqueo`.
- `Carga del equipo` = horas registradas ÷ capacidad, sobre la relación muchos a muchos de `asignaciones`.
- `Consumo de presupuesto` = horas × tarifa ÷ presupuesto, y `Costo por punto`.
- La simulación de Monte Carlo se precalcula en Python (`pronostico_termino.csv`); DAX solo
  lee percentiles. Así el modelo no depende de una aleatoriedad que Power BI recalcularía en
  cada interacción.

## Historias sembradas en los datos

| Industria | Resultado | Historia |
|---|---|---|
| Salud | Ficha clínica +75 días | Crece el alcance a mitad de proyecto: suben los puntos comprometidos y la fecha P85 se aleja, aunque la velocidad se mantiene |
| Energía | 39% del bloqueo | Integraciones bloquea a los demás equipos: concentra la mayor parte de las horas en `bloqueado` y es el cuello de botella de la cartera |
| Manufactura | Previsibilidad 90% | Migración de ERP con flujo estable: tiempo de ciclo acotado y P50 dentro de la fecha comprometida |

Los porcentajes son metas de calibración del generador; los tests verifican que los datos
las cumplan.

## Habilidades para el catálogo

Métricas de flujo ágil (velocidad, tiempo de ciclo, WIP) · Relación muchos a muchos ·
Percentiles en DAX · Pronóstico de Monte Carlo · Análisis de dependencias entre equipos ·
Proyecto PBIP versionado en Git

## Tests previstos (`tests/test_proyectos_ti.py`)

- Reproducibilidad: dos corridas con la misma semilla dan archivos idénticos.
- Integridad: cada transición parte del estado en que quedó la anterior; ninguna issue
  `hecho` vuelve a abrirse sin una transición explícita.
- Coherencia: las horas de `worklogs` caen solo en días en que la persona está asignada a
  ese equipo.
- Calibración: las tres historias se cumplen dentro de una tolerancia.
- Monte Carlo: P50 ≤ P85 ≤ P95 en todos los proyectos.

## Pasos manuales en Power BI Desktop

Iguales a los de los reportes anteriores ([`../how-to-pbi.md`](../how-to-pbi.md)). Al
trabajar en el PBIP:
- cerrar Desktop antes de que se edite el proyecto como código;
- descartar los cambios solo de CRLF (`git diff --ignore-cr-at-eol`);
- dejar `activePageName` en `portada`;
- no usar `top` como nombre de `VAR`, que es palabra reservada.
