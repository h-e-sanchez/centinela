"""Corre sql/reglas_auditoria.sql sobre los estados de pago y escribe las observaciones.

Carga las tablas en una base SQLite en memoria (sqlite3 de la stdlib, sin dependencias), ejecuta
el archivo de reglas tal cual está versionado y devuelve una fila por línea y regla incumplida.

Uso:
    python sql/auditar.py                       # lee y escribe en data/contratistas/
    python sql/auditar.py --datos otra/carpeta
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

REGLAS = Path(__file__).with_name("reglas_auditoria.sql")
COLUMNAS_SALIDA = ["id_linea", "periodo", "id_contratista", "sede", "id_ot", "regla", "monto_observado",
                   "resolucion"]
# Tipos SQLite de las columnas que usan las reglas (el resto se carga como texto).
TIPOS = {
    "estados_pago": {"cantidad_cobrada": "REAL", "precio_cobrado": "INTEGER", "monto": "INTEGER"},
    "ordenes_trabajo": {"cantidad_ejecutada": "REAL", "horas_ejecutadas": "REAL", "horas_detencion": "REAL"},
    "tarifas": {"precio_unitario": "INTEGER"},
}


def _valor(texto: str, tipo: str):
    if texto == "" or texto is None:
        return None
    if tipo == "REAL":
        return float(texto)
    if tipo == "INTEGER":
        return int(texto)
    return texto


def auditar(tablas: dict[str, list[dict]]) -> list[dict]:
    """Ejecuta las reglas sobre las tablas (filas como dict de str) y devuelve las observaciones."""
    con = sqlite3.connect(":memory:")
    try:
        for nombre, tipos in TIPOS.items():
            filas = tablas[nombre]
            columnas = list(filas[0])
            definicion = ", ".join(f"{c} {tipos.get(c, 'TEXT')}" for c in columnas)
            con.execute(f"CREATE TABLE {nombre} ({definicion})")
            con.executemany(
                f"INSERT INTO {nombre} VALUES ({', '.join('?' for _ in columnas)})",
                [[_valor(str(f[c]) if f[c] is not None else "", tipos.get(c, "TEXT")) for c in columnas]
                 for f in filas],
            )
        cursor = con.execute(REGLAS.read_text(encoding="utf-8"))
        nombres = [d[0] for d in cursor.description]
        return [{c: ("" if v is None else v) for c, v in zip(nombres, fila)} for fila in cursor]
    finally:
        con.close()


def _leer(carpeta: Path, nombre: str) -> list[dict]:
    with (carpeta / f"{nombre}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser(description="Audita los estados de pago con las reglas SQL.")
    parser.add_argument("--datos", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "contratistas")
    args = parser.parse_args()
    observaciones = auditar({n: _leer(args.datos, n) for n in TIPOS})
    with (args.datos / "observaciones.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_SALIDA, lineterminator="\n")
        w.writeheader()
        w.writerows(observaciones)
    print(f"{len(observaciones)} observaciones")


if __name__ == "__main__":
    main()
