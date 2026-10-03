"""Los datos de contratistas cuentan la historia que prometen y las reglas SQL encuentran justo lo inyectado."""

from __future__ import annotations

import csv
import importlib.util
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"
CARPETA = DATA / "contratistas"

_spec = importlib.util.spec_from_file_location("generar_contratistas", DATA / "generar_contratistas.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["generar_contratistas"] = gen  # dataclasses necesita el módulo registrado
_spec.loader.exec_module(gen)

INDUSTRIAS = list(gen.INDUSTRIAS)
CONTROL = gen.INICIO_CONTROL.isoformat()


def _leer(carpeta: Path, nombre: str) -> list[dict]:
    with (carpeta / f"{nombre}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def t():
    return {n: _leer(CARPETA, n) for n in gen.ARCHIVOS}


@pytest.fixture(scope="module")
def industria(t):
    return {c["id_contratista"]: c["industria"] for c in t["contratistas"]}


@pytest.fixture(scope="module")
def por_mes(t, industria):
    """Facturado y observado por (industria, periodo)."""
    facturado, observado = Counter(), Counter()
    for f in t["estados_pago"]:
        facturado[(industria[f["id_contratista"]], f["periodo"])] += int(f["monto"])
    for o in t["observaciones"]:
        observado[(industria[o["id_contratista"]], o["periodo"])] += int(o["monto_observado"])
    return facturado, observado


def test_csv_al_dia_y_reproducibles(tmp_path):
    gen.escribir(gen.generar(), tmp_path)
    for nombre in gen.ARCHIVOS:
        nuevo = (tmp_path / f"{nombre}.csv").read_bytes()
        guardado = (CARPETA / f"{nombre}.csv").read_bytes().replace(b"\r\n", b"\n")
        assert nuevo == guardado, f"{nombre}.csv desactualizado: corre python data/generar_contratistas.py"


def test_reglas_sql_encuentran_exactamente_las_anomalias_inyectadas(t):
    inyectadas = {(f["id_linea"], f["anomalia_inyectada"]) for f in t["estados_pago"] if f["anomalia_inyectada"]}
    observadas = {(o["id_linea"], o["regla"]) for o in t["observaciones"]}
    assert observadas == inyectadas  # recall y precisión de 100%
    assert {r for _, r in inyectadas} == set(gen.PESOS_ANOMALIA)  # las cinco reglas se ejercitan


def test_auditar_desde_csv_da_lo_mismo(t):
    """sql/auditar.py leyendo los CSV (todo texto) reproduce observaciones.csv."""
    desde_csv = gen.auditar.auditar({n: t[n] for n in gen.auditar.TIPOS})
    assert [{k: str(v) for k, v in o.items()} for o in desde_csv] == t["observaciones"]


def test_mismas_sedes_que_workforce(t):
    clave = ("sede", "industria", "empresa", "orden")
    workforce = [{k: s[k] for k in clave} for s in _leer(DATA / "workforce", "sedes")]
    assert [{k: s[k] for k in clave} for s in t["sedes"]] == workforce


def test_integridad_referencial(t):
    ots = {o["id_ot"] for o in t["ordenes_trabajo"]}
    activos = {a["id_activo"] for a in t["activos"]}
    contratistas = {c["id_contratista"] for c in t["contratistas"]}
    sedes = {s["sede"] for s in t["sedes"]}
    assert {o["id_activo"] for o in t["ordenes_trabajo"]} <= activos
    assert {f["id_contratista"] for f in t["estados_pago"]} <= contratistas
    assert {f["sede"] for f in t["estados_pago"]} <= sedes
    # Solo las líneas de cobro sin OT citan una OT inexistente (o ninguna).
    huerfanas = {f["anomalia_inyectada"] for f in t["estados_pago"] if f["id_ot"] not in ots}
    assert huerfanas == {"sin_ot"}


@pytest.mark.parametrize("ind", INDUSTRIAS)
def test_facturacion_cerca_de_200_millones_al_mes(por_mes, ind):
    facturado, _ = por_mes
    meses = [v for (i, _), v in facturado.items() if i == ind]
    assert len(meses) == 24
    assert 170e6 <= sum(meses) / len(meses) <= 230e6


@pytest.mark.parametrize("ind", INDUSTRIAS)
def test_observado_entre_3_y_6_por_ciento(por_mes, ind):
    facturado, observado = por_mes
    total = sum(v for (i, _), v in facturado.items() if i == ind)
    assert 0.03 <= sum(v for (i, _), v in observado.items() if i == ind) / total <= 0.06


def test_el_control_baja_las_anomalias(por_mes):
    facturado, observado = por_mes
    for ind in INDUSTRIAS:
        def tasa(antes: bool, ind: str = ind) -> float:
            claves = [k for k in facturado if k[0] == ind and (k[1] < CONTROL) == antes]
            return sum(observado[k] for k in claves) / sum(facturado[k] for k in claves)
        assert tasa(True) > 2 * tasa(False)


def test_un_mes_de_pico_sostiene_el_relato(por_mes):
    """El relato es de 5 a 50 millones observados al mes; la simulación llega a más de 25 en el pico."""
    _, observado = por_mes
    assert max(observado.values()) > 25e6
    assert max(observado, key=observado.get)[0] == "Energia"


def test_pagado_de_mas_solo_antes_del_control(t):
    for o in t["observaciones"]:
        esperado = "Pagada sin control" if o["periodo"] < CONTROL else "Rechazada"
        assert o["resolucion"] == esperado
    assert any(o["resolucion"] == "Pagada sin control" for o in t["observaciones"])


def test_riesgosos_concentran_lo_observado(t):
    perfil = {c["id_contratista"]: c["perfil"] for c in t["contratistas"]}
    monto = Counter()
    for o in t["observaciones"]:
        monto[perfil[o["id_contratista"]]] += int(o["monto_observado"])
    assert monto["Riesgoso"] / sum(monto.values()) > 0.55


def test_riesgosos_cumplen_menos_el_plan_preventivo(t):
    perfil = {c["id_contratista"]: c["perfil"] for c in t["contratistas"]}
    cumplidas, programadas = Counter(), Counter()
    for o in t["ordenes_trabajo"]:
        if o["clase"] != "Preventiva" or o["fecha_programada"] >= "2026-12-01":
            continue
        p = perfil[o["id_contratista"]]
        programadas[p] += 1
        if o["estado"] == "Cerrada":
            atraso = (date.fromisoformat(o["fecha_inicio"]) - date.fromisoformat(o["fecha_programada"])).days
            cumplidas[p] += atraso <= 7
    limpio, riesgoso = (cumplidas[p] / programadas[p] for p in ("Limpio", "Riesgoso"))
    assert limpio > 0.88 and riesgoso < 0.78


def test_mtbf_y_mttr_plausibles(t):
    activos = {a["id_activo"]: a for a in t["activos"]}
    fallas, horas = Counter(), defaultdict(float)
    n_activos = Counter(a["tipo_activo"] for a in t["activos"])
    for o in t["ordenes_trabajo"]:
        if o["clase"] == "Correctiva":
            tipo = activos[o["id_activo"]]["tipo_activo"]
            fallas[tipo] += 1
            horas[tipo] += float(o["horas_ejecutadas"])
    objetivo = {a["tipo_activo"]: int(a["mtbf_objetivo_dias"]) for a in t["activos"]}
    for tipo, n in fallas.items():
        mtbf = 730 * n_activos[tipo] / n
        assert 0.7 * objetivo[tipo] <= mtbf <= 1.3 * objetivo[tipo], tipo
        assert 2 <= horas[tipo] / n <= 16, tipo
