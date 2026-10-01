"""La vitrina: catálogo completo, descargas al día con sus fuentes, guías fieles al modelo y sin datos personales."""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import re
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
REPORTES = RAIZ / "reportes"
CATALOGO = json.loads((REPORTES / "catalogo.json").read_text(encoding="utf-8"))["reportes"]
TMDL = RAIZ / "powerbi" / "centinela.SemanticModel" / "definition" / "tables" / "desviacion.tmdl"
CAMPOS = {"slug", "titulo", "resumen", "tema", "fecha", "embed_url", "habilidades", "descargas", "tecnico"}

_spec = importlib.util.spec_from_file_location("empaquetar", RAIZ / "herramientas" / "empaquetar_descargas.py")
empaquetar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(empaquetar)


def _sin_cr(datos: bytes) -> bytes:
    return datos.replace(b"\r\n", b"\n")


@pytest.mark.parametrize("rep", CATALOGO, ids=[r["slug"] for r in CATALOGO])
def test_catalogo_completo_y_archivos_presentes(rep):
    assert CAMPOS <= set(rep), f"faltan campos: {CAMPOS - set(rep)}"
    carpeta = REPORTES / rep["slug"]
    assert (carpeta / "guia.md").exists()
    assert rep["embed_url"].startswith("https://app.powerbi.com/view?r=")
    for d in rep["descargas"]:
        if not d.get("opcional"):
            assert (carpeta / d["archivo"]).exists(), f"falta {d['archivo']}"


def test_un_solo_reporte_destacado():
    assert sum(1 for r in CATALOGO if r.get("destacado")) == 1


def test_zip_csv_al_dia():
    with zipfile.ZipFile(empaquetar.DESTINO / "centinela-datos-csv.zip") as zf:
        guardado = {n: _sin_cr(zf.read(n)) for n in zf.namelist()}
    esperado = {n: _sin_cr(d) for n, d in empaquetar.entradas_csv()}
    assert guardado == esperado, "corre python herramientas/empaquetar_descargas.py"


def test_zip_pbip_al_dia_y_sin_archivos_locales():
    with zipfile.ZipFile(empaquetar.DESTINO / "centinela-pbip.zip") as zf:
        guardado = {n: _sin_cr(zf.read(n)) for n in zf.namelist()}
    assert not any(Path(n).name in empaquetar.EXCLUIR_PBIP for n in guardado)
    assert "centinela.pbip" in guardado
    esperado = {n: _sin_cr(d) for n, d in empaquetar.entradas_pbip()}
    assert guardado == esperado, "corre python herramientas/empaquetar_descargas.py"


def test_xlsx_coincide_con_los_csv():
    openpyxl = pytest.importorskip("openpyxl")
    libro = openpyxl.load_workbook(empaquetar.DESTINO / "centinela-datos.xlsx", read_only=True)
    for nombre in ("presupuesto", "real"):
        filas_xlsx = [[str(c) if c is not None else "" for c in fila] for fila in libro[nombre].iter_rows(values_only=True)]
        with (empaquetar.ESCENARIOS / f"{nombre}.csv").open(encoding="utf-8") as f:
            filas_csv = list(csv.reader(f))
        assert filas_xlsx[0] == filas_csv[0]
        assert len(filas_xlsx) == len(filas_csv)
        for a, b in zip(filas_xlsx[1:], filas_csv[1:]):
            assert a[:6] == b[:6] and float(a[6]) == float(b[6])


def test_guias_solo_citan_medidas_del_modelo():
    medidas = {
        m.group(1) or m.group(2)
        for m in re.finditer(r"^\t(?:measure|column) (?:'((?:[^']|'')+)'|(\S+))", _sin_cr(TMDL.read_bytes()).decode("utf-8"), re.MULTILINE)
    }
    for rep in CATALOGO:
        guia = (REPORTES / rep["slug"] / "guia.md").read_text(encoding="utf-8")
        bloque = guia[guia.index("```dax"):guia.index("```", guia.index("```dax") + 6)]
        definidas = re.findall(r"^(?!VAR\b)([^\s=][^=\n]*?) =", bloque, re.MULTILINE)  # VAR x = ... no es medida
        assert definidas, "la guía no define medidas"
        for nombre in definidas:
            assert nombre.strip() in medidas, f"{rep['slug']}: {nombre} no existe en el TMDL"


def test_sin_correos_ni_telefonos_en_la_web():
    correo = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    telefono = re.compile(r"\+?56\s?9\s?\d{4}\s?\d{4}")
    archivos = list(RAIZ.glob("*.html")) + list(REPORTES.rglob("*.md")) + [REPORTES / "catalogo.json"]
    for ruta in archivos:
        texto = ruta.read_text(encoding="utf-8")
        assert not correo.search(texto), f"correo en {ruta.name}"
        assert not telefono.search(texto), f"teléfono en {ruta.name}"


def test_leeme_del_zip_describe_todas_las_columnas():
    with zipfile.ZipFile(empaquetar.DESTINO / "centinela-datos-csv.zip") as zf:
        leeme = zf.read("LEEME.txt").decode("utf-8")
        cabecera = next(csv.reader(io.StringIO(zf.read("real.csv").decode("utf-8"))))
    for columna in cabecera:
        assert columna in leeme
