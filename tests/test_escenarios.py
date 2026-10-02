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


# --- Detalle para Power BI (montos.csv) ---------------------------------------------------------

def _montos() -> list[dict]:
    with (DATA / "escenarios" / "montos.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _suma(filas, version, anio, llave=("industria", "mes", "centro_costo", "componente")) -> Counter:
    s = Counter()
    for f in filas:
        if f["version"] == version and int(f["anio"]) == anio:
            s[tuple(str(f[k]) for k in llave)] += float(f["monto"])
    return s


def test_montos_versionado_al_dia(tmp_path):
    ruta = tmp_path / "montos.csv"
    gen.escribir(gen.generar_montos(), ruta, gen.CAMPOS_MONTOS)
    assert ruta.read_bytes() == (DATA / "escenarios" / "montos.csv").read_bytes(), "montos.csv desactualizado"


def test_montos_2026_suman_lo_mismo_que_los_csv_agregados():
    # Así el detalle de Power BI y reporte.html cuentan las mismas historias.
    montos = _montos()
    for version, agregado in zip(("Presupuesto", "Real"), gen.generar()):
        esperado = _suma([{**f, "version": version} for f in agregado], version, gen.ANIO)
        assert _suma(montos, version, gen.ANIO) == esperado, version


def test_forecast_3_mas_9():
    montos = _montos()
    for anio in (gen.ANIO_BASE, gen.ANIO):
        real, fcst = _suma(montos, "Real", anio), _suma(montos, "Forecast", anio)
        for clave, monto in real.items():
            if int(clave[1]) <= gen.MESES_REALES_FORECAST:
                assert fcst[clave] == monto, f"{anio} {clave}: el trimestre real debe copiarse al forecast"
    # El run-rate de marzo no anticipa la campaña de invierno de Salud.
    clave = ("industria", "anio", "mes", "grupo_cuenta")
    real, fcst = _suma(montos, "Real", gen.ANIO, clave), _suma(montos, "Forecast", gen.ANIO, clave)
    for mes in gen.INVIERNO:
        k = ("Salud", str(gen.ANIO), str(mes), "Costos")
        assert real[k] > fcst[k] * 1.1


def test_montos_completos_y_sin_negativos():
    montos = _montos()
    assert all(int(f["monto"]) >= 0 for f in montos)
    assert {f["version"] for f in montos} == set(gen.VERSIONES)
    assert {int(f["anio"]) for f in montos} == {gen.ANIO_BASE, gen.ANIO}
    for industria, sucursales in gen.SUCURSALES.items():
        assert {f["sucursal"] for f in montos if f["industria"] == industria} == set(sucursales)
    assert {f["tipo_gasto"] for f in montos if f["grupo_cuenta"] == "Ingresos"} == {"Ingreso"}
    assert {f["tipo_gasto"] for f in montos if f["grupo_cuenta"] != "Ingresos"} == {"Fijo", "Variable"}


def test_salud_sobregasto_de_invierno_se_concentra_en_poniente():
    montos = _montos()
    desvio = Counter()
    for f in montos:
        if (f["industria"], f["grupo_cuenta"]) == ("Salud", "Costos") and int(f["anio"]) == gen.ANIO \
                and int(f["mes"]) in gen.INVIERNO and f["version"] != "Forecast":
            desvio[f["sucursal"]] += int(f["monto"]) * (1 if f["version"] == "Real" else -1)
    assert max(desvio, key=desvio.get) == "Clínica Poniente"


def test_repartir_no_pierde_pesos():
    for total in (0, 1, 999, -1_234_567, 41_000_001):
        partes = gen.repartir(total, [0.45, 0.35, 0.2])
        assert sum(partes) == total
