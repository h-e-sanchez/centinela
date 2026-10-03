# Glosario: Workforce: dotación, ausentismo y cobertura

> Qué significa cada concepto del reporte y cómo se calcula. La primera parte lo explica con palabras; la segunda lista **todas** las medidas DAX del modelo, leídas del proyecto PBIP con `herramientas/generar_glosario.py`, así que coinciden con lo que calcula Power BI.

## Conceptos

### Dotación y rotación

**Dotación.** Personas contratadas en una fecha, el último día del periodo filtrado. Una persona cuenta si ingresó en o antes de esa fecha y no ha egresado (o egresó después). Es una foto, no un flujo: la dotación de un año es la del 31 de diciembre, no la suma de los meses. La medida nunca pasa de la **fecha de corte** (31-12-2026), porque lo posterior es pronóstico.

**Dotación promedio.** El promedio de la dotación de cierre de cada mes del periodo. Es el denominador correcto para tasas anuales: si la plantilla creció de 300 a 400 personas, dividir por 400 subestimaría la rotación.

**Contrataciones y egresos.** Flujos del periodo: personas que ingresan y personas que salen, por cualquier motivo (voluntario, involuntario o jubilación).

**Rotación 12 meses %** = egresos de los últimos 12 meses ÷ dotación promedio de esos 12 meses. Usa una ventana móvil para que el número de un mes cualquiera sea comparable con el de otro, sin depender de cuántos meses lleva el año.

**Rotación voluntaria 12 meses %.** Lo mismo, contando solo las renuncias: es la parte que la gestión de personas puede influir (clima, renta, jefaturas). Los despidos y jubilaciones responden a otras decisiones.

**Antigüedad promedio.** Años promedio en la empresa de quienes están contratados al cierre. Una rotación alta del primer año la hace bajar.

**Pirámide de edad.** La dotación por tramo de edad, con los hombres hacia la izquierda (la medida les cambia el signo) y las mujeres hacia la derecha.

### Ausentismo (índices de la Dipres)

La Dirección de Presupuestos (Dipres) mide el ausentismo del sector público con tres índices complementarios. El reporte usa los mismos, con el mismo criterio de **excluir las licencias parentales** (pre y posnatal), que no son ausentismo gestionable.

**Días perdidos.** Días hábiles (lunes a viernes) en que una persona contratada no trabajó por licencia médica, accidente u otra ausencia.

**Días disponibles.** Días hábiles en que cada persona estaba contratada: el denominador. Alguien que ingresó a mitad de mes aporta solo los días desde su ingreso.

**Tasa global %** = días perdidos ÷ días disponibles. Responde *¿qué parte del tiempo contratado se perdió?* Un 5% equivale a perder, en promedio, un día de cada veinte.

**Índice de frecuencia** = episodios ÷ dotación promedio, anualizado. Responde *¿cuántas veces al año se ausenta cada persona?* Un **episodio** es una ausencia continua (una licencia de 10 días es un episodio, no diez).

**Tasa de gravedad** = días promedio por episodio. Responde *¿cuánto duran las ausencias?*

Dos unidades con la misma tasa global pueden tener historias opuestas: muchas ausencias cortas (frecuencia alta y gravedad baja) o pocas largas (al revés). Se gestionan distinto: las cortas y repetidas apuntan a clima o carga; las largas, a salud.

**Referencia Dipres.** Con Salud filtrada, la línea punteada muestra la tasa del sector Salud público (10,8%). Es contexto, no meta: una clínica privada se ubica más abajo.

### Patrones individuales

**Factor Bradford** = S² × D, donde S es el número de episodios y D el total de días de una persona en los últimos 12 meses (solo licencias comunes y accidentes). Elevar los episodios al cuadrado castiga las ausencias **cortas y frecuentes**, que desordenan más la operación que una sola ausencia larga:
- 1 episodio de 10 días → 1² × 10 = **10**;
- 5 episodios de 2 días → 5² × 10 = **250**.

Mismos 10 días, Bradford 25 veces mayor. Sobre **200** suele gatillar una conversación de seguimiento; no es una sanción automática. El histograma agrupa a las personas en tramos: sin ausencias, 1 a 50, 51 a 200, 201 a 500 y más de 500.

### Cobertura de las ausencias

