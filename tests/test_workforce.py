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


@pytest.fixture(scope="module")
def tasas(t):
    """Tasa global (sin licencias parentales) por estamento, sexo, mes y en total."""
    personas = {p["id_persona"]: p for p in t["personas"]}
    parental = {e["id_episodio"] for e in t["episodios"] if e["tipo"] == "Licencia parental"}
    perdidos, disponibles = Counter(), Counter()
    for f in t["ausencia_diaria"]:
        if f["id_episodio"] not in parental:
            p = personas[f["id_persona"]]
            for clave in ("total", p["estamento"], p["sexo"], int(f["fecha"][5:7])):
                perdidos[clave] += 1
    for f in t["disponibilidad_mensual"]:
        p = personas[f["id_persona"]]
        for clave in ("total", p["estamento"], p["sexo"], int(f["fecha"][5:7])):
            disponibles[clave] += int(f["dias_habiles"])
    return {k: perdidos[k] / disponibles[k] for k in disponibles}


def test_csv_al_dia_y_reproducibles(tmp_path):
    gen.escribir(gen.generar(), tmp_path)
    for nombre in gen.ARCHIVOS:
        nuevo = (tmp_path / f"{nombre}.csv").read_bytes()
        guardado = (CARPETA / f"{nombre}.csv").read_bytes().replace(b"\r\n", b"\n")
        assert nuevo == guardado, f"{nombre}.csv desactualizado: corre python data/generar_workforce.py"


def test_tasa_global_de_clinica_privada(tasas):
    assert 0.06 <= tasas["total"] <= 0.085


def test_orden_de_estamentos_como_la_dipres(tasas):
    assert tasas["Directivos"] < tasas["Profesionales"] < tasas["Auxiliares"] < tasas["Técnicos"]
    assert tasas["Administrativos"] < tasas["Técnicos"]


def test_mujeres_se_ausentan_casi_el_doble(tasas):
    assert 1.5 <= tasas["F"] / tasas["M"] <= 2.3


def test_pico_de_invierno_y_minimo_en_febrero(tasas):
    assert max(range(1, 13), key=lambda m: tasas[m]) in (5, 6, 7)
    assert tasas[2] < tasas[6]


def test_salud_mental_es_el_principal_motivo(t):
    dias = Counter()
    for e in t["episodios"]:
        if e["tipo"] == "Licencia común":
            dias[e["grupo_diagnostico"]] += int(e["dias_habiles"])
    total = sum(dias.values())
    assert dias.most_common(1)[0][0] == "Salud mental"
    assert 0.25 <= dias["Salud mental"] / total <= 0.40


def test_rotacion_anual_y_mas_alta_el_primer_anio(t):
    for anio in ("2025", "2026"):
        egresos = sum(1 for p in t["personas"] if p["fecha_egreso"].startswith(anio))
        activos = sum(1 for p in t["personas"] if p["fecha_ingreso"] <= f"{anio}-12-31"
                      and (not p["fecha_egreso"] or p["fecha_egreso"] > f"{anio}-12-31"))
        assert 0.10 <= egresos / activos <= 0.20, anio
    motivos = Counter(p["motivo_egreso"] for p in t["personas"] if p["fecha_egreso"])
    assert motivos["Voluntario"] > motivos["Involuntario"] > motivos["Jubilación"] > 0


def test_ausencias_dentro_del_contrato(t):
    personas = {p["id_persona"]: p for p in t["personas"]}
    for f in t["ausencia_diaria"]:
        p = personas[f["id_persona"]]
        assert p["fecha_ingreso"] <= f["fecha"] and (not p["fecha_egreso"] or f["fecha"] <= p["fecha_egreso"])
    assert {f["id_episodio"] for f in t["ausencia_diaria"]} == {e["id_episodio"] for e in t["episodios"]}


def _costo_por_hora(t, clinica: str, desde: str, hasta: str) -> tuple[float, float]:
    fs = [f for f in t["cobertura_mensual"]
          if f["clinica"] == clinica and desde <= f"{f['anio']}-{int(f['mes']):02d}" <= hasta]
    costo = sum(float(f[c]) for f in fs for c in ("costo_sobretiempo", "costo_pool", "costo_externo"))
    horas = sum(float(f[c]) for f in fs for c in ("horas_sobretiempo", "horas_pool", "horas_externo"))
    sobretiempo = sum(float(f["horas_sobretiempo"]) for f in fs) / sum(float(f["horas_requeridas"]) for f in fs)
    return costo / horas, sobretiempo


def test_piloto_de_norte_baja_sobretiempo_y_costo_frente_al_control(t):
    antes, st_antes = _costo_por_hora(t, "Norte", "2025-01", "2025-06")
    despues, st_despues = _costo_por_hora(t, "Norte", "2025-10", "2026-12")
    assert st_antes > 0.55 and st_despues < 0.30
    assert despues / antes < 0.90
    for control in ("Centro", "Sur"):
        c_antes, _ = _costo_por_hora(t, control, "2025-01", "2025-06")
        c_despues, _ = _costo_por_hora(t, control, "2025-10", "2026-12")
        assert abs(c_despues / c_antes - 1) < 0.08, control


def test_cobertura_cuadra_con_las_horas_requeridas(t):
    for f in t["cobertura_mensual"]:
        partes = sum(float(f[c]) for c in ("horas_sobretiempo", "horas_pool", "horas_externo", "horas_no_cubiertas"))
        assert abs(partes - float(f["horas_requeridas"])) < 0.5


def test_credibilidad_crece_con_la_exposicion(t):
    celdas = {(f["clinica"], f["unidad"], f["estamento"]): f for f in t["pronostico"] if f["mes"] == "1"}
    por_estamento = defaultdict(list)
    for (_, _, est), f in celdas.items():
        por_estamento[est].append((float(f["anios_persona"]), float(f["z_credibilidad"])))
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


def test_ids_sinteticos_sin_nombres(t):
    assert all(p["id_persona"].startswith("P") and p["id_persona"][1:].isdigit() for p in t["personas"])
    assert set(t["personas"][0]) == set(gen.ARCHIVOS["personas"])
