"""El capital de trabajo cuadra con el reporte #1, la caja suma y los datos cuentan las tres historias que prometen."""

from __future__ import annotations

import csv
import importlib.util
import sys
from collections import defaultdict
from datetime import date
from itertools import pairwise
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"
CARPETA = DATA / "capital-de-trabajo"

_spec = importlib.util.spec_from_file_location("generar_capital_de_trabajo", DATA / "generar_capital_de_trabajo.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["generar_capital_de_trabajo"] = gen
_spec.loader.exec_module(gen)

CIERRE_2025, CIERRE_2026 = date(2025, 12, 31), date(2026, 12, 31)


def _leer(carpeta: Path, nombre: str) -> list[dict]:
    with (carpeta / f"{nombre}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def t():
    return {n: _leer(CARPETA, n) for n in gen.ARCHIVOS}


def _d(texto: str) -> date | None:
    return date.fromisoformat(texto) if texto else None


def _abierta(f: dict, corte: date) -> bool:
    return _d(f["emision"]) <= corte and (not f["pago"] or _d(f["pago"]) > corte)


def _dias(facturas: list[dict], corte: date) -> float:
    """Saldo abierto al corte sobre el flujo de los tres meses que terminan en el corte, en días."""
    inicio = date(corte.year, corte.month - 2, 1)
    saldo = sum(int(f["monto"]) for f in facturas if _abierta(f, corte))
    flujo = sum(int(f["monto"]) for f in facturas if inicio <= _d(f["emision"]) <= corte)
    return saldo / flujo * ((corte - inicio).days + 1)


def _dio(inventario: list[dict], corte: date) -> float:
    inicio = date(corte.year, corte.month - 2, 1)
    saldo = sum(int(r["saldo"]) for r in inventario if _d(r["fecha"]) == date(corte.year, corte.month, 1))
    consumo = sum(int(r["consumo"]) for r in inventario if inicio <= _d(r["fecha"]) <= corte)
    return saldo / consumo * ((corte - inicio).days + 1)


def _ciclo(t, industria: str, corte: date) -> dict[str, float]:
    filtro = lambda filas: [x for x in filas if x["industria"] == industria]
    dso, dpo = _dias(filtro(t["facturas_venta"]), corte), _dias(filtro(t["facturas_compra"]), corte)
    dio = _dio(filtro(t["inventario_mensual"]), corte)
    return {"DSO": dso, "DIO": dio, "DPO": dpo, "CCC": dso + dio - dpo}


def test_csv_al_dia_y_reproducibles(tmp_path):
    gen.escribir(gen.generar(), tmp_path)
    for nombre in gen.ARCHIVOS:
        nuevo = (tmp_path / f"{nombre}.csv").read_bytes()
        guardado = (CARPETA / f"{nombre}.csv").read_bytes().replace(b"\r\n", b"\n")
        assert nuevo == guardado, f"{nombre}.csv desactualizado: corre python data/generar_capital_de_trabajo.py"


@pytest.mark.parametrize("tabla,grupo", [("facturas_venta", "Ingresos"), ("facturas_compra", "Costos")])
def test_facturas_cuadran_con_el_real_del_reporte_1(t, tabla, grupo):
    cuentas = {f["cuenta"] for f in t[tabla]}
    real = defaultdict(int)
    for r in _leer(DATA / "escenarios", "montos"):
        if r["version"] == "Real" and r["grupo_cuenta"] == grupo and r["cuenta"] in cuentas:
            real[(r["industria"], r["sucursal"], r["anio"], f"{int(r['mes']):02d}", r["cuenta"])] += round(float(r["monto"]))
    facturado = defaultdict(int)
    for f in t[tabla]:
        if f["emision"] >= "2025":  # las de 2024 son la cartera de apertura
            facturado[(f["industria"], f["sucursal"], f["emision"][:4], f["emision"][5:7], f["cuenta"])] += int(f["monto"])
    assert facturado == real


def test_compras_cubren_las_cuentas_de_proveedores_y_no_las_remuneraciones(t):
    cuentas = {f["cuenta"] for f in t["facturas_compra"]}
    assert cuentas == {c for cs in gen.COMPRAS.values() for c in cs}
    assert not {c for c in cuentas if c.startswith(("Sueldos", "Horas extra", "Turnos", "Guardias"))}


@pytest.mark.parametrize("tabla", ["facturas_venta", "facturas_compra"])
def test_fechas_coherentes(t, tabla):
    for f in t[tabla]:
        assert f["emision"] <= f["vencimiento"]
        if f["pago"]:
            assert f["emision"] <= f["pago"] <= gen.CORTE.isoformat()
        assert int(f["monto"]) > 0
    apertura = [f for f in t[tabla] if f["emision"] < "2025"]
    assert apertura and all(not f["pago"] or f["pago"] >= "2025-01-01" for f in apertura)


def test_integridad_referencial(t):
    clientes = {(c["industria"], c["cliente"]) for c in t["clientes"]}
    proveedores = {(p["industria"], p["proveedor"]) for p in t["proveedores"]}
    sucursales = {(s["industria"], s["sucursal"]) for s in t["sucursales"]}
    for f in t["facturas_venta"]:
        assert (f["industria"], f["cliente"]) in clientes and (f["industria"], f["sucursal"]) in sucursales
    for f in t["facturas_compra"]:
        assert (f["industria"], f["proveedor"]) in proveedores and (f["industria"], f["sucursal"]) in sucursales


def test_caja_suma_semana_a_semana(t):
    por_industria = defaultdict(list)
    for s in t["caja_semanal"]:
        por_industria[s["industria"]].append(s)
        pagos = int(s["pagos_proveedores"]) + int(s["otros_pagos"]) + int(s["inversiones_dividendos"])
        assert int(s["pagos"]) == pagos
        assert int(s["saldo_final"]) == int(s["saldo_inicial"]) + int(s["cobros"]) - pagos
    for semanas in por_industria.values():
        for a, b in pairwise(semanas):
            assert b["saldo_inicial"] == a["saldo_final"]
        tipos = [s["tipo"] for s in semanas]
        assert tipos.count("Proyectado") == gen.SEMANAS_PROYECTADAS and tipos[-1] == "Proyectado"
        assert sum(s["ventana"] == "Últimas 13 semanas" for s in semanas) == gen.SEMANAS_PROYECTADAS


def test_cobros_reales_son_las_facturas_pagadas(t):
    cobrado = defaultdict(int)
    for f in t["facturas_venta"]:
        if f["pago"]:
            cobrado[f["industria"]] += int(f["monto"])
    caja = defaultdict(int)
    for s in t["caja_semanal"]:
        if s["tipo"] == "Real":
            caja[s["industria"]] += int(s["cobros"])
    assert caja == cobrado


# --- historias ---------------------------------------------------------------------------------


def test_historia_salud_cobra_lento_y_la_caja_se_estrecha(t):
    ciclos = {i: _ciclo(t, i, CIERRE_2026) for i in gen.EMPRESAS}
    assert ciclos["Salud"]["DSO"] > 90
    assert max(ciclos, key=lambda i: ciclos[i]["CCC"]) == "Salud"
    bajo = [s for s in t["caja_semanal"] if int(s["saldo_final"]) < 60_000_000]
    assert bajo and all(s["industria"] == "Salud" and "2026-04" <= s["semana"] <= "2026-11-30" for s in bajo)


def test_historia_manufactura_sobrestock_en_antofagasta(t):
    def dio(sucursal: str, corte: date) -> float:
        return _dio([r for r in t["inventario_mensual"] if r["sucursal"] == sucursal], corte)

    resto = (dio("Santiago", CIERRE_2025) + dio("Concepción", CIERRE_2025)) / 2
    assert 20 <= dio("Antofagasta", CIERRE_2025) - resto <= 32
    assert abs(dio("Antofagasta", CIERRE_2026) - resto) < 8  # 2026 liquida el sobrestock


def test_historia_energia_ciclo_negativo(t):
    for corte in (CIERRE_2025, CIERRE_2026):
        ciclo = _ciclo(t, "Energia", corte)
        assert ciclo["CCC"] < 0 and ciclo["DPO"] > ciclo["DSO"] + ciclo["DIO"]