No toda hora ausente se reemplaza: en las unidades operativas (producción, urgencia, despacho) sí; en las administrativas, casi nunca. **Horas requeridas** son las horas ausentes que la unidad necesita cubrir.

Se cubren de tres formas, cada una con su costo sobre el valor hora:

| Modalidad | Costo | Por qué |
|---|---|---|
| Sobretiempo | ×1,5 | recargo legal de 50% de las horas extra |
| Pool interno | ×1,1 | personal propio de reemplazo, más un costo de coordinación |
| Externo | ×1,8 | empresa externa: margen y menor productividad inicial |

Lo que no se cubre son **horas no cubiertas**: carga que absorbe el resto del equipo.

**Costo por hora cubierta** = costo de cobertura ÷ horas cubiertas. Es la medida que el piloto busca bajar.

**% cubierto con sobretiempo.** La dependencia del sobretiempo: además de caro, cansa a los mismos equipos y puede generar más ausencias.

### El piloto y su grupo de control

Desde julio de 2025, una sede de cada empresa (Concepción, Zona Norte y Clínica Oriente) cubre con un **pool interno** en vez de sobretiempo. Las otras dos sedes siguen igual y son el **grupo de control**.

**Antes y con piloto.** El costo por hora de enero a junio de 2025 (antes) se compara con el de octubre de 2025 en adelante (con piloto). Julio a septiembre quedan fuera como **marcha blanca**, mientras el pool se arma.

**Cambio costo/hora %** = costo con piloto ÷ costo antes − 1, por sede. La lectura correcta compara la sede piloto con las de control: si la piloto baja 18% y las de control no se mueven, el cambio se debe al pool y no a algo que afectó a toda la empresa. Es una **diferencia en diferencias** simple.

**Ahorro del piloto** = (costo/hora antes − costo/hora con piloto) × horas cubiertas desde octubre de 2025, en las sedes piloto. Es lo que esas sedes habrían pagado de más sin el pool.

### Pronóstico 2027 con credibilidad

El pronóstico estima los días perdidos de 2027 por **celda** (sede × unidad × estamento).

**Años-persona.** La exposición de una celda: 10 personas durante 2 años son 20 años-persona. Es la cantidad de historia que respalda la tasa observada.

**Tasa observada 2025-2026 %.** La tasa propia de la celda. Con poca exposición es ruidosa: dos directivos que se enferman el mismo mes dan una tasa altísima que no se va a repetir.

**Credibilidad (Z).** Cuánto confiar en la historia propia, entre 0 y 1, según el modelo de **Bühlmann-Straub**: Z = w ÷ (w + k). Aquí w es la exposición de la celda y k mide cuánto varía una celda contra sí misma frente a cuánto varían las celdas entre sí. Mucha exposición → Z cerca de 1; poca → Z cerca de 0.

**Tasa con credibilidad** = Z × tasa propia + (1 − Z) × tasa del estamento en la empresa. Las celdas grandes conservan su tasa; las chicas se acercan a la de su estamento. Así se evita sobreestimar (o subestimar) en segmentos con poca historia.

**Días esperados, P10 y P90.** Los días esperados aplican la tasa con credibilidad a la dotación actual. La incertidumbre sale de simular 1.000 años de episodios por celda. P90 significa que solo 1 de cada 10 años debería superar ese valor.

Para el total de varias celdas, la medida suma las **varianzas** de las simulaciones y aplica la aproximación normal: P90 = esperado + 1,28 × √(suma de varianzas), y P10 con −1,28. No suma los P90 de cada celda: el P90 de un total es menor que esa suma, porque no todas las celdas tienen un mal año a la vez.

## Medidas del modelo

El modelo tiene 49 medidas, agrupadas por carpeta como aparecen en el panel de datos de Power BI. Las de *portada* y *tarjetas* solo dan formato de texto a otras medidas.

### 0. Auxiliares

#### Fecha de corte

Último día con datos reales (31-12-2026). Lo posterior es pronóstico.

```dax
EOMONTH(CALCULATE(MAX(disponibilidad_mensual[fecha]), REMOVEFILTERS()), 0)
```

*Tabla `personas` · formato `Short Date`*

#### Fecha de análisis

Fin del periodo filtrado, sin pasar de la fecha de corte.

```dax
VAR fin = MAX(Calendario[Date])
VAR corte = [Fecha de corte]
RETURN IF(fin > corte, corte, fin)
```

