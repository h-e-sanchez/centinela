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

Además genera data/escenarios/montos.csv, el detalle que lee el modelo de Power BI:
2025 y 2026, tres sucursales por industria, cuentas dentro de cada componente (gasto fijo o
variable) y tres versiones (Presupuesto, Forecast 3+9 y Real). El 2026 de montos.csv suma
exactamente lo mismo que presupuesto.csv y real.csv, así las tres historias no cambian.

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


def escribir(filas: list[dict], ruta: Path, campos: list[str] = CAMPOS) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)


# ---------------------------------------------------------------------------------------------
# Detalle para Power BI: sucursales, cuentas, 2025 y Forecast 3+9
# ---------------------------------------------------------------------------------------------

ANIO_BASE = 2025
VERSIONES = ("Presupuesto", "Forecast", "Real")
MESES_REALES_FORECAST = 3  # Forecast 3+9: enero a marzo real, abril a diciembre re-proyectado

# industria -> sucursal -> (peso en el presupuesto, peso en la desviación del real)
SUCURSALES = {
    "Manufactura": {"Santiago": (0.50, 0.30), "Concepción": (0.30, 0.20), "Antofagasta": (0.20, 0.50)},
    "Energia": {"Zona Norte": (0.40, 0.40), "Zona Centro": (0.35, 0.35), "Zona Sur": (0.25, 0.25)},
    "Salud": {"Clínica Oriente": (0.45, 0.20), "Clínica Centro": (0.35, 0.30), "Clínica Poniente": (0.20, 0.50)},
}

# componente -> [(cuenta, peso, tipo de gasto)]. En Ingresos el tipo es "Ingreso".
CUENTAS = {
    "ventas_linea_industrial": [("Ventas nacionales", 0.7, "Ingreso"), ("Exportaciones", 0.3, "Ingreso")],
    "ventas_linea_consumo": [("Canal supermercados", 0.6, "Ingreso"), ("Canal mayorista", 0.4, "Ingreso")],
    "servicios_postventa": [("Contratos de mantención", 0.7, "Ingreso"), ("Repuestos", 0.3, "Ingreso")],
    "materias_primas": [("Acero y metales", 0.6, "Variable"), ("Insumos químicos", 0.4, "Variable")],
    "mano_de_obra_directa": [("Sueldos operarios", 0.8, "Fijo"), ("Horas extra", 0.2, "Variable")],
    "energia_planta": [("Electricidad", 0.8, "Variable"), ("Gas", 0.2, "Variable")],
    "comisiones": [("Comisiones directas", 0.7, "Variable"), ("Bonos por meta", 0.3, "Variable")],
    "marketing": [("Medios digitales", 0.6, "Variable"), ("Ferias y eventos", 0.4, "Fijo")],
    "logistica_distribucion": [("Fletes", 0.75, "Variable"), ("Bodegaje", 0.25, "Fijo")],
    "remuneraciones_administrativas": [("Sueldos administrativos", 0.85, "Fijo"), ("Beneficios", 0.15, "Fijo")],
    "arriendo": [("Arriendo oficinas", 1.0, "Fijo")],
    "software": [("Licencias", 0.7, "Fijo"), ("Soporte TI", 0.3, "Fijo")],
    "tecnologia": [("Licencias", 0.6, "Fijo"), ("Infraestructura nube", 0.4, "Variable")],
    "venta_energia_contratos": [("Clientes libres", 0.6, "Ingreso"), ("Distribuidoras", 0.4, "Ingreso")],
    "venta_energia_spot": [("Mercado spot", 1.0, "Ingreso")],
    "peajes_transmision": [("Peajes nacionales", 0.7, "Ingreso"), ("Peajes zonales", 0.3, "Ingreso")],
    "compras_energia": [("Compras a terceros", 1.0, "Variable")],
    "combustibles": [("Gas natural", 0.6, "Variable"), ("Diésel", 0.4, "Variable")],
    "mantenimiento_centrales": [("Mantención preventiva", 0.6, "Fijo"), ("Mantención correctiva", 0.4, "Variable")],
    "permisos_ambientales": [("Monitoreo ambiental", 0.6, "Fijo"), ("Permisos y tasas", 0.4, "Fijo")],
    "seguros": [("Seguros de activos", 1.0, "Fijo")],
    "prestaciones_ambulatorias": [("Pacientes Fonasa", 0.45, "Ingreso"), ("Pacientes Isapre", 0.55, "Ingreso")],
    "hospitalizacion": [("Días cama", 0.7, "Ingreso"), ("Medicamentos facturados", 0.3, "Ingreso")],
    "pabellon": [("Cirugías programadas", 0.75, "Ingreso"), ("Cirugías de urgencia", 0.25, "Ingreso")],
    "remuneraciones_clinicas": [("Sueldos base clínicos", 0.75, "Fijo"), ("Turnos extra y reemplazos", 0.25, "Variable")],
    "honorarios_medicos": [("Honorarios por acto", 0.8, "Variable"), ("Guardias médicas", 0.2, "Fijo")],
    "insumos_medicos": [("Medicamentos", 0.55, "Variable"), ("Material clínico", 0.45, "Variable")],
    "mantencion_equipos": [("Contratos de mantención", 0.7, "Fijo"), ("Reparaciones", 0.3, "Variable")],
    "aseo_y_alimentacion": [("Aseo", 0.5, "Fijo"), ("Alimentación pacientes", 0.5, "Variable")],
}
PESO_DESVIO_VARIABLE = 3.0  # la desviación del real cae sobre todo en las cuentas variables

