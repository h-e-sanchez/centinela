## Conceptos

### Los documentos que se cruzan

**Orden de trabajo (OT).** El registro, en el sistema de mantenimiento (por ejemplo, SAP PM), de un trabajo sobre un activo: qué se hizo, cuándo, cuántas horas y si está cerrado. Hay dos clases:
- **preventiva:** sale del plan de mantención; tiene una fecha programada;
- **correctiva:** nace de una falla avisada; su fecha programada es la del aviso.

Una OT **cerrada** es trabajo terminado y respaldado. Una **abierta** todavía no debería cobrarse.

**Estado de pago (EP).** El cobro mensual que presenta el contratista. Cada **línea** dice qué servicio cobra, la cantidad, el precio unitario y qué OT lo respalda.

**Tarifa.** El precio unitario pactado en el contrato por cada servicio: la visita preventiva y la hora correctiva.

**Facturado** = suma de todas las líneas de EP. Incluye lo legítimo y lo que después se observa.

### Las cinco reglas de auditoría

Cada regla es una consulta SQL (`sql/reglas_auditoria.sql`) que cruza la línea del EP con su OT y con la tarifa. Una línea puede pasar todas las reglas o incumplir una.

| Regla | Qué detecta | Monto observado |
|---|---|---|
| **Cobro sin OT** | la línea no cita OT, o cita una que no existe en el sistema | la línea completa |
| **OT abierta** | se cobra trabajo no terminado: la OT sigue abierta o se cerró después del mes cobrado | la línea completa |
| **Cantidad sobre lo ejecutado** | se cobran más horas o visitas que las registradas en la OT, sobre una tolerancia de 5% | solo el exceso × precio |
| **Precio sobre tarifa** | el precio unitario supera el del contrato | solo el exceso × cantidad |
| **Doble cobro** | la misma OT y servicio ya se cobró antes | la línea completa |

**Por qué a veces se observa solo el exceso.** Si un contratista cobra 12 horas y la OT registra 8, las 8 horas se deben igual: lo discutible son las 4 de más. Por eso el monto observado mide lo que el control de verdad ahorra, no el total de líneas con problemas.

**Tolerancia de cantidad.** Hasta 5% sobre lo ejecutado no se observa, para no discutir redondeos. Es un parámetro del SQL, no una constante escondida.

**Doble cobro con `ROW_NUMBER`.** La consulta numera los cobros de cada OT y servicio en orden de periodo. El primero es legítimo; el segundo en adelante, doble cobro.

### Monto observado y resolución

**Observado** = suma del monto observado de todas las reglas. **% Observado** = observado ÷ facturado.

**El control.** Hasta junio de 2025 nadie cruzaba el EP con las OT. Desde el 1 de julio de 2025, lo observado se rechaza antes de pagar. La misma medida se lee distinto según la fecha:
- **Pagado de más:** observado antes del control. Ya salió de la caja; recuperarlo exige negociar con el contratista.
- **Monto evitado:** observado con control. Nunca se pagó.

**% observado antes y con control.** El control no solo rechaza: también **disuade**. Cuando los contratistas saben que cada línea se cruza con su OT, cobran menos de más. Por eso el % observado baja de ~9,5% a ~3,5%.

**Facturado sin observaciones** = facturado − observado: lo que pasa todas las reglas.

### Plan preventivo

**Preventivas programadas.** Mantenciones del plan con fecha en el periodo. La frecuencia depende de la **criticidad** del activo: A mensual, B bimestral y C trimestral.

**Cumplimiento preventivo %** = preventivas iniciadas a tiempo ÷ programadas. *A tiempo* significa a más tardar 7 días después de la fecha programada. Una preventiva atrasada no es solo un incumplimiento de contrato: aumenta la probabilidad de falla.

**Backlog (OT).** Preventivas vencidas y sin iniciar al cierre del periodo, incluidas las de meses anteriores. Es trabajo atrasado que se acumula.

**Backlog (semanas)** = backlog ÷ preventivas que el plan programa en una semana promedio. Dice cuántas semanas de trabajo preventivo están pendientes: 1 semana se recupera; 6 semanas indican que el contratista no da abasto.

**% Correctivo** = OT correctivas ÷ OT totales. Una operación sana es mayoritariamente preventiva; si lo correctivo crece, se está reparando lo que no se mantuvo.

### Confiabilidad de los activos

**Falla.** Cada OT correctiva.

**MTBF (tiempo medio entre fallas)** = días-activo de operación ÷ fallas. Con 10 activos durante 365 días y 40 fallas: 10 × 365 ÷ 40 ≈ 91 días entre fallas. Más alto es mejor. El reporte lo compara con el **MTBF objetivo** de diseño de cada tipo de activo.

**MTTR (tiempo medio de reparación)** = horas promedio de trabajo de las correctivas cerradas. Más bajo es mejor.

**Detención media** = horas promedio que el activo está detenido por falla: el **tiempo de respuesta** del contratista (desde el aviso hasta que llega) más la reparación. La diferencia entre detención y MTTR es la espera. Un contratista puede reparar rápido y aun así dejar el activo detenido medio día por llegar tarde.

**Disponibilidad %** = 1 − horas detenidas por falla ÷ horas totales de los activos. Un 98,7% parece alto, pero en una flota de 78 activos durante dos años son miles de horas sin operar.

### Contratistas

**Perfil limpio / riesgoso.** Es la etiqueta de la simulación: los riesgosos concentran las anomalías y también cumplen peor el plan y responden más lento. En datos reales esta columna no existiría. Lo que el reporte muestra es cómo el ranking los **revela** sin saberlo de antemano: los mismos nombres arriba en % observado y abajo en cumplimiento preventivo.

**Facturado por OT** = facturado ÷ OT del periodo: el costo medio de cada intervención, útil para comparar contratistas de la misma especialidad.
