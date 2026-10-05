"""Los datos de proyectos de TI son coherentes como un historial de Jira y cuentan las tres historias que prometen."""

from __future__ import annotations

import csv
import importlib.util
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"
CARPETA = DATA / "proyectos-ti"

_spec = importlib.util.spec_from_file_location("generar_proyectos_ti", DATA / "generar_proyectos_ti.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["generar_proyectos_ti"] = gen  # dataclasses necesita el módulo registrado
_spec.loader.exec_module(gen)

SIGUIENTES = {"por_hacer": {"en_curso"}, "en_curso": {"en_revision", "bloqueado", "hecho"},
              "bloqueado": {"en_curso"}, "en_revision": {"hecho"}}


def _leer(carpeta: Path, nombre: str) -> list[dict]:
    with (carpeta / f"{nombre}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def t():
    return {n: _leer(CARPETA, n) for n in gen.ARCHIVOS}


def test_csv_al_dia_y_reproducibles(tmp_path):
    gen.escribir(gen.generar(), tmp_path)
    for nombre in gen.ARCHIVOS:
        nuevo = (tmp_path / f"{nombre}.csv").read_bytes()
        guardado = (CARPETA / f"{nombre}.csv").read_bytes().replace(b"\r\n", b"\n")
        assert nuevo == guardado, f"{nombre}.csv desactualizado: corre python data/generar_proyectos_ti.py"


def test_mismas_empresas_que_workforce(t):
    sedes = _leer(DATA / "workforce", "sedes")
    assert {(s["industria"], s["empresa"]) for s in sedes} == {(e["industria"], e["empresa"]) for e in t["empresas"]}


def test_integridad_referencial(t):
    proyectos = {p["proyecto"] for p in t["proyectos"]}
    issues = {i["issue"] for i in t["issues"]}
    personas = {p["persona_ti"] for p in t["personas_ti"]}
    equipos = {e["equipo"] for e in t["equipos"]}
    sprints = {s["sprint"] for s in t["sprints"]}
    assert len(issues) == len(t["issues"]), "claves de issue repetidas"
    assert all(i["proyecto"] in proyectos and i["equipo"] in equipos for i in t["issues"])
    assert all(i["epica_padre"] in issues for i in t["issues"] if i["tipo"] != "epica")
    assert all(f["issue"] in issues for f in t["transiciones"])
    assert all(w["issue"] in issues and w["persona_ti"] in personas for w in t["worklogs"])
    assert all(d["issue_bloqueante"] in issues and d["issue_bloqueado"] in issues for d in t["dependencias"])
    assert all(c["issue"] in issues and c["sprint"] in sprints for c in t["compromisos"])
    assert all(i["sprint"] in sprints for i in t["issues"] if i["sprint"])


def test_transiciones_siguen_el_flujo(t):
    """Cada transición parte del estado en que quedó la anterior, y el estado al corte es el último."""
    por_issue = defaultdict(list)
    for f in t["transiciones"]:
        por_issue[f["issue"]].append(f)
    for i in t["issues"]:
        estado = "por_hacer"
        for f in sorted(por_issue[i["issue"]], key=lambda x: x["fecha_hora"]):
            assert f["estado_desde"] == estado, f"{i['issue']}: {f['estado_desde']} no sigue a {estado}"
            assert f["estado_hasta"] in SIGUIENTES[estado]
            estado = f["estado_hasta"]
        assert estado == i["estado_al_corte"], i["issue"]
        assert (estado == "hecho") == bool(i["fecha_fin"]), i["issue"]


def test_fechas_coherentes(t):
    corte = gen.CORTE.isoformat()
    for i in t["issues"]:
        assert i["creado"] <= (i["fecha_inicio"] or corte) <= (i["fecha_fin"] or corte) <= corte, i["issue"]
        if i["dias_ciclo"]:
            ciclo = (date.fromisoformat(i["fecha_fin"]) - date.fromisoformat(i["fecha_inicio"])).days
            assert int(i["dias_ciclo"]) == ciclo


def test_worklogs_solo_en_dias_habiles_y_dentro_de_la_asignacion(t):
    asignado = {(a["persona_ti"], a["equipo"]) for a in t["asignaciones"]}
    equipo_de = {i["issue"]: i["equipo"] for i in t["issues"]}
    for w in t["worklogs"]:
        assert date.fromisoformat(w["fecha"]).weekday() < 5
        assert (w["persona_ti"], w["equipo"]) in asignado
        assert equipo_de[w["issue"]] == w["equipo"]


def test_dependencias_cruzan_equipos_dentro_del_proyecto(t):
    proyecto_de = {i["issue"]: i["proyecto"] for i in t["issues"]}
    for d in t["dependencias"]:
        assert d["equipo_bloqueante"] != d["equipo_bloqueado"]
        assert proyecto_de[d["issue_bloqueante"]] == proyecto_de[d["issue_bloqueado"]] == d["proyecto"]


def test_pronostico_ordenado_y_distribucion_completa(t):
    for p in t["pronostico_termino"]:
        assert p["fecha_p50"] <= p["fecha_p85"] <= p["fecha_p95"], p["proyecto"]
        if p["estado"] == "En curso":
            assert int(p["issues_pendientes"]) > 0 and p["fecha_p50"] > gen.CORTE.isoformat()
    total = defaultdict(float)
    for f in t["pronostico_distribucion"]:
        total[f["proyecto"]] += float(f["probabilidad"])
    abiertos = {p["proyecto"] for p in t["pronostico_termino"] if p["estado"] == "En curso"}
    assert set(total) == abiertos
    assert all(abs(v - 1) < 0.01 for v in total.values())


# --- historias ---------------------------------------------------------------------------------


def _previsibilidad(t, proyecto: str) -> float:
    comprometido = sum(int(c["puntos"]) for c in t["compromisos"] if c["proyecto"] == proyecto)
    completado = sum(int(c["puntos"]) for c in t["compromisos"] if c["proyecto"] == proyecto and c["completada"] == "1")
    return completado / comprometido


def test_historia_salud_la_ficha_clinica_crece_y_se_atrasa(t):
    ficha = next(p for p in t["pronostico_termino"] if p["proyecto"] == "SAL-FIC")
    plan = next(p for p in t["proyectos"] if p["proyecto"] == "SAL-FIC")
    assert int(plan["puntos_agregados"]) > 0.2 * int(plan["puntos_planificados"])
    assert ficha["estado"] == "En curso"
    assert 50 <= int(ficha["atraso_p85_dias"]) <= 110  # unos cinco sprints tarde


def test_historia_energia_integraciones_concentra_el_bloqueo(t):
    horas = defaultdict(int)
    for d in t["dependencias"]:
        if d["industria"] == "Energia":
            horas[d["equipo_bloqueante"]] += int(d["horas_bloqueado"])
    total = sum(horas.values())
    assert max(horas, key=horas.get) == "Integraciones"
    assert 0.33 <= horas["Integraciones"] / total <= 0.48
    por_industria = defaultdict(int)
    for d in t["dependencias"]:
        por_industria[d["industria"]] += int(d["horas_bloqueado"])
    assert por_industria["Energia"] == max(por_industria.values())  # la empresa más bloqueada


def test_historia_manufactura_erp_previsible_y_a_tiempo(t):
    assert 0.86 <= _previsibilidad(t, "MAN-ERP") <= 0.95
    erp = next(p for p in t["pronostico_termino"] if p["proyecto"] == "MAN-ERP")
    assert erp["fecha_p50"] <= erp["fin_comprometido"]
    previsibilidad = {i: [] for i in gen.INDUSTRIAS}
    for p in t["proyectos"]:
        previsibilidad[p["industria"]].append(_previsibilidad(t, p["proyecto"]))
    promedio = {i: sum(v) / len(v) for i, v in previsibilidad.items()}
    assert promedio["Manufactura"] == max(promedio.values())
