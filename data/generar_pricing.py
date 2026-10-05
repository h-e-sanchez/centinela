"""Genera data/pricing-margenes/: precios, descuentos y márgenes por canal de las tres empresas ficticias.

Abre la venta del reporte Presupuesto vs. Real (#1) para ver a qué precio y con qué margen se
vendió. Los ingresos netos **cuadran con las cuentas de ingreso Real de data/escenarios/montos.csv**
por industria, sucursal, mes y cuenta, en 2025 y 2026:

- **Canales:** cada cuenta de ingreso se reparte entre canales (Manufactura: retail, distribuidores,
  industrial nacional, exportación y postventa; Energía: clientes libres, distribuidoras, mercado
  spot y peajes; Salud: Fonasa, isapres, convenios con empresas y particulares).
- **Cascada de precios:** cada línea parte del precio de lista y descuenta el descuento comercial,
  el rappel y la bonificación según el canal y la propensión del cliente. Con el costo variable
  del producto y el costo de servir del canal queda el margen de contribución.
- **Cuadratura:** las cantidades se escalan para que la suma de ingresos netos de cada celda sea
  exactamente el Real del #1. En Energía el volumen (MWh) es casi el mismo cada año y lo que se
  ajusta es el precio: la variación de ingresos viene del precio.
- **Presupuesto:** las cuentas de ingreso del Presupuesto del #1 viajan aparte, para comparar.

Tres historias quedan sembradas: en Manufactura, retail mueve el mayor volumen pero, con rappel y
costo de servir, deja el margen de contribución más bajo; en Energía, el efecto precio explica casi
toda la variación de 2026 contra 2025; en Salud, una parte de las líneas de convenios con empresas
supera el descuento máximo de la política y algunos convenios quedan con margen negativo.

Montos en CLP. Reproducible (semilla fija). Ningún dato real de ningún empleador.

Uso:
    python data/generar_pricing.py
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

SEMILLA = 42
DATA = Path(__file__).resolve().parent
ALZA_LISTA_2026 = 0.04  # reajuste de la lista de precios (no aplica a energía, que se fija por mercado)
LINEAS_POR_CANAL = (2, 4)  # líneas de venta por canal, sucursal, mes y cuenta


@dataclass(frozen=True)
class Canal:
    nombre: str
    clientes: tuple[str, ...]
    descuento: tuple[float, float, float]  # comercial, rappel y bonificación promedio (sobre la lista)
    maximo: float  # descuento total máximo según la política comercial
    costo_servir: float  # sobre el ingreso neto: logística, comisiones y atención del canal
    elasticidad: float  # cambio % de volumen por cada 1% de cambio de precio (supuesto del simulador)


def _clientes(prefijo: str, n: int) -> tuple[str, ...]:
    return tuple(f"{prefijo} {k:02d}" for k in range(1, n + 1))


CANALES = {
    "Manufactura": {
        "Retail": Canal("Retail", ("Supermercados Ejemplo Uno", "Supermercados Ejemplo Dos", "Hipermercado Ejemplo",
                                   "Mayorista Retail Ejemplo"), (0.09, 0.09, 0.05), 0.24, 0.115, -1.6),
        "Distribuidores": Canal("Distribuidores", _clientes("Distribuidora Ejemplo", 10), (0.10, 0.02, 0.01), 0.15, 0.04, -1.2),
        "Industrial nacional": Canal("Industrial nacional", _clientes("Industria Cliente Ejemplo", 12), (0.05, 0.0, 0.0), 0.08,
                                     0.03, -0.6),
        "Exportación": Canal("Exportación", _clientes("Importador Ejemplo", 5), (0.03, 0.0, 0.0), 0.05, 0.06, -0.8),
        "Postventa": Canal("Postventa", _clientes("Cliente Postventa Ejemplo", 15), (0.02, 0.0, 0.0), 0.05, 0.10, -0.3),
    },
    "Energia": {
        "Clientes libres": Canal("Clientes libres", _clientes("Cliente Libre Ejemplo", 8), (0.05, 0.0, 0.0), 0.08, 0.02, -0.3),
        "Distribuidoras": Canal("Distribuidoras", _clientes("Distribuidora Eléctrica Ejemplo", 3), (0.08, 0.0, 0.0), 0.10,
                                0.01, -0.1),
        "Mercado spot": Canal("Mercado spot", ("Mercado spot (coordinador)",), (0.0, 0.0, 0.0), 0.0, 0.005, 0.0),
        "Peajes": Canal("Peajes", ("Usuarios del sistema de transmisión",), (0.0, 0.0, 0.0), 0.0, 0.01, 0.0),
    },
    "Salud": {
        "Fonasa": Canal("Fonasa", ("Fonasa",), (0.40, 0.0, 0.0), 0.40, 0.03, -0.2),
        "Isapres": Canal("Isapres", _clientes("Isapre Ejemplo", 6), (0.18, 0.0, 0.0), 0.22, 0.04, -0.5),
        "Convenios con empresas": Canal("Convenios con empresas", _clientes("Empresa Convenio Ejemplo", 14), (0.19, 0.0, 0.0),
                                        0.25, 0.05, -0.9),
        "Particulares": Canal("Particulares", ("Pacientes particulares",), (0.02, 0.0, 0.0), 0.05, 0.03, -1.1),
    },
}

# cuenta del #1 -> (productos con su costo variable como fracción de la lista, reparto de la cuenta entre canales)
CUENTAS = {
    "Manufactura": {
        "Canal supermercados": ({"Línea consumo · Producto A": 0.66, "Línea consumo · Producto B": 0.64,
                                 "Línea consumo · Producto C": 0.68}, {"Retail": 1.0}),
        "Canal mayorista": ({"Línea consumo · Producto A": 0.66, "Línea consumo · Producto B": 0.64,
                             "Línea consumo · Producto C": 0.68}, {"Distribuidores": 1.0}),
        "Ventas nacionales": ({"Línea industrial · Producto D": 0.58, "Línea industrial · Producto E": 0.60},
                              {"Industrial nacional": 1.0}),
        "Exportaciones": ({"Línea industrial · Producto D": 0.58, "Línea industrial · Producto E": 0.60},
                          {"Exportación": 1.0}),
        "Contratos de mantención": ({"Contrato de mantención (mes)": 0.45}, {"Postventa": 1.0}),
        "Repuestos": ({"Kit de repuestos": 0.55}, {"Postventa": 1.0}),
    },
    "Energia": {
        "Clientes libres": ({"Energía contratada (MWh)": 0.52}, {"Clientes libres": 1.0}),
        "Distribuidoras": ({"Energía regulada (MWh)": 0.55}, {"Distribuidoras": 1.0}),
        "Mercado spot": ({"Energía spot (MWh)": 0.60}, {"Mercado spot": 1.0}),
        "Peajes nacionales": ({"Peaje de transmisión (MWh)": 0.20}, {"Peajes": 1.0}),
        "Peajes zonales": ({"Peaje de transmisión (MWh)": 0.20}, {"Peajes": 1.0}),
    },
    "Salud": {
        "Pacientes Fonasa": ({"Consulta ambulatoria": 0.55, "Examen de laboratorio": 0.50}, {"Fonasa": 1.0}),
        "Pacientes Isapre": ({"Consulta ambulatoria": 0.55, "Examen de laboratorio": 0.50}, {"Isapres": 1.0}),
        "Días cama": ({"Día cama": 0.55}, {"Fonasa": 0.35, "Isapres": 0.40, "Convenios con empresas": 0.15,
                                          "Particulares": 0.10}),
        "Medicamentos facturados": ({"Medicamento facturado": 0.62}, {"Fonasa": 0.35, "Isapres": 0.40,
                                                                     "Convenios con empresas": 0.15, "Particulares": 0.10}),
        "Cirugías programadas": ({"Cirugía programada": 0.55}, {"Isapres": 0.50, "Convenios con empresas": 0.25,
                                                               "Fonasa": 0.15, "Particulares": 0.10}),
        "Cirugías de urgencia": ({"Cirugía de urgencia": 0.58}, {"Fonasa": 0.40, "Isapres": 0.40,
                                                                "Convenios con empresas": 0.10, "Particulares": 0.10}),
    },
}

PRECIO_LISTA_2025 = {  # CLP por unidad
    "Línea consumo · Producto A": 12_000, "Línea consumo · Producto B": 8_500, "Línea consumo · Producto C": 15_500,
    "Línea industrial · Producto D": 240_000, "Línea industrial · Producto E": 410_000,
    "Contrato de mantención (mes)": 1_150_000, "Kit de repuestos": 180_000,
    "Energía contratada (MWh)": 92_000, "Energía regulada (MWh)": 98_000, "Energía spot (MWh)": 110_000,
    "Peaje de transmisión (MWh)": 18_000,
    "Consulta ambulatoria": 45_000, "Examen de laboratorio": 28_000, "Día cama": 420_000,
    "Medicamento facturado": 38_000, "Cirugía programada": 3_800_000, "Cirugía de urgencia": 4_600_000,
}
ENERGIA_POR_MERCADO = {"Energía contratada (MWh)", "Energía regulada (MWh)", "Energía spot (MWh)",
                       "Peaje de transmisión (MWh)"}
CONVENIOS_SOBRE_POLITICA = 3  # convenios de Salud que negocian descuentos sobre la política
EMPRESAS = {"Manufactura": "Manufacturas Ejemplo S.A.", "Energia": "Energía Ejemplo S.A.",
            "Salud": "Red Asistencial Ejemplo S.A."}

ARCHIVOS = {
    "empresas": ["industria", "empresa", "orden"],
    "sucursales": ["sucursal", "industria", "orden"],
    "canales": ["canal", "industria", "descuento_maximo", "costo_servir_pct", "elasticidad", "orden"],
    "clientes": ["cliente", "industria", "canal", "segmento"],
    "productos": ["producto", "industria", "linea", "unidad", "costo_variable_pct"],
    "lista_precios": ["producto", "industria", "anio", "precio_lista"],
    "transacciones": ["id_linea", "fecha", "anio", "industria", "sucursal", "cuenta", "canal", "cliente", "producto",
                      "cantidad", "ingreso_lista", "descuento_comercial", "rappel", "bonificacion", "ingreso_neto",
                      "costo_variable", "costo_servir"],
    "presupuesto_ingresos": ["fecha", "anio", "industria", "sucursal", "cuenta", "monto"],
}


def leer_montos() -> list[dict]:
    with (DATA / "escenarios" / "montos.csv").open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r["grupo_cuenta"] == "Ingresos" and r["version"] in ("Real", "Presupuesto")]


def precio_lista(producto: str, anio: int) -> int:
    alza = 0 if producto in ENERGIA_POR_MERCADO else ALZA_LISTA_2026
    return int(round(PRECIO_LISTA_2025[producto] * (1 + alza) ** (anio - 2025), -1))


def generar(seed: int = SEMILLA) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    montos = leer_montos()
    sucursales_de = defaultdict(list)
    for r in montos:
        if r["sucursal"] not in sucursales_de[r["industria"]]:
            sucursales_de[r["industria"]].append(r["sucursal"])

    # Propensión de cada cliente a negociar descuentos (los de convenios sobre la política, marcados).
    propension = {}
    for industria, canales in CANALES.items():
        for canal in canales.values():
            for cliente in canal.clientes:
                propension[cliente] = rng.uniform(0.85, 1.12)
    convenios = list(CANALES["Salud"]["Convenios con empresas"].clientes)
    for cliente in rng.sample(convenios, CONVENIOS_SOBRE_POLITICA):
        propension[cliente] = rng.uniform(2.05, 2.35)  # negocian 39% a 45% sobre la lista

    # Volumen de energía por celda: el de 2025 a precio de lista, casi igual en 2026. El precio se ajusta para
    # cuadrar con el #1, así que la variación de ingresos de Energía viene del precio.
    monto_2025 = {(r["sucursal"], int(r["mes"]), r["cuenta"]): float(r["monto"]) for r in montos
                  if r["version"] == "Real" and r["anio"] == "2025" and r["industria"] == "Energia"}
    volumen_base = {}

    lineas, n = [], 0
    reales = sorted((r for r in montos if r["version"] == "Real"),
                    key=lambda r: (r["industria"], r["sucursal"], int(r["anio"]), int(r["mes"]), r["cuenta"]))
    for r in reales:
        industria, anio, mes, cuenta = r["industria"], int(r["anio"]), int(r["mes"]), r["cuenta"]
        objetivo = round(float(r["monto"]))
        productos, reparto = CUENTAS[industria][cuenta]
        canales = list(reparto)
        restante = objetivo
        for k, nombre in enumerate(canales):
            canal = CANALES[industria][nombre]
            meta = restante if k == len(canales) - 1 else round(objetivo * reparto[nombre])
            restante -= meta
            borrador = []
            for _ in range(rng.randint(*LINEAS_POR_CANAL)):
                cliente = rng.choice(canal.clientes)
                producto = rng.choice(list(productos))
                factor = propension[cliente]
                dc, rp, bo = (min(0.6, max(0.0, d * factor * rng.uniform(0.9, 1.1))) for d in canal.descuento)
                if producto in ENERGIA_POR_MERCADO:
                    clave = (r["sucursal"], mes, cuenta, producto)
                    volumen_base.setdefault(clave, rng.uniform(0.9, 1.1))
                    peso = volumen_base[clave] * (1 + rng.uniform(-0.01, 0.01))
                else:
                    peso = rng.uniform(0.6, 1.4)
                borrador.append([cliente, producto, peso, dc, rp, bo])
            # Escala: la suma de ingresos netos del canal = meta. Fuera de Energía se escala la cantidad a precio de
            # lista; en Energía la cantidad sale del volumen de 2025 y se escala el precio.
            neto_por_peso = sum(p * precio_lista(prod, anio) * (1 - dc - rp - bo) for _, prod, p, dc, rp, bo in borrador)
            escala = meta / neto_por_peso if neto_por_peso else 0
            energia = industria == "Energia"
            if energia:
                volumen = monto_2025[(r["sucursal"], mes, cuenta)] * reparto[nombre]
                peso_total = sum(b[2] for b in borrador)
                escala_volumen = volumen / precio_lista(borrador[0][1], 2025) / peso_total
            acumulado = 0
            for j, (cliente, producto, peso, dc, rp, bo) in enumerate(borrador):
                unitario = precio_lista(producto, anio)
                cantidad = peso * escala
                if energia:
                    cantidad = peso * escala_volumen
                    unitario = precio_lista(producto, anio) * (peso * escala) / cantidad
                bruto = cantidad * unitario
                d_com, d_rap, d_bon = round(bruto * dc), round(bruto * rp), round(bruto * bo)
                neto = round(bruto) - d_com - d_rap - d_bon
                if j == len(borrador) - 1:  # el residuo de redondeo cae en la última línea
                    neto = meta - acumulado
                acumulado += neto
                ingreso_lista = neto + d_com + d_rap + d_bon
                n += 1
                lineas.append({
                    "id_linea": f"V{n:06d}", "fecha": f"{anio}-{mes:02d}-01", "anio": anio, "industria": industria,
                    "sucursal": r["sucursal"], "cuenta": cuenta, "canal": nombre, "cliente": cliente, "producto": producto,
                    "cantidad": round(cantidad, 2), "ingreso_lista": ingreso_lista, "descuento_comercial": d_com,
                    "rappel": d_rap, "bonificacion": d_bon, "ingreso_neto": neto,
                    "costo_variable": round(ingreso_lista * productos[producto]),
                    "costo_servir": round(neto * canal.costo_servir),
                })

    tablas = {
        "empresas": [{"industria": i, "empresa": e, "orden": k} for k, (i, e) in enumerate(EMPRESAS.items(), 1)],
        "sucursales": [{"sucursal": s, "industria": i, "orden": k + 1} for i in EMPRESAS for k, s in enumerate(sucursales_de[i])],
        "canales": [{"canal": c.nombre, "industria": i, "descuento_maximo": c.maximo, "costo_servir_pct": c.costo_servir,
                     "elasticidad": c.elasticidad, "orden": k + 1}
                    for i, canales in CANALES.items() for k, c in enumerate(canales.values())],
        "clientes": [{"cliente": cl, "industria": i, "canal": c.nombre,
                      "segmento": "Sobre la política" if propension[cl] > 1.5 else "Estándar"}
                     for i, canales in CANALES.items() for c in canales.values() for cl in c.clientes],
        "productos": [],
        "lista_precios": [],
        "transacciones": lineas,
        "presupuesto_ingresos": [{"fecha": f"{r['anio']}-{int(r['mes']):02d}-01", "anio": int(r["anio"]),
                                  "industria": r["industria"], "sucursal": r["sucursal"], "cuenta": r["cuenta"],
                                  "monto": round(float(r["monto"]))}
                                 for r in sorted((m for m in montos if m["version"] == "Presupuesto"),
                                                 key=lambda m: (m["industria"], m["sucursal"], int(m["anio"]),
                                                                int(m["mes"]), m["cuenta"]))],
    }
    vistos = set()
    for industria, cuentas in CUENTAS.items():
        for productos, _ in cuentas.values():
            for producto, costo in productos.items():
                if (industria, producto) in vistos:
                    continue
                vistos.add((industria, producto))
                linea = producto.split(" · ")[0] if " · " in producto else producto.split(" (")[0]
                unidad = "MWh" if "MWh" in producto else "mes" if "(mes)" in producto else "unidad"
                tablas["productos"].append({"producto": producto, "industria": industria, "linea": linea,
                                            "unidad": unidad, "costo_variable_pct": costo})
                for anio in (2025, 2026):
                    tablas["lista_precios"].append({"producto": producto, "industria": industria, "anio": anio,
                                                    "precio_lista": precio_lista(producto, anio)})
    return tablas


def escribir(tablas: dict[str, list[dict]], carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, campos in ARCHIVOS.items():
        with (carpeta / f"{nombre}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
            w.writeheader()
            w.writerows(tablas[nombre])


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los datos sintéticos del reporte de pricing y márgenes.")
    parser.add_argument("--seed", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=DATA / "pricing-margenes")
    args = parser.parse_args()
    tablas = generar(args.seed)
    escribir(tablas, args.salida)
    for nombre, filas in tablas.items():
        print(f"{nombre:22} {len(filas):7d} filas")


if __name__ == "__main__":
    main()
