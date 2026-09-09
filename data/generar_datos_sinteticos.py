"""Genera presupuesto.csv y real.csv sintéticos para centinela.

Reproducible (semilla fija): la misma semilla siempre genera la misma pareja
de datasets, incluyendo las mismas desviaciones grandes inyectadas — así los
tests pueden verificar que el motor las clasifica exactamente donde deben
caer. Ningún dato real de ningún empleador: centros de costo y componentes
son genéricos.

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

CENTROS_COSTO = {
    "Operaciones": ["mano_de_obra", "materiales", "mantencion"],
    "Comercial": ["comisiones", "marketing", "viajes"],
    "Administracion y Finanzas": ["arriendo", "servicios_basicos", "software"],
    "Personas": ["capacitacion", "beneficios", "reclutamiento"],
    "Tecnologia": ["licencias", "infraestructura_cloud", "soporte"],
}

RANGO_MONTO_BASE = (500_000, 8_000_000)
TASA_DESVIACION_GRANDE = 0.08  # fracción de líneas con una desviación >=15% inyectada a propósito


def generar_presupuesto(anio: int, meses: int, rng: random.Random) -> list[dict]:
    filas = []
    for centro, componentes in CENTROS_COSTO.items():
        for componente in componentes:
            monto_base = rng.uniform(*RANGO_MONTO_BASE)
            for mes in range(1, meses + 1):
                filas.append({
                    "anio": anio,
                    "mes": mes,
                    "centro_costo": centro,
                    "componente": componente,
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
    with ruta_salida.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["anio", "mes", "centro_costo", "componente", "monto"])
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
