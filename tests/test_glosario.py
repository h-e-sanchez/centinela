"""El glosario de cada reporte está al día con su modelo y explica todas las medidas."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("generar_glosario", RAIZ / "herramientas" / "generar_glosario.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["generar_glosario"] = gen  # dataclasses necesita el módulo registrado
_spec.loader.exec_module(gen)
CATALOGO = gen.catalogo()
IDS = [r["slug"] for r in CATALOGO]


@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_glosario_al_dia(rep):
    guardado = (gen.REPORTES / rep["slug"] / "glosario.md").read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
    assert guardado == gen.glosario(rep), "corre python herramientas/generar_glosario.py"


@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_todas_las_medidas_tienen_descripcion_y_formula(rep):
    medidas, _ = gen.leer_modelo(RAIZ / rep["modelo"])
    assert medidas
    for m in medidas:
        assert m.descripcion, f"{m.nombre} sin descripción /// en el TMDL"
        assert m.expresion.strip(), f"{m.nombre} sin fórmula"
        assert "lineageTag" not in m.expresion and "displayFolder" not in m.expresion, m.nombre


@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_conceptos_escritos_a_mano(rep):
    texto = (gen.REPORTES / rep["slug"] / "conceptos.md").read_text(encoding="utf-8")
    assert texto.startswith("## Conceptos")
    assert texto.count("\n### ") >= 4, "los conceptos se agrupan en temas"


@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_csv_del_glosario_al_dia_para_power_bi(rep):
    guardado = (gen.REPORTES / rep["slug"] / "glosario.csv").read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
    assert guardado == gen.glosario_csv(rep), "corre python herramientas/generar_glosario.py"
    medidas, _ = gen.leer_modelo(RAIZ / rep["modelo"])
    assert sum(1 for linea in guardado.splitlines() if ",Medida," in linea) == len(medidas)
