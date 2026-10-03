"""Arma el glosario de cada reporte de la vitrina: conceptos explicados + todas las medidas DAX del modelo.

Por reporte (`reportes/catalogo.json`) escribe reportes/<slug>/glosario.md con dos partes:

1. **Conceptos:** el texto de reportes/<slug>/conceptos.md, escrito a mano (qué es cada cosa, cómo
   se calcula y cómo leerla).
2. **Medidas del modelo:** se leen del TMDL del proyecto PBIP (`modelo` en el catálogo): nombre,
   descripción (`///`), fórmula DAX y formato, agrupadas por carpeta. También los ítems de los
   grupos de cálculo. Como salen del modelo, no se desactualizan: tests/test_glosario.py exige que
   el archivo versionado sea idéntico a lo que genera este script.

También escribe reportes/<slug>/glosario.csv (una fila por concepto, medida o ítem de cálculo, en
texto plano) que lee la página «Glosario» de cada reporte de Power BI desde GitHub.

Uso:
    python herramientas/generar_glosario.py
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REPORTES = RAIZ / "reportes"
SIN_CARPETA = "Otras"
NOMBRE = r"(?:'((?:[^']|'')+)'|([^\s=]+))"


@dataclass
class Medida:
    tabla: str
    nombre: str
    descripcion: str
    expresion: str
    formato: str
    carpeta: str


@dataclass
class ItemCalculo:
    grupo: str
    nombre: str
    expresion: str
    formato: str


def _nombre(m: re.Match) -> str:
    return (m.group(1) or m.group(2)).replace("''", "'")


def _expresion(lineas: list[str], i: int, cabecera: str, sangria: int) -> tuple[str, int]:
    """Expresión que empieza en la línea i (después del '='); devuelve el texto y la línea siguiente."""
    resto = cabecera.strip()
    if resto.startswith("```"):  # bloque cercado que guarda Desktop
        cuerpo, j = [], i + 1
        while not lineas[j].strip().startswith("```"):
            cuerpo.append(lineas[j])
            j += 1
        return _dedent(cuerpo), j + 1
    if resto:
        return resto, i + 1
    cuerpo, j = [], i + 1
    while j < len(lineas) and (lineas[j].startswith("\t" * (sangria + 1)) or not lineas[j].strip()):
        linea = lineas[j]
        propiedad = "^" + "\t" * (sangria + 1) + r"\w+(:| =|$)"
        if re.match(propiedad, linea) and not linea.startswith("\t" * (sangria + 2)):
            break  # propiedad del objeto (formatString:, displayFolder:...)
        cuerpo.append(linea)
        j += 1
    while cuerpo and not cuerpo[-1].strip():
        cuerpo.pop()
    return _dedent(cuerpo), j


def _dedent(cuerpo: list[str]) -> str:
    utiles = [linea for linea in cuerpo if linea.strip()]
    if not utiles:
        return ""
    tabs = min(len(linea) - len(linea.lstrip("\t")) for linea in utiles)
    sin_tabs = [linea[tabs:] for linea in cuerpo]
    espacios = min(len(linea) - len(linea.lstrip(" ")) for linea in sin_tabs if linea.strip())
    return "\n".join(linea[espacios:] for linea in sin_tabs).strip("\n")


def _propiedad(lineas: list[str], j: int, sangria: int, clave: str) -> str:
    while j < len(lineas):
        linea = lineas[j]
        if linea.strip() and not linea.startswith("\t" * sangria) or re.match("^" + "\t" * (sangria - 1) + r"\S", linea):
            break
        if linea.strip().startswith(f"{clave}:"):
            return linea.split(":", 1)[1].strip()
        if linea.strip().startswith(f"{clave} ="):
            return linea.split("=", 1)[1].strip().strip('"')
        j += 1
    return ""


def leer_modelo(modelo: Path) -> tuple[list[Medida], list[ItemCalculo]]:
    medidas, items = [], []
    for ruta in sorted(next(modelo.glob("*.SemanticModel")).glob("definition/tables/*.tmdl")):
        lineas = ruta.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
        tabla = _nombre(re.match(r"^table " + NOMBRE, next(linea for linea in lineas if linea.startswith("table "))))
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            if m := re.match(r"^\tmeasure " + NOMBRE + r" =(.*)$", linea):
                desc, k = [], i - 1
                while k >= 0 and lineas[k].startswith("\t///"):
                    desc.insert(0, lineas[k][4:].strip())
                    k -= 1
                expr, j = _expresion(lineas, i, m.group(3), 1)
                medidas.append(Medida(tabla, _nombre(m), " ".join(desc), expr,
                                      _propiedad(lineas, j, 2, "formatString"),
                                      _propiedad(lineas, j, 2, "displayFolder") or SIN_CARPETA))
                i = j
                continue
            if m := re.match(r"^\t\tcalculationItem " + NOMBRE + r" =(.*)$", linea):
                expr, j = _expresion(lineas, i, m.group(3), 2)
                items.append(ItemCalculo(tabla, _nombre(m), expr, _propiedad(lineas, j, 3, "formatStringDefinition")))
                i = j
                continue
            i += 1
    return medidas, items


def _clave_carpeta(carpeta: str) -> tuple:
    m = re.match(r"(\d+)\.", carpeta)
    return (0, int(m.group(1)), carpeta) if m else (1, 0, carpeta)


def glosario(rep: dict) -> str:
    medidas, items = leer_modelo(RAIZ / rep["modelo"])
    conceptos = (REPORTES / rep["slug"] / "conceptos.md").read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    partes = [
        f"# Glosario: {rep['titulo']}",
        "",
        ("> Qué significa cada concepto del reporte y cómo se calcula. La primera parte lo explica con "
         "palabras; la segunda lista **todas** las medidas DAX del modelo, leídas del proyecto PBIP con "
         "`herramientas/generar_glosario.py`, así que coinciden con lo que calcula Power BI."),
        "",
        conceptos,
        "",
        "## Medidas del modelo",
        "",
        (f"El modelo tiene {len(medidas)} medidas, agrupadas por carpeta como aparecen en el panel de datos de "
         "Power BI. Las de *portada* y *tarjetas* solo dan formato de texto a otras medidas."),
    ]
    carpetas: dict[str, list[Medida]] = {}
    for medida in medidas:
        carpetas.setdefault(medida.carpeta, []).append(medida)
    for carpeta in sorted(carpetas, key=_clave_carpeta):
        partes += ["", f"### {carpeta}"]
        for medida in carpetas[carpeta]:
            partes += ["", f"#### {medida.nombre}", ""]
            if medida.descripcion:
                partes += [medida.descripcion, ""]
            partes += ["```dax", medida.expresion, "```"]
            detalle = f"Tabla `{medida.tabla}`"
            if medida.formato:
                detalle += f" · formato `{medida.formato}`"
            partes += ["", f"*{detalle}*"]
    grupos: dict[str, list[ItemCalculo]] = {}
    for item in items:
        grupos.setdefault(item.grupo, []).append(item)
    for grupo, lista in grupos.items():
        partes += ["", f"## Grupo de cálculo «{grupo}»", "",
                   ("Cada ítem se aplica sobre la medida que esté en el visual (`SELECTEDMEASURE()`), así que una "
                    "sola definición sirve para todas las medidas.")]
        for item in lista:
            partes += ["", f"#### {item.nombre}", "", "```dax", item.expresion, "```"]
            if item.formato:
                partes += ["", f"*Formato propio: `{item.formato}`*"]
    return "\n".join(partes) + "\n"


COLUMNAS_CSV = ["n", "tipo", "seccion", "termino", "explicacion", "formula"]


def _plano(texto: str) -> str:
    """Markdown → texto de una línea para una celda de Power BI."""
    lineas = []
    for linea in texto.split("\n"):
        linea = linea.strip()
        if not linea or re.fullmatch(r"\|?[\s:|-]+\|?", linea):  # vacía o separador de tabla
            continue
        if linea.startswith("|"):
            celdas = [c.strip() for c in linea.strip("|").split("|")]
            linea = celdas[0] + ": " + "; ".join(celdas[1:]) + "."
        elif linea.startswith("- "):
            linea = "• " + linea[2:]
        lineas.append(linea)
    plano = " ".join(lineas)
    plano = re.sub(r"\*\*([^*]+)\*\*", r"\1", plano)
    plano = re.sub(r"\*([^*]+)\*", r"\1", plano)
    plano = re.sub(r"`([^`]+)`", r"\1", plano)
    plano = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", plano)
    return re.sub(r"\s+", " ", plano).strip()


def conceptos_csv(texto: str) -> list[tuple[str, str, str]]:
    """(sección, término, explicación) desde conceptos.md: cada párrafo que parte en negrita abre un término."""
    filas, seccion = [], ""
    for bloque in re.split(r"\n\s*\n", texto.replace("\r\n", "\n")):
        bloque = bloque.strip()
        if not bloque or bloque.startswith("## "):
            continue
        if bloque.startswith("### "):
            seccion = bloque[4:].strip()
            continue
        if m := re.match(r"\*\*([^*]+?)\.?\*\*", bloque):
            filas.append([seccion, m.group(1).strip(), bloque])
        elif filas and filas[-1][0] == seccion:
            filas[-1][2] += "\n" + bloque
        else:  # introducción de la sección, antes del primer término
            filas.append([seccion, seccion, bloque])
    salida = []
    for sec, termino, cuerpo in filas:
        plano = _plano(cuerpo)
        if plano.startswith(termino + ". "):  # el término ya va en su propia columna
            plano = plano[len(termino) + 2:]
        salida.append((sec, termino, plano))
    return salida


def _una_linea(expresion: str) -> str:
    return re.sub(r"\s+", " ", expresion).strip()


def glosario_csv(rep: dict) -> str:
    medidas, items = leer_modelo(RAIZ / rep["modelo"])
    conceptos = (REPORTES / rep["slug"] / "conceptos.md").read_text(encoding="utf-8")
    filas = [("Concepto", sec, termino, explicacion, "") for sec, termino, explicacion in conceptos_csv(conceptos)]
    for medida in sorted(medidas, key=lambda x: _clave_carpeta(x.carpeta)):
        filas.append(("Medida", medida.carpeta, medida.nombre, medida.descripcion, _una_linea(medida.expresion)))
    for item in items:
        filas.append(("Grupo de cálculo", item.grupo, item.nombre,
                      "Se aplica sobre la medida que esté en el visual (SELECTEDMEASURE()).", _una_linea(item.expresion)))
    salida = io.StringIO()
    w = csv.writer(salida, lineterminator="\n")
    w.writerow(COLUMNAS_CSV)
    for n, fila in enumerate(filas, start=1):
        w.writerow([n, *fila])
    return salida.getvalue()


def catalogo() -> list[dict]:
    return json.loads((REPORTES / "catalogo.json").read_text(encoding="utf-8"))["reportes"]


def main() -> None:
    for rep in catalogo():
        texto = glosario(rep)
        (REPORTES / rep["slug"] / "glosario.md").write_text(texto, encoding="utf-8", newline="\n")
        (REPORTES / rep["slug"] / "glosario.csv").write_text(glosario_csv(rep), encoding="utf-8", newline="\n")
        print(f"{rep['slug']:22} {texto.count(chr(10) + '#### ')} entradas")


if __name__ == "__main__":
    main()
