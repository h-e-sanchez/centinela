"""Consistencia de los proyectos de Power BI (powerbi/<reporte>/, TMDL + PBIR) con el resto del repo.

No abre Power BI (no es posible en CI): verifica que el texto versionado diga lo mismo
que el resto del repo. Las pruebas genéricas corren sobre cada proyecto; las de reporte.html
y el semáforo, solo sobre presupuesto-vs-real.
"""

from __future__ import annotations

import importlib.util
import json
import re
import unicodedata
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("industria_inicial", RAIZ / "herramientas" / "industria_inicial.py")
industria_inicial = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(industria_inicial)
PROYECTOS = sorted(p.parent for p in (RAIZ / "powerbi").glob("*/*.pbip"))
IDS = [p.name for p in PROYECTOS]
PBI = RAIZ / "powerbi" / "presupuesto-vs-real"
TMDL = PBI / "centinela.SemanticModel" / "definition" / "tables" / "desviacion.tmdl"


def _modelo(proyecto: Path) -> Path:
    return next(proyecto.glob("*.SemanticModel"))


def _reporte(proyecto: Path) -> Path:
    return next(proyecto.glob("*.Report"))


def _objetos_tmdl() -> set[str]:
    texto = TMDL.read_text(encoding="utf-8")
    return {
        (m.group(2) or m.group(3)).replace("''", "'")
        for m in re.finditer(r"^\t(measure|column) (?:'((?:[^']|'')+)'|(\S+)) =", texto, re.MULTILINE)
    }


def test_reporte_solo_cita_medidas_que_existen_en_el_modelo():
    html = (RAIZ / "reporte.html").read_text(encoding="utf-8")
    js = (RAIZ / "reporte.js").read_text(encoding="utf-8")
    citadas = {n for grupo in re.findall(r'data-medidas="([^"]+)"', html) for n in grupo.split("|")}
    citadas |= set(re.findall(r'\["([^"]+)", (?:millones|pct|`)', js))  # tarjetas KPI
    assert citadas, "no se encontraron medidas citadas"
    faltan = citadas - _objetos_tmdl()
    assert not faltan, f"reporte cita medidas que no están en el TMDL: {faltan}"


def test_semaforo_del_modelo_usa_los_umbrales_del_motor():
    texto = TMDL.read_text(encoding="utf-8")
    bloque = texto[texto.index("column 'Estado Semáforo'"):texto.index("partition desviacion")]
    main = (RAIZ / "src" / "main.py").read_text(encoding="utf-8")
    umbral = re.search(r'"--umbral", type=float, default=([\d.]+)', main).group(1)
    critico = re.search(r'"--umbral-critico", type=float, default=([\d.]+)', main).group(1)
    assert f"ABS(pct) > {umbral}" in bloque
    assert f"ABS(pct) > {critico}" in bloque


def test_hay_un_proyecto_por_reporte():
    assert PBI in PROYECTOS
    for proyecto in PROYECTOS:
        assert len(list(proyecto.glob("*.pbip"))) == 1


@pytest.mark.parametrize("proyecto", PROYECTOS, ids=IDS)
def test_ninguna_medida_se_llama_como_una_columna_de_su_tabla(proyecto):
    """Desktop no abre el modelo si una medida se llama igual que una columna de su tabla.

    La comparación ignora mayúsculas y tildes, como Analysis Services. Pasó con «Estado» frente a la
    columna `estado` en proyectos-ti.
    """
    def clave(nombre: str) -> str:
        return "".join(ch for ch in unicodedata.normalize("NFKD", nombre.lower()) if not unicodedata.combining(ch))

    for archivo in (_modelo(proyecto) / "definition" / "tables").glob("*.tmdl"):
        objetos = {"measure": set(), "column": set()}
        for m in re.finditer(r"^\t(measure|column) (?:'((?:[^']|'')+)'|(\S+))", archivo.read_text(encoding="utf-8"), re.MULTILINE):
            objetos[m.group(1)].add(clave((m.group(2) or m.group(3)).replace("''", "'")))
        choques = objetos["measure"] & objetos["column"]
        assert not choques, f"{archivo.name}: medida y columna con el mismo nombre: {choques}"


