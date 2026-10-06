"""Genera data/estados-financieros/: el libro diario de las tres empresas ficticias y lo necesario para sus EEFF.

Cierra el círculo del reporte Presupuesto vs. Real (#1): sus ingresos, costos y gastos Real pasan a
asientos contables, y se les suma lo que el #1 no muestra (cobranza, compras e inventario, pago de
remuneraciones, depreciación, inversión, deuda e impuestos). Con eso salen el balance, el estado de
resultados y el flujo de efectivo de cada empresa, mes a mes, en 2025 y 2026. Sin consolidación:
cada empresa lleva su propia contabilidad.

- **Partida doble:** cada asiento suma lo mismo al debe y al haber. Un asiento de apertura al 1 de
  enero de 2025 deja el balance inicial cuadrado (los resultados acumulados son el cuadre).
- **EBITDA = resultado operacional del #1:** ingresos, costos y gastos operacionales son los Real del
  #1 por sucursal y cuenta. Bajo el EBITDA van depreciación, gastos financieros e impuesto (27%).
- **Capital de trabajo:** las ventas se cobran con el patrón de días de cada industria (las
  aseguradoras de Salud pagan lento); los materiales pasan por inventario (Manufactura compra según
  presupuesto, así que en su año flojo de ventas el inventario crece); los proveedores se pagan con
  su propio plazo y las remuneraciones al mes siguiente.
- **Cierre:** el 31 de diciembre los resultados se cierran contra «Resultado del ejercicio» y en
  enero se traspasan a «Resultados acumulados». El impuesto del año se paga en abril siguiente.

Tres historias quedan sembradas: Salud cobra a más de 90 días y vive con liquidez justa, apoyada en
un crédito de corto plazo; Energía es intensiva en activo fijo, con depreciación y deuda altas; y
Manufactura acumula inventario en su año flojo de ventas.

Montos en CLP, sin IVA. Reproducible (semilla fija). Ningún dato real de ningún empleador.

Uso:
    python data/generar_estados_financieros.py
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SEMILLA = 42
DATA = Path(__file__).resolve().parent
TASA_IMPUESTO = 0.27
MESES = [(a, m) for a in (2025, 2026) for m in range(1, 13)]
CAJA_MINIMA = 0.20  # meses de venta: bajo esto se gira la línea de crédito de corto plazo
CAJA_HOLGADA = 0.60  # sobre esto se amortiza la línea
INVENTARIABLES = {"materias_primas", "combustibles", "insumos_medicos"}
REMUNERACIONES = {"mano_de_obra_directa", "remuneraciones_administrativas", "remuneraciones_clinicas", "honorarios_medicos"}


@dataclass(frozen=True)
class Perfil:
    empresa: str
    cobranza: dict[int, float]  # meses de atraso → fracción de la venta que se cobra
    pago_proveedores: dict[int, float]
    caja_inicial_meses: float  # meses de venta
    dias_inventario: float  # inventario inicial, en días de consumo
    compra_segun_presupuesto: float  # 0: compra lo que consume; >0: compra el presupuesto 2025 por este factor
    activo_fijo_ventas: float  # activo fijo bruto inicial sobre la venta anual
    depreciacion_acumulada: float  # fracción ya depreciada al inicio
    tasa_depreciacion: float  # anual sobre el activo fijo bruto
    inversion_anual: float  # sobre el activo fijo bruto
    deuda_lp: float  # deuda de largo plazo sobre el activo fijo neto
    amortizacion_meses: int
    deuda_cp: int  # crédito de corto plazo (CLP)
    tasa_interes: float
    capital: float  # fracción del patrimonio inicial que es capital pagado


PERFILES = {
    "Manufactura": Perfil("Manufacturas Ejemplo S.A.", {1: 0.30, 2: 0.60, 3: 0.10}, {1: 0.35, 2: 0.65}, 1.0, 60, 1.18,
                          0.80, 0.40, 0.08, 0.06, 0.30, 120, 0, 0.075, 0.40),
    "Energia": Perfil("Energía Ejemplo S.A.", {1: 0.90, 2: 0.10}, {1: 0.55, 2: 0.45}, 1.0, 30, 0,
                      2.50, 0.40, 0.05, 0.04, 0.70, 240, 0, 0.07, 0.30),
    "Salud": Perfil("Red Asistencial Ejemplo S.A.", {2: 0.15, 3: 0.50, 4: 0.35}, {1: 0.50, 2: 0.50}, 0.3, 25, 0,
                    0.60, 0.40, 0.08, 0.05, 0.20, 120, 140_000_000, 0.08, 0.50),
}

# código, nombre, tipo, clasificación, línea del EERR o del balance, naturaleza (1 deudora, -1 acreedora)
CUENTAS_BALANCE = [
    ("1101", "Caja y bancos", "Activo", "Activo corriente", "Efectivo", 1),
    ("1102", "Deudores por ventas", "Activo", "Activo corriente", "Deudores por ventas", 1),
    ("1103", "Inventarios", "Activo", "Activo corriente", "Inventarios", 1),
    ("1201", "Propiedades, planta y equipo", "Activo", "Activo no corriente", "Activo fijo neto", 1),
    ("1202", "Depreciación acumulada", "Activo", "Activo no corriente", "Activo fijo neto", 1),
    ("2101", "Proveedores", "Pasivo", "Pasivo corriente", "Proveedores", -1),
    ("2102", "Remuneraciones por pagar", "Pasivo", "Pasivo corriente", "Remuneraciones por pagar", -1),
    ("2103", "Préstamos bancarios de corto plazo", "Pasivo", "Pasivo corriente", "Deuda financiera de corto plazo", -1),
    ("2104", "Impuesto a la renta por pagar", "Pasivo", "Pasivo corriente", "Impuestos por pagar", -1),
    ("2201", "Deuda financiera de largo plazo", "Pasivo", "Pasivo no corriente", "Deuda financiera de largo plazo", -1),
    ("3101", "Capital pagado", "Patrimonio", "Patrimonio", "Capital", -1),
    ("3102", "Resultados acumulados", "Patrimonio", "Patrimonio", "Resultados acumulados", -1),
    ("3103", "Resultado del ejercicio", "Patrimonio", "Patrimonio", "Resultado del ejercicio", -1),
]
CUENTAS_BAJO_EBITDA = [
    ("6901", "Depreciación", "Gasto", "Depreciación", "Depreciación", 1),
    ("6902", "Intereses", "Gasto", "Gastos financieros", "Gastos financieros", 1),
    ("6903", "Impuesto a la renta", "Gasto", "Impuesto a la renta", "Impuesto a la renta", 1),
]

ARCHIVOS = {
    "empresas": ["industria", "empresa", "orden"],
    "plan_cuentas": ["cuenta_codigo", "industria", "cuenta", "tipo", "clasificacion", "linea", "naturaleza", "componente",
                     "inventariable", "orden"],
    "asientos": ["asiento", "fecha", "industria", "tipo", "glosa"],
    "lineas_asiento": ["asiento", "linea", "industria", "cuenta_codigo", "sucursal", "debe", "haber"],
    "eerr_reporte1": ["version", "fecha", "industria", "sucursal", "cuenta_codigo", "monto"],
}


def fecha_fin(anio: int, mes: int) -> date:
    siguiente = date(anio + mes // 12, mes % 12 + 1, 1)
    return date.fromordinal(siguiente.toordinal() - 1)


def leer_montos() -> list[dict]:
    with (DATA / "escenarios" / "montos.csv").open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r["version"] in ("Real", "Presupuesto")]


def plan_de_cuentas(montos: list[dict]) -> tuple[list[dict], dict[tuple[str, str], str]]:
    """Plan común de balance y bajo EBITDA, más una cuenta de resultados por cuenta del #1 y empresa."""
    filas, codigo_de = [], {}
    orden = 0
    for industria in PERFILES:
        for cod, nombre, tipo, clas, linea, nat in CUENTAS_BALANCE + CUENTAS_BAJO_EBITDA:
            orden += 1
            filas.append({"cuenta_codigo": f"{industria[:3].upper()}-{cod}", "industria": industria, "cuenta": nombre,
                          "tipo": tipo, "clasificacion": clas, "linea": linea, "naturaleza": nat, "componente": "",
                          "inventariable": 0, "orden": int(cod)})
        vistos = {}
        for r in montos:
            if r["industria"] != industria:
                continue
            clave = (r["grupo_cuenta"], r["componente"], r["cuenta"])
            vistos.setdefault(clave, None)
        contadores = defaultdict(int)
        prefijo = {"Ingresos": "41", "Costos": "51", "Gastos Operacionales": "61"}
        for grupo, componente, cuenta in sorted(vistos, key=lambda k: (prefijo[k[0]], k[1], k[2])):
            contadores[grupo] += 1
            cod = f"{prefijo[grupo]}{contadores[grupo]:02d}"
            tipo = {"Ingresos": "Ingreso", "Costos": "Costo", "Gastos Operacionales": "Gasto"}[grupo]
            linea = {"Ingresos": "Ingresos", "Costos": "Costos", "Gastos Operacionales": "Gastos operacionales"}[grupo]
            codigo = f"{industria[:3].upper()}-{cod}"
            codigo_de[(industria, cuenta, componente)] = codigo
            filas.append({"cuenta_codigo": codigo, "industria": industria, "cuenta": cuenta, "tipo": tipo,
                          "clasificacion": "Estado de resultados", "linea": linea,
                          "naturaleza": -1 if tipo == "Ingreso" else 1, "componente": componente,
                          "inventariable": int(componente in INVENTARIABLES), "orden": int(cod)})
    return filas, codigo_de


