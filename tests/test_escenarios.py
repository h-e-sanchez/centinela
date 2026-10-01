"""Los tres escenarios cuentan la historia que prometen: positivo, neutro y rojo con estacionalidad."""

from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def _cargar(nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, DATA / f"{nombre}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


gen = _cargar("generar_escenarios")


def _ro(filas: list[dict], industria: str, meses=None) -> float:
    s = Counter()
    for f in filas:
        if f["industria"] == industria and (meses is None or int(f["mes"]) in meses):
            s[f["grupo_cuenta"]] += float(f["monto"])
    return s["Ingresos"] - s["Costos"] - s["Gastos Operacionales"]


def _desv(industria: str, meses=None) -> float:
    ppto, real = gen.generar()
    p = _ro(ppto, industria, meses)
    return (_ro(real, industria, meses) - p) / abs(p)


def test_manufactura_es_positiva():
    assert _desv("Manufactura") > 0.10


def test_energia_es_neutra():
    assert abs(_desv("Energia")) < 0.02


def test_salud_es_roja_y_peor_en_invierno():
    assert _desv("Salud") < -0.30
    invierno = _desv("Salud", gen.INVIERNO)
    resto = _desv("Salud", [m for m in range(1, 13) if m not in gen.INVIERNO])
    assert invierno < resto - 0.5, "la campaña de invierno debe pesar mucho más que el resto del año"
    _, real = gen.generar()
    assert all(_ro(real, "Salud", [m]) < 0 for m in gen.INVIERNO), "invierno con resultado operacional negativo"


def test_reproducible_y_csv_versionados_al_dia(tmp_path):
    for nombre, filas in zip(("presupuesto.csv", "real.csv"), gen.generar()):
        ruta = tmp_path / nombre
        gen.escribir(filas, ruta)
        assert ruta.read_bytes() == (DATA / "escenarios" / nombre).read_bytes(), f"{nombre} desactualizado"


def test_json_web_coincide_con_los_csv():
    exp = _cargar("exportar_escenarios_web")
    guardado = json.loads((DATA / "escenarios-web.json").read_text(encoding="utf-8"))
    assert guardado == exp.combinar()
    assert set(guardado) == {"Manufactura", "Energia", "Salud"}


def test_cada_industria_tiene_los_tres_grupos_de_cuenta():
    with (DATA / "escenarios" / "presupuesto.csv").open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for industria in gen.ESTRUCTURA:
        grupos = {f["grupo_cuenta"] for f in filas if f["industria"] == industria}
        assert grupos == {"Ingresos", "Costos", "Gastos Operacionales"}
