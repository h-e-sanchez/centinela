"""Las remuneraciones son de las mismas personas de Workforce y cuentan las tres historias que prometen."""

from __future__ import annotations

import csv
import importlib.util
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"
CARPETA = DATA / "compensaciones"
RAIZ = DATA.parent

_spec = importlib.util.spec_from_file_location("generar_compensaciones", DATA / "generar_compensaciones.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["generar_compensaciones"] = gen
_spec.loader.exec_module(gen)


def _leer(carpeta: Path, nombre: str) -> list[dict]:
    with (carpeta / f"{nombre}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def t():
    return {n: _leer(CARPETA, n) for n in gen.ARCHIVOS}


@pytest.fixture(scope="module")
def foto(t):
    """Remuneraciones del último mes, con su banda y el sexo de la persona."""
    banda = {b["banda"]: b for b in t["bandas"]}
    sexo = {p["id_persona"]: p["sexo"] for p in t["personas"]}
    ultimo = max(r["fecha"] for r in t["remuneraciones"])
    return [r | {"b": banda[r["banda"]], "sexo": sexo[r["id_persona"]]}
            for r in t["remuneraciones"] if r["fecha"] == ultimo]


def _compa(filas: list[dict]) -> float:
    return sum(int(r["sueldo_base_44h"]) for r in filas) / sum(int(r["b"]["punto_medio"]) for r in filas)


def test_csv_al_dia_y_reproducibles(tmp_path):
    gen.escribir(gen.generar(), tmp_path)
    for nombre in gen.ARCHIVOS:
        nuevo = (tmp_path / f"{nombre}.csv").read_bytes()
        guardado = (CARPETA / f"{nombre}.csv").read_bytes().replace(b"\r\n", b"\n")
        assert nuevo == guardado, f"{nombre}.csv desactualizado: corre python data/generar_compensaciones.py"


def test_mismas_personas_que_workforce(t):
    workforce = {p["id_persona"]: p for p in _leer(DATA / "workforce", "personas")}
    assert set(workforce) == {p["id_persona"] for p in t["personas"]}
    for p in t["personas"]:
        w = workforce[p["id_persona"]]
        assert (p["industria"], p["sede"], p["servicio"], p["sexo"], p["fecha_ingreso"], p["fecha_egreso"]) == \
               (w["industria"], w["sede"], w["unidad"], w["sexo"], w["fecha_ingreso"], w["fecha_egreso"])


def test_solo_hay_remuneracion_mientras_la_persona_esta_vigente(t):
    persona = {p["id_persona"]: p for p in t["personas"]}
    for r in t["remuneraciones"]:
        p = persona[r["id_persona"]]
        assert p["fecha_ingreso"][:7] <= r["fecha"][:7]
        assert not p["fecha_egreso"] or r["fecha"][:7] <= p["fecha_egreso"][:7]


def test_bandas_validas_y_referencias(t):
    bandas = {b["banda"] for b in t["bandas"]}
    for b in t["bandas"]:
        assert int(b["minimo"]) < int(b["punto_medio"]) < int(b["maximo"])
        assert int(b["mercado_p25"]) < int(b["mercado_p50"]) < int(b["mercado_p75"])
    cargos = {c["cargo"] for c in t["cargos"]}
    servicios = {(s["industria"], s["servicio"]) for s in t["servicios"]}
    assert all(p["cargo"] in cargos and (p["industria"], p["servicio"]) in servicios for p in t["personas"])
    assert all(r["banda"] in bandas for r in t["remuneraciones"])


def test_jornada_parcial_cobra_en_proporcion(t):
    for r in t["remuneraciones"]:
        esperado = int(r["sueldo_base_44h"]) * int(r["jornada_horas"]) / gen.JORNADA_COMPLETA
        assert abs(int(r["sueldo_base"]) - esperado) <= 1000


def test_rls_un_rol_por_servicio():
    roles = RAIZ / "powerbi" / "compensaciones" / "compensaciones.SemanticModel" / "definition" / "roles"
    servicios = {s["servicio"] for s in _leer(CARPETA, "servicios")}
    filtros = set()
    for archivo in roles.glob("*.tmdl"):
        texto = archivo.read_text(encoding="utf-8")
        assert "tablePermission servicios = servicios[servicio] = " in texto, archivo.name
        filtros.add(texto.split('servicios[servicio] = "')[1].split('"')[0])
    assert filtros == servicios


# --- historias ---------------------------------------------------------------------------------


def test_historia_salud_uci_sobre_la_banda_y_ambulatorio_bajo(foto):
    salud = [r for r in foto if r["industria"] == "Salud"]
    uci = _compa([r for r in salud if r["servicio"] == "UCI"])
    ambulatorio = _compa([r for r in salud if r["servicio"] == "Ambulatorio"])
    assert 1.07 <= uci <= 1.16
    assert ambulatorio < 0.95
    servicios = {r["servicio"] for r in salud}
    assert uci == max(_compa([r for r in salud if r["servicio"] == s]) for s in servicios)


def test_historia_energia_ingresos_recientes_bajo_el_minimo(foto):
    energia = [r for r in foto if r["industria"] == "Energia"]
    bajo = [r for r in energia if int(r["sueldo_base_44h"]) < int(r["b"]["minimo"])]
    assert 0.06 <= len(bajo) / len(energia) <= 0.12
    otras = [r for r in foto if r["industria"] != "Energia"]
    assert sum(1 for r in otras if int(r["sueldo_base_44h"]) < int(r["b"]["minimo"])) / len(otras) < 0.02


def test_historia_manufactura_la_brecha_cruda_engana(foto):
    manu = [r for r in foto if r["industria"] == "Manufactura"]
    hombres = [int(r["sueldo_base_44h"]) for r in manu if r["sexo"] == "M"]
    mujeres = [int(r["sueldo_base_44h"]) for r in manu if r["sexo"] == "F"]
    cruda = (st.median(hombres) - st.median(mujeres)) / st.median(hombres)
    por_grado = defaultdict(lambda: {"M": [], "F": []})
    for r in manu:
        por_grado[r["grado"]][r["sexo"]].append(int(r["sueldo_base_44h"]))
    num = den = 0
    for d in por_grado.values():
        if d["M"] and d["F"]:
            n = len(d["M"]) + len(d["F"])
            num += (st.median(d["M"]) - st.median(d["F"])) / st.median(d["M"]) * n
            den += n
    assert cruda < 0  # en el agregado las mujeres parecen ganar más (composición de estamentos)
    assert 0.025 <= num / den <= 0.06  # dentro del mismo grado ganan menos
