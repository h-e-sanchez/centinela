"""Cada archivo PBIR de los reportes cumple el esquema oficial de Microsoft que declara en `$schema`.

Desktop rechaza un archivo que no cumple su esquema (pasó con un `filterConfig` dentro de `visual`).
Los esquemas están copiados en `tests/esquemas_pbir/` para validar sin conexión. Un archivo que
declara una versión que no está copiada se omite: Desktop guarda versiones nuevas al abrir un reporte.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

RAIZ = Path(__file__).resolve().parent.parent
ESQUEMAS = Path(__file__).resolve().parent / "esquemas_pbir"
BASE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
REGISTRO = Registry().with_resources(
    (BASE + f.name.replace("_", "/"), Resource.from_contents(json.loads(f.read_text(encoding="utf-8")),
                                                             default_specification=DRAFT7))
    for f in ESQUEMAS.glob("*.json"))
ARCHIVOS = sorted(RAIZ.glob("powerbi/*/*.Report/definition/**/*.json"))
_validadores: dict[str, Draft7Validator] = {}


def _validador(url: str) -> Draft7Validator | None:
    if url not in _validadores:
        disponible = (ESQUEMAS / url.removeprefix(BASE).replace("/", "_")).exists()
        _validadores[url] = Draft7Validator({"$ref": url}, registry=REGISTRO) if disponible else None
    return _validadores[url]


def test_hay_esquemas_para_las_versiones_que_escribe_el_constructor():
    for url in (BASE + "visualContainer/2.4.0/schema.json", BASE + "page/1.4.0/schema.json"):
        assert _validador(url), url


@pytest.mark.parametrize("proyecto", sorted({f.relative_to(RAIZ).parts[1] for f in ARCHIVOS}))
def test_archivos_pbir_cumplen_su_esquema(proyecto):
    errores, validados = [], 0
    for archivo in (f for f in ARCHIVOS if f.relative_to(RAIZ).parts[1] == proyecto):
        datos = json.loads(archivo.read_text(encoding="utf-8-sig"))
        url = datos.get("$schema", "") if isinstance(datos, dict) else ""
        validador = _validador(url) if url.startswith(BASE) else None
        if not validador:
            continue
        validados += 1
        errores += [f"{archivo.parent.name}/{archivo.name} {e.json_path}: {e.message[:160]}" for e in validador.iter_errors(datos)]
    assert validados, "no se validó ningún archivo"
    assert not errores, "\n".join(errores[:10])
