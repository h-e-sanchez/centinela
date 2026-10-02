# Guía: Workforce · dotación, ausentismo y cobertura

> Reporte de People Analytics en Power BI que conecta tres preguntas que suelen vivir en planillas separadas: cuánta gente tenemos, cuánta falta y cuánto cuesta reemplazarla, en tres industrias. Todos los datos son sintéticos.

## Qué resuelve

Una gerencia de personas necesita responder cada mes:
- ¿la dotación es estable o estamos perdiendo gente, y por qué?
- ¿quién se ausenta, cuánto y con qué patrón?
- ¿cómo cubrimos esas horas y cuánto nos cuesta?

El reporte responde las tres para tres empresas distintas y permite compararlas. Además, pronostica el año siguiente con un método actuarial que no sobrerreacciona en las unidades chicas.

## Datos

Son las **mismas tres empresas ficticias del reporte Presupuesto vs. Real**, con sus sucursales como sedes. Suman unas 1.400 personas, simuladas día hábil a día hábil en 2025 y 2026:

| Industria | Empresa | Sedes (la piloto en negrita) | Unidades | Estamentos |
|---|---|---|---|---|
| Manufactura | Manufacturas Ejemplo S.A. | Santiago, **Concepción**, Antofagasta | producción, mantenimiento, calidad, bodega, ventas, administración | directivos, profesionales, administrativos, técnicos, operarios |
| Energía | Energía Ejemplo S.A. | **Zona Norte**, Zona Centro, Zona Sur | operación de centrales, mantenimiento, transmisión, despacho, comercial, gestión | directivos, profesionales, administrativos, técnicos, operarios |
| Salud | Red Asistencial Ejemplo S.A. | **Clínica Oriente**, Clínica Centro, Clínica Poniente | urgencia, hospitalización, pabellón, UCI, ambulatorio, apoyo | directivos, profesionales, administrativos, auxiliares, técnicos |

| Archivo | Grano | Para qué |
|---|---|---|
| `personas.csv` | persona (ID sintético, sin nombre) | industria, sede, dotación, ingresos, egresos y motivo |
| `episodios.csv` | episodio de ausencia | tipo, diagnóstico agrupado y duración |
| `ausencia_diaria.csv` | persona × día hábil ausente | días y horas perdidas por mes |
| `disponibilidad_mensual.csv` | persona × mes | días hábiles contratados: el denominador de la tasa |
| `cobertura_mensual.csv` | sede × unidad × estamento × mes | horas cubiertas con sobretiempo, pool interno o externo, y su costo |
| `pronostico.csv` | celda × mes de 2027 | credibilidad y simulación |
| `sedes.csv`, `unidades.csv`, `estamentos.csv` | dimensión | segmentadores compartidos; la sede trae su industria y si es piloto |

Se generan con `data/generar_workforce.py` (semilla fija) y se pueden reproducir.

### Calibración

Calibramos los datos con referencias públicas en orden de magnitud. No copiamos cifras.

