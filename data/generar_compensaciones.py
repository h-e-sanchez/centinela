"""Genera data/compensaciones/: bandas salariales y remuneraciones de las personas del reporte Workforce.

Son las mismas personas de data/workforce/personas.csv (mismos IDs, sede, servicio, estamento,
sexo, ingreso y egreso), así que un mismo ID se puede seguir en dotación, ausentismo y renta.
Simulamos 2025 y 2026, mes a mes:

- **Grados y bandas:** siete grados por empresa (directivos; profesionales y técnicos senior o no
  según antigüedad; administrativos; operarios o auxiliares). Cada grado tiene una banda con
  mínimo (80% del punto medio), punto medio y máximo (120%). Las bandas suben 4,5% en 2026.
- **Encuesta de mercado:** cada banda trae el P25, P50 y P75 de una encuesta sintética del sector.
- **Sueldo base:** punto medio × compa-ratio individual. El compa-ratio crece con la antigüedad,
  tiene ruido y recoge tres prácticas que el reporte debe destapar: la UCI paga sobre la banda
  para retener técnicos (y ambulatorio bajo el punto medio), Energía contrata en Zona Norte desde
  mediados de 2024 bajo el mínimo de la banda, y las mujeres ganan menos que los hombres del mismo grado
  (más en Manufactura).
- **Variable:** bono mensual como porcentaje del sueldo base, según el estamento.

Montos en CLP brutos mensuales. Las jornadas parciales (22 horas) cobran en proporción; el
compa-ratio se mide sobre el equivalente a 44 horas. Reproducible (semilla fija). Ningún
dato real de ningún empleador.

Uso:
    python data/generar_compensaciones.py
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date
from pathlib import Path

SEMILLA = 42
ANIOS = (2025, 2026)
JORNADA_COMPLETA = 44
REAJUSTE_2026 = 0.045  # IPC aplicado a las bandas y a los sueldos en enero de 2026
ANCHO_BANDA = 0.20  # mínimo y máximo a ±20% del punto medio
MERCADO = (0.92, 1.03, 1.15)  # P25, P50 y P75 de la encuesta, sobre el punto medio propio
DATA = Path(__file__).resolve().parent

# grado: (nombre, punto medio 2025 en CLP para Manufactura, % variable)
GRADOS = {
    1: ("Directivos", 4_600_000, 0.15),
    2: ("Profesionales senior", 2_700_000, 0.08),
    3: ("Profesionales", 1_950_000, 0.06),
    4: ("Técnicos senior", 1_350_000, 0.04),
    5: ("Técnicos", 1_080_000, 0.03),
    6: ("Administrativos", 980_000, 0.03),
    7: ("Operarios y auxiliares", 780_000, 0.02),
}
FACTOR_INDUSTRIA = {"Manufactura": 1.00, "Energia": 1.15, "Salud": 0.95}
ANTIGUEDAD_SENIOR = 6  # años al 1 de enero de 2025 para pasar al grado senior
# Prácticas sembradas -----------------------------------------------------------------------
EFECTO_SERVICIO = {("Salud", "UCI"): 0.12, ("Salud", "Ambulatorio"): -0.07}
BRECHA_GENERO = {"Manufactura": 0.035, "Energia": 0.015, "Salud": 0.015}  # menos para mujeres, mismo grado
INGRESOS_BAJO_MINIMO = ("Energia", "Zona Norte", date(2024, 7, 1), 0.72)  # contratados desde esa fecha
RUIDO = 0.06
AREA = {"Urgencia": "Clínica", "Hospitalización": "Clínica", "Pabellón": "Clínica", "UCI": "Clínica",
        "Ambulatorio": "Clínica", "Apoyo": "Soporte",
        "Operación de centrales": "Operación", "Mantenimiento": "Operación", "Transmisión": "Operación",
        "Centro de despacho": "Operación", "Comercial": "Soporte", "Gestión corporativa": "Soporte",
        "Producción": "Operación", "Mantenimiento industrial": "Operación", "Calidad": "Operación",
        "Bodega y logística": "Operación", "Ventas": "Soporte", "Administración y finanzas": "Soporte"}

ARCHIVOS = {
    "empresas": ["industria", "empresa", "orden"],
    "servicios": ["servicio", "industria", "area", "orden"],
    "grados": ["grado", "nombre", "pct_variable"],
    "bandas": ["banda", "industria", "grado", "anio", "minimo", "punto_medio", "maximo", "mercado_p25",
               "mercado_p50", "mercado_p75"],
    "cargos": ["cargo", "industria", "servicio", "grado", "estamento"],
    "personas": ["id_persona", "industria", "sede", "servicio", "estamento", "sexo", "fecha_nacimiento",
                 "fecha_ingreso", "fecha_egreso", "jornada_horas", "cargo", "grado"],
    "remuneraciones": ["id_persona", "fecha", "anio", "industria", "servicio", "grado", "banda", "jornada_horas",
                       "sueldo_base", "sueldo_base_44h", "variable"],
}


def meses() -> list[date]:
    return [date(a, m, 1) for a in ANIOS for m in range(1, 13)]


def fin_de_mes(d: date) -> date:
    siguiente = date(d.year + d.month // 12, d.month % 12 + 1, 1)
    return date.fromordinal(siguiente.toordinal() - 1)


def leer_workforce() -> tuple[list[dict], list[dict], list[dict]]:
    def leer(nombre: str) -> list[dict]:
        with (DATA / "workforce" / f"{nombre}.csv").open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return leer("personas"), leer("sedes"), leer("unidades")


def grado_de(p: dict) -> int:
    antiguedad = (date(2025, 1, 1) - date.fromisoformat(p["fecha_ingreso"])).days / 365.25
    senior = antiguedad >= ANTIGUEDAD_SENIOR
    return {"Directivos": 1, "Profesionales": 2 if senior else 3, "Técnicos": 4 if senior else 5,
            "Administrativos": 6, "Operarios": 7, "Auxiliares": 7}[p["estamento"]]


def bandas() -> list[dict]:
    filas = []
    for industria, factor in FACTOR_INDUSTRIA.items():
        for grado, (_, medio, _) in GRADOS.items():
            for anio in ANIOS:
                pm = round(medio * factor * (1 + REAJUSTE_2026) ** (anio - 2025), -3)
                filas.append({"banda": f"{industria[:3].upper()}-G{grado}-{anio}", "industria": industria,
                              "grado": grado, "anio": anio, "minimo": int(round(pm * (1 - ANCHO_BANDA), -3)),
                              "punto_medio": int(pm), "maximo": int(round(pm * (1 + ANCHO_BANDA), -3)),
                              **{f"mercado_{n}": int(round(pm * k, -3)) for n, k in zip(("p25", "p50", "p75"), MERCADO)}})
    return filas


def compa_individual(rng: random.Random, p: dict) -> float:
    """Compa-ratio de la persona al ingresar: antigüedad, servicio, sexo, contratación y ruido."""
    ingreso = date.fromisoformat(p["fecha_ingreso"])
    antiguedad = max(0.0, (date(2025, 1, 1) - ingreso).days / 365.25)
    compa = 0.94 + min(antiguedad, 12) * 0.008 + rng.gauss(0, RUIDO)
    compa += EFECTO_SERVICIO.get((p["industria"], p["unidad"]), 0.0)
    if p["sexo"] == "F":
        compa -= BRECHA_GENERO[p["industria"]]
    industria, sede, desde, nivel = INGRESOS_BAJO_MINIMO
    if p["industria"] == industria and p["sede"] == sede and ingreso >= desde:
        compa = nivel + rng.gauss(0, 0.03)  # entraron bajo el mínimo de la banda
    return max(0.62, min(1.45, compa))


def generar(seed: int = SEMILLA) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    personas_wf, sedes, unidades = leer_workforce()
    empresas = {s["industria"]: s["empresa"] for s in sedes}
    tabla_bandas = bandas()
    banda = {(b["industria"], b["grado"], b["anio"]): b for b in tabla_bandas}

    cargos, personas, remuneraciones = {}, [], []
    for p in personas_wf:
        grado = grado_de(p)
        clave_cargo = f"{p['industria'][:3].upper()}-{p['unidad']}-G{grado}"
        cargos.setdefault(clave_cargo, {"cargo": clave_cargo, "industria": p["industria"], "servicio": p["unidad"],
                                        "grado": grado, "estamento": p["estamento"]})
        personas.append({"id_persona": p["id_persona"], "industria": p["industria"], "sede": p["sede"],
                         "servicio": p["unidad"], "estamento": p["estamento"], "sexo": p["sexo"],
                         "fecha_nacimiento": p["fecha_nacimiento"], "fecha_ingreso": p["fecha_ingreso"],
                         "fecha_egreso": p["fecha_egreso"], "jornada_horas": p["jornada_horas"],
                         "cargo": clave_cargo, "grado": grado})
        compa = compa_individual(rng, p)
        merito_2026 = rng.gauss(0.01, 0.01)  # sobre el reajuste por IPC
        variable = GRADOS[grado][2]
        ingreso, egreso = date.fromisoformat(p["fecha_ingreso"]), p["fecha_egreso"]
        for mes in meses():
            if ingreso > fin_de_mes(mes) or (egreso and date.fromisoformat(egreso) < mes):
                continue
            b = banda[(p["industria"], grado, mes.year)]
            factor = compa * (1 + merito_2026 if mes.year == 2026 else 1)
            base_44 = round(b["punto_medio"] * factor, -3)
            jornada = int(p["jornada_horas"])
            base = round(base_44 * jornada / JORNADA_COMPLETA, -3)
            bono = round(base * max(0.0, rng.gauss(variable, variable * 0.4)), -3)
            remuneraciones.append({"id_persona": p["id_persona"], "fecha": mes.isoformat(), "anio": mes.year,
                                   "industria": p["industria"], "servicio": p["unidad"], "grado": grado,
                                   "banda": b["banda"], "jornada_horas": jornada, "sueldo_base": int(base),
                                   "sueldo_base_44h": int(base_44), "variable": int(bono)})

    orden_servicio = {(u["industria"], u["unidad"]): int(u["orden"]) for u in unidades}
    servicios = [{"servicio": u, "industria": i, "area": AREA[u], "orden": orden_servicio[(i, u)]}
                 for (i, u) in sorted(orden_servicio, key=lambda k: (list(FACTOR_INDUSTRIA).index(k[0]),
                                                                     orden_servicio[k]))]
    return {
        "empresas": [{"industria": i, "empresa": empresas[i], "orden": n} for n, i in enumerate(FACTOR_INDUSTRIA, 1)],
        "servicios": servicios,
        "grados": [{"grado": g, "nombre": v[0], "pct_variable": v[2]} for g, v in GRADOS.items()],
        "bandas": tabla_bandas,
        "cargos": sorted(cargos.values(), key=lambda c: c["cargo"]),
        "personas": personas,
        "remuneraciones": remuneraciones,
    }


def escribir(tablas: dict[str, list[dict]], carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, campos in ARCHIVOS.items():
        with (carpeta / f"{nombre}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
            w.writeheader()
            w.writerows(tablas[nombre])


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los datos sintéticos del reporte de compensaciones.")
    parser.add_argument("--seed", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=DATA / "compensaciones")
    args = parser.parse_args()
    tablas = generar(args.seed)
    escribir(tablas, args.salida)
    for nombre, filas in tablas.items():
        print(f"{nombre:16} {len(filas):7d} filas")


if __name__ == "__main__":
    main()
