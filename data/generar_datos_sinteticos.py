"""Genera presupuesto.csv y real.csv sintéticos para centinela.

Reproducible (semilla fija): la misma semilla siempre genera la misma pareja
de datasets, incluyendo las mismas desviaciones grandes inyectadas — así los
tests pueden verificar que el motor las clasifica exactamente donde deben
caer. Ningún dato real de ningún empleador: centros de costo y componentes
son genéricos.

Cada centro de costo (incluida la línea de Ingresos) declara su grupo_cuenta
("Ingresos" / "Costos" / "Gastos Operacionales") — la clasificación mínima que
permite armar un Estado de Resultados (Resultado Operacional = Ingresos -
Costos - Gastos Operacionales), no solo una lista plana de gastos.

Uso:
    python data/generar_datos_sinteticos.py
    python data/generar_datos_sinteticos.py --anio 2026 --meses 12 --seed 42
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

SEMILLA = 42

# Rango de monto default para centros de costo/gasto. La línea de Ingresos usa un
# rango propio, mucho mayor, para que el negocio sintético tenga margen positivo.
RANGO_MONTO_BASE = (500_000, 8_000_000)
RANGO_MONTO_INGRESOS = (15_000_000, 35_000_000)

CENTROS = {
    "Ingresos": {
        "grupo_cuenta": "Ingresos",
        "componentes": ["ventas_producto_a", "ventas_producto_b", "ventas_servicios"],
        "rango_monto": RANGO_MONTO_INGRESOS,
    },
    "Operaciones": {
        "grupo_cuenta": "Costos",
        "componentes": ["mano_de_obra", "materiales", "mantencion"],
        "rango_monto": RANGO_MONTO_BASE,
    },
    "Comercial": {
        "grupo_cuenta": "Gastos Operacionales",
        "componentes": ["comisiones", "marketing", "viajes"],
        "rango_monto": RANGO_MONTO_BASE,
    },
    "Administracion y Finanzas": {
        "grupo_cuenta": "Gastos Operacionales",
        "componentes": ["arriendo", "servicios_basicos", "software"],
        "rango_monto": RANGO_MONTO_BASE,
    },
    "Personas": {
        "grupo_cuenta": "Gastos Operacionales",
        "componentes": ["capacitacion", "beneficios", "reclutamiento"],
        "rango_monto": RANGO_MONTO_BASE,
    },
    "Tecnologia": {
        "grupo_cuenta": "Gastos Operacionales",
        "componentes": ["licencias", "infraestructura_cloud", "soporte"],
        "rango_monto": RANGO_MONTO_BASE,
    },
}

TASA_DESVIACION_GRANDE = 0.08  # fracción de líneas con una desviación >=15% inyectada a propósito


def generar_presupuesto(anio: int, meses: int, rng: random.Random) -> list[dict]:
    filas = []
    for centro, datos in CENTROS.items():
        for componente in datos["componentes"]:
            monto_base = rng.uniform(*datos["rango_monto"])
            for mes in range(1, meses + 1):
                filas.append({
                    "anio": anio,
                    "mes": mes,
                    "centro_costo": centro,
                    "componente": componente,
                    "grupo_cuenta": datos["grupo_cuenta"],
                    "monto": round(monto_base, 0),
                })
    return filas


def generar_real(presupuesto: list[dict], rng: random.Random) -> list[dict]:
    """A partir del presupuesto, genera el "real": ruido gaussiano acotado
    (+-3% típico) más una fracción de líneas (TASA_DESVIACION_GRANDE) con una
    desviación grande intencional, sobre-ejecución o sub-ejecución, para que
    el motor tenga algo real que clasificar como alerta/crítica.
    """
    filas = []
    for fila in presupuesto:
        monto_presupuesto = fila["monto"]
        if rng.random() < TASA_DESVIACION_GRANDE:
            factor = rng.choice([rng.uniform(1.15, 1.4), rng.uniform(0.6, 0.85)])
        else:
            factor = 1 + rng.gauss(0, 0.03)
        filas.append({
            **fila,
            "monto": round(max(0.0, monto_presupuesto * factor), 0),
        })
    return filas


def escribir_csv(filas: list[dict], ruta_salida: Path) -> None:
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    campos = ["anio", "mes", "centro_costo", "componente", "grupo_cuenta", "monto"]
    with ruta_salida.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera presupuesto.csv y real.csv sintéticos.")
    parser.add_argument("--anio", type=int, default=2026)
    parser.add_argument("--meses", type=int, default=12)
    parser.add_argument("--seed", type=int, default=SEMILLA)
    parser.add_argument("--salida-presupuesto", type=Path, default=Path("data/presupuesto.csv"))
    parser.add_argument("--salida-real", type=Path, default=Path("data/real.csv"))
    args = parser.parse_args()

    rng_presupuesto = random.Random(args.seed)
    presupuesto = generar_presupuesto(args.anio, args.meses, rng_presupuesto)

    rng_real = random.Random(args.seed + 1)
    real = generar_real(presupuesto, rng_real)

    escribir_csv(presupuesto, args.salida_presupuesto)
    escribir_csv(real, args.salida_real)
    print(f"Generadas {len(presupuesto)} filas de presupuesto -> {args.salida_presupuesto}")
    print(f"Generadas {len(real)} filas de real -> {args.salida_real}")


if __name__ == "__main__":
    main()
