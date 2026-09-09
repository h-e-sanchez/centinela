"""Motor de desviación: cruza presupuesto vs. real y clasifica cada línea.

Completitud de grilla: cualquier combinación (año, mes, centro de costo,
componente) presente en un lado y ausente en el otro se completa con monto 0
explícito, nunca se omite — evita el sesgo de subconteo típico al agregar
eventos poco frecuentes (la misma práctica aplica a rotación de clientes,
downtime de máquinas o siniestralidad).
"""

from __future__ import annotations

from .modelos import (
    GRUPOS_CUENTA,
    LineaDesviacion,
    LineaPresupuesto,
    LineaReal,
    ParametrosAlerta,
    ResumenGrupo,
)

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


def _resumen_de(
    nombre: str,
    monto_presupuesto: float,
    monto_real: float,
    parametros: ParametrosAlerta,
) -> ResumenGrupo:
    desviacion_monto = monto_real - monto_presupuesto
    desviacion_pct = desviacion_monto / monto_presupuesto if monto_presupuesto else None
    estado = _clasificar(desviacion_monto, desviacion_pct, parametros)
    return ResumenGrupo(
        nombre=nombre,
        monto_presupuesto=monto_presupuesto,
        monto_real=monto_real,
        desviacion_monto=desviacion_monto,
        desviacion_pct=desviacion_pct,
        estado=estado,
    )


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
    # El grupo de cuenta es metadata de la clave (centro de costo + componente), no del
    # lado presupuesto/real — debería coincidir en ambos; si una clave solo existe en un
    # lado, se toma el grupo de ese lado.
    grupo_por_clave = {
        _clave(p.anio, p.mes, p.centro_costo, p.componente): p.grupo_cuenta for p in presupuesto
    }
    grupo_por_clave.update({
        _clave(r.anio, r.mes, r.centro_costo, r.componente): r.grupo_cuenta for r in real
    })

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
                grupo_cuenta=grupo_por_clave[clave],
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


def resumen_por_grupo(
    filas: list[LineaDesviacion],
    parametros: ParametrosAlerta | None = None,
) -> list[ResumenGrupo]:
    """Subtotales por grupo de cuenta (Ingresos/Costos/Gastos Operacionales) más el
    Resultado Operacional derivado (Ingresos - Costos - Gastos Operacionales) —
    un extracto de Estado de Resultados con columnas clave, no las 20+ de un
    export SAP real. Opera sobre las filas que se le pasen: para un período
    específico, filtrarlas por año/mes antes de llamar.
    """
    parametros = parametros or ParametrosAlerta()

    montos_presupuesto = dict.fromkeys(GRUPOS_CUENTA, 0.0)
    montos_real = dict.fromkeys(GRUPOS_CUENTA, 0.0)
    for fila in filas:
        if fila.grupo_cuenta not in montos_presupuesto:
            continue  # grupo desconocido -- no debería pasar con datos bien formados
        montos_presupuesto[fila.grupo_cuenta] += fila.monto_presupuesto
        montos_real[fila.grupo_cuenta] += fila.monto_real

    resumenes = [
        _resumen_de(grupo, montos_presupuesto[grupo], montos_real[grupo], parametros)
        for grupo in GRUPOS_CUENTA
    ]

    resultado_presupuesto = (
        montos_presupuesto["Ingresos"]
        - montos_presupuesto["Costos"]
        - montos_presupuesto["Gastos Operacionales"]
    )
    resultado_real = (
        montos_real["Ingresos"] - montos_real["Costos"] - montos_real["Gastos Operacionales"]
    )
    resumenes.append(
        _resumen_de("Resultado Operacional", resultado_presupuesto, resultado_real, parametros)
    )
    return resumenes
