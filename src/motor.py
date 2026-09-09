"""Motor de desviación: cruza presupuesto vs. real y clasifica cada línea.

Completitud de grilla: cualquier combinación (año, mes, centro de costo,
componente) presente en un lado y ausente en el otro se completa con monto 0
explícito, nunca se omite — evita el sesgo de subconteo típico al agregar
eventos poco frecuentes (la misma práctica aplica a rotación de clientes,
downtime de máquinas o siniestralidad).
"""

from __future__ import annotations

from .modelos import LineaDesviacion, LineaPresupuesto, LineaReal, ParametrosAlerta

Clave = tuple[int, int, str, str]


def _clave(anio: int, mes: int, centro_costo: str, componente: str) -> Clave:
    return (anio, mes, centro_costo, componente)


def _clasificar(
    desviacion_monto: float,
    desviacion_pct: float | None,
    parametros: ParametrosAlerta,
) -> str:
    if desviacion_pct is None:
        # Sin presupuesto asignado (monto_presupuesto == 0): cualquier gasto
        # real es 100% no presupuestado — no hay "% de cero" que calcular,
        # así que se marca crítica directamente si el monto real no es cero.
        return "critica" if desviacion_monto != 0 else "ok"
    magnitud = abs(desviacion_pct)
    if magnitud > parametros.umbral_critico_pct:
        return "critica"
    if magnitud > parametros.umbral_pct:
        return "alerta"
    return "ok"


def calcular_desviaciones(
    presupuesto: list[LineaPresupuesto],
    real: list[LineaReal],
    parametros: ParametrosAlerta | None = None,
) -> list[LineaDesviacion]:
    parametros = parametros or ParametrosAlerta()

    presupuesto_por_clave = {
        _clave(p.anio, p.mes, p.centro_costo, p.componente): p.monto for p in presupuesto
    }
    real_por_clave = {
        _clave(r.anio, r.mes, r.centro_costo, r.componente): r.monto for r in real
    }

    claves = sorted(set(presupuesto_por_clave) | set(real_por_clave))

    filas: list[LineaDesviacion] = []
    for clave in claves:
        anio, mes, centro_costo, componente = clave
        monto_presupuesto = presupuesto_por_clave.get(clave, 0.0)
        monto_real = real_por_clave.get(clave, 0.0)
        desviacion_monto = monto_real - monto_presupuesto
        desviacion_pct = (
            desviacion_monto / monto_presupuesto if monto_presupuesto else None
        )
        estado = _clasificar(desviacion_monto, desviacion_pct, parametros)
        filas.append(
            LineaDesviacion(
                anio=anio,
                mes=mes,
                centro_costo=centro_costo,
                componente=componente,
                monto_presupuesto=monto_presupuesto,
                monto_real=monto_real,
                desviacion_monto=desviacion_monto,
                desviacion_pct=desviacion_pct,
                estado=estado,
            )
        )
    return filas


def resumen_por_estado(filas: list[LineaDesviacion]) -> dict[str, int]:
    resumen = {"ok": 0, "alerta": 0, "critica": 0}
    for fila in filas:
        resumen[fila.estado] += 1
    return resumen


def lineas_en_alerta(filas: list[LineaDesviacion]) -> list[LineaDesviacion]:
    return [f for f in filas if f.estado != "ok"]
