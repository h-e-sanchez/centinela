"""Genera data/capital-de-trabajo/: cobranza, pagos, inventario y caja semanal de las tres empresas ficticias.

Muestra cuándo llega a la caja el resultado del reporte Presupuesto vs. Real (#1). Las facturas
**cuadran con data/escenarios/montos.csv** por industria, sucursal, mes y cuenta, en 2025 y 2026:

- **Facturas de venta:** cada cuenta de ingreso Real se reparte entre los clientes del reporte de
  pricing (#7), con la condición de pago de su canal y un atraso propio de cada cliente.
- **Facturas de compra:** las cuentas de Costos que se compran a proveedores (materiales,
  combustibles, energía, mantención, medicamentos, honorarios) se reparten entre proveedores
  ficticios. Remuneraciones y gastos operacionales no pasan por facturas: se pagan en el mes.
- **Apertura:** facturas de octubre a diciembre de 2024 todavía abiertas el 1 de enero de 2025,
  para que la cobranza y los pagos de 2025 partan con cartera. No cuentan en la cuadratura.
- **Inventario:** saldo mensual por familia, como días de cobertura del consumo del mes (las
  cuentas de materiales del #1).
- **Caja semanal:** cobros y pagos reales por semana hasta la fecha de corte, y 13 semanas
  proyectadas con los vencimientos abiertos y la actividad del mismo mes de 2026. Suma los
  desembolsos que no están en el estado de resultados: dividendos e inversión en equipos.

Tres historias quedan sembradas: en Salud, Fonasa y las isapres pagan lento, el DSO supera los 90
días y la caja cae bajo el mínimo en el invierno de 2026; en Manufactura, el año flojo de 2025 deja
sobrestock de producto terminado en Antofagasta; en Energía, cobra antes de pagar y el ciclo de
conversión de caja es negativo.

Montos en CLP. Reproducible (semilla fija). Ningún dato real de ningún empleador.

Uso:
    python data/generar_capital_de_trabajo.py
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA))
# mismos clientes, canales y empresas del reporte de pricing (#7)
from generar_pricing import CANALES, CUENTAS, EMPRESAS

SEMILLA = 42
CORTE = date(2026, 12, 27)  # último día con pagos conocidos (domingo): lo posterior es proyección
INICIO_CAJA = date(2024, 12, 30)  # lunes de la primera semana de caja
SEMANAS_PROYECTADAS = 13
SALDO_INICIAL = {"Manufactura": 140_000_000, "Energia": 120_000_000, "Salud": 95_000_000}
# Desembolsos que no pasan por el estado de resultados del #1: dividendos e inversión en equipos.
NO_OPERACIONALES = [("Manufactura", date(2025, 5, 15), 120_000_000), ("Manufactura", date(2026, 5, 15), 220_000_000),
                    ("Energia", date(2025, 5, 15), 130_000_000), ("Energia", date(2026, 5, 15), 240_000_000),
                    ("Salud", date(2026, 4, 15), 95_000_000)]
DIA_MAXIMO_EMISION = 27  # se factura entre el 1 y el 27 de cada mes


@dataclass(frozen=True)
class Cobro:
    condicion: int  # días de crédito del canal
    atraso: float  # atraso promedio sobre el vencimiento
    dispersion: float


COBRO = {
    "Retail": Cobro(60, 8, 6), "Distribuidores": Cobro(45, 10, 8), "Industrial nacional": Cobro(30, 5, 5),
    "Exportación": Cobro(60, 0, 3), "Postventa": Cobro(30, 12, 8),
    "Clientes libres": Cobro(20, 2, 2), "Distribuidoras": Cobro(30, 3, 2), "Mercado spot": Cobro(15, 0, 1),
    "Peajes": Cobro(15, 0, 1),
    "Fonasa": Cobro(60, 58, 10), "Isapres": Cobro(45, 50, 10), "Convenios con empresas": Cobro(30, 15, 8),
    "Particulares": Cobro(0, 1, 1),
}
MOROSOS = {"Distribuidora Ejemplo 03": 55, "Distribuidora Ejemplo 07": 45, "Isapre Ejemplo 04": 40,
           "Cliente Postventa Ejemplo 09": 35}  # atraso adicional: concentran la cartera vencida

# cuenta de Costos del #1 -> (categoría, proveedores, condición de pago en días)
COMPRAS = {
    "Manufactura": {
        "Acero y metales": ("Materias primas", ("Aceros Ejemplo", "Metales del Norte Ejemplo", "Fundición Ejemplo"), 45),
        "Insumos químicos": ("Materias primas", ("Química Ejemplo", "Insumos Industriales Ejemplo"), 30),
        "Electricidad": ("Energía", ("Distribuidora Eléctrica Ejemplo Norte",), 30),
        "Gas": ("Energía", ("Gas Industrial Ejemplo",), 30),
    },
    "Energia": {
        "Compras a terceros": ("Energía comprada", ("Generadora Ejemplo 01", "Generadora Ejemplo 02",
                                                   "Generadora Ejemplo 03"), 45),
        "Gas natural": ("Combustibles", ("GNL Ejemplo", "Gas Andino Ejemplo"), 60),
        "Diésel": ("Combustibles", ("Combustibles Ejemplo", "Petrolera Ejemplo"), 60),
        "Mantención preventiva": ("Mantención", ("Servicios Técnicos Ejemplo 01", "Servicios Técnicos Ejemplo 02"), 60),
        "Mantención correctiva": ("Mantención", ("Servicios Técnicos Ejemplo 03", "Servicios Técnicos Ejemplo 04"), 60),
    },
    "Salud": {
        "Honorarios por acto": ("Honorarios médicos", tuple(f"Sociedad Médica Ejemplo {k:02d}" for k in range(1, 7)), 30),
        "Medicamentos": ("Medicamentos", ("Laboratorio Ejemplo 01", "Laboratorio Ejemplo 02", "Laboratorio Ejemplo 03",
                                          "Droguería Ejemplo"), 60),
        "Material clínico": ("Material clínico", ("Insumos Clínicos Ejemplo 01", "Insumos Clínicos Ejemplo 02",
                                                  "Insumos Clínicos Ejemplo 03"), 60),
    },
}
PRONTO_PAGO = 0.12  # Manufactura paga antes de plazo una parte de las facturas, por descuento
ATRASO_INVIERNO_SALUD = (12, 28)  # Salud estira a proveedores las facturas que vencen de junio a septiembre de 2026

# familia de inventario -> (cuentas de consumo, cobertura objetivo en días)
INVENTARIO = {
    "Manufactura": {"Materias primas": (("Acero y metales", "Insumos químicos"), 35),
                    "Producto terminado": (("Acero y metales", "Insumos químicos", "Sueldos operarios", "Electricidad",
                                            "Gas"), 20)},
    "Energia": {"Combustibles": (("Gas natural", "Diésel"), 14)},
    "Salud": {"Medicamentos": (("Medicamentos",), 28), "Material clínico": (("Material clínico",), 30)},
}
SOBRESTOCK_ANTOFAGASTA = 38  # días extra de producto terminado que alcanza a acumular a fines de 2025

ARCHIVOS = {
    "empresas": ["industria", "empresa", "orden"],
    "sucursales": ["sucursal", "industria", "orden"],
    "clientes": ["cliente", "industria", "segmento", "condicion_dias", "limite_credito", "perfil_pago"],
    "proveedores": ["proveedor", "industria", "categoria", "condicion_dias"],
    "facturas_venta": ["factura", "industria", "sucursal", "cliente", "cuenta", "emision", "vencimiento", "pago", "monto"],
    "facturas_compra": ["factura", "industria", "sucursal", "proveedor", "cuenta", "emision", "vencimiento", "pago",
                        "monto"],
    "inventario_mensual": ["fecha", "anio", "mes", "industria", "sucursal", "familia", "saldo", "consumo",
                           "cobertura_objetivo"],
    "caja_semanal": ["semana", "industria", "saldo_inicial", "cobros", "pagos_proveedores", "otros_pagos",
                     "inversiones_dividendos", "pagos",
                     "saldo_final", "tipo", "ventana"],
}


def leer_montos() -> list[dict]:
    with (DATA / "escenarios" / "montos.csv").open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r["version"] == "Real"]


def fin_de_mes(anio: int, mes: int) -> date:
    return (date(anio + mes // 12, mes % 12 + 1, 1) - timedelta(days=1))


def repartir(total: int, n: int, rng: random.Random) -> list[int]:
    pesos = [rng.uniform(0.6, 1.4) for _ in range(n)]
    partes = [round(total * p / sum(pesos)) for p in pesos]
    partes[-1] = total - sum(partes[:-1])
    return partes


def generar(seed: int = SEMILLA) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    montos = leer_montos()
    celdas = defaultdict(float)  # (industria, sucursal, anio, mes, cuenta) -> monto
    sucursales_de = defaultdict(list)
    grupo = {(r["industria"], r["cuenta"]): r["grupo_cuenta"] for r in montos}
    for r in montos:
        celdas[(r["industria"], r["sucursal"], int(r["anio"]), int(r["mes"]), r["cuenta"])] += float(r["monto"])
        if r["sucursal"] not in sucursales_de[r["industria"]]:
            sucursales_de[r["industria"]].append(r["sucursal"])
    clientes_de = {(i, nombre): canal.clientes for i, canales in CANALES.items() for nombre, canal in canales.items()}
    atraso_cliente = {cl: rng.uniform(0.7, 1.3) for cls in clientes_de.values() for cl in cls}

    def emision(anio: int, mes: int) -> date:
        return date(anio, mes, rng.randint(1, DIA_MAXIMO_EMISION))

    def atraso_esperado(segmento: str, cliente: str) -> float:
        return COBRO[segmento].atraso * atraso_cliente[cliente] + MOROSOS.get(cliente, 0)

    # --- facturas de venta ------------------------------------------------------------------------
    def facturas_de_venta(anio: int, mes: int, factor: float = 1.0, base_anio: int | None = None) -> list[dict]:
        salida = []
        for industria, cuentas in CUENTAS.items():
            for sucursal in sucursales_de[industria]:
                for cuenta, (_, reparto) in cuentas.items():
                    total = round(celdas.get((industria, sucursal, base_anio or anio, mes, cuenta), 0) * factor)
                    if total <= 0:
                        continue
                    restante = total
                    canales = list(reparto)
                    for k, canal in enumerate(canales):
                        meta = restante if k == len(canales) - 1 else round(total * reparto[canal])
                        restante -= meta
                        for monto in repartir(meta, rng.randint(1, 3), rng):
                            cliente = rng.choice(clientes_de[(industria, canal)])
                            e = emision(anio, mes)
                            v = e + timedelta(days=COBRO[canal].condicion)
                            atraso = rng.gauss(atraso_esperado(canal, cliente), COBRO[canal].dispersion)
                            p = max(e, v + timedelta(days=round(atraso)))
                            salida.append({"industria": industria, "sucursal": sucursal, "cliente": cliente,
                                           "segmento": canal, "cuenta": cuenta, "emision": e, "vencimiento": v,
                                           "pago": p, "monto": monto})
        return salida

    # --- facturas de compra -----------------------------------------------------------------------
    def facturas_de_compra(anio: int, mes: int, factor: float = 1.0, base_anio: int | None = None) -> list[dict]:
        salida = []
        for industria, cuentas in COMPRAS.items():
            for sucursal in sucursales_de[industria]:
                for cuenta, (_, proveedores, condicion) in cuentas.items():
                    total = round(celdas.get((industria, sucursal, base_anio or anio, mes, cuenta), 0) * factor)
                    if total <= 0:
                        continue
                    for monto in repartir(total, rng.randint(1, 3), rng):
                        e = emision(anio, mes)
                        v = e + timedelta(days=condicion)
                        atraso = rng.gauss(0, 2)
                        if industria == "Manufactura" and rng.random() < PRONTO_PAGO:
                            atraso = -rng.uniform(10, 18)
                        if industria == "Salud" and date(2026, 6, 1) <= v <= date(2026, 9, 30):
                            atraso = rng.uniform(*ATRASO_INVIERNO_SALUD)
                        p = max(e, v + timedelta(days=round(atraso)))
                        salida.append({"industria": industria, "sucursal": sucursal, "proveedor": rng.choice(proveedores),
                                       "cuenta": cuenta, "emision": e, "vencimiento": v, "pago": p, "monto": monto})
        return salida

    meses = [(a, m) for a in (2025, 2026) for m in range(1, 13)]
    ventas, compras = [], []
    for a, m in [(2024, 10), (2024, 11), (2024, 12)]:  # apertura: solo lo que sigue abierto el 1 de enero
        ventas += [f for f in facturas_de_venta(a, m, 0.95, base_anio=2025) if f["pago"] >= date(2025, 1, 1)]
        compras += [f for f in facturas_de_compra(a, m, 0.95, base_anio=2025) if f["pago"] >= date(2025, 1, 1)]
    for a, m in meses:
        ventas += facturas_de_venta(a, m)
        compras += facturas_de_compra(a, m)
    # actividad proyectada de enero a marzo de 2027 (igual al mismo mes de 2026), solo para la caja
    ventas_futuras = [f for m in (1, 2, 3) for f in facturas_de_venta(2027, m, base_anio=2026)]
    compras_futuras = [f for m in (1, 2, 3) for f in facturas_de_compra(2027, m, base_anio=2026)]

    # --- caja semanal -----------------------------------------------------------------------------
    semanas_reales = (CORTE - INICIO_CAJA).days // 7 + 1
    fin_proyeccion = CORTE + timedelta(days=7 * SEMANAS_PROYECTADAS)

    def semana(d: date) -> date:
        return INICIO_CAJA + timedelta(days=(d - INICIO_CAJA).days // 7 * 7)

    flujos = defaultdict(lambda: [0, 0, 0, 0])  # (industria, semana) -> cobros, proveedores, otros pagos, inversiones
    vencidas_abiertas = defaultdict(int)

    def esperado_venta(f: dict) -> date:
        return f["vencimiento"] + timedelta(days=round(atraso_esperado(f["segmento"], f["cliente"])))

    for f in ventas:
        if f["pago"] <= CORTE:
            flujos[(f["industria"], semana(f["pago"]))][0] += f["monto"]
        else:  # abierta al corte: se proyecta con el atraso típico del cliente
            d = max(esperado_venta(f), CORTE + timedelta(days=1 + vencidas_abiertas[f["industria"]] % 28))
            vencidas_abiertas[f["industria"]] += 1
            if d <= fin_proyeccion:
                flujos[(f["industria"], semana(d))][0] += f["monto"]
    for f in ventas_futuras:
        d = max(esperado_venta(f), f["emision"])
        if d <= fin_proyeccion:
            flujos[(f["industria"], semana(d))][0] += f["monto"]
    for f in compras:
        if f["pago"] <= CORTE:
            flujos[(f["industria"], semana(f["pago"]))][1] += f["monto"]
        else:
            d = max(f["vencimiento"], CORTE + timedelta(days=1))
            if d <= fin_proyeccion:
                flujos[(f["industria"], semana(d))][1] += f["monto"]
    for f in compras_futuras:
        if f["vencimiento"] <= fin_proyeccion:
            flujos[(f["industria"], semana(f["vencimiento"]))][1] += f["monto"]
    # remuneraciones a fin de mes; gastos operacionales en dos pagos (día 10 y día 25)
    compradas = {(i, c) for i, cuentas in COMPRAS.items() for c in cuentas}
    otros = defaultdict(lambda: [0.0, 0.0])
    for (industria, sucursal, anio, mes, cuenta), monto in celdas.items():
        if (industria, cuenta) in compradas or grupo[(industria, cuenta)] == "Ingresos":
            continue
        es_remuneracion = cuenta.startswith(("Sueldos", "Horas extra", "Turnos", "Guardias", "Bonos", "Beneficios"))
        otros[(industria, anio, mes)][0 if es_remuneracion else 1] += monto
    for (industria, anio, mes), (remuneraciones, gastos) in otros.items():
        pagos = [(fin_de_mes(anio, mes), remuneraciones), (date(anio, mes, 10), gastos / 2), (date(anio, mes, 25), gastos / 2)]
        if anio == 2026 and mes <= 3:  # el mismo calendario se repite en la proyección de 2027
            pagos += [(fin_de_mes(2027, mes), remuneraciones), (date(2027, mes, 10), gastos / 2),
                      (date(2027, mes, 25), gastos / 2)]
        for d, monto in pagos:
            if INICIO_CAJA <= d <= fin_proyeccion:
                flujos[(industria, semana(d))][2] += round(monto)

    for industria, d, monto in NO_OPERACIONALES:
        flujos[(industria, semana(d))][3] += monto

    caja = []
    for industria in EMPRESAS:
        saldo = SALDO_INICIAL[industria]
        for k in range(semanas_reales + SEMANAS_PROYECTADAS):
            s = INICIO_CAJA + timedelta(days=7 * k)
            cobros, proveedores, otros_pagos, inversiones = (round(x) for x in flujos[(industria, s)])
            pagos = proveedores + otros_pagos + inversiones
            real = k < semanas_reales
            ventana = ("Últimas 13 semanas" if k >= semanas_reales - SEMANAS_PROYECTADAS else "Historia") if real \
                else "Próximas 13 semanas"
            caja.append({"semana": s.isoformat(), "industria": industria, "saldo_inicial": saldo, "cobros": cobros,
                         "pagos_proveedores": proveedores, "otros_pagos": otros_pagos,
                         "inversiones_dividendos": inversiones, "pagos": pagos, "saldo_final": saldo + cobros - pagos,
                         "tipo": "Real" if real else "Proyectado", "ventana": ventana})
            saldo = caja[-1]["saldo_final"]

    # --- inventario mensual -----------------------------------------------------------------------
    inventario = []
    for industria, familias in INVENTARIO.items():
        for sucursal in sucursales_de[industria]:
            for familia, (cuentas, objetivo) in familias.items():
                for a, m in meses:
                    consumo = round(sum(celdas.get((industria, sucursal, a, m, c), 0) for c in cuentas))
                    dias = objetivo * rng.uniform(0.85, 1.15)
                    if industria == "Manufactura" and sucursal == "Antofagasta" and familia == "Producto terminado":
                        # 2025 vende bajo el presupuesto y la planta sigue produciendo; 2026 liquida el stock
                        k = (a - 2025) * 12 + m
                        dias += SOBRESTOCK_ANTOFAGASTA * (k / 12 if k <= 12 else max(0.0, 1 - (k - 12) / 6))
                    if industria == "Salud" and a == 2026 and m in (6, 7, 8) and rng.random() < 0.5:
                        dias = rng.uniform(2, 4)  # quiebre: el consumo de invierno supera la reposición
                    inventario.append({"fecha": f"{a}-{m:02d}-01", "anio": a, "mes": m, "industria": industria,
                                       "sucursal": sucursal, "familia": familia, "saldo": round(consumo / 30 * dias),
                                       "consumo": consumo, "cobertura_objetivo": objetivo})

    # --- dimensiones y salida ---------------------------------------------------------------------
    venta_mensual = defaultdict(float)
    for f in ventas:
        if f["emision"].year >= 2025:
            venta_mensual[f["cliente"]] += f["monto"] / 24
    clientes = []
    for industria, canales in CANALES.items():
        for nombre, canal in canales.items():
            for cl in canal.clientes:
                atraso = atraso_esperado(nombre, cl)
                perfil = "Moroso" if cl in MOROSOS else "Lento" if atraso > 20 else "Puntual"
                limite = round(venta_mensual[cl] * max(1, COBRO[nombre].condicion / 30) * 1.5, -6)
                clientes.append({"cliente": cl, "industria": industria, "segmento": nombre,
                                 "condicion_dias": COBRO[nombre].condicion, "limite_credito": int(limite),
                                 "perfil_pago": perfil})
    proveedores = [{"proveedor": p, "industria": i, "categoria": cat, "condicion_dias": cond}
                   for i, cuentas in COMPRAS.items() for cat, ps, cond in cuentas.values() for p in ps]

    def filas(facturas: list[dict], prefijo: str, contraparte: str) -> list[dict]:
        orden = sorted(facturas, key=lambda f: (f["emision"], f["industria"], f["sucursal"], f["cuenta"], f[contraparte]))
        return [{"factura": f"{prefijo}{k:06d}", "industria": f["industria"], "sucursal": f["sucursal"],
                 contraparte: f[contraparte], "cuenta": f["cuenta"], "emision": f["emision"].isoformat(),
                 "vencimiento": f["vencimiento"].isoformat(),
                 "pago": f["pago"].isoformat() if f["pago"] <= CORTE else "", "monto": f["monto"]}
                for k, f in enumerate(orden, 1)]

    return {
        "empresas": [{"industria": i, "empresa": e, "orden": k} for k, (i, e) in enumerate(EMPRESAS.items(), 1)],
        "sucursales": [{"sucursal": s, "industria": i, "orden": k + 1} for i in EMPRESAS for k, s in enumerate(sucursales_de[i])],
        "clientes": clientes,
        "proveedores": proveedores,
        "facturas_venta": filas(ventas, "FV", "cliente"),
        "facturas_compra": filas(compras, "FC", "proveedor"),
        "inventario_mensual": inventario,
        "caja_semanal": caja,
    }


def escribir(tablas: dict[str, list[dict]], carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, campos in ARCHIVOS.items():
        with (carpeta / f"{nombre}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
            w.writeheader()
            w.writerows(tablas[nombre])


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los datos sintéticos del reporte de capital de trabajo.")
    parser.add_argument("--seed", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=DATA / "capital-de-trabajo")
    args = parser.parse_args()
    tablas = generar(args.seed)
    escribir(tablas, args.salida)
    for nombre, filas in tablas.items():
        print(f"{nombre:20} {len(filas):7d} filas")


if __name__ == "__main__":
    main()
