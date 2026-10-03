-- Reglas de auditoría de los estados de pago (EP) de contratistas.
--
-- Cada línea de EP se cruza con la orden de trabajo (OT) que dice cobrar y con la tarifa del
-- contrato. Una CTE por regla; el resultado es una fila por línea y regla incumplida, con el
-- monto que la regla deja observado. Lo ejecuta sql/auditar.py sobre sqlite3 (stdlib).
--
-- Escrito en SQL estándar (CTE, LEFT JOIN, CASE, SUBSTR, ROW_NUMBER) para que se pueda llevar a
-- otro motor con cambios mínimos; solo lo verificamos en SQLite.
--
-- Tablas de entrada: estados_pago, ordenes_trabajo, tarifas (columnas en data/contratistas/).

WITH parametros AS (
    SELECT
        0.05         AS tolerancia_cantidad,  -- 5% sobre lo ejecutado no se observa
        '2025-07-01' AS inicio_control        -- desde aquí lo observado se rechaza antes de pagar
),

lineas AS (
    SELECT
        ep.id_linea,
        ep.periodo,
        ep.id_contratista,
        ep.sede,
        ep.id_ot,
        ep.servicio,
        ep.cantidad_cobrada,
        ep.precio_cobrado,
        ep.monto,
        ot.estado,
        ot.fecha_cierre,
        ot.cantidad_ejecutada,
        t.precio_unitario AS tarifa
    FROM estados_pago AS ep
    LEFT JOIN ordenes_trabajo AS ot ON ot.id_ot = ep.id_ot
    LEFT JOIN tarifas AS t ON t.id_contratista = ep.id_contratista AND t.servicio = ep.servicio
),

-- 1. Cobro sin respaldo: la línea no cita OT o cita una que no existe.
sin_ot AS (
    SELECT id_linea, 'sin_ot' AS regla, monto AS monto_observado
    FROM lineas
    WHERE estado IS NULL
),

-- 2. Cobro anticipado: la OT sigue abierta o se cerró después del mes que se cobra.
ot_abierta AS (
    SELECT id_linea, 'ot_abierta' AS regla, monto AS monto_observado
    FROM lineas
    WHERE estado IS NOT NULL
      AND (estado <> 'Cerrada' OR SUBSTR(fecha_cierre, 1, 7) > SUBSTR(periodo, 1, 7))
),

-- 3. Cantidad inflada: se cobra más de lo que la OT registra como ejecutado.
sobre_cantidad AS (
    SELECT l.id_linea, 'sobre_cantidad' AS regla,
           ROUND((l.cantidad_cobrada - l.cantidad_ejecutada) * l.precio_cobrado) AS monto_observado
    FROM lineas AS l
    CROSS JOIN parametros AS p
    WHERE l.estado = 'Cerrada'
      AND l.cantidad_cobrada > l.cantidad_ejecutada * (1 + p.tolerancia_cantidad)
),

-- 4. Precio fuera de contrato: el precio unitario supera la tarifa pactada.
sobre_precio AS (
    SELECT id_linea, 'sobre_precio' AS regla,
           ROUND((precio_cobrado - tarifa) * cantidad_cobrada) AS monto_observado
    FROM lineas
    WHERE tarifa IS NOT NULL AND precio_cobrado > tarifa
),

-- 5. Doble cobro: la misma OT y servicio ya se cobró en una línea anterior.
duplicada AS (
    SELECT id_linea, 'duplicada' AS regla, monto AS monto_observado
    FROM (
        SELECT id_linea, monto,
               ROW_NUMBER() OVER (PARTITION BY id_ot, servicio ORDER BY periodo, id_linea) AS vez
        FROM lineas
        WHERE estado IS NOT NULL
    ) AS cobros
    WHERE vez > 1
),

observadas AS (
    SELECT * FROM sin_ot
    UNION ALL SELECT * FROM ot_abierta
    UNION ALL SELECT * FROM sobre_cantidad
    UNION ALL SELECT * FROM sobre_precio
    UNION ALL SELECT * FROM duplicada
)

SELECT
    o.id_linea,
    l.periodo,
    l.id_contratista,
    l.sede,
    l.id_ot,
    o.regla,
    CAST(o.monto_observado AS INTEGER) AS monto_observado,
    CASE WHEN l.periodo < p.inicio_control THEN 'Pagada sin control' ELSE 'Rechazada' END AS resolucion
FROM observadas AS o
JOIN lineas AS l ON l.id_linea = o.id_linea
CROSS JOIN parametros AS p
ORDER BY o.id_linea, o.regla;
