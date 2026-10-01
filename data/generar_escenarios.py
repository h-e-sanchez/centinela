"""Genera data/escenarios/presupuesto.csv y real.csv: tres industrias, tres historias.

Cada industria tiene su propia estructura de centros de costo y cuentas, una
estacionalidad presupuestada y un comportamiento del "real" que cuenta una historia
distinta sobre el Resultado Operacional (Ingresos − Costos − Gastos Operacionales):

- Manufactura: escenario positivo. Ingresos sobre presupuesto (peak en el cuarto
  trimestre) y costos controlados.
- Energia: escenario neutro. La estacionalidad de invierno está bien presupuestada
  y el real se mueve dentro del ruido.
- Salud: escenario rojo. La campaña de invierno (junio a agosto) dispara los costos
  clínicos por sobre lo presupuestado y febrero baja los ingresos.

Mismo formato tidy que data/presupuesto.csv, con una columna `industria` adelante.
Reproducible (semilla fija). Ningún dato real de ningún empleador.

Uso:
    python data/generar_escenarios.py
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

SEMILLA = 42
ANIO = 2026
RUIDO = 0.015  # desviación típica del real alrededor de su factor de escenario
INVIERNO = (6, 7, 8)

# industria -> centro_costo -> (grupo_cuenta, {componente: monto mensual base})
ESTRUCTURA = {
    "Manufactura": {
        "Ingresos": ("Ingresos", {"ventas_linea_industrial": 42_000_000, "ventas_linea_consumo": 30_000_000,
                                  "servicios_postventa": 6_000_000}),
        "Produccion": ("Costos", {"materias_primas": 24_000_000, "mano_de_obra_directa": 12_000_000,
                                  "energia_planta": 4_500_000}),
        "Comercial": ("Gastos Operacionales", {"comisiones": 3_000_000, "marketing": 2_500_000,
                                               "logistica_distribucion": 4_000_000}),
        "Administracion": ("Gastos Operacionales", {"remuneraciones_administrativas": 5_000_000,
                                                    "arriendo": 1_800_000, "software": 1_200_000}),
    },
    "Energia": {
        "Ingresos": ("Ingresos", {"venta_energia_contratos": 55_000_000, "venta_energia_spot": 12_000_000,
                                  "peajes_transmision": 8_000_000}),
        "Operacion": ("Costos", {"compras_energia": 22_000_000, "combustibles": 14_000_000,
                                 "mantenimiento_centrales": 6_000_000}),
        "Regulatorio": ("Gastos Operacionales", {"permisos_ambientales": 1_500_000, "seguros": 2_000_000}),
        "Administracion": ("Gastos Operacionales", {"remuneraciones_administrativas": 6_000_000,
                                                    "tecnologia": 2_500_000}),
    },
    "Salud": {
        "Ingresos": ("Ingresos", {"prestaciones_ambulatorias": 26_000_000, "hospitalizacion": 34_000_000,
                                  "pabellon": 18_000_000}),
        "Atencion clinica": ("Costos", {"remuneraciones_clinicas": 30_000_000, "honorarios_medicos": 14_000_000,
                                        "insumos_medicos": 9_000_000}),
        "Soporte": ("Gastos Operacionales", {"mantencion_equipos": 3_000_000, "aseo_y_alimentacion": 4_000_000}),
        "Administracion": ("Gastos Operacionales", {"remuneraciones_administrativas": 5_500_000,
                                                    "tecnologia": 2_200_000}),
    },
}


def estacionalidad(industria: str, grupo: str, mes: int) -> float:
    """Perfil presupuestado: lo que la empresa ya espera de cada mes."""
    if industria == "Manufactura":
        return {10: 1.08, 11: 1.15, 12: 1.2, 1: 0.9, 2: 0.88}.get(mes, 1.0)
    if industria == "Energia":
        return 1.18 if mes in INVIERNO else (0.92 if mes in (12, 1, 2) else 1.0)
    # Salud: el invierno trae más demanda (ingresos y costos) y febrero baja la actividad.
    if mes in INVIERNO:
        return 1.12
    return 0.85 if mes == 2 else 1.0


def factor_real(industria: str, grupo: str, componente: str, mes: int) -> float:
    """Cuánto se aleja el real del presupuesto en cada escenario (antes del ruido)."""
    if industria == "Manufactura":
        if grupo == "Ingresos":
            return 1.07 if mes >= 10 else 1.04
        return 0.98 if componente == "materias_primas" else 1.0
    if industria == "Energia":
        return 1.0
    # Salud
    if grupo == "Ingresos":
        return 0.9 if mes == 2 else 0.98
    if grupo == "Costos":
        if mes in INVIERNO:  # sobretiempo, reemplazos e insumos de la campaña de invierno
            return {"remuneraciones_clinicas": 1.22, "honorarios_medicos": 1.18, "insumos_medicos": 1.3}[componente]
        return 1.04
    return 1.02


def generar(seed: int = SEMILLA) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    presupuesto, real = [], []
    for industria, centros in ESTRUCTURA.items():
        for centro, (grupo, componentes) in centros.items():
            for componente, base in componentes.items():
                for mes in range(1, 13):
                    ppto = round(base * estacionalidad(industria, grupo, mes), -3)
                    clave = {"industria": industria, "anio": ANIO, "mes": mes, "centro_costo": centro,
                             "componente": componente, "grupo_cuenta": grupo}
                    presupuesto.append({**clave, "monto": ppto})
                    factor = factor_real(industria, grupo, componente, mes) * (1 + rng.gauss(0, RUIDO))
                    real.append({**clave, "monto": round(max(0.0, ppto * factor), 0)})
    return presupuesto, real


CAMPOS = ["industria", "anio", "mes", "centro_costo", "componente", "grupo_cuenta", "monto"]


def escribir(filas: list[dict], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los escenarios por industria.")
    parser.add_argument("--seed", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=Path(__file__).parent / "escenarios")
    args = parser.parse_args()
    presupuesto, real = generar(args.seed)
    escribir(presupuesto, args.salida / "presupuesto.csv")
    escribir(real, args.salida / "real.csv")
    print(f"{len(presupuesto)} filas por archivo en {args.salida}")


if __name__ == "__main__":
    main()
