# Glosario: Equidad salarial y bandas: por persona y por servicio

> Qué significa cada concepto del reporte y cómo se calcula. La primera parte lo explica con palabras; la segunda lista **todas** las medidas DAX del modelo, leídas del proyecto PBIP con `herramientas/generar_glosario.py`, así que coinciden con lo que calcula Power BI.

## Conceptos

### La estructura salarial

**Grado.** Un nivel de la estructura que agrupa cargos de responsabilidad parecida. Aquí hay siete grados: directivos; profesionales senior y profesionales; técnicos senior y técnicos; administrativos; y operarios o auxiliares.

**Banda salarial.** El rango de sueldo base que la empresa considera correcto para un grado:
- **mínimo:** lo menos que debería ganar alguien del grado (aquí, 80% del punto medio);
- **punto medio:** el sueldo de alguien plenamente competente en el cargo;
- **máximo:** el techo del grado (aquí, 120% del punto medio).

**Cargo.** La combinación de servicio y grado, por ejemplo «Técnico senior · UCI».

**Sueldo base equivalente a 44 horas.** El sueldo de una jornada parcial llevado a jornada completa. Sin esa conversión, quien trabaja 22 horas parecería mal pagado.

### Medir la posición en la banda

**Compa-ratio** = sueldo base / punto medio de la banda. 1,00 es el punto medio. Bajo 0,90 la persona está mal pagada para su grado; sobre 1,10, sobre lo que su grado justifica.

**Posición en banda** = (sueldo − mínimo) / (máximo − mínimo). 0% es el mínimo y 100% el máximo.

**Fuera de banda.** Bajo el mínimo o sobre el máximo. Lo primero es un riesgo de rotación y de equidad; lo segundo, de costo y de techo para el mérito.

### Equidad

**Equidad interna.** Que el mismo grado se pague parecido en toda la empresa. Se mide con la **dispersión entre servicios**: el coeficiente de variación del sueldo promedio del mismo grado entre servicios.

**Brecha de género cruda.** Diferencia entre la mediana de sueldo de hombres y de mujeres, sin controlar por nada. Mezcla dos cosas: si a las mujeres se les paga distinto y en qué cargos están.

**Brecha de género en el grado.** La misma diferencia, pero calculada dentro de cada banda (empresa × grado) y ponderada por su dotación. Compara cargos equivalentes, así que mide la parte que sí es una diferencia de pago. La Ley 20.348 establece el principio de igual remuneración para un mismo trabajo.

**Mediana.** El valor del medio al ordenar los sueldos. Se usa en vez del promedio porque unos pocos sueldos altos no la mueven.

### Mercado y costo de corregir

**Encuesta de mercado.** Lo que pagan otras empresas del sector por cargos equivalentes, resumido en percentiles: P25 (el cuarto que menos paga), P50 (la mitad) y P75.

**Posición vs. mercado** = sueldo base / P50 de mercado. Bajo 1,00, la empresa paga menos que la mitad del mercado: es más barata, pero se expone a perder gente.

**Costo de llevar al mínimo.** Lo que cuesta al mes subir a cada persona bajo el mínimo hasta el mínimo de su banda. Es la corrección indispensable.

**Costo de llevar al P25.** Lo que cuesta llevar a todos al menos al primer cuarto de su banda. Es una corrección más sana, que deja espacio para el mérito.

**Reajuste negociado.** Un aumento general del sueldo base, por ejemplo el que resulta de una negociación colectiva. El parámetro del reporte calcula su impacto anual sobre la masa salarial.

**Seguridad por fila.** Una regla del modelo que limita qué filas ve cada usuario. Aquí, cada jefatura ve solo su servicio.

## Medidas del modelo

El modelo tiene 40 medidas, agrupadas por carpeta como aparecen en el panel de datos de Power BI. Las de *portada* y *tarjetas* solo dan formato de texto a otras medidas.

### 0. Auxiliares

#### Color compa-ratio

Fondo del mapa de calor: rojo bajo 0,90, ámbar sobre 1,10, verde en la banda.

```dax
VAR c = [Compa-ratio]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(c), BLANK(),
        c < 0.9, "#F2D4CC",
        c > 1.1, "#F3E3C3",
        "#D9E8DA"
    )
```

*Tabla `remuneraciones`*

