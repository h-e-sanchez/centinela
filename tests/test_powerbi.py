"""Consistencia entre el modelo de Power BI (powerbi/, TMDL), la página reporte.html y el motor.

No abre Power BI (no es posible en CI): verifica que el texto versionado diga lo mismo
que el resto del repo.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PBI = RAIZ / "powerbi"
TMDL = PBI / "centinela.SemanticModel" / "definition" / "tables" / "desviacion.tmdl"


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


def test_jsons_del_proyecto_son_validos_y_apuntan_bien():
    for ruta in PBI.rglob("*.json"):
        json.loads(ruta.read_text(encoding="utf-8-sig"))
    pbir = json.loads((PBI / "centinela.Report" / "definition.pbir").read_text(encoding="utf-8"))
    destino = (PBI / "centinela.Report" / pbir["datasetReference"]["byPath"]["path"]).resolve()
    assert (destino / "definition.pbism").exists()
    pbip = json.loads((PBI / "centinela.pbip").read_text(encoding="utf-8"))
    assert (PBI / pbip["artifacts"][0]["report"]["path"] / "definition.pbir").exists()


def test_tmdl_usa_tabs_y_utf8_sin_bom():
    # TMDL exige sangría con tabs; dentro de una expresión M o DAX pueden seguir espacios.
    for ruta in (PBI / "centinela.SemanticModel" / "definition").rglob("*.tmdl"):
        crudo = ruta.read_bytes()
        assert not crudo.startswith(b"\xef\xbb\xbf"), f"{ruta.name} tiene BOM"
        for n, linea in enumerate(crudo.decode("utf-8").splitlines(), 1):
            assert not linea.startswith(" "), f"{ruta.name}:{n} indentado con espacios"


def _columnas_tmdl() -> dict[str, set[str]]:
    tablas = {}
    for ruta in (PBI / "centinela.SemanticModel" / "definition" / "tables").glob("*.tmdl"):
        texto = ruta.read_text(encoding="utf-8")
        tabla = re.search(r"^table (?:'([^']+)'|(\S+))", texto, re.MULTILINE)
        nombre_tabla = tabla.group(1) or tabla.group(2)
        tablas[nombre_tabla] = {
            m.group(1) or m.group(2)
            for m in re.finditer(r"^\tcolumn (?:'((?:[^']|'')+)'|(\S+))", texto, re.MULTILINE)
        }
    return tablas


def _campos(nodo):
    if isinstance(nodo, dict):
        for tipo in ("Column", "Measure"):
            if tipo in nodo and "Property" in nodo[tipo]:
                yield tipo, nodo[tipo]["Expression"]["SourceRef"]["Entity"], nodo[tipo]["Property"]
        for v in nodo.values():
            yield from _campos(v)
    elif isinstance(nodo, list):
        for v in nodo:
            yield from _campos(v)


def test_visuales_solo_usan_campos_y_medidas_del_modelo():
    columnas = _columnas_tmdl()
    medidas = _objetos_tmdl() - columnas["desviacion"]
    visuales = list((PBI / "centinela.Report" / "definition" / "pages").glob("*/visuals/*/visual.json"))
    assert visuales, "el reporte no tiene visuales"
    for ruta in visuales:
        for tipo, tabla, prop in _campos(json.loads(ruta.read_text(encoding="utf-8"))):
            if tipo == "Measure":
                assert tabla == "desviacion" and prop in medidas, f"{ruta.parent.name}: medida {tabla}.{prop}"
            else:
                assert prop in columnas.get(tabla, set()), f"{ruta.parent.name}: columna {tabla}.{prop}"
