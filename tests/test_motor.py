from __future__ import annotations

import pytest

from src.modelos import LineaPresupuesto, LineaReal, ParametrosAlerta
from src.motor import calcular_desviaciones, lineas_en_alerta, resumen_por_estado


def _presupuesto(monto: float, mes: int = 1, centro: str = "Operaciones", componente: str = "materiales"):
    return LineaPresupuesto(anio=2026, mes=mes, centro_costo=centro, componente=componente, monto=monto)


def _real(monto: float, mes: int = 1, centro: str = "Operaciones", componente: str = "materiales"):
    return LineaReal(anio=2026, mes=mes, centro_costo=centro, componente=componente, monto=monto)


def test_sin_desviacion_es_ok():
    filas = calcular_desviaciones([_presupuesto(1_000_000)], [_real(1_000_000)])
    assert filas[0].estado == "ok"
    assert filas[0].desviacion_pct == 0.0


def test_desviacion_dentro_del_umbral_es_ok():
    # 3% de desviación, umbral default 5% -> ok
    filas = calcular_desviaciones([_presupuesto(1_000_000)], [_real(1_030_000)])
    assert filas[0].estado == "ok"


def test_desviacion_sobre_umbral_es_alerta():
    # 10% de desviación, umbral default 5%, crítico 15% -> alerta
    filas = calcular_desviaciones([_presupuesto(1_000_000)], [_real(1_100_000)])
    assert filas[0].estado == "alerta"


def test_desviacion_sobre_umbral_critico_es_critica():
    filas = calcular_desviaciones([_presupuesto(1_000_000)], [_real(1_200_000)])
    assert filas[0].estado == "critica"


def test_umbral_es_estrictamente_mayor_no_inclusivo():
    parametros = ParametrosAlerta(umbral_pct=0.05, umbral_critico_pct=0.15)
    # Exactamente 5.0% de desviación: NO dispara alerta (comparación estricta).
    filas_borde = calcular_desviaciones([_presupuesto(1_000_000)], [_real(1_050_000)], parametros)
    assert filas_borde[0].estado == "ok"
    # 5.01%: sí dispara.
    filas_sobre = calcular_desviaciones([_presupuesto(1_000_000)], [_real(1_050_100)], parametros)
    assert filas_sobre[0].estado == "alerta"


def test_sub_ejecucion_tambien_dispara_alerta():
    # Gastar mucho menos de lo presupuestado también es una desviación relevante.
    filas = calcular_desviaciones([_presupuesto(1_000_000)], [_real(800_000)])
    assert filas[0].estado == "critica"
    assert filas[0].desviacion_pct == pytest.approx(-0.2)


def test_completa_celdas_faltantes_con_cero_no_las_omite():
    # Una línea presupuestada sin real registrado -> se completa con real=0,
    # no desaparece de la agregación.
    filas = calcular_desviaciones([_presupuesto(500_000, mes=3)], [])
    assert len(filas) == 1
    assert filas[0].monto_real == 0.0
    assert filas[0].desviacion_pct == pytest.approx(-1.0)
    assert filas[0].estado == "critica"


def test_real_sin_presupuesto_es_critica():
    filas = calcular_desviaciones([], [_real(300_000)])
    assert len(filas) == 1
    assert filas[0].desviacion_pct is None
    assert filas[0].estado == "critica"


def test_sin_presupuesto_ni_real_no_aparece():
    # No hay ninguna clave -> lista vacía, no una fila fantasma.
    assert calcular_desviaciones([], []) == []


def test_resumen_por_estado_cuenta_correctamente():
    filas = calcular_desviaciones(
        [_presupuesto(1_000_000, mes=1), _presupuesto(1_000_000, mes=2), _presupuesto(1_000_000, mes=3)],
        [_real(1_000_000, mes=1), _real(1_100_000, mes=2), _real(1_300_000, mes=3)],
    )
    resumen = resumen_por_estado(filas)
    assert resumen == {"ok": 1, "alerta": 1, "critica": 1}


def test_lineas_en_alerta_excluye_las_ok():
    filas = calcular_desviaciones(
        [_presupuesto(1_000_000, mes=1), _presupuesto(1_000_000, mes=2)],
        [_real(1_000_000, mes=1), _real(1_200_000, mes=2)],
    )
    en_alerta = lineas_en_alerta(filas)
    assert len(en_alerta) == 1
    assert en_alerta[0].mes == 2


def test_parametros_alerta_rechaza_umbral_critico_menor_al_umbral():
    with pytest.raises(ValueError):
        ParametrosAlerta(umbral_pct=0.10, umbral_critico_pct=0.05)