# 2025: el presupuesto 2026 descontado por el crecimiento esperado, con su propia historia.
CRECIMIENTO_2026 = {"Manufactura": 0.06, "Energia": 0.04, "Salud": 0.05}


def factor_real_2025(industria: str, grupo: str, componente: str, mes: int) -> float:
    """2025 cuenta otra historia: así la comparación interanual dice algo."""
    if industria == "Manufactura":  # año flojo: ventas bajo el presupuesto
        return 0.97 if grupo == "Ingresos" else 1.01
    if industria == "Energia":  # año seco: invierno con más combustible y mejor precio spot
        if mes in INVIERNO and componente == "combustibles":
            return 1.12
        return 1.08 if mes in INVIERNO and componente == "venta_energia_spot" else 1.0
    if grupo == "Ingresos":  # Salud: invierno más suave que el de 2026
        return 0.99
    return 1.08 if grupo == "Costos" and mes in INVIERNO else 1.02


def repartir(total: int, pesos: list[float]) -> list[int]:
    """Reparte un entero según pesos sin perder un peso (mayor resto); acepta totales negativos."""
    signo, total = (-1, -total) if total < 0 else (1, total)
    suma = sum(pesos)
    exactos = [total * p / suma for p in pesos]
    partes = [int(x) for x in exactos]
    for i in sorted(range(len(pesos)), key=lambda i: exactos[i] - partes[i], reverse=True)[: total - sum(partes)]:
        partes[i] += 1
    return [signo * p for p in partes]


def _celdas(industria: str, componente: str) -> list[tuple[str, str, str, float, float]]:
    """(sucursal, cuenta, tipo_gasto, peso presupuesto, peso desviación) de un componente."""
    celdas = []
    for sucursal, (w_ppto, w_desv) in SUCURSALES[industria].items():
        for cuenta, w_cta, tipo in CUENTAS[componente]:
            extra = PESO_DESVIO_VARIABLE if tipo == "Variable" else 1.0
            celdas.append((sucursal, cuenta, tipo, w_ppto * w_cta, w_desv * w_cta * extra))
    return celdas