*Tabla `personas` · formato `Short Date`*

#### Meses en periodo

Meses con datos reales dentro del periodo filtrado (para anualizar).

```dax
VAR corte = [Fecha de corte]
RETURN COUNTROWS(FILTER(VALUES(Calendario[FinMes]), Calendario[FinMes] <= corte))
```

*Tabla `personas` · formato `0`*

### 0. Portada

#### Portada frase 1

Primera frase: tasa global y el mes de mayor ausentismo.

```dax
VAR meses = FILTER(VALUES(Calendario[Mes Año]), NOT ISBLANK([Tasa global %]))
VAR pico = MAXX(TOPN(1, meses, [Tasa global %], DESC), Calendario[Mes Año])
RETURN FORMAT([Tasa global %], "0.0%") & " de ausentismo · pico " & pico
```

*Tabla `personas`*

#### Portada frase 2

Segunda frase: el efecto del pool interno en la sede piloto.

```dax
VAR sede = CALCULATE(SELECTEDVALUE(sedes[sede]), sedes[piloto] = 1)
VAR cambio = FORMAT([Cambio costo/hora piloto %], "+0%;-0%")
RETURN IF(ISBLANK(sede), "Pilotos: " & cambio & " costo/hora", "Piloto " & sede & ": " & cambio & " costo/hora")
```

*Tabla `personas`*

### 1. Dotación

#### Dotación

Personas contratadas al cierre del periodo (patrón de fechas de ingreso y egreso).

```dax
VAR fin = [Fecha de análisis]
RETURN
    IF(
        MIN(Calendario[Date]) <= [Fecha de corte],
        COUNTROWS(
            FILTER(personas, personas[fecha_ingreso] <= fin && (ISBLANK(personas[fecha_egreso]) || personas[fecha_egreso] > fin))
        )
    )
```

*Tabla `personas` · formato `#,##0`*

#### Dotación promedio

Promedio de la dotación de cierre de cada mes del periodo.

```dax
VAR corte = [Fecha de corte]
RETURN
    AVERAGEX(
        FILTER(VALUES(Calendario[FinMes]), Calendario[FinMes] <= corte),
        VAR f = Calendario[FinMes]
        RETURN COUNTROWS(FILTER(personas, personas[fecha_ingreso] <= f && (ISBLANK(personas[fecha_egreso]) || personas[fecha_egreso] > f)))
    )
```

*Tabla `personas` · formato `#,##0.0`*

#### Dotación (pirámide)

Dotación con signo negativo para hombres: dibuja la pirámide de edad en un gráfico de barras.

```dax
VAR d = [Dotación]
RETURN IF(SELECTEDVALUE(personas[sexo]) = "Hombre", -d, d)
```

*Tabla `personas` · formato `#,##0;#,##0`*

#### Contrataciones

Personas que ingresan en el periodo.

```dax
VAR ini = MIN(Calendario[Date])
VAR fin = MAX(Calendario[Date])
RETURN COUNTROWS(FILTER(personas, personas[fecha_ingreso] >= ini && personas[fecha_ingreso] <= fin))
```

*Tabla `personas` · formato `#,##0`*

#### Egresos

Personas que egresan en el periodo, por cualquier motivo.

```dax
VAR ini = MIN(Calendario[Date])
VAR fin = MAX(Calendario[Date])
RETURN COUNTROWS(FILTER(personas, NOT ISBLANK(personas[fecha_egreso]) && personas[fecha_egreso] >= ini && personas[fecha_egreso] <= fin))
```

*Tabla `personas` · formato `#,##0`*

#### Rotación 12m %

Egresos de los últimos 12 meses sobre la dotación promedio de esos meses.

```dax
VAR fin = [Fecha de análisis]
VAR egresos = COUNTROWS(FILTER(personas, personas[fecha_egreso] > EDATE(fin, -12) && personas[fecha_egreso] <= fin))
VAR dotacion = CALCULATE([Dotación promedio], DATESINPERIOD(Calendario[Date], fin, -12, MONTH))
RETURN IF(MIN(Calendario[Date]) <= [Fecha de corte], DIVIDE(egresos, dotacion))
```

*Tabla `personas` · formato `0.0%`*

#### Rotación voluntaria 12m %