### 0. Portada

#### Portada compa-ratio

Compa-ratio para la tarjeta.

```dax
FORMAT([Compa-ratio], "0.00")
```

*Tabla `remuneraciones`*

#### Portada fuera de banda

Parte de la dotación fuera de banda, para la tarjeta.

```dax
FORMAT([% fuera de banda], "0.0%")
```

*Tabla `remuneraciones`*

#### Portada costo

Costo anual de llevar al mínimo, abreviado.

```dax
VAR v = [Costo anual de llevar al mínimo]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(v), BLANK(),
        ABS(v) >= 1000000000, FORMAT(v / 1000000000, "$ #,0.0") & " mil M",
        ABS(v) >= 1000000, FORMAT(v / 1000000, "$ #,0.0") & " M",
        FORMAT(v, "$ #,0")
    )
```

*Tabla `remuneraciones`*

#### Portada frase 1

Primera frase: el servicio que más paga sobre la banda y el que menos.

```dax
VAR mayor = TOPN(1, FILTER(VALUES(servicios[servicio]), NOT ISBLANK([Compa-ratio])), [Compa-ratio], DESC)
VAR menor = TOPN(1, FILTER(VALUES(servicios[servicio]), NOT ISBLANK([Compa-ratio])), [Compa-ratio], ASC)
VAR nMayor = MAXX(mayor, servicios[servicio])
VAR nMenor = MAXX(menor, servicios[servicio])
RETURN
    nMayor & " paga " & FORMAT(CALCULATE([Compa-ratio], servicios[servicio] = nMayor), "0.00")
        & " del punto medio; " & nMenor & ", " & FORMAT(CALCULATE([Compa-ratio], servicios[servicio] = nMenor), "0.00")
```

*Tabla `remuneraciones`*

#### Portada frase 2

Segunda frase: la brecha de género sin controlar y dentro del mismo grado.

```dax
"Brecha de género: " & FORMAT([Brecha de género cruda], "0.0%") & " cruda, "
    & FORMAT([Brecha de género en el grado], "0.0%") & " en el mismo grado"
```

*Tabla `remuneraciones`*

### 1. Estructura

#### Dotación

Personas con remuneración en el último mes del periodo.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        DISTINCTCOUNT(remuneraciones[id_persona]),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `#,##0`*

#### Masa salarial del mes

Sueldo base más variable del último mes del periodo.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        SUM(remuneraciones[sueldo_base]) + SUM(remuneraciones[variable]),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Masa salarial del periodo

Sueldo base más variable de todos los meses del periodo.

```dax
SUM(remuneraciones[sueldo_base]) + SUM(remuneraciones[variable])
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Sueldo base promedio

Sueldo base promedio equivalente a 44 horas, en el último mes.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        AVERAGE(remuneraciones[sueldo_base_44h]),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Sueldo base mediano

Mediana del sueldo base equivalente a 44 horas, en el último mes.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        MEDIAN(remuneraciones[sueldo_base_44h]),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

### 2. Bandas

#### Compa-ratio

Sueldo base (44 h) sobre el punto medio de la banda: 1,00 es el punto medio.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        DIVIDE(SUM(remuneraciones[sueldo_base_44h]), SUMX(remuneraciones, RELATED(bandas[punto_medio]))),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `0.00`*

#### Posición en banda %

0% es el mínimo de la banda y 100% el máximo; promedio de las personas.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        AVERAGEX(
            remuneraciones,
            DIVIDE(remuneraciones[sueldo_base_44h] - RELATED(bandas[minimo]), RELATED(bandas[maximo]) - RELATED(bandas[minimo]))
        ),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `0%`*

#### Bajo el mínimo

Personas con sueldo base (44 h) bajo el mínimo de su banda.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        COUNTROWS(FILTER(remuneraciones, remuneraciones[sueldo_base_44h] < RELATED(bandas[minimo]))),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `#,##0`*

#### Sobre el máximo

Personas con sueldo base (44 h) sobre el máximo de su banda.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        COUNTROWS(FILTER(remuneraciones, remuneraciones[sueldo_base_44h] > RELATED(bandas[maximo]))),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `#,##0`*

#### % bajo el mínimo

Parte de la dotación bajo el mínimo de su banda.

