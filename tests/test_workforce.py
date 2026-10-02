"""Los datos de Workforce cuentan la historia que prometen y están calibrados con las referencias citadas."""

from __future__ import annotations

import csv
import importlib.util
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"
CARPETA = DATA / "workforce"

_spec = importlib.util.spec_from_file_location("generar_workforce", DATA / "generar_workforce.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["generar_workforce"] = gen  # dataclasses necesita el módulo registrado
_spec.loader.exec_module(gen)


def _leer(nombre: str) -> list[dict]:
    with (CARPETA / f"{nombre}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def t():
    return {n: _leer(n) for n in gen.ARCHIVOS}


INDUSTRIAS = list(gen.INDUSTRIAS)


@pytest.fixture(scope="module")
def tasas(t):
    """Tasa global (sin licencias parentales) por industria y, dentro de ella, por estamento, sexo y mes."""
    personas = {p["id_persona"]: p for p in t["personas"]}
    parental = {e["id_episodio"] for e in t["episodios"] if e["tipo"] == "Licencia parental"}
    perdidos, disponibles = Counter(), Counter()

    def claves(p, fecha):
        return [(p["industria"], c) for c in ("total", p["estamento"], p["sexo"], int(fecha[5:7]))]

    for f in t["ausencia_diaria"]:
        if f["id_episodio"] not in parental:
            for clave in claves(personas[f["id_persona"]], f["fecha"]):
                perdidos[clave] += 1
    for f in t["disponibilidad_mensual"]:
        for clave in claves(personas[f["id_persona"]], f["fecha"]):
            disponibles[clave] += int(f["dias_habiles"])
    salida = defaultdict(dict)
    for (industria, clave), dias in disponibles.items():
        salida[industria][clave] = perdidos[(industria, clave)] / dias
    return salida


def test_csv_al_dia_y_reproducibles(tmp_path):
    gen.escribir(gen.generar(), tmp_path)
    for nombre in gen.ARCHIVOS:
        nuevo = (tmp_path / f"{nombre}.csv").read_bytes()
        guardado = (CARPETA / f"{nombre}.csv").read_bytes().replace(b"\r\n", b"\n")
        assert nuevo == guardado, f"{nombre}.csv desactualizado: corre python data/generar_workforce.py"


def test_tasa_global_por_industria(tasas):
    # Salud a escala de clínica privada (bajo el 10,8% del sector público); Energía, la más baja.
    assert 0.055 <= tasas["Salud"]["total"] <= 0.085
    assert 0.04 <= tasas["Manufactura"]["total"] <= 0.07
    assert 0.025 <= tasas["Energia"]["total"] <= 0.045
    assert tasas["Energia"]["total"] < tasas["Manufactura"]["total"] < tasas["Salud"]["total"]


def test_orden_de_estamentos_en_salud_como_la_dipres(tasas):
    s = tasas["Salud"]
    assert s["Directivos"] < s["Profesionales"] < s["Auxiliares"] < s["Técnicos"]
    assert s["Administrativos"] < s["Técnicos"]


@pytest.mark.parametrize("industria", INDUSTRIAS)
def test_directivos_se_ausentan_menos_que_la_operacion(tasas, industria):
    operacion = "Técnicos" if industria == "Salud" else "Operarios"
    assert tasas[industria]["Directivos"] < tasas[industria][operacion]


def test_mujeres_se_ausentan_casi_el_doble_en_salud(tasas):
    assert 1.5 <= tasas["Salud"]["F"] / tasas["Salud"]["M"] <= 2.4


@pytest.mark.parametrize("industria", INDUSTRIAS)
def test_pico_de_invierno_y_minimo_en_febrero(tasas, industria):
    t = tasas[industria]
    assert max(range(1, 13), key=lambda m: t[m]) in (5, 6, 7, 8)
    assert t[2] < t[6]


def test_salud_mental_es_el_principal_motivo(t):
    dias = Counter()
    for e in t["episodios"]:
        if e["tipo"] == "Licencia común":
            dias[e["grupo_diagnostico"]] += int(e["dias_habiles"])
    total = sum(dias.values())
    assert dias.most_common(1)[0][0] == "Salud mental"
    assert 0.25 <= dias["Salud mental"] / total <= 0.40


@pytest.mark.parametrize("industria", INDUSTRIAS)
def test_rotacion_anual_y_mas_alta_el_primer_anio(t, industria):
    personas = [p for p in t["personas"] if p["industria"] == industria]
    for anio in ("2025", "2026"):
        egresos = sum(1 for p in personas if p["fecha_egreso"].startswith(anio))
        activos = sum(1 for p in personas if p["fecha_ingreso"] <= f"{anio}-12-31"
                      and (not p["fecha_egreso"] or p["fecha_egreso"] > f"{anio}-12-31"))
        assert 0.06 <= egresos / activos <= 0.25, anio
    motivos = Counter(p["motivo_egreso"] for p in t["personas"] if p["fecha_egreso"])
    assert motivos["Voluntario"] > motivos["Involuntario"] > motivos["Jubilación"] > 0


def test_ausencias_dentro_del_contrato(t):
    personas = {p["id_persona"]: p for p in t["personas"]}
    for f in t["ausencia_diaria"]:
        p = personas[f["id_persona"]]
        assert p["fecha_ingreso"] <= f["fecha"] and (not p["fecha_egreso"] or f["fecha"] <= p["fecha_egreso"])
    assert {f["id_episodio"] for f in t["ausencia_diaria"]} == {e["id_episodio"] for e in t["episodios"]}


def _costo_por_hora(t, sede: str, desde: str, hasta: str) -> tuple[float, float]:
    fs = [f for f in t["cobertura_mensual"]
          if f["sede"] == sede and desde <= f"{f['anio']}-{int(f['mes']):02d}" <= hasta]
    costo = sum(float(f[c]) for f in fs for c in ("costo_sobretiempo", "costo_pool", "costo_externo"))
    horas = sum(float(f[c]) for f in fs for c in ("horas_sobretiempo", "horas_pool", "horas_externo"))
    sobretiempo = sum(float(f["horas_sobretiempo"]) for f in fs) / sum(float(f["horas_requeridas"]) for f in fs)
    return costo / horas, sobretiempo


@pytest.mark.parametrize("industria", INDUSTRIAS)
def test_piloto_baja_sobretiempo_y_costo_frente_al_control(t, industria):
    piloto = gen.INDUSTRIAS[industria].piloto
    antes, st_antes = _costo_por_hora(t, piloto, "2025-01", "2025-06")
    despues, st_despues = _costo_por_hora(t, piloto, "2025-10", "2026-12")
    assert st_antes > 0.55 and st_despues < 0.30
    assert despues / antes < 0.88
    for control in gen.INDUSTRIAS[industria].sedes:
        if control != piloto:
            c_antes, _ = _costo_por_hora(t, control, "2025-01", "2025-06")
            c_despues, _ = _costo_por_hora(t, control, "2025-10", "2026-12")
            assert abs(c_despues / c_antes - 1) < 0.08, control


def test_cobertura_cuadra_con_las_horas_requeridas(t):
    for f in t["cobertura_mensual"]:
        partes = sum(float(f[c]) for c in ("horas_sobretiempo", "horas_pool", "horas_externo", "horas_no_cubiertas"))
        assert abs(partes - float(f["horas_requeridas"])) < 0.5


def test_credibilidad_crece_con_la_exposicion(t):
    celdas = {(f["sede"], f["unidad"], f["estamento"]): f for f in t["pronostico"] if f["mes"] == "1"}
    por_estamento = defaultdict(list)
    for (_, _, est), f in celdas.items():
        por_estamento[(f["industria"], est)].append((float(f["anios_persona"]), float(f["z_credibilidad"])))
    for est, pares in por_estamento.items():
        pares.sort()
        zs = [z for _, z in pares]
        assert zs == sorted(zs), f"{est}: Z debe crecer con los años-persona"
        assert all(0 <= z <= 1 for z in zs)


def test_pronostico_ordenado_y_coherente(t):
    for f in t["pronostico"]:
        assert int(f["dias_p50"]) <= int(f["dias_p90"])
        assert float(f["varianza_dias"]) >= 0
        assert 0 <= float(f["tasa_credibilidad"]) < 0.3
        if float(f["z_credibilidad"]) == 1:
            assert f["tasa_credibilidad"] == f["tasa_observada"]


def test_sedes_alineadas_con_el_reporte_de_presupuesto():
    # Las mismas empresas en los dos reportes: las sedes son las sucursales de presupuesto-vs-real.
    spec = importlib.util.spec_from_file_location("generar_escenarios", DATA / "generar_escenarios.py")
    esc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(esc)
    for industria, ind in gen.INDUSTRIAS.items():
        assert set(ind.sedes) == set(esc.SUCURSALES[industria]), industria


def test_ids_sinteticos_sin_nombres(t):
    assert all(p["id_persona"].startswith("P") and p["id_persona"][1:].isdigit() for p in t["personas"])
    assert set(t["personas"][0]) == set(gen.ARCHIVOS["personas"])