Solo renuncias: la rotación que la gestión de personas puede influir.

```dax
VAR fin = [Fecha de análisis]
VAR egresos =
    COUNTROWS(
        FILTER(personas, personas[fecha_egreso] > EDATE(fin, -12) && personas[fecha_egreso] <= fin && personas[motivo_egreso] = "Voluntario")
    )
VAR dotacion = CALCULATE([Dotación promedio], DATESINPERIOD(Calendario[Date], fin, -12, MONTH))
RETURN IF(MIN(Calendario[Date]) <= [Fecha de corte], DIVIDE(egresos, dotacion))
```

*Tabla `personas` · formato `0.0%`*

#### Antigüedad promedio

Años promedio en la empresa de quienes están contratados al cierre.

```dax
VAR fin = [Fecha de análisis]
RETURN
    AVERAGEX(
        FILTER(personas, personas[fecha_ingreso] <= fin && (ISBLANK(personas[fecha_egreso]) || personas[fecha_egreso] > fin)),
        DATEDIFF(personas[fecha_ingreso], fin, DAY) / 365.25
    )
```

*Tabla `personas` · formato `0.0`*

### 2. Ausentismo

#### Días perdidos

Días hábiles ausentes, sin licencias parentales (criterio de la Dipres).

```dax
CALCULATE(COUNTROWS(ausencia_diaria), KEEPFILTERS(ausencia_diaria[tipo] <> "Licencia parental"))
```

*Tabla `ausencia_diaria` · formato `#,##0`*

#### Días perdidos con parentales

Todos los días hábiles ausentes, incluidas las licencias parentales.

```dax
COUNTROWS(ausencia_diaria)
```

*Tabla `ausencia_diaria` · formato `#,##0`*

#### Horas perdidas

Horas de jornada perdidas, sin licencias parentales.

```dax
CALCULATE(SUM(ausencia_diaria[horas]), KEEPFILTERS(ausencia_diaria[tipo] <> "Licencia parental"))
```

*Tabla `ausencia_diaria` · formato `#,##0`*

#### Tasa global %

Días perdidos sobre días disponibles (tasa global de ausentismo de la Dipres).

```dax
DIVIDE([Días perdidos], [Días disponibles])
```

*Tabla `ausencia_diaria` · formato `0.0%`*

#### Referencia Dipres salud

Tasa global del sector Salud público en 2023 (Dipres, 2024): referencia de contexto, solo con Salud filtrada.

```dax
IF(NOT ISBLANK([Tasa global %]) && SELECTEDVALUE(sedes[industria]) = "Salud", 0.108)
```

*Tabla `ausencia_diaria` · formato `0.0%`*

#### Color tasa

Fondo del mapa de calor: más oscuro cuanto más alta la tasa.

```dax
VAR t = [Tasa global %]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(t), "#FFFFFF",
        t >= 0.10, "#D98C7A",
        t >= 0.075, "#E8C27E",
        t >= 0.05, "#F3E6C8",
        "#FBFAF7"
    )
```

*Tabla `ausencia_diaria`*

#### Días disponibles

Días hábiles en que cada persona estaba contratada.

```dax
SUM(disponibilidad_mensual[dias_habiles])
```

*Tabla `disponibilidad_mensual` · formato `#,##0`*

#### Episodios

Episodios de ausencia iniciados en el periodo, sin licencias parentales.

```dax
CALCULATE(COUNTROWS(episodios), KEEPFILTERS(episodios[tipo] <> "Licencia parental"))
```

*Tabla `episodios` · formato `#,##0`*

#### Índice de frecuencia

Episodios por persona al año (índice de frecuencia de la Dipres, anualizado).

```dax
DIVIDE([Episodios], [Dotación promedio]) * DIVIDE(12, [Meses en periodo])
```

*Tabla `episodios` · formato `0.00`*

#### Tasa de gravedad

Días hábiles promedio por episodio (tasa de gravedad de la Dipres).

```dax
CALCULATE(AVERAGE(episodios[dias_habiles]), KEEPFILTERS(episodios[tipo] <> "Licencia parental"))
```

*Tabla `episodios` · formato `0.0`*

### 3. Patrones individuales

#### Episodios 12m

Licencias comunes y accidentes iniciados en los 12 meses previos al cierre.