class Libro:
    def __init__(self) -> None:
        self.asientos, self.lineas = [], []
        self.saldo = defaultdict(int)  # saldo deudor acumulado por cuenta

    def asiento(self, fecha: date, industria: str, tipo: str, glosa: str, movimientos: list[tuple[str, str, int]]) -> None:
        """movimientos: (cuenta, sucursal, monto con signo: + al debe, − al haber)."""
        movimientos = [(c, s, round(m)) for c, s, m in movimientos if round(m) != 0]
        if not movimientos:
            return
        descuadre = sum(m for _, _, m in movimientos)
        assert descuadre == 0, (tipo, fecha, descuadre)
        clave = f"{industria[:3].upper()}-{len(self.asientos) + 1:05d}"
        self.asientos.append({"asiento": clave, "fecha": fecha.isoformat(), "industria": industria, "tipo": tipo,
                              "glosa": glosa})
        for n, (cuenta, sucursal, monto) in enumerate(movimientos, 1):
            self.lineas.append({"asiento": clave, "linea": n, "industria": industria, "cuenta_codigo": cuenta,
                                "sucursal": sucursal, "debe": max(monto, 0), "haber": max(-monto, 0)})
            self.saldo[cuenta] += monto


def cuadrar(movimientos: list[tuple[str, str, float]], contrapartida: tuple[str, str]) -> list[tuple[str, str, int]]:
    """Redondea y lleva la diferencia a la contrapartida, para que el asiento sume cero."""
    redondos = [(c, s, round(m)) for c, s, m in movimientos]
    return redondos + [(contrapartida[0], contrapartida[1], -sum(m for _, _, m in redondos))]


