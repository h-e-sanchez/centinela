## Conceptos

### Cómo se trabaja en un Jira ágil

**Issue.** La unidad de trabajo en Jira. Hay cuatro tipos:
- **épica:** agrupa el trabajo de un tema grande; no lleva puntos;
- **historia:** una funcionalidad que se puede entregar;
- **tarea:** trabajo técnico sin valor visible para el usuario;
- **bug:** un defecto que hay que corregir.

**Puntos de historia.** La estimación relativa del esfuerzo de una issue, en una escala tipo Fibonacci (1, 2, 3, 5, 8). No son horas: sirven para comparar y para medir cuánto entrega un equipo.

**Sprint.** Un ciclo fijo de dos semanas. Al inicio, el equipo compromete lo que espera terminar; al final, se mide qué terminó.

**Estados.** Una issue avanza por por hacer, en curso, en revisión y hecho. Si a mitad del trabajo falta algo de otro equipo, pasa a **bloqueado** hasta que puede seguir.

### Medir la entrega

**Comprometido y completado.** Comprometido son los puntos que el equipo planificó al inicio del sprint (lo que arrastraba en curso más lo que empezó la primera semana). Completado es la parte de eso que llegó a «hecho» dentro del mismo sprint.

**Previsibilidad** = completado / comprometido. Mide si se puede confiar en lo que el equipo promete. Un equipo puede terminar mucho y aun así ser poco previsible.

**Velocidad.** Puntos terminados por sprint. Sirve para planificar el sprint siguiente; no sirve para comparar equipos, porque cada equipo estima con su propia vara.

**Throughput.** Issues terminadas por semana o por mes. Es la base del pronóstico, porque contar issues es más estable que sumar estimaciones.

### Medir el flujo

**Tiempo de ciclo.** Días corridos entre que una issue entra a «en curso» y llega a «hecho». Incluye la revisión y los bloqueos.

**Percentil 85 (P85).** El valor que no supera el 85% de los casos. En tiempos de ciclo es el plazo que conviene prometer: el promedio queda corto porque unas pocas issues bloqueadas tardan mucho.

**WIP (trabajo en curso).** Issues empezadas y no terminadas a una fecha, incluidas las bloqueadas. Mucho WIP con poco throughput es señal de trabajo atascado.

**Diagrama de flujo acumulado.** Para cada semana, cuántas issues hay en cada estado. Si la banda de «en curso» o de «bloqueado» se ensancha, el trabajo entra más rápido de lo que sale.

### Capacidad y colaboración

**Capacidad.** Horas de jornada disponibles: la dedicación de cada persona a cada equipo por 40 horas a la semana. Quien reparte la semana entre dos equipos aporta media capacidad a cada uno.

**Carga** = horas registradas en proyectos / capacidad. Bajo 100% hay días de soporte u holgura; sobre 100%, sobretiempo.

**Dependencia.** Una issue que necesita algo de otro equipo para terminar. Las horas que espera bloqueada se atribuyen al equipo del que esperaba (el **equipo que bloquea**).

**Traspaso.** El tiempo entre que el equipo que bloquea termina y la issue bloqueada vuelve a avanzar. Un traspaso lento (por ejemplo, desplegar solo en ventanas semanales) alarga los bloqueos aunque el otro equipo trabaje rápido.

### Pronóstico y presupuesto

**Monte Carlo.** Para cada proyecto abierto se simulan 10.000 futuros: cada semana se toma al azar el throughput de una de las últimas 12 semanas, hasta agotar las issues pendientes. La distribución de las semanas de término da las fechas P50, P85 y P95.

**Atraso P85.** Días entre la fecha P85 y la comprometida. Negativo es holgura. El semáforo es verde si no hay atraso, ámbar hasta 30 días y rojo sobre 30.

**Presupuesto y consumo.** El presupuesto son las horas planificadas por la tarifa de cada equipo. Consumo = costo acumulado (horas registradas × tarifa) / presupuesto. Si el consumo supera al avance, el proyecto gasta más rápido de lo que entrega.

**Alcance agregado.** Puntos que entran al proyecto después de aprobarlo. Es la causa más común de atraso que no se ve en la velocidad: el equipo rinde igual, pero la meta se aleja.
