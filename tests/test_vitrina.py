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
CAMPOS = {"slug", "titulo", "resumen", "tema", "fecha", "modelo", "datos", "prefijo", "habilidades", "descargas", "tecnico"}
IDS = [r["slug"] for r in CATALOGO]

_spec = importlib.util.spec_from_file_location("empaquetar", RAIZ / "herramientas" / "empaquetar_descargas.py")
empaquetar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(empaquetar)


def _sin_cr(datos: bytes) -> bytes:
    return datos.replace(b"\r\n", b"\n")


def _objetos_del_modelo(rep) -> set[str]:
    """Medidas y columnas de todas las tablas del modelo semántico del reporte."""
    objetos = set()
    for ruta in (RAIZ / rep["modelo"]).glob("*.SemanticModel/definition/tables/*.tmdl"):
        texto = _sin_cr(ruta.read_bytes()).decode("utf-8")
        objetos |= {
            (m.group(1) or m.group(2)).replace("''", "'")
            for m in re.finditer(r"^\t(?:measure|column) (?:'((?:[^']|'')+)'|(\S+))", texto, re.MULTILINE)
        }
    return objetos


@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_catalogo_completo_y_archivos_presentes(rep):
    assert CAMPOS <= set(rep), f"faltan campos: {CAMPOS - set(rep)}"
    carpeta = REPORTES / rep["slug"]
    assert (carpeta / "guia.md").exists()
    assert (carpeta / "diccionario.json").exists()
    assert list((RAIZ / rep["modelo"]).glob("*.pbip")), f"{rep['modelo']} sin proyecto .pbip"
    assert empaquetar.csvs(rep), f"{rep['datos']} sin CSV"
    if rep.get("estado") == "en-preparacion":
        assert not rep.get("destacado"), "un reporte sin publicar no puede ser el destacado"
    else:
        assert rep["embed_url"].startswith("https://app.powerbi.com/view?r=")
    for d in rep["descargas"]:
        if not d.get("opcional"):
            assert (carpeta / d["archivo"]).exists(), f"falta {d['archivo']}"
            assert d["archivo"].startswith(f"descargas/{rep['prefijo']}-"), d["archivo"]



@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_cada_historia_tiene_un_titular_que_dice_que_mide(rep):
    # La vitrina muestra el titular con la cifra en negrita: «3,2% a 6,1%» sola no dice qué mide.
    for h in rep.get("historias", []):
        assert h.get("titular"), f"{h['resultado']} sin titular"
        assert h["resultado"] in h["titular"], f"el titular no contiene la cifra {h['resultado']}"
        assert len(h["titular"]) <= 70, f"titular largo ({len(h['titular'])}): {h['titular']}"
        assert h["titular"] != h["resultado"], "el titular debe decir qué mide la cifra"

def test_un_solo_reporte_destacado():
    assert sum(1 for r in CATALOGO if r.get("destacado")) == 1


def test_slugs_y_prefijos_unicos():
    assert len(set(IDS)) == len(IDS)
    assert len({r["prefijo"] for r in CATALOGO}) == len(CATALOGO)


@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_zip_csv_al_dia(rep):
    with zipfile.ZipFile(empaquetar.destino(rep) / f"{rep['prefijo']}-datos-csv.zip") as zf:
        guardado = {n: _sin_cr(zf.read(n)) for n in zf.namelist()}
    esperado = {n: _sin_cr(d) for n, d in empaquetar.entradas_csv(rep)}
    assert guardado == esperado, "corre python herramientas/empaquetar_descargas.py"


@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_zip_pbip_al_dia_y_sin_archivos_locales(rep):
    with zipfile.ZipFile(empaquetar.destino(rep) / f"{rep['prefijo']}-pbip.zip") as zf:
        guardado = {n: _sin_cr(zf.read(n)) for n in zf.namelist()}
    assert not any(Path(n).name in empaquetar.EXCLUIR_PBIP for n in guardado)
    assert any(n.endswith(".pbip") and "/" not in n for n in guardado)
    esperado = {n: _sin_cr(d) for n, d in empaquetar.entradas_pbip(rep)}
    assert guardado == esperado, "corre python herramientas/empaquetar_descargas.py"