@pytest.mark.parametrize("proyecto", PROYECTOS, ids=IDS)
def test_jsons_del_proyecto_son_validos_y_apuntan_bien(proyecto):
    for ruta in proyecto.rglob("*.json"):
        json.loads(ruta.read_text(encoding="utf-8-sig"))
    reporte = _reporte(proyecto)
    pbir = json.loads((reporte / "definition.pbir").read_text(encoding="utf-8"))
    destino = (reporte / pbir["datasetReference"]["byPath"]["path"]).resolve()
    assert (destino / "definition.pbism").exists()
    pbip = json.loads(next(proyecto.glob("*.pbip")).read_text(encoding="utf-8"))
    assert (proyecto / pbip["artifacts"][0]["report"]["path"] / "definition.pbir").exists()


@pytest.mark.parametrize("proyecto", PROYECTOS, ids=IDS)
def test_tmdl_usa_tabs_y_utf8_sin_bom(proyecto):
    # TMDL exige sangría con tabs; dentro de una expresión M o DAX pueden seguir espacios.
    for ruta in (_modelo(proyecto) / "definition").rglob("*.tmdl"):
        crudo = ruta.read_bytes()
        assert not crudo.startswith(b"\xef\xbb\xbf"), f"{ruta.name} tiene BOM"
        for n, linea in enumerate(crudo.decode("utf-8").splitlines(), 1):
            assert not linea.startswith(" "), f"{ruta.name}:{n} indentado con espacios"


def _objetos_por_tabla(proyecto: Path) -> dict[str, dict[str, set[str]]]:
    """{tabla: {"column": {...}, "measure": {...}}} leído de los TMDL del proyecto."""
    tablas = {}
    for ruta in (_modelo(proyecto) / "definition" / "tables").glob("*.tmdl"):
        texto = ruta.read_text(encoding="utf-8")
        tabla = re.search(r"^table (?:'([^']+)'|(\S+))", texto, re.MULTILINE)
        objetos = {"column": set(), "measure": set()}
        for m in re.finditer(r"^\t(column|measure) (?:'((?:[^']|'')+)'|(\S+))", texto, re.MULTILINE):
            objetos[m.group(1)].add((m.group(2) or m.group(3)).replace("''", "'"))
        tablas[tabla.group(1) or tabla.group(2)] = objetos
    return tablas


def _campos(nodo, alias=None):
    """Recorre el visual; las consultas guardadas por Desktop usan alias ("Source") declarados en "From"."""
    alias = dict(alias or {})
    if isinstance(nodo, dict):
        for d in nodo.get("From", []) if isinstance(nodo.get("From"), list) else []:
            alias[d.get("Name")] = d.get("Entity")
        for tipo in ("Column", "Measure"):
            if tipo in nodo and "Property" in nodo[tipo]:
                ref = nodo[tipo]["Expression"]["SourceRef"]
                yield tipo, ref.get("Entity") or alias.get(ref.get("Source")), nodo[tipo]["Property"]
        for v in nodo.values():
            yield from _campos(v, alias)
    elif isinstance(nodo, list):
        for v in nodo:
            yield from _campos(v, alias)


def _visuales(proyecto: Path) -> list[Path]:
    return list((_reporte(proyecto) / "definition" / "pages").glob("*/visuals/*/visual.json"))


@pytest.mark.parametrize("proyecto", PROYECTOS, ids=IDS)
def test_visuales_solo_usan_campos_y_medidas_del_modelo(proyecto):
    tablas = _objetos_por_tabla(proyecto)
    visuales = _visuales(proyecto)
    assert visuales, "el reporte no tiene visuales"
    for ruta in visuales:
        for tipo, tabla, prop in _campos(json.loads(ruta.read_text(encoding="utf-8"))):
            clave = "measure" if tipo == "Measure" else "column"
            assert prop in tablas.get(tabla, {}).get(clave, set()), f"{ruta.parent.name}: {clave} {tabla}.{prop}"


def _parametros_de_campo(proyecto: Path) -> set[str]:
    """Tablas que son parámetros de campo (columna con ParameterMetadata)."""
    tablas = set()
    for ruta in (_modelo(proyecto) / "definition" / "tables").glob("*.tmdl"):
        texto = ruta.read_text(encoding="utf-8")
        if "extendedProperty ParameterMetadata" in texto:
            tabla = re.search(r"^table (?:'([^']+)'|(\S+))", texto, re.MULTILINE)
            tablas.add(tabla.group(1) or tabla.group(2))
    return tablas


