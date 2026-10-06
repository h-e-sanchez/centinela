"""El libro diario respeta la partida doble y produce EEFF que cuadran entre sí y con el reporte #1."""

from __future__ import annotations

import csv
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"
CARPETA = DATA / "estados-financieros"

_spec = importlib.util.spec_from_file_location("generar_estados_financieros", DATA / "generar_estados_financieros.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["generar_estados_financieros"] = gen
_spec.loader.exec_module(gen)
CIERRES = ("Apertura", "Cierre", "Traspaso")


def _leer(carpeta: Path, nombre: str) -> list[dict]:
    with (carpeta / f"{nombre}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def t():
    tablas = {n: _leer(CARPETA, n) for n in gen.ARCHIVOS}
    asiento = {a["asiento"]: a for a in tablas["asientos"]}
    plan = {p["cuenta_codigo"]: p for p in tablas["plan_cuentas"]}
    for ln in tablas["lineas_asiento"]:
        ln["fecha"], ln["tipo_asiento"] = asiento[ln["asiento"]]["fecha"], asiento[ln["asiento"]]["tipo"]
        ln["p"] = plan[ln["cuenta_codigo"]]
        ln["monto"] = int(ln["debe"]) - int(ln["haber"])
    return tablas


def _saldos(t, industria: str, hasta: str) -> dict[str, int]:
    s = defaultdict(int)
    for ln in t["lineas_asiento"]:
        if ln["industria"] == industria and ln["fecha"] <= hasta:
            s[ln["cuenta_codigo"]] += ln["monto"]
    return s


def _resultados(t, industria: str, anio: str) -> dict[str, int]:
    """Estado de resultados por línea (ingresos positivos, gastos negativos), sin asientos de cierre."""
    e = defaultdict(int)
    for ln in t["lineas_asiento"]:
        if (ln["industria"] == industria and ln["fecha"].startswith(anio) and ln["tipo_asiento"] not in CIERRES
                and ln["p"]["tipo"] in ("Ingreso", "Costo", "Gasto")):
            e[ln["p"]["linea"]] -= ln["monto"]
    return e


def test_csv_al_dia_y_reproducibles(tmp_path):
    gen.escribir(gen.generar(), tmp_path)
    for nombre in gen.ARCHIVOS:
        nuevo = (tmp_path / f"{nombre}.csv").read_bytes()
        guardado = (CARPETA / f"{nombre}.csv").read_bytes().replace(b"\r\n", b"\n")
        assert nuevo == guardado, f"{nombre}.csv desactualizado: corre python data/generar_estados_financieros.py"


def test_partida_doble_en_cada_asiento(t):
    suma = defaultdict(int)
    for ln in t["lineas_asiento"]:
        assert (int(ln["debe"]) == 0) != (int(ln["haber"]) == 0), "cada línea va al debe o al haber, no a ambos"
        suma[ln["asiento"]] += ln["monto"]
    assert all(v == 0 for v in suma.values())


def test_balance_cuadra_cada_mes(t):
    for industria in gen.PERFILES:
        for anio, mes in gen.MESES:
            s = _saldos(t, industria, gen.fecha_fin(anio, mes).isoformat())
            plan = {p["cuenta_codigo"]: p for p in t["plan_cuentas"]}
            activo = sum(v for c, v in s.items() if plan[c]["tipo"] == "Activo")
            pasivo_y_patrimonio = -sum(v for c, v in s.items() if plan[c]["tipo"] != "Activo")
            assert activo == pasivo_y_patrimonio, (industria, anio, mes)


def test_ebitda_cuadra_con_el_resultado_operacional_del_reporte_1(t):
    real = defaultdict(float)
    for r in _leer(DATA / "escenarios", "montos"):
        if r["version"] == "Real":
            signo = 1 if r["grupo_cuenta"] == "Ingresos" else -1
            real[(r["industria"], r["anio"])] += signo * float(r["monto"])
    for industria in gen.PERFILES:
        for anio in ("2025", "2026"):
            e = _resultados(t, industria, anio)
            ebitda = e["Ingresos"] + e["Costos"] + e["Gastos operacionales"]
            assert abs(ebitda - real[(industria, anio)]) < 50, (industria, anio)


def test_cierre_deja_en_cero_los_resultados_y_traspasa_la_utilidad(t):
    for industria in gen.PERFILES:
        s = _saldos(t, industria, "2025-12-31")
        assert all(v == 0 for c, v in s.items() if c.split("-")[1][0] in "456")
        e = _resultados(t, industria, "2025")
        s = _saldos(t, industria, "2026-01-02")
        assert -s[f"{industria[:3].upper()}-3103"] == 0
        apertura = -_saldos(t, industria, "2025-01-01")[f"{industria[:3].upper()}-3102"]
        assert -s[f"{industria[:3].upper()}-3102"] - apertura == sum(e.values())


def test_flujo_de_efectivo_explica_la_variacion_de_caja(t):
    """Método indirecto: resultado − variación de las demás cuentas de balance (sin patrimonio) = variación de caja."""
    for industria in gen.PERFILES:
        for anio in ("2025", "2026"):
            resultado = sum(_resultados(t, industria, anio).values())
            otras = caja = 0
            for ln in t["lineas_asiento"]:
                if ln["industria"] != industria or not ln["fecha"].startswith(anio) or ln["tipo_asiento"] in CIERRES:
                    continue
                if ln["p"]["tipo"] in ("Activo", "Pasivo"):
                    if ln["cuenta_codigo"].endswith("-1101"):
                        caja += ln["monto"]
                    else:
                        otras += ln["monto"]
            assert resultado - otras == caja, (industria, anio)


def test_eerr_reporte1_trae_real_y_presupuesto(t):
    versiones = {r["version"] for r in t["eerr_reporte1"]}
    assert versiones == {"Real", "Presupuesto"}
    plan = {p["cuenta_codigo"] for p in t["plan_cuentas"]}
    assert all(r["cuenta_codigo"] in plan for r in t["eerr_reporte1"])


# --- historias ---------------------------------------------------------------------------------


def _ratios(t, industria: str, hasta: str) -> dict[str, float]:
    s = _saldos(t, industria, hasta)
    plan = {p["cuenta_codigo"]: p for p in t["plan_cuentas"]}
    p = industria[:3].upper()
    ac = sum(v for c, v in s.items() if plan[c]["clasificacion"] == "Activo corriente")
    pc = -sum(v for c, v in s.items() if plan[c]["clasificacion"] == "Pasivo corriente")
    activo = sum(v for c, v in s.items() if plan[c]["tipo"] == "Activo")
    pasivo = -sum(v for c, v in s.items() if plan[c]["tipo"] == "Pasivo")
    anio = hasta[:4]
    e = _resultados(t, industria, anio)
    consumo = sum(ln["monto"] for ln in t["lineas_asiento"] if ln["industria"] == industria
                  and ln["fecha"].startswith(anio) and ln["tipo_asiento"] == "Consumo" and ln["monto"] > 0)
    return {"liquidez": ac / pc, "endeudamiento": pasivo / (activo - pasivo),
            "fijo": (s[f"{p}-1201"] + s[f"{p}-1202"]) / activo, "dso": s[f"{p}-1102"] / e["Ingresos"] * 365,
            "dio": s[f"{p}-1103"] / consumo * 365, "depreciacion": -e["Depreciación"] / e["Ingresos"]}


def test_historia_salud_cobra_lento_y_vive_con_liquidez_justa(t):
    r = {i: _ratios(t, i, "2026-12-31") for i in gen.PERFILES}
    assert r["Salud"]["dso"] >= 85
    assert r["Salud"]["liquidez"] == min(x["liquidez"] for x in r.values())
    assert r["Salud"]["liquidez"] < 1.6
    giros = [a for a in t["asientos"] if a["industria"] == "Salud" and a["tipo"] == "Crédito de corto plazo"]
    assert giros


def test_historia_energia_intensiva_en_activo_fijo_y_deuda(t):
    r = {i: _ratios(t, i, "2026-12-31") for i in gen.PERFILES}
    assert r["Energia"]["fijo"] >= 0.75
    assert r["Energia"]["endeudamiento"] == max(x["endeudamiento"] for x in r.values())
    assert r["Energia"]["depreciacion"] == max(x["depreciacion"] for x in r.values())


def test_historia_manufactura_acumula_inventario_en_su_anio_flojo(t):
    inicio = _ratios(t, "Manufactura", "2025-01-31")["dio"]
    cierre_2025 = _ratios(t, "Manufactura", "2025-12-31")["dio"]
    cierre_2026 = _ratios(t, "Manufactura", "2026-12-31")["dio"]
    assert cierre_2025 > 1.5 * 60  # partió en ~60 días de consumo
    assert cierre_2026 < cierre_2025
    assert inicio < cierre_2025
