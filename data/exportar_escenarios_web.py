"""Genera data/escenarios-web.json para reporte.html: presupuesto y real cruzados por industria.

Lee los CSV versionados de data/escenarios/ (los mismos que carga el modelo de Power BI),
así la página y el reporte publicado muestran exactamente los mismos números.

Uso:
    python data/exportar_escenarios_web.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

DATA = Path(__file__).parent
LLAVE = ("industria", "anio", "mes", "centro_costo", "componente", "grupo_cuenta")


def leer(ruta: Path) -> dict[tuple, float]:
    with ruta.open(encoding="utf-8") as f:
        return {tuple(fila[k] for k in LLAVE): float(fila["monto"]) for fila in csv.DictReader(f)}


def combinar() -> dict[str, list[dict]]:
    ppto = leer(DATA / "escenarios" / "presupuesto.csv")
    real = leer(DATA / "escenarios" / "real.csv")
    salida: dict[str, list[dict]] = {}
    for clave in sorted(ppto.keys() | real.keys(), key=lambda k: (k[0], int(k[2]), k[3], k[4])):
        industria, anio, mes, centro, componente, grupo = clave
        salida.setdefault(industria, []).append({
            "anio": int(anio), "mes": int(mes), "centro_costo": centro, "componente": componente,
            "grupo_cuenta": grupo, "monto_presupuesto": ppto.get(clave, 0.0), "monto_real": real.get(clave, 0.0),
        })
    return salida


def main() -> None:
    destino = DATA / "escenarios-web.json"
    destino.write_text(json.dumps(combinar(), ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"escrito {destino}")


if __name__ == "__main__":
    main()