def generar(seed: int = SEMILLA) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    montos = leer_montos()
    plan, codigo_de = plan_de_cuentas(montos)
    libro = Libro()
    eerr_1 = []

    for industria, perfil in PERFILES.items():
        c = {cod: f"{industria[:3].upper()}-{cod}" for cod, *_ in CUENTAS_BALANCE + CUENTAS_BAJO_EBITDA}
        real = defaultdict(list)  # (anio, mes) → filas Real del #1
        presupuesto = defaultdict(float)  # (anio, mes) → consumo presupuestado de materiales
        for r in montos:
            if r["industria"] != industria:
                continue
            clave = (int(r["anio"]), int(r["mes"]))
            if r["version"] == "Real":
                real[clave].append(r)
            elif r["grupo_cuenta"] == "Costos" and r["componente"] in INVENTARIABLES:
                presupuesto[clave] += float(r["monto"])
            codigo = codigo_de[(industria, r["cuenta"], r["componente"])]
            eerr_1.append({"version": r["version"], "fecha": f"{r['anio']}-{int(r['mes']):02d}-01", "industria": industria,
                           "sucursal": r["sucursal"], "cuenta_codigo": codigo, "monto": round(float(r["monto"]))})

        def suma(clave: tuple[int, int], grupo: str, componentes: set[str] | None = None, excluir: bool = False,
                 real: dict = real) -> float:
            return sum(float(r["monto"]) for r in real[clave] if r["grupo_cuenta"] == grupo and (
                componentes is None or ((r["componente"] in componentes) != excluir)))

        ventas = {k: suma(k, "Ingresos") for k in MESES}
        consumo = {k: suma(k, "Costos", INVENTARIABLES) for k in MESES}
        nomina = {k: suma(k, "Costos", REMUNERACIONES) + suma(k, "Gastos Operacionales", REMUNERACIONES) for k in MESES}
        servicios = {k: suma(k, "Costos", INVENTARIABLES | REMUNERACIONES, excluir=True)
                     + suma(k, "Gastos Operacionales", REMUNERACIONES, excluir=True) for k in MESES}
        venta_previa, consumo_previo = ventas[MESES[0]], consumo[MESES[0]]
        compras_previas = consumo_previo + servicios[MESES[0]]

        # --- Apertura al 1 de enero de 2025 ---------------------------------------------------------
        caja = perfil.caja_inicial_meses * venta_previa
        deudores = venta_previa * sum(f * lag for lag, f in perfil.cobranza.items())  # ventas aún sin cobrar
        inventario = consumo_previo * 12 / 365 * perfil.dias_inventario
        venta_anual = 12 * venta_previa
        activo_bruto = perfil.activo_fijo_ventas * venta_anual
        dep_acum = perfil.depreciacion_acumulada * activo_bruto
        proveedores = compras_previas * sum(f * lag for lag, f in perfil.pago_proveedores.items())
        remuneraciones = nomina[MESES[0]]
        deuda_lp = perfil.deuda_lp * (activo_bruto - dep_acum)
        impuesto_previo = 0.0
        activo = caja + deudores + inventario + activo_bruto - dep_acum
        pasivo = proveedores + remuneraciones + perfil.deuda_cp + deuda_lp + impuesto_previo
        capital = perfil.capital * (activo - pasivo)
        apertura = [(c["1101"], "", caja), (c["1102"], "", deudores), (c["1103"], "", inventario),
                    (c["1201"], "", activo_bruto), (c["1202"], "", -dep_acum), (c["2101"], "", -proveedores),
                    (c["2102"], "", -remuneraciones), (c["2103"], "", -perfil.deuda_cp), (c["2201"], "", -deuda_lp),
                    (c["3101"], "", -capital)]
        libro.asiento(date(2025, 1, 1), industria, "Apertura", "Balance de apertura al 1 de enero de 2025",
                      cuadrar(apertura, (c["3102"], "")))

        deuda_saldo = round(deuda_lp)
        amortizacion = round(deuda_lp / perfil.amortizacion_meses)
        compras_mes = {}
        impuesto_ano = defaultdict(float)
        bruto = activo_bruto
        for i, (anio, mes) in enumerate(MESES):
            k, fin = (anio, mes), fecha_fin(anio, mes)
            filas = real[k]
            # Ventas por sucursal y cuenta
            venta = [(codigo_de[(industria, r["cuenta"], r["componente"])], r["sucursal"], -float(r["monto"]))
                     for r in filas if r["grupo_cuenta"] == "Ingresos"]
            libro.asiento(fin, industria, "Venta", f"Facturación de {fin:%m-%Y}", cuadrar(venta, (c["1102"], "")))
            # Cobranza de las ventas de meses anteriores (antes de 2025, al ritmo de enero)
            cobro = sum(f * (ventas[MESES[i - lag]] if i - lag >= 0 else venta_previa)
                        for lag, f in perfil.cobranza.items())
            libro.asiento(fin, industria, "Cobranza", f"Cobranza de {fin:%m-%Y}", [(c["1101"], "", cobro), (c["1102"], "", -cobro)])
            # Compras de materiales: según presupuesto (Manufactura) o según consumo
            if perfil.compra_segun_presupuesto and anio == 2025:  # compra para un año que no llegó
                compra_mat = presupuesto[k] * perfil.compra_segun_presupuesto
            elif perfil.compra_segun_presupuesto:  # en 2026 compra menos de lo que consume: baja el inventario
                compra_mat = consumo[k] * 0.93
            else:
                compra_mat = consumo[k] * rng.uniform(0.97, 1.03)
            if compra_mat:
                libro.asiento(fin, industria, "Compra", f"Compra de materiales de {fin:%m-%Y}",
                              [(c["1103"], "", compra_mat), (c["2101"], "", -compra_mat)])
            # Consumo de materiales (costo) desde inventario
            uso = [(codigo_de[(industria, r["cuenta"], r["componente"])], r["sucursal"], float(r["monto"]))
                   for r in filas if r["grupo_cuenta"] == "Costos" and r["componente"] in INVENTARIABLES]
            if uso:
                libro.asiento(fin, industria, "Consumo", f"Consumo de materiales de {fin:%m-%Y}", cuadrar(uso, (c["1103"], "")))
            # Servicios y otros gastos contra proveedores
            serv = [(codigo_de[(industria, r["cuenta"], r["componente"])], r["sucursal"], float(r["monto"]))
                    for r in filas if r["grupo_cuenta"] != "Ingresos"
                    and r["componente"] not in INVENTARIABLES | REMUNERACIONES]
            libro.asiento(fin, industria, "Gasto", f"Servicios y gastos de {fin:%m-%Y}", cuadrar(serv, (c["2101"], "")))
            compras_mes[k] = compra_mat + sum(m for _, _, m in serv)
            # Remuneraciones devengadas y pago de las del mes anterior
            rem = [(codigo_de[(industria, r["cuenta"], r["componente"])], r["sucursal"], float(r["monto"]))
                   for r in filas if r["componente"] in REMUNERACIONES]
            libro.asiento(fin, industria, "Remuneraciones", f"Remuneraciones de {fin:%m-%Y}", cuadrar(rem, (c["2102"], "")))
            pagar = nomina[MESES[i - 1]] if i else remuneraciones
            libro.asiento(date(anio, mes, 5), industria, "Pago de remuneraciones", "Pago de remuneraciones del mes anterior",
                          [(c["2102"], "", pagar), (c["1101"], "", -pagar)])
            # Pago a proveedores
            pago = sum(f * (compras_mes[MESES[i - lag]] if i - lag >= 0 else compras_previas)
                       for lag, f in perfil.pago_proveedores.items())
            libro.asiento(fin, industria, "Pago a proveedores", f"Pago a proveedores de {fin:%m-%Y}",
                          [(c["2101"], "", pago), (c["1101"], "", -pago)])
            # Inversión y depreciación
            inversion = bruto * perfil.inversion_anual / 12 * rng.uniform(0.5, 1.5)
            libro.asiento(fin, industria, "Inversión", f"Inversión en activo fijo de {fin:%m-%Y}",
                          [(c["1201"], "", inversion), (c["1101"], "", -inversion)])
            bruto += round(inversion)
            depreciacion = bruto * perfil.tasa_depreciacion / 12
            libro.asiento(fin, industria, "Depreciación", f"Depreciación de {fin:%m-%Y}",
                          [(c["6901"], "", depreciacion), (c["1202"], "", -depreciacion)])
            # Intereses y amortización de deuda
            intereses = (deuda_saldo - libro.saldo[c["2103"]]) * perfil.tasa_interes / 12
            libro.asiento(fin, industria, "Intereses", f"Intereses de {fin:%m-%Y}",
                          [(c["6902"], "", intereses), (c["1101"], "", -intereses)])
            libro.asiento(fin, industria, "Amortización de deuda", f"Cuota de capital de {fin:%m-%Y}",
                          [(c["2201"], "", amortizacion), (c["1101"], "", -amortizacion)])
            deuda_saldo -= amortizacion
            # Impuesto devengado sobre el resultado del mes
            ebitda = ventas[k] - consumo[k] - nomina[k] - servicios[k]
            rai = ebitda - round(depreciacion) - round(intereses)
            impuesto = TASA_IMPUESTO * rai
            libro.asiento(fin, industria, "Impuesto", f"Impuesto a la renta devengado de {fin:%m-%Y}",
                          [(c["6903"], "", impuesto), (c["2104"], "", -impuesto)])
            impuesto_ano[anio] += round(impuesto)
            # Pago anual del impuesto del año anterior, en abril
            if mes == 4 and anio - 1 in impuesto_ano and impuesto_ano[anio - 1] > 0:
                libro.asiento(date(anio, 4, 30), industria, "Pago de impuesto", f"Pago del impuesto a la renta {anio - 1}",
                              [(c["2104"], "", impuesto_ano[anio - 1]), (c["1101"], "", -impuesto_ano[anio - 1])])
            # Línea de crédito de corto plazo: gira bajo la caja mínima y amortiza cuando sobra
            caja_hoy, minima = libro.saldo[c["1101"]], CAJA_MINIMA * ventas[k]
            credito = -libro.saldo[c["2103"]]
            if caja_hoy < minima:
                giro = -(-(minima - caja_hoy) // 5_000_000) * 5_000_000
                libro.asiento(fin, industria, "Crédito de corto plazo", f"Giro de la línea de crédito de {fin:%m-%Y}",
                              [(c["1101"], "", giro), (c["2103"], "", -giro)])
            elif caja_hoy > CAJA_HOLGADA * ventas[k] and credito > 0:
                abono = min(credito, (caja_hoy - CAJA_HOLGADA * ventas[k]) // 5_000_000 * 5_000_000)
                if abono:
                    libro.asiento(fin, industria, "Crédito de corto plazo", f"Abono a la línea de crédito de {fin:%m-%Y}",
                                  [(c["2103"], "", abono), (c["1101"], "", -abono)])
            # Cierre anual de resultados
            if mes == 12:
                saldos = defaultdict(int)
                for linea in libro.lineas:
                    if linea["industria"] == industria and linea["asiento"] in _del_anio(libro, industria, anio):
                        saldos[(linea["cuenta_codigo"], linea["sucursal"])] += linea["debe"] - linea["haber"]
                resultado = [(cta, suc, -m) for (cta, suc), m in saldos.items() if _es_resultado(cta) and m]
                libro.asiento(fin, industria, "Cierre", f"Cierre de resultados {anio}", cuadrar(resultado, (c["3103"], "")))
                if anio < 2026:
                    neto = -sum(m for _, _, m in resultado)  # negativo (acreedor) si hubo utilidad
                    libro.asiento(date(anio + 1, 1, 2), industria, "Traspaso", f"Traspaso del resultado {anio}",
                                  [(c["3103"], "", -neto), (c["3102"], "", neto)])

    return {
        "empresas": [{"industria": i, "empresa": p.empresa, "orden": n} for n, (i, p) in enumerate(PERFILES.items(), 1)],
        "plan_cuentas": plan, "asientos": libro.asientos, "lineas_asiento": libro.lineas,
        "eerr_reporte1": sorted(eerr_1, key=lambda r: (r["version"], r["industria"], r["fecha"], r["sucursal"], r["cuenta_codigo"])),
    }



def _del_anio(libro: Libro, industria: str, anio: int) -> set[str]:
    """Asientos de la empresa fechados en el año, sin apertura ni cierres (para calcular el cierre)."""
    return {a["asiento"] for a in libro.asientos if a["industria"] == industria and a["fecha"].startswith(str(anio))
            and a["tipo"] not in ("Apertura", "Cierre", "Traspaso")}


def _es_resultado(cuenta: str) -> bool:
    numero = cuenta.split("-")[1]
    return numero[0] in "456"


def escribir(tablas: dict[str, list[dict]], carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, campos in ARCHIVOS.items():
        with (carpeta / f"{nombre}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
            w.writeheader()
            w.writerows(tablas[nombre])


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el libro diario y los datos de los EEFF.")
    parser.add_argument("--seed", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=DATA / "estados-financieros")
    args = parser.parse_args()
    tablas = generar(args.seed)
    escribir(tablas, args.salida)
    for nombre, filas in tablas.items():
        print(f"{nombre:16} {len(filas):7d} filas")


if __name__ == "__main__":
    main()
