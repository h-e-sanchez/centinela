"""Deja los segmentadores de industria de los reportes Power BI abiertos en una industria.

La vitrina abre todos los reportes en la misma industria (INDUSTRIA_INICIAL), así el
visitante compara reportes sobre la misma empresa sintética. El resto de los
segmentadores sigue sin selección guardada (lo verifica tests/test_powerbi.py).

Uso:
    python herramientas/industria_inicial.py
"""

from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INDUSTRIA_INICIAL = "Energia"
COLUMNAS_INDUSTRIA = {"industria"}


def filtro(entidad: str, propiedad: str, valor: str = INDUSTRIA_INICIAL) -> dict:
    return {"filter": {
        "Version": 2, "From": [{"Name": "i", "Entity": entidad, "Type": 0}],
        "Where": [{"Condition": {"In": {
            "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "i"}}, "Property": propiedad}}],
            "Values": [[{"Literal": {"Value": f"'{valor}'"}}]]}}}]}}


def aplicar(ruta: Path) -> bool:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    visual = datos["visual"]
    if visual.get("visualType") != "slicer":
        return False
    columna = visual["query"]["queryState"]["Values"]["projections"][0]["field"].get("Column")
    if not columna or columna["Property"] not in COLUMNAS_INDUSTRIA:
        return False
    entidad = columna["Expression"]["SourceRef"]["Entity"]
    generales = visual.setdefault("objects", {}).setdefault("general", [{"properties": {}}])
    generales[0].setdefault("properties", {})["filter"] = filtro(entidad, columna["Property"])
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> None:
    cambiados = [r for r in sorted((RAIZ / "powerbi").glob("*/*.Report/definition/pages/*/visuals/*/visual.json"))
                 if aplicar(r)]
    for r in cambiados:
        print(r.relative_to(RAIZ).as_posix())
    print(f"{len(cambiados)} segmentadores en {INDUSTRIA_INICIAL}")


if __name__ == "__main__":
    main()