```dax
VAR fin = [Fecha de análisis]
RETURN
    CALCULATE(
        COUNTROWS(episodios),
        REMOVEFILTERS(Calendario),
        episodios[fecha_inicio] > EDATE(fin, -12),
        episodios[fecha_inicio] <= fin,
        KEEPFILTERS(episodios[tipo] IN {"Licencia común", "Accidente laboral"})
    )
```

*Tabla `episodios` · formato `0`*

#### Días 12m

Días hábiles de esos episodios.

```dax
VAR fin = [Fecha de análisis]
RETURN
    CALCULATE(
        SUM(episodios[dias_habiles]),
        REMOVEFILTERS(Calendario),
        episodios[fecha_inicio] > EDATE(fin, -12),
        episodios[fecha_inicio] <= fin,
        KEEPFILTERS(episodios[tipo] IN {"Licencia común", "Accidente laboral"})
    )
```

*Tabla `episodios` · formato `0`*

#### Bradford 12m

Factor Bradford S² × D por persona: castiga las ausencias cortas y frecuentes.

```dax
SUMX(
    VALUES(personas[id_persona]),
    VAR s = [Episodios 12m]
    VAR d = [Días 12m]
    RETURN s * s * d
)
```

*Tabla `episodios` · formato `#,##0`*

#### Personas por tramo Bradford

Personas contratadas al cierre en cada tramo del Factor Bradford.

```dax
VAR desde = SELECTEDVALUE('Tramos Bradford'[desde])
VAR hasta = SELECTEDVALUE('Tramos Bradford'[hasta])
VAR fin = [Fecha de análisis]
RETURN
    COUNTROWS(
        FILTER(
            FILTER(personas, personas[fecha_ingreso] <= fin && (ISBLANK(personas[fecha_egreso]) || personas[fecha_egreso] > fin)),
            VAR b = [Bradford 12m] + 0
            RETURN b >= desde && b <= hasta
        )
    )
```

*Tabla `episodios` · formato `#,##0`*

#### Personas con Bradford alto

Personas con Bradford sobre 200: el umbral habitual para una conversación de seguimiento.

```dax
VAR fin = [Fecha de análisis]
RETURN
    COUNTROWS(
        FILTER(FILTER(personas, personas[fecha_ingreso] <= fin && (ISBLANK(personas[fecha_egreso]) || personas[fecha_egreso] > fin)), [Bradford 12m] > 200)
    )
```

*Tabla `episodios` · formato `#,##0`*

### 4. Cobertura

#### Cambio costo/hora piloto %

Cambio del costo por hora cubierta en la sede piloto de la empresa filtrada.

```dax
CALCULATE([Cambio costo/hora %], sedes[piloto] = 1)
```

*Tabla `cobertura` · formato `0.0%;-0.0%`*

#### Horas requeridas

Horas ausentes que la unidad necesita cubrir.

```dax
SUM(cobertura[horas_requeridas])
```

*Tabla `cobertura` · formato `#,##0`*

#### Horas sobretiempo

Cubiertas con horas extra del propio equipo (recargo de 50%).

```dax
SUM(cobertura[horas_sobretiempo])
```

*Tabla `cobertura` · formato `#,##0`*

#### Horas pool

Cubiertas con el pool interno de reemplazos.

```dax
SUM(cobertura[horas_pool])
```

*Tabla `cobertura` · formato `#,##0`*

#### Horas externo

Cubiertas con personal de una empresa externa.

```dax
SUM(cobertura[horas_externo])
```

*Tabla `cobertura` · formato `#,##0`*

#### Horas no cubiertas

Horas que quedaron sin reemplazo: carga para el resto del equipo.

```dax
SUM(cobertura[horas_no_cubiertas])
```

*Tabla `cobertura` · formato `#,##0`*

#### Horas cubiertas

Horas reemplazadas por cualquier modalidad.

```dax
[Horas sobretiempo] + [Horas pool] + [Horas externo]
```

*Tabla `cobertura` · formato `#,##0`*

#### % cubierto con sobretiempo

Dependencia del sobretiempo: lo que el piloto busca bajar.

```dax
DIVIDE([Horas sobretiempo], [Horas requeridas])
```

*Tabla `cobertura` · formato `0.0%`*

#### Costo de cobertura

Costo de todas las horas reemplazadas.