def _anio_base(seed: int) -> tuple[list[dict], list[dict]]:
    """Presupuesto y real 2025 agregados (mismo grano que presupuesto.csv), con su propio RNG."""
    rng = random.Random(seed + ANIO_BASE)
    ppto_2026, _ = generar(seed)
    presupuesto, real = [], []
    for fila in ppto_2026:
        ppto = round(fila["monto"] / (1 + CRECIMIENTO_2026[fila["industria"]]), -3)
        clave = {**fila, "anio": ANIO_BASE}
        presupuesto.append({**clave, "monto": ppto})
        factor = factor_real_2025(fila["industria"], fila["grupo_cuenta"], fila["componente"], fila["mes"])
        real.append({**clave, "monto": round(max(0.0, ppto * factor * (1 + rng.gauss(0, RUIDO))), 0)})
    return presupuesto, real


def _forecast(presupuesto: list[dict], real: list[dict]) -> list[float]:
    """Forecast 3+9 por línea: real de enero a marzo y, después, presupuesto × run-rate del trimestre."""
    q1: dict[tuple, list[float]] = {}
    for p, r in zip(presupuesto, real):
        if p["mes"] <= MESES_REALES_FORECAST:
            acum = q1.setdefault((p["industria"], p["componente"]), [0.0, 0.0])
            acum[0] += p["monto"]
            acum[1] += r["monto"]
    salida = []
    for p, r in zip(presupuesto, real):
        if p["mes"] <= MESES_REALES_FORECAST:
            salida.append(r["monto"])
        else:
            base, ejecutado = q1[(p["industria"], p["componente"])]
            salida.append(round(p["monto"] * (ejecutado / base if base else 1.0), 0))
    return salida


CAMPOS_MONTOS = ["version", "industria", "anio", "mes", "sucursal", "centro_costo", "componente", "cuenta",
                 "tipo_gasto", "grupo_cuenta", "monto"]


def generar_montos(seed: int = SEMILLA) -> list[dict]:
    """Detalle tidy de las tres versiones, 2025 y 2026, por sucursal y cuenta (montos enteros)."""
    filas = []
    for presupuesto, real in (_anio_base(seed), generar(seed)):
        forecast = _forecast(presupuesto, real)
        for p, r, f in zip(presupuesto, real, forecast):
            celdas = _celdas(p["industria"], p["componente"])
            pesos_ppto = [c[3] for c in celdas]
            montos_ppto = repartir(int(p["monto"]), pesos_ppto)
            desvio = repartir(int(r["monto"]) - int(p["monto"]), [c[4] for c in celdas])
            montos_real = [a + b for a, b in zip(montos_ppto, desvio)]
            if p["mes"] <= MESES_REALES_FORECAST:
                montos_fcst = montos_real
            else:
                montos_fcst = repartir(int(f), pesos_ppto)
            for version, montos in zip(VERSIONES, (montos_ppto, montos_fcst, montos_real)):
                for (sucursal, cuenta, tipo, _, _), monto in zip(celdas, montos):
                    filas.append({"version": version, "industria": p["industria"], "anio": p["anio"],
                                  "mes": p["mes"], "sucursal": sucursal, "centro_costo": p["centro_costo"],
                                  "componente": p["componente"], "cuenta": cuenta, "tipo_gasto": tipo,
                                  "grupo_cuenta": p["grupo_cuenta"], "monto": monto})
    orden_version = {v: i for i, v in enumerate(VERSIONES)}
    filas.sort(key=lambda f: (orden_version[f["version"]], f["anio"]))
    return filas


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los escenarios por industria.")
    parser.add_argument("--seed", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=Path(__file__).parent / "escenarios")
    args = parser.parse_args()
    presupuesto, real = generar(args.seed)
    escribir(presupuesto, args.salida / "presupuesto.csv")
    escribir(real, args.salida / "real.csv")
    montos = generar_montos(args.seed)
    escribir(montos, args.salida / "montos.csv", CAMPOS_MONTOS)
    print(f"{len(presupuesto)} filas por archivo en {args.salida}; {len(montos)} filas en montos.csv")


if __name__ == "__main__":
    main()