def _valores_guardados(visual: dict) -> list:
    valores = []
    for entrada in visual.get("objects", {}).get("general", []):
        filtro = entrada.get("properties", {}).get("filter")
        if filtro:
            for cond in filtro["filter"]["Where"]:
                valores += [v[0]["Literal"]["Value"] for v in cond["Condition"]["In"]["Values"]]
    return valores


@pytest.mark.parametrize("proyecto", PROYECTOS, ids=IDS)
def test_segmentadores_sin_seleccion_guardada(proyecto):
    # Un reporte público debe abrir en "Todas": una selección guardada en Desktop lo publica filtrado.
    # Excepciones: un parámetro de campo necesita una opción elegida para que el visual muestre una sola
    # dimensión, y los segmentadores de industria abren en la industria común de la vitrina.
    parametros = _parametros_de_campo(proyecto)
    for ruta in _visuales(proyecto):
        visual = json.loads(ruta.read_text(encoding="utf-8"))["visual"]
        if visual["visualType"] != "slicer":
            continue
        campos = list(_campos(visual["query"]))
        if {t for _, t, _ in campos} <= parametros:
            continue
        valores = _valores_guardados(visual)
        if {p for _, _, p in campos} <= industria_inicial.COLUMNAS_INDUSTRIA:
            assert valores == [f"'{industria_inicial.INDUSTRIA_INICIAL}'"], \
                f"{ruta.parent.name}: industria debe abrir en {industria_inicial.INDUSTRIA_INICIAL}"
        else:
            assert not valores, f"{ruta.parent.name}: segmentador con selección guardada"


@pytest.mark.parametrize("proyecto", PROYECTOS, ids=IDS)
def test_filtros_de_visual_van_fuera_de_visual(proyecto):
    # Desktop rechaza el archivo: «Se ha incluido una propiedad 'filterConfig' adicional en /visual».
    for ruta in _visuales(proyecto):
        assert "filterConfig" not in json.loads(ruta.read_text(encoding="utf-8"))["visual"], ruta.parent.name


@pytest.mark.parametrize("proyecto", PROYECTOS, ids=IDS)
def test_columnas_con_nombre_inferido_se_llaman_como_su_origen(proyecto):
    # Con isNameInferred, Desktop renombra la columna como su origen: un parámetro what-if
    # (GENERATESERIES → [Value]) pasaría a llamarse «Value» y sus medidas no lo encontrarían.
    for archivo in (_modelo(proyecto) / "definition" / "tables").glob("*.tmdl"):
        texto = archivo.read_text(encoding="utf-8")
        for m in re.finditer(r"^\tcolumn (?:'((?:[^']|'')+)'|(\S+))\n((?:\t\t.*\n|\n)*?)\t\tsourceColumn: \[([^\]]+)\]",
                             texto.replace("\r\n", "\n"), re.MULTILINE):
            if "\t\tisNameInferred" in m.group(3):
                nombre = (m.group(1) or m.group(2)).replace("''", "'")
                assert nombre == m.group(4), f"{archivo.name}: {nombre} se renombraría a {m.group(4)}"


@pytest.mark.parametrize("proyecto", PROYECTOS, ids=IDS)
def test_visuales_con_parametro_de_campo_lo_declaran(proyecto):
    # Sin «fieldParameters», Power BI trata el parámetro como texto: el eje muestra «Sexo» en vez de cambiar a sexo.
    tablas = set()
    for ruta in (_modelo(proyecto) / "definition" / "tables").glob("*.tmdl"):
        texto = ruta.read_text(encoding="utf-8")
        if '"kind": 2' in texto:
            tabla = re.search(r"^table (?:'([^']+)'|(\S+))", texto, re.MULTILINE)
            tablas.add(tabla.group(1) or tabla.group(2))
    for ruta in _visuales(proyecto):
        visual = json.loads(ruta.read_text(encoding="utf-8"))["visual"]
        if visual["visualType"] == "slicer":
            continue
        for rol, estado in visual.get("query", {}).get("queryState", {}).items():
            usa = any(p["field"].get("Column", {}).get("Expression", {}).get("SourceRef", {}).get("Entity") in tablas
                      for p in estado["projections"])
            assert not usa or estado.get("fieldParameters"), f"{ruta.parent.name}: {rol} usa un parámetro de campo sin fieldParameters"
