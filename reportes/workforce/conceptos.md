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
