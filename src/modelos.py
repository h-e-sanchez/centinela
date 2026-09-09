"""Modelos de datos de centinela.

Formato tidy/long deliberado (una fila por año, mes, centro de costo y
componente) — trivial de pivotear en Excel, Power BI o pandas sin lógica
adicional, y trivial de cruzar entre presupuesto y real por la misma clave.
"""

from __future__ import annotations

from dataclasses import dataclass

# Grupo/naturaleza de cuenta — la clasificación mínima que permite armar un Estado de
# Resultados (Ingresos - Costos - Gastos Operacionales = Resultado Operacional) en vez
# de solo una lista plana de líneas con desviación. Deliberadamente 3 grupos, no el P&L
# completo de 4+ niveles (Costo de Venta / Margen Bruto / Gastos Admin-Ventas por
# separado) — el modelo sintético no sostiene esa granularidad con datos reales.
GRUPOS_CUENTA = ("Ingresos", "Costos", "Gastos Operacionales")


@dataclass(frozen=True)
class LineaPresupuesto:
    anio: int
    mes: int
    centro_costo: str
    componente: str
    grupo_cuenta: str
    monto: float


@dataclass(frozen=True)
class LineaReal:
    anio: int
    mes: int
    centro_costo: str
    componente: str
    grupo_cuenta: str
    monto: float


@dataclass(frozen=True)
class ParametrosAlerta:
    """Los diales que un Analista de Control de Gestión ajusta sin tocar
    código — separación explícita entre parámetro de negocio y lógica fija.

    umbral_pct: desviación porcentual absoluta a partir de la cual una línea
        pasa de "ok" a "alerta" (0.05 = 5%). La comparación es estricta
        (>), no inclusiva: una línea en exactamente el umbral no dispara.
    umbral_critico_pct: desviación porcentual absoluta a partir de la cual
        una línea pasa a "critica". Debe ser mayor o igual a umbral_pct.
    """

    umbral_pct: float = 0.05
    umbral_critico_pct: float = 0.15

    def __post_init__(self) -> None:
        if self.umbral_critico_pct < self.umbral_pct:
            raise ValueError("umbral_critico_pct no puede ser menor que umbral_pct")


@dataclass(frozen=True)
class LineaDesviacion:
    anio: int
    mes: int
    centro_costo: str
    componente: str
    grupo_cuenta: str
    monto_presupuesto: float
    monto_real: float
    desviacion_monto: float
    desviacion_pct: float | None  # None cuando monto_presupuesto es 0
    estado: str  # "ok" | "alerta" | "critica"


@dataclass(frozen=True)
class ResumenGrupo:
    """Un subtotal — de un grupo de cuenta (Ingresos/Costos/Gastos Operacionales) o
    del Resultado Operacional derivado. Misma forma que LineaDesviacion sin las
    columnas de detalle (centro de costo/componente), porque ya es una agregación.
    """

    nombre: str
    monto_presupuesto: float
    monto_real: float
    desviacion_monto: float
    desviacion_pct: float | None
    estado: str
