"""Arma los descargables de la vitrina a partir de las fuentes del repo.

- centinela-datos-csv.zip  data/escenarios/*.csv + LEEME.txt (diccionario de columnas)
- centinela-datos.xlsx     hojas presupuesto, real y diccionario
- centinela-pbip.zip       powerbi/ sin la caché ni la configuración local de Desktop

Los zip son reproducibles (entradas ordenadas, fecha fija). El .pbix no se genera aquí:
se exporta a mano desde Power BI Desktop (Archivo → Guardar como).

Uso (requiere openpyxl, en requirements-dev.txt):
    python herramientas/empaquetar_descargas.py
"""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESCENARIOS = RAIZ / "data" / "escenarios"
POWERBI = RAIZ / "powerbi"
DESTINO = RAIZ / "reportes" / "presupuesto-vs-real" / "descargas"
FECHA_FIJA = (2026, 1, 1, 0, 0, 0)
EXCLUIR_PBIP = {"cache.abf", "localSettings.json"}

DICCIONARIO = [
    ("industria", "Empresa sintética: Manufactura, Energia o Salud"),
    ("anio", "Año del registro"),
    ("mes", "Mes (1 a 12)"),
    ("centro_costo", "Centro de costo"),
    ("componente", "Cuenta o línea dentro del centro de costo"),
    ("grupo_cuenta", "Ingresos, Costos o Gastos Operacionales (para el Estado de Resultados)"),
    ("monto", "Monto en pesos chilenos, sin decimales"),
]

LEEME = """centinela · Presupuesto vs. Real por industria
Datos 100% sintéticos, generados con data/generar_escenarios.py (semilla 42).
https://h-e-sanchez.github.io/centinela/

presupuesto.csv y real.csv tienen las mismas columnas (separador coma, UTF-8):

{columnas}

Resultado Operacional = Ingresos - Costos - Gastos Operacionales.
"""


def _escribir_zip(destino: Path, entradas: list[tuple[str, bytes]]) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, datos in sorted(entradas):
            info = zipfile.ZipInfo(nombre, date_time=FECHA_FIJA)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, datos)


def entradas_csv() -> list[tuple[str, bytes]]:
    columnas = "\n".join(f"  {c:<14} {d}" for c, d in DICCIONARIO)
    entradas = [("LEEME.txt", LEEME.format(columnas=columnas).encode("utf-8"))]
    for ruta in sorted(ESCENARIOS.glob("*.csv")):
        entradas.append((ruta.name, ruta.read_bytes()))
    return entradas


def entradas_pbip() -> list[tuple[str, bytes]]:
    entradas = []
    for ruta in sorted(POWERBI.rglob("*")):
        if ruta.is_file() and ruta.name not in EXCLUIR_PBIP:
            entradas.append((ruta.relative_to(POWERBI).as_posix(), ruta.read_bytes()))
    return entradas


def leer_csv(ruta: Path) -> list[list[str]]:
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def escribir_xlsx(destino: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    libro = Workbook()
    libro.remove(libro.active)
    for nombre in ("presupuesto", "real"):
        hoja = libro.create_sheet(nombre)
        filas = leer_csv(ESCENARIOS / f"{nombre}.csv")
        hoja.append(filas[0])
        for fila in filas[1:]:
            hoja.append([fila[0], int(fila[1]), int(fila[2]), fila[3], fila[4], fila[5], float(fila[6])])
        for celda in hoja[1]:
            celda.font = Font(bold=True)
        hoja.freeze_panes = "A2"
    dic = libro.create_sheet("diccionario")
    dic.append(["columna", "descripcion"])
    for fila in DICCIONARIO:
        dic.append(list(fila))
    libro.properties.creator = "centinela"
    destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(destino)


def main() -> None:
    _escribir_zip(DESTINO / "centinela-datos-csv.zip", entradas_csv())
    _escribir_zip(DESTINO / "centinela-pbip.zip", entradas_pbip())
    escribir_xlsx(DESTINO / "centinela-datos.xlsx")
    for ruta in sorted(DESTINO.iterdir()):
        print(f"{ruta.name:28} {ruta.stat().st_size / 1024:8.1f} KB")


if __name__ == "__main__":
    main()