```dax
DIVIDE([Bajo el mínimo], [Dotación])
```

*Tabla `remuneraciones` · formato `0.0%`*

#### % fuera de banda

Parte de la dotación bajo el mínimo o sobre el máximo de su banda.

```dax
DIVIDE([Bajo el mínimo] + [Sobre el máximo], [Dotación])
```

*Tabla `remuneraciones` · formato `0.0%`*

#### Mínimo de banda

Mínimo de la banda (promedio si el filtro mezcla grados).

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        AVERAGEX(remuneraciones, RELATED(bandas[minimo])),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Punto medio de banda

Punto medio de la banda (promedio si el filtro mezcla grados).

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        AVERAGEX(remuneraciones, RELATED(bandas[punto_medio])),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Máximo de banda

Máximo de la banda (promedio si el filtro mezcla grados).

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        AVERAGEX(remuneraciones, RELATED(bandas[maximo])),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Alerta de banda

En la tabla por persona: si su sueldo está fuera de la banda.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        
            SWITCH(
                TRUE(),
                MAX(remuneraciones[sueldo_base_44h]) < MAXX(remuneraciones, RELATED(bandas[minimo])), "Bajo el mínimo",
                MAX(remuneraciones[sueldo_base_44h]) > MAXX(remuneraciones, RELATED(bandas[maximo])), "Sobre el máximo",
                BLANK()
            ),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones`*

### 3. Equidad

#### Dispersión entre servicios

Coeficiente de variación del sueldo promedio entre servicios: cuánto paga distinto cada servicio por el mismo grado.

```dax
VAR promedios =
    ADDCOLUMNS(VALUES(servicios[servicio]), "p", [Sueldo base promedio])
RETURN
    DIVIDE(STDEVX.P(FILTER(promedios, NOT ISBLANK([p])), [p]), AVERAGEX(FILTER(promedios, NOT ISBLANK([p])), [p]))
```

*Tabla `remuneraciones` · formato `0.0%`*

#### Mediana hombres

Mediana del sueldo base (44 h) de los hombres, en el último mes.

```dax
CALCULATE([Sueldo base mediano], personas[sexo] = "M")
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Mediana mujeres

Mediana del sueldo base (44 h) de las mujeres, en el último mes.

```dax
CALCULATE([Sueldo base mediano], personas[sexo] = "F")
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Brecha de género cruda

Diferencia de medianas sin controlar por grado. Positiva: las mujeres ganan menos.

```dax
DIVIDE([Mediana hombres] - [Mediana mujeres], [Mediana hombres])
```

*Tabla `remuneraciones` · formato `0.0%`*

#### Brecha de género en el grado

Brecha de medianas dentro de cada banda (empresa × grado), ponderada por su dotación. Compara cargos equivalentes.

```dax
VAR porGrado =
    ADDCOLUMNS(
        CALCULATETABLE(VALUES(remuneraciones[banda]), remuneraciones[fecha] = MAX(remuneraciones[fecha])),
        "h", [Mediana hombres],
        "m", [Mediana mujeres],
        "n", [Dotación]
    )