| Indicador | En los datos | Referencia |
|---|---|---|
| Tasa global (sin licencias parentales) | Salud 6,1%, Manufactura 5,2%, Energía 3,2% | 10,8% en el sector Salud público ([Dipres, 2024](https://www.dipres.gob.cl/598/articles-355566_doc_pdf.pdf)); una clínica privada se ubica más abajo, y las plantillas industriales, más masculinas, todavía más |
| Orden de estamentos en Salud | técnicos > auxiliares > administrativos ≈ profesionales > directivos | técnicos 14,1%, directivos 3,2% (Dipres) |
| Operación frente a oficina | operarios y técnicos sobre profesionales y directivos en las tres empresas | — |
| Mujeres frente a hombres en Salud | 2,2 veces | 11,1% frente a 5,9% (Dipres) |
| Estacionalidad | pico en invierno (mayo a julio), mínimo en febrero | el mismo patrón en la Dipres |
| Principal diagnóstico | salud mental, ~32% de los días | ~28% en el NHS de Inglaterra; cerca de la mitad de las licencias en Chile entre salud mental y musculoesquelético (SUSESO 2025) |
| Episodios por persona al año | Salud 2,0, Manufactura 1,6, Energía 1,1 | 1,04 licencias por cotizante en el sistema general (SUSESO 2025) |
| Rotación anual | Manufactura ~20%, Salud ~14%, Energía ~10%, más alta el primer año | — |

**La historia de la cobertura:** desde julio de 2025 una sede de cada empresa cubre las ausencias con un **pool interno** en vez de sobretiempo: Concepción, Zona Norte y Clínica Oriente. Las otras dos sedes de cada empresa no cambian y sirven de **grupo de control**. Una hora de pool cuesta 1,1 veces el valor hora; una de sobretiempo, 1,5 veces; y una externa, 1,8 veces. El valor hora es el promedio de la unidad, porque quien cubre no siempre es del estamento ausente. La literatura sobre *float pools* en hospitales reporta ahorros de 30% a 50% frente a agencias externas.

## Modelo

- **Power Query** lee los CSV desde GitHub con una función compartida, `LeerCsv`, que convierte las celdas vacías en `null` (fechas de egreso) y tipa con cultura en-US.
  - `ausencia_diaria` trae el tipo y el diagnóstico del episodio con un *merge*. Así no hace falta relacionarla con `episodios`, lo que evita caminos ambiguos.
  - Edad y antigüedad se calculan en tramos al cierre de los datos o al egreso.
- **Copo de nieve con dimensiones compartidas:** `sedes` (con su industria), `unidades` y `estamentos` filtran a la vez a `personas` (y por ella a ausencias, episodios y disponibilidad), a `cobertura` y a `pronostico`. Un mismo segmentador sirve para todas las páginas.
- **Segmentadores dependientes:** los de unidad y estamento llevan un filtro de visual `Dotación > 0`, así que solo muestran las opciones de la empresa elegida, sin crear caminos de filtro bidireccionales.
- **`Calendario`** es una tabla calculada de 2025 a 2027, marcada como tabla de fechas. 2027 es el año del pronóstico, y las medidas de dotación no se extienden más allá de la fecha de corte.
- **Parámetro de campo «Comparar por»:** el visitante elige industria, sede, unidad, estamento, sexo, tramo de edad o antigüedad, y el mismo gráfico compara la tasa por esa dimensión.
- **Tabla desconectada `Tramos Bradford`:** alimenta el histograma del Factor Bradford.

## Medidas clave

```dax
Dotación =
VAR fin = [Fecha de análisis]
RETURN
    IF(
        MIN(Calendario[Date]) <= [Fecha de corte],
        COUNTROWS(
            FILTER(personas, personas[fecha_ingreso] <= fin && (ISBLANK(personas[fecha_egreso]) || personas[fecha_egreso] > fin))
        )
    )

Rotación 12m % =
VAR fin = [Fecha de análisis]
VAR egresos = COUNTROWS(FILTER(personas, personas[fecha_egreso] > EDATE(fin, -12) && personas[fecha_egreso] <= fin))
VAR dotacion = CALCULATE([Dotación promedio], DATESINPERIOD(Calendario[Date], fin, -12, MONTH))
RETURN IF(MIN(Calendario[Date]) <= [Fecha de corte], DIVIDE(egresos, dotacion))

Días perdidos = CALCULATE(COUNTROWS(ausencia_diaria), KEEPFILTERS(ausencia_diaria[tipo] <> "Licencia parental"))

Tasa global % = DIVIDE([Días perdidos], [Días disponibles])

Índice de frecuencia = DIVIDE([Episodios], [Dotación promedio]) * DIVIDE(12, [Meses en periodo])

Bradford 12m =
SUMX(
    VALUES(personas[id_persona]),
    VAR s = [Episodios 12m]
    VAR d = [Días 12m]
    RETURN s * s * d
)

Cambio costo/hora % = DIVIDE([Costo/hora con piloto], [Costo/hora antes del piloto]) - 1

Días P90 (banda) =
VAR e = [Días esperados]
RETURN IF(NOT ISBLANK(e), e + 1.2816 * SQRT(SUM(pronostico[varianza_dias])))
```

Algunas decisiones de diseño:
- **`KEEPFILTERS` en `Días perdidos`:** excluye las licencias parentales sin pisar el filtro del visitante. Si alguien filtra por tipo de ausencia, el filtro se respeta.
- **`Bradford 12m`:** recorre las personas y calcula S² × D para cada una. A nivel agregado, la suma de los Bradford individuales sí tiene sentido; S² × D sobre el total no lo tendría.
- **La banda del pronóstico:** suma las **varianzas** de 1.000 simulaciones por celda, no los percentiles. El P90 de una suma no es la suma de los P90.
- **`Ahorro del piloto`:** se calcula sobre las sedes marcadas como piloto (`sedes[piloto] = 1`), así que la misma medida sirve para las tres empresas.

## Pronóstico con credibilidad

La tasa de 2027 de cada celda (sede × unidad × estamento) mezcla dos fuentes:

**tasa con credibilidad = Z × tasa propia + (1 − Z) × tasa del estamento en la empresa**

El peso Z sale del modelo de **Bühlmann-Straub**: Z = w / (w + k). Aquí w son los días expuestos de la celda, y k compara la variación dentro de cada celda con la variación entre celdas de la misma empresa.
- Una unidad grande, con años de historia, confía en sus propios datos (Z cerca de 1).
- Dos directivos en una unidad chica casi no pesan (Z cerca de 0) y heredan la tasa de su estamento.

Así evitamos sobreestimar la tasa en segmentos con poca historia. Los días esperados se simulan como episodios (inicios de Poisson con duraciones observadas), no como días independientes, porque las ausencias vienen en rachas.

## Cómo leerlo

| Medida | Qué significa |
|---|---|
| **Tasa global** | Días perdidos sobre días disponibles, sin licencias parentales (criterio de la Dipres). Con Salud filtrada, la línea punteada del resumen es la referencia del sector Salud público (10,8%), como contexto, no como meta. |
| **Frecuencia** | Episodios por persona al año. |
| **Gravedad** | Días por episodio. Dos unidades con la misma tasa pueden tener historias opuestas: muchas ausencias cortas o pocas largas. |
| **Factor Bradford** | Sobre 200 suele gatillar una conversación de seguimiento. Lo calculamos sobre licencias comunes y accidentes de los 12 meses previos al cierre. |
| **Cambio del costo por hora** | Compara a la sede piloto con las otras dos sedes de su empresa en la misma ventana: es una **diferencia en diferencias** simple. |

El reporte abre en **Energía**, la misma industria con que abren los demás reportes de la vitrina. Valores de control para revisar al abrir el reporte:

| Indicador | Energía (al abrir) | Las tres empresas (sin filtro) |
|---|---|---|
| Dotación al 31-12-2026 | 368 | 1.400 |
| Rotación de 12 meses | 11,0% | 15,7% |
| Tasa global 2025-2026 | 3,21% | 5,06% |
| Personas con Bradford sobre 200 | 27 | 207 |
| Cambio del costo por hora en la sede piloto | Zona Norte −18,5%, frente a −1,3% en Zona Centro y +0,5% en Zona Sur | Concepción −16,9% y Clínica Oriente −19,7% |
| Días esperados en 2027 | 3.101 (P10-P90: 2.790 a 3.413) | 18.600 (P10-P90: 17.740 a 19.460) |

## Cómo abrirlo

- **`.pbix`:** doble clic con Power BI Desktop.
- **Proyecto PBIP:** descomprimir, abrir `workforce.pbip` y pulsar **Actualizar**. Los datos se leen desde GitHub; si pide credenciales, elegir Anónimo.
- **Solo los datos:** el zip de CSV o el Excel, con una hoja por tabla y un diccionario de columnas.

## Gobierno de datos

Los IDs son sintéticos y no hay nombres.
- **Datos reales:** la página de patrones individuales se restringiría con seguridad a nivel de fila (RLS) para que cada jefatura vea solo a su equipo, y el diagnóstico agrupado quedaría fuera del alcance de las jefaturas.
- **Lo que no publicamos:** ninguna cifra, regla ni parámetro de un empleador real.

## Qué demuestra

- People Analytics de punta a punta en tres industrias: dotación, rotación, ausentismo con los índices de la Dipres y costo de cobertura.
- Un pronóstico actuarial (credibilidad de Bühlmann-Straub y simulación).
- Evaluación de tres pilotos, cada uno con su grupo de control.
- DAX con patrones de fechas de ingreso y egreso, `KEEPFILTERS`, parámetros de campo, segmentadores filtrados por medida y formato condicional por medida.
- Un proyecto de Power BI versionado en Git, con tests que verifican que los datos cuenten la historia que el reporte promete.