```dax
SUMX(cobertura, cobertura[costo_sobretiempo] + cobertura[costo_pool] + cobertura[costo_externo])
```

*Tabla `cobertura` · formato `\$ #,##0`*

#### Costo por hora cubierta

Costo promedio de una hora reemplazada.

```dax
DIVIDE([Costo de cobertura], [Horas cubiertas])
```

*Tabla `cobertura` · formato `\$ #,##0`*

#### Costo/hora antes del piloto

Enero a junio de 2025, antes de que la sede piloto instale el pool.

```dax
CALCULATE([Costo por hora cubierta], DATESBETWEEN(Calendario[Date], DATE(2025, 1, 1), DATE(2025, 6, 30)))
```

*Tabla `cobertura` · formato `\$ #,##0`*

#### Costo/hora con piloto

Octubre de 2025 en adelante, con el pool ya instalado (tres meses de marcha blanca).

```dax
CALCULATE([Costo por hora cubierta], DATESBETWEEN(Calendario[Date], DATE(2025, 10, 1), DATE(2026, 12, 31)))
```

*Tabla `cobertura` · formato `\$ #,##0`*

#### Cambio costo/hora %

La sede piloto frente a las otras dos sedes de su empresa, que no cambiaron de modelo.

```dax
DIVIDE([Costo/hora con piloto], [Costo/hora antes del piloto]) - 1
```

*Tabla `cobertura` · formato `0.0%;-0.0%`*

#### Ahorro del piloto

Lo que las sedes piloto habrían pagado de más con su costo por hora anterior al pool.

```dax
CALCULATE(
    VAR horas = CALCULATE([Horas cubiertas], DATESBETWEEN(Calendario[Date], DATE(2025, 10, 1), DATE(2026, 12, 31)))
    RETURN ([Costo/hora antes del piloto] - [Costo/hora con piloto]) * horas,
    sedes[piloto] = 1
)
```

*Tabla `cobertura` · formato `\$ #,##0`*

### 5. Pronóstico

#### Días esperados

Días perdidos esperados en 2027 con la tasa ajustada por credibilidad y la dotación actual.

```dax
SUM(pronostico[dias_esperados])
```

*Tabla `pronostico` · formato `#,##0`*

#### Días P90 (banda)

Borde alto de la banda: las varianzas de la simulación se suman (celdas independientes); los percentiles no.

```dax
VAR e = [Días esperados]
RETURN IF(NOT ISBLANK(e), e + 1.2816 * SQRT(SUM(pronostico[varianza_dias])))
```

*Tabla `pronostico` · formato `#,##0`*

#### Días P10 (banda)

Borde bajo de la banda, con el mismo criterio.

```dax
VAR e = [Días esperados]
RETURN IF(NOT ISBLANK(e), MAX(0, e - 1.2816 * SQRT(SUM(pronostico[varianza_dias]))))
```

*Tabla `pronostico` · formato `#,##0`*

#### Tasa observada 2025-2026 %

Tasa propia de cada celda en los dos años de historia.

```dax
DIVIDE(SUMX(pronostico, pronostico[tasa_observada] * pronostico[dotacion] * pronostico[dias_habiles]), SUMX(pronostico, pronostico[dotacion] * pronostico[dias_habiles]))
```

*Tabla `pronostico` · formato `0.0%`*

#### Tasa con credibilidad %

Z × tasa propia + (1 − Z) × tasa del estamento en la empresa (Bühlmann-Straub).

```dax
DIVIDE(SUMX(pronostico, pronostico[tasa_credibilidad] * pronostico[dotacion] * pronostico[dias_habiles]), SUMX(pronostico, pronostico[dotacion] * pronostico[dias_habiles]))
```

*Tabla `pronostico` · formato `0.0%`*

#### Z credibilidad

Peso de la historia propia: cerca de 1 con mucha exposición, cerca de 0 con poca.

```dax
DIVIDE(SUMX(pronostico, pronostico[z_credibilidad] * pronostico[anios_persona]), SUM(pronostico[anios_persona]))
```

*Tabla `pronostico` · formato `0.00`*

#### Años-persona

Exposición de la celda en 2025-2026: la base de la credibilidad.

```dax
AVERAGEX(VALUES(pronostico[mes]), CALCULATE(SUM(pronostico[anios_persona])))
```

*Tabla `pronostico` · formato `#,##0.0`*