def _igual(celda, texto: str) -> bool:
    if celda is None:
        return texto == ""
    if isinstance(celda, (int, float)):
        return float(celda) == float(texto)
    return str(celda) == texto


@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_xlsx_coincide_con_los_csv(rep):
    openpyxl = pytest.importorskip("openpyxl")
    libro = openpyxl.load_workbook(empaquetar.destino(rep) / f"{rep['prefijo']}-datos.xlsx", read_only=True)
    for ruta in empaquetar.csvs(rep):
        filas_xlsx = list(libro[ruta.stem[:31]].iter_rows(values_only=True))
        with ruta.open(encoding="utf-8") as f:
            filas_csv = list(csv.reader(f))
        assert list(filas_xlsx[0]) == filas_csv[0]
        assert len(filas_xlsx) == len(filas_csv)
        for a, b in zip(filas_xlsx[1:], filas_csv[1:]):
            assert all(_igual(x, y) for x, y in zip(a, b)), f"{ruta.name}: {a} != {b}"


@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_guia_solo_cita_medidas_de_su_modelo(rep):
    medidas = _objetos_del_modelo(rep)
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


@pytest.mark.parametrize("rep", CATALOGO, ids=IDS)
def test_leeme_del_zip_describe_todas_las_columnas(rep):
    with zipfile.ZipFile(empaquetar.destino(rep) / f"{rep['prefijo']}-datos-csv.zip") as zf:
        leeme = zf.read("LEEME.txt").decode("utf-8")
        for nombre in zf.namelist():
            if nombre.endswith(".csv"):
                for columna in next(csv.reader(io.StringIO(zf.read(nombre).decode("utf-8")))):
                    assert columna in leeme, f"{nombre}: {columna} sin describir en el LEEME"


def test_portada_presenta_el_producto_y_firma_al_autor():
    # El H1 es el producto; el autor va en la firma y en el pie (relato de portafolio).
    html = (RAIZ / "index.html").read_text(encoding="utf-8")
    assert re.search(r"<h1>\s*centinela\s*</h1>", html)
    assert re.search(r'class="firma">por Hernán Elías Sánchez', html)
    assert "Control de gestión, construido como software" in html


def test_enlaces_cruzados_del_portafolio():
    portada = (RAIZ / "index.html").read_text(encoding="utf-8")
    for sitio in ("consulta", "cartilla"):
        assert f"h-e-sanchez.github.io/{sitio}" in portada, f"portada sin enlace a {sitio}"
    for rel in ("index.html", "README.md"):
        assert "h-e-sanchez.github.io/consulta" in (RAIZ / rel).read_text(encoding="utf-8") or \
            "github.com/h-e-sanchez/consulta" in (RAIZ / rel).read_text(encoding="utf-8"), rel
    for rel in ("index.html", "ficha.html", "reporte.html", "datos.html"):
        assert 'class="firma-pie"' in (RAIZ / rel).read_text(encoding="utf-8"), f"{rel} sin firma en el pie"


@pytest.mark.parametrize("pagina", sorted(p.name for p in RAIZ.glob("*.html")))
def test_cada_pagina_mide_visitas_y_lo_declara(pagina):
    html = (RAIZ / pagina).read_text(encoding="utf-8")
    assert '<script src="analitica.js?v=1" data-sitio="centinela"></script>' in html
    assert "GoatCounter" in html.split("<footer", 1)[-1], "el pie debe avisar que medimos visitas"


def test_los_iframes_de_power_bi_cuentan_su_vista():
    for js in ("ficha.js", "reporte.js"):
        assert "analitica?.alVer(iframe" in (RAIZ / js).read_text(encoding="utf-8"), js
