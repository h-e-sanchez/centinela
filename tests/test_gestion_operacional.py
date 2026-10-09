"""La operación clínica es coherente consigo misma y con la producción, y cuenta las tres historias que promete."""

from __future__ import annotations

import csv
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
CARPETA = DATA / "gestion-operacional"

_spec = importlib.util.spec_from_file_location("generar_gestion_operacional", DATA / "generar_gestion_operacional.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["generar_gestion_operacional"] = gen
_spec.loader.exec_module(gen)


def _leer(nombre: str) -> list[dict]:
    with (CARPETA / f"{nombre}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def t():
    return {n: _leer(n) for n in gen.ARCHIVOS}


def _suma(filas, clave, *cols) -> dict:
    d = defaultdict(lambda: [0.0] * len(cols))
    for x in filas:
        for i, c in enumerate(cols):
            d[clave(x)][i] += float(x[c])
    return d


def _tasa(filas, num: str, den: str, **filtro) -> float:
    sel = [x for x in filas if all(x[k] == v for k, v in filtro.items())]
    return sum(float(x[num]) for x in sel) / sum(float(x[den]) for x in sel)


def test_csv_al_dia_y_reproducibles(tmp_path):
    gen.escribir(gen.generar(), tmp_path)
    for nombre in gen.ARCHIVOS:
        nuevo = (tmp_path / f"{nombre}.csv").read_bytes()
        guardado = (CARPETA / f"{nombre}.csv").read_bytes().replace(b"\r\n", b"\n")
        assert nuevo == guardado, f"{nombre}.csv desactualizado: corre python data/generar_gestion_operacional.py"


def test_clinicas_y_meses_son_los_de_salud_en_el_reporte_1(t):
    with (DATA / "escenarios" / "montos.csv").open(encoding="utf-8", newline="") as f:
        real = [x for x in csv.DictReader(f) if x["industria"] == "Salud" and x["version"] == "Real"]
    assert {x["sucursal"] for x in t["sucursales"]} == {x["sucursal"] for x in real}
    meses_real = {(int(x["anio"]), int(x["mes"])) for x in real}
    assert {(int(x["anio"]), int(x["mes"])) for x in t["camas"]} <= meses_real


def test_produccion_sale_de_la_operacion(t):
    clave = lambda x: (x["fecha"], x["sucursal"], x["linea"])
    prod = _suma(t["produccion"], clave, "prestaciones")
    for x in t["camas"]:
        assert prod[clave(x)][0] == float(x["dias_cama_ocupados"])
    por_mes = lambda filas, col: _suma(filas, lambda x: (x["fecha"], x["sucursal"]), col)
    for linea, filas, col in (("Pabellón", t["pabellones"], "cirugias_realizadas"),
                              ("Urgencia", t["urgencia"], "atenciones"),
                              ("Consultas", t["ambulatorio"], "consultas_realizadas")):
        for (fecha, sucursal), (n,) in por_mes(filas, col).items():
            assert prod[(fecha, sucursal, linea)][0] == n, (linea, fecha, sucursal)
    for unidad in ("Laboratorio", "Imagenología"):
        for (fecha, sucursal), (n,) in por_mes([x for x in t["apoyo"] if x["unidad"] == unidad], "examenes").items():
            assert prod[(fecha, sucursal, unidad)][0] == n


def test_suspensiones_por_causa_cuadran_con_pabellones(t):
    clave = lambda x: (x["fecha"], x["sucursal"])
    assert _suma(t["suspensiones"], clave, "suspendidas") == _suma(t["pabellones"], clave, "cirugias_suspendidas")


def test_integridad_de_cada_fila(t):
    for x in t["camas"]:
        assert int(x["dias_cama_ocupados"]) <= int(x["dias_cama_disponibles"])
    for x in t["pabellones"]:
        assert int(x["cirugias_realizadas"]) + int(x["cirugias_suspendidas"]) == int(x["cirugias_programadas"])
        assert int(x["horas_utilizadas"]) <= int(x["horas_habilitadas"])
        assert int(x["primeras_a_la_hora"]) <= int(x["primeras_del_dia"])
    for x in t["urgencia"]:
        assert int(x["atenciones_en_meta"]) <= int(x["atenciones"])
        assert int(x["hospitalizados"]) <= int(x["atenciones"])
    for x in t["ambulatorio"]:
        assert int(x["consultas_realizadas"]) + int(x["inasistencias"]) == int(x["consultas_agendadas"])
        assert int(x["horas_ofertadas"]) <= int(x["horas_box"])
    for x in t["apoyo"]:
        assert int(x["examenes_en_meta"]) <= int(x["examenes"])


def test_metas_tienen_valor_en_el_modelo(t):
    tmdl = (RAIZ / "powerbi" / "gestion-operacional" / "gestion-operacional.SemanticModel" / "definition" / "tables"
            / "metas.tmdl").read_text(encoding="utf-8")
    for x in t["metas"]:
        assert f'"{x["indicador"]}", [' in tmdl, f"{x['indicador']} sin medida en «Valor del indicador»"
        assert x["sentido"] in ("mayor", "menor")


def test_historia_invierno_llena_camas_y_frena_urgencia(t):
    for servicio in ("Pediatría", "Médico-quirúrgico"):
        assert _tasa(t["camas"], "dias_cama_ocupados", "dias_cama_disponibles", fecha="2026-07-01", linea=servicio) > 0.9
    julio = _tasa(t["urgencia"], "horas_espera_cama", "hospitalizados", fecha="2026-07-01")
    enero = _tasa(t["urgencia"], "horas_espera_cama", "hospitalizados", fecha="2026-01-01")
    assert julio > 2 * enero
    assert _tasa(t["urgencia"], "atenciones_en_meta", "atenciones", fecha="2026-07-01") < 0.75


def test_historia_poniente_suspende_por_causas_evitables(t):
    poniente = _tasa(t["pabellones"], "cirugias_suspendidas", "cirugias_programadas", sucursal="Clínica Poniente")
    oriente = _tasa(t["pabellones"], "cirugias_suspendidas", "cirugias_programadas", sucursal="Clínica Oriente")
    assert poniente > 0.14 and poniente > 2 * oriente
    evitables = sum(int(x["suspendidas"]) for x in t["suspensiones"]
                    if x["sucursal"] == "Clínica Poniente" and x["evitable"] == "1")
    total = sum(int(x["suspendidas"]) for x in t["suspensiones"] if x["sucursal"] == "Clínica Poniente")
    assert evitables / total > 0.9
    assert _tasa(t["pabellones"], "primeras_a_la_hora", "primeras_del_dia", sucursal="Clínica Poniente") < 0.5


def test_historia_centro_estada_prolongada(t):
    iema = _tasa(t["camas"], "dias_estada", "dias_estada_esperados", sucursal="Clínica Centro", linea="Médico-quirúrgico")
    assert iema > 1.2
    for otra in ("Clínica Oriente", "Clínica Poniente"):
        assert _tasa(t["camas"], "dias_estada", "dias_estada_esperados", sucursal=otra, linea="Médico-quirúrgico") < 1.1