VAR comparables = FILTER(porGrado, NOT ISBLANK([h]) && NOT ISBLANK([m]))
RETURN DIVIDE(SUMX(comparables, DIVIDE([h] - [m], [h]) * [n]), SUMX(comparables, [n]))
```

*Tabla `remuneraciones` · formato `0.0%`*

### 4. Mercado

#### Mercado P50

P50 de la encuesta de mercado del grado (promedio si el filtro mezcla grados).

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        AVERAGEX(remuneraciones, RELATED(bandas[mercado_p50])),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Mercado P25

P25 de la encuesta de mercado del grado.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        AVERAGEX(remuneraciones, RELATED(bandas[mercado_p25])),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Mercado P75

P75 de la encuesta de mercado del grado.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        AVERAGEX(remuneraciones, RELATED(bandas[mercado_p75])),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Posición vs. mercado

Sueldo base (44 h) sobre el P50 de mercado: bajo 1,00 la empresa paga menos que el mercado.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        DIVIDE(SUM(remuneraciones[sueldo_base_44h]), SUMX(remuneraciones, RELATED(bandas[mercado_p50]))),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `0.00`*

### 5. Costo de corregir

#### Reajuste negociado %

Reajuste elegido en el segmentador; si no hay uno elegido, 4,5% (el IPC de 2026 en el modelo).

```dax
SELECTEDVALUE('Reajuste negociado'[Reajuste negociado], 0.045)
```

*Tabla `Reajuste negociado` · formato `0.0%`*

#### Costo de llevar al mínimo (mes)

Lo que cuesta al mes subir a cada persona bajo el mínimo hasta el mínimo de su banda.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        SUMX(
            remuneraciones,
            MAX(0, RELATED(bandas[minimo]) - remuneraciones[sueldo_base_44h]) * remuneraciones[jornada_horas] / 44
        ),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Costo de llevar al P25 (mes)

Lo que cuesta al mes llevar a todos al menos al primer cuarto de su banda.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        SUMX(
            remuneraciones,
            VAR p25 = RELATED(bandas[minimo]) + 0.25 * (RELATED(bandas[maximo]) - RELATED(bandas[minimo]))
            RETURN MAX(0, p25 - remuneraciones[sueldo_base_44h]) * remuneraciones[jornada_horas] / 44
        ),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Costo anual de llevar al mínimo

Costo de llevar al mínimo, por 12 meses.

```dax
[Costo de llevar al mínimo (mes)] * 12
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Costo anual de llevar al P25

Costo de llevar al P25 de la banda, por 12 meses.

```dax
[Costo de llevar al P25 (mes)] * 12
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Sueldo base del mes

Suma de sueldos base del último mes, sobre la que se aplica un reajuste.

```dax
VAR ultimo = MAX(remuneraciones[fecha])
RETURN
    CALCULATE(
        SUM(remuneraciones[sueldo_base]),
        remuneraciones[fecha] = ultimo
    )
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

#### Impacto anual del reajuste

Costo anual de un reajuste general sobre el sueldo base, según el parámetro elegido.

```dax
[Sueldo base del mes] * 12 * [Reajuste negociado %]
```

*Tabla `remuneraciones` · formato `\$ #,##0`*

### 7. Ayudas

#### Ayuda contexto

Servicio y grado del dato sobre el que está el mouse, para el tooltip.

```dax
VAR s = SELECTEDVALUE(servicios[servicio])
VAR g = SELECTEDVALUE(grados[nombre])
RETURN
    SWITCH(
        TRUE(),
        NOT ISBLANK(s) && NOT ISBLANK(g), s & " · " & g,
        NOT ISBLANK(s), s,
        NOT ISBLANK(g), g,
        "Toda la selección"
    )
```

*Tabla `remuneraciones`*

#### Ayuda compa-ratio

Explica el compa-ratio del dato con sus cifras: sueldo, punto medio y lectura.

```dax
VAR c = [Compa-ratio]
VAR s = [Sueldo base promedio]
VAR pm = [Punto medio de banda]
RETURN
    IF(
        NOT ISBLANK(c),
        "Sueldo base promedio de " & FORMAT(s, "$ #,0") & " frente a un punto medio de " & FORMAT(pm, "$ #,0") & ": "
            & FORMAT(ABS(c - 1), "0%") & IF(c >= 1, " sobre", " bajo") & " el punto medio. "
            & SWITCH(
                TRUE(),
                c < 0.9, "Bajo 0,90: mal pagado para su grado.",
                c > 1.1, "Sobre 1,10: paga por sobre su banda.",
                "Dentro del rango esperado (0,90 a 1,10)."
            )
    )
```

*Tabla `remuneraciones`*

#### Ayuda fuera de banda

Explica el % fuera de banda del dato: cuántas personas, en qué lado y cuánto cuesta corregir.

```dax
VAR b = COALESCE([Bajo el mínimo], 0)
VAR o = COALESCE([Sobre el máximo], 0)
VAR d = [Dotación]
RETURN
    IF(
        d > 0,
        FORMAT(b + o, "0") & " de " & FORMAT(d, "0") & " personas fuera de banda: " & FORMAT(b, "0") & " bajo el mínimo y "
            & FORMAT(o, "0") & " sobre el máximo. Subir a los de abajo hasta el mínimo cuesta "
            & FORMAT(COALESCE([Costo anual de llevar al mínimo], 0), "$ #,0") & " al año."
    )
```

*Tabla `remuneraciones`*
