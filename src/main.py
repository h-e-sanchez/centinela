"""CLI de centinela: cruza presupuesto vs. real y reporta desviaciones.

Ejemplo:
    python data/generar_datos_sinteticos.py
    python -m src.main --presupuesto data/presupuesto.csv --real data/real.csv --umbral 0.05
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.modelos import LineaPresupuesto, LineaReal, ParametrosAlerta
from src.motor import calcular_desviaciones, lineas_en_alerta, resumen_por_estado

MESES_ES = [
    "", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


def _cargar_presupuesto(ruta: Path) -> list[LineaPresupuesto]:
    with ruta.open(newline="", encoding="utf-8") as f:
        return [
            LineaPresupuesto(
                anio=int(fila["anio"]),
                mes=int(fila["mes"]),
                centro_costo=fila["centro_costo"],
                componente=fila["componente"],
                monto=float(fila["monto"]),
            )
            for fila in csv.DictReader(f)
        ]


def _cargar_real(ruta: Path) -> list[LineaReal]:
    with ruta.open(newline="", encoding="utf-8") as f:
        return [
            LineaReal(
                anio=int(fila["anio"]),
                mes=int(fila["mes"]),
                centro_costo=fila["centro_costo"],
                componente=fila["componente"],
                monto=float(fila["monto"]),
            )
            for fila in csv.DictReader(f)
        ]


def imprimir_resumen(filas, resumen: dict[str, int]) -> None:
    print(
        f"Líneas evaluadas: {len(filas)} — "
        f"ok: {resumen['ok']}, alerta: {resumen['alerta']}, crítica: {resumen['critica']}"
    )
    print()
    en_alerta = sorted(
        lineas_en_alerta(filas),
        key=lambda f: abs(f.desviacion_pct) if f.desviacion_pct is not None else float("inf"),
        reverse=True,
    )
    if not en_alerta:
        print("Sin líneas en alerta.")
        return
    print("Líneas en alerta (ordenadas por magnitud de desviación):")
    for f in en_alerta[:20]:
        pct = f"{f.desviacion_pct * 100:+.1f}%" if f.desviacion_pct is not None else "sin presupuesto"
        print(
            f"  [{f.estado.upper():8}] {MESES_ES[f.mes]} {f.anio} — "
            f"{f.centro_costo} / {f.componente}: "
            f"presupuesto ${f.monto_presupuesto:,.0f} vs real ${f.monto_real:,.0f} ({pct})"
        )


def exportar_csv(filas, ruta_salida: Path) -> None:
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    with ruta_salida.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "anio", "mes", "centro_costo", "componente",
            "monto_presupuesto", "monto_real", "desviacion_monto",
            "desviacion_pct", "estado",
        ])
        for fila in filas:
            writer.writerow([
                fila.anio, fila.mes, fila.centro_costo, fila.componente,
                fila.monto_presupuesto, fila.monto_real, fila.desviacion_monto,
                fila.desviacion_pct if fila.desviacion_pct is not None else "",
                fila.estado,
            ])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cruza presupuesto vs. real y reporta desviaciones con alertas por umbral."
    )
    parser.add_argument("--presupuesto", type=Path, default=Path("data/presupuesto.csv"))
    parser.add_argument("--real", type=Path, default=Path("data/real.csv"))
    parser.add_argument(
        "--umbral", type=float, default=0.05,
        help="Umbral de alerta, como fracción (0.05 = 5%%).",
    )
    parser.add_argument(
        "--umbral-critico", type=float, default=0.15,
        help="Umbral de alerta crítica, como fracción.",
    )
    parser.add_argument(
        "--salida", type=Path, default=None,
        help="Ruta opcional para exportar el detalle a CSV tidy.",
    )
    args = parser.parse_args()

    presupuesto = _cargar_presupuesto(args.presupuesto)
    real = _cargar_real(args.real)
    parametros = ParametrosAlerta(umbral_pct=args.umbral, umbral_critico_pct=args.umbral_critico)

    filas = calcular_desviaciones(presupuesto, real, parametros)
    resumen = resumen_por_estado(filas)
    imprimir_resumen(filas, resumen)

    if args.salida:
        exportar_csv(filas, args.salida)
        print(f"\nDetalle exportado a {args.salida}")


if __name__ == "__main__":
    main()
