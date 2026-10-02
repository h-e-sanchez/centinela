"""Consistencia de los proyectos de Power BI (powerbi/<reporte>/, TMDL + PBIR) con el resto del repo.

No abre Power BI (no es posible en CI): verifica que el texto versionado diga lo mismo
que el resto del repo. Las pruebas genéricas corren sobre cada proyecto; las de reporte.html
y el semáforo, solo sobre presupuesto-vs-real.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
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


@pytest.mark.parametrize("proyecto", PROYECTOS, ids=IDS)
def test_segmentadores_sin_seleccion_guardada(proyecto):
    # Un reporte público debe abrir en "Todas": una selección guardada en Desktop lo publica filtrado.
    for ruta in _visuales(proyecto):
        visual = json.loads(ruta.read_text(encoding="utf-8"))["visual"]
        if visual["visualType"] != "slicer":
            continue
        for entrada in visual.get("objects", {}).get("general", []):
            assert "filter" not in entrada.get("properties", {}), f"{ruta.parent.name}: segmentador con selección guardada"
