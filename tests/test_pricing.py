"""Los precios y márgenes cuadran con los ingresos del reporte #1 y cuentan las tres historias que prometen."""

from __future__ import annotations

import csv
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"
CARPETA = DATA / "pricing-margenes"

_spec = importlib.util.spec_from_file_location("generar_pricing", DATA / "generar_pricing.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["generar_pricing"] = gen
_spec.loader.exec_module(gen)


def _leer(carpeta: Path, nombre: str) -> list[dict]:
    with (carpeta / f"{nombre}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def t():
    return {n: _leer(CARPETA, n) for n in gen.ARCHIVOS}


def _margen(filas: list[dict]) -> float:
    neto = sum(int(x["ingreso_neto"]) for x in filas)
    return (neto - sum(int(x["costo_variable"]) + int(x["costo_servir"]) for x in filas)) / neto


def _pvm(t, industria: str) -> dict[str, float]:
    q, r = defaultdict(float), defaultdict(float)
    for x in t["transacciones"]:
        if x["industria"] == industria:
            q[(x["anio"], x["producto"])] += float(x["cantidad"])
            r[(x["anio"], x["producto"])] += int(x["ingreso_neto"])
    productos = {p for _, p in q}
    r0, r1 = (sum(r[(a, p)] for p in productos) for a in ("2025", "2026"))
    q0, q1 = (sum(q[(a, p)] for p in productos) for a in ("2025", "2026"))
    precio = sum((r[("2026", p)] / q[("2026", p)] - r[("2025", p)] / q[("2025", p)]) * q[("2026", p)] for p in productos)
    volumen_mezcla = sum((q[("2026", p)] - q[("2025", p)]) * r[("2025", p)] / q[("2025", p)] for p in productos)
    volumen = (q1 - q0) * r0 / q0
    return {"delta": r1 - r0, "precio": precio, "volumen": volumen, "mezcla": volumen_mezcla - volumen}


def test_csv_al_dia_y_reproducibles(tmp_path):
    gen.escribir(gen.generar(), tmp_path)
    for nombre in gen.ARCHIVOS:
        nuevo = (tmp_path / f"{nombre}.csv").read_bytes()
        guardado = (CARPETA / f"{nombre}.csv").read_bytes().replace(b"\r\n", b"\n")
        assert nuevo == guardado, f"{nombre}.csv desactualizado: corre python data/generar_pricing.py"


def test_ingresos_cuadran_con_el_real_del_reporte_1(t):
    real = defaultdict(int)
    for r in _leer(DATA / "escenarios", "montos"):
        if r["version"] == "Real" and r["grupo_cuenta"] == "Ingresos":
            real[(r["industria"], r["sucursal"], r["anio"], f"{int(r['mes']):02d}", r["cuenta"])] += round(float(r["monto"]))
    neto = defaultdict(int)
    for x in t["transacciones"]:
        neto[(x["industria"], x["sucursal"], x["anio"], x["fecha"][5:7], x["cuenta"])] += int(x["ingreso_neto"])
    assert neto == real


def test_cascada_de_precios_coherente(t):
    for x in t["transacciones"]:
        descuentos = int(x["descuento_comercial"]) + int(x["rappel"]) + int(x["bonificacion"])
        assert int(x["ingreso_lista"]) == int(x["ingreso_neto"]) + descuentos
        assert min(int(x["descuento_comercial"]), int(x["rappel"]), int(x["bonificacion"])) >= 0
        assert 0 < int(x["ingreso_neto"]) <= int(x["ingreso_lista"])


def test_integridad_referencial(t):
    clientes = {(c["cliente"], c["canal"]) for c in t["clientes"]}
    productos = {(p["industria"], p["producto"]) for p in t["productos"]}
    sucursales = {(s["industria"], s["sucursal"]) for s in t["sucursales"]}
    for x in t["transacciones"]:
        assert (x["cliente"], x["canal"]) in clientes
        assert (x["industria"], x["producto"]) in productos
        assert (x["industria"], x["sucursal"]) in sucursales


def test_precio_volumen_mezcla_suman_la_variacion(t):
    for industria in gen.CANALES:
        e = _pvm(t, industria)
        assert abs(e["precio"] + e["volumen"] + e["mezcla"] - e["delta"]) < 1


# --- historias ---------------------------------------------------------------------------------


def test_historia_manufactura_retail_vende_mucho_y_deja_poco(t):
    manu = [x for x in t["transacciones"] if x["industria"] == "Manufactura" and x["anio"] == "2026"]
    por_canal = defaultdict(list)
    for x in manu:
        por_canal[x["canal"]].append(x)
    margen = {c: _margen(v) for c, v in por_canal.items()}
    cantidad = {c: sum(float(x["cantidad"]) for x in v) for c, v in por_canal.items()}
    assert min(margen, key=margen.get) == "Retail"
    assert 0.02 <= margen["Retail"] <= 0.07
    assert max(cantidad, key=cantidad.get) == "Retail"


def test_historia_energia_el_precio_explica_la_variacion(t):
    e = _pvm(t, "Energia")
    assert e["delta"] > 0
    assert e["precio"] / e["delta"] >= 0.9


def test_historia_salud_convenios_fuera_de_politica(t):
    maximo = {c["canal"]: float(c["descuento_maximo"]) for c in t["canales"]}
    convenios = [x for x in t["transacciones"] if x["canal"] == "Convenios con empresas"]
    fuera = [x for x in convenios
             if 1 - int(x["ingreso_neto"]) / int(x["ingreso_lista"]) > maximo["Convenios con empresas"]]
    assert 0.12 <= len(fuera) / len(convenios) <= 0.30
    margen_cliente = defaultdict(int)
    for x in t["transacciones"]:
        if x["industria"] == "Salud":
            margen_cliente[x["cliente"]] += int(x["ingreso_neto"]) - int(x["costo_variable"]) - int(x["costo_servir"])
    negativos = [c for c, v in margen_cliente.items() if v < 0]
    assert negativos and all(c.startswith("Empresa Convenio") for c in negativos)
