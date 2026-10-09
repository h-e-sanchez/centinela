"""Genera data/gestion-operacional/: la operación clínica de la empresa de Salud de la vitrina.

Es la empresa de Salud de los otros reportes, «Red Asistencial Ejemplo S.A.», con sus tres
clínicas: Oriente, Centro y Poniente. El reporte mira la operación de enero de 2025 a septiembre de
2026, los meses con Real en el reporte #1:

- **Hospitalizado:** días cama disponibles y ocupados, egresos y días de estada por servicio
  (UCI, UTI, médico-quirúrgico, pediatría y maternidad), con la estada esperada según la norma
  (GRD simplificado) y los reingresos a 30 días.
- **Pabellones:** horas habilitadas, programadas y utilizadas por especialidad, cirugías
  programadas, realizadas y suspendidas (con su causa) y la primera cirugía del día a la hora.
- **Urgencia:** atenciones por categoría de triage (C1 a C5), espera hasta la atención médica
  frente a la meta, abandonos, hospitalizaciones y horas de espera de cama.
- **Ambulatorio:** horas de box, agenda, consultas, inasistencias, lista de espera y días al
  tercer cupo por especialidad.
- **Apoyo:** exámenes de laboratorio e imagenología por origen y su tiempo de respuesta (TAT).
- **Producción:** prestaciones, ingresos por previsión y costos directos por línea, para el margen
  de contribución.

Las prestaciones de producción salen de la misma operación: los días cama son los ocupados, las
cirugías son las realizadas, etc. Los volúmenes son los de una red de tres clínicas de tamaño
real y **no cuadran con el reporte #1**: allí la empresa de Salud está a escala de ejemplo.

Tres historias quedan sembradas: en invierno la ocupación de pediatría y médico-quirúrgico supera
el 90%, y con las camas llenas sube la espera de cama en urgencia y la suspensión de cirugías; la
Clínica Poniente suspende el 15% de sus cirugías (más de 9 de cada 10 por causas evitables) y
solo 45% de las primeras cirugías del día parte a la hora; y la estada de médico-quirúrgico en la Clínica Centro está un 25% sobre la
norma, lo que inmoviliza camas que el invierno necesita.

Reproducible (semilla fija). Montos en CLP. Ningún dato real de ningún empleador.

Uso:
    python data/generar_gestion_operacional.py
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from datetime import date
from pathlib import Path

SEMILLA = 42
DATA = Path(__file__).resolve().parent
MESES = [(a, m) for a in (2025, 2026) for m in range(1, 13) if (a, m) <= (2026, 9)]
INVIERNO = {6: 0.7, 7: 1.0, 8: 0.8, 5: 0.3, 9: 0.2}  # intensidad de la campaña de invierno por mes
EMPRESA = "Red Asistencial Ejemplo S.A."
CLINICAS = ["Clínica Oriente", "Clínica Centro", "Clínica Poniente"]

# --- Hospitalizado ----------------------------------------------------------------------------------
SERVICIOS = ["UCI", "UTI", "Médico-quirúrgico", "Pediatría", "Maternidad"]
CAMAS = {
    "Clínica Oriente": {"UCI": 16, "UTI": 20, "Médico-quirúrgico": 90, "Pediatría": 24, "Maternidad": 20},
    "Clínica Centro": {"UCI": 12, "UTI": 16, "Médico-quirúrgico": 70, "Pediatría": 18, "Maternidad": 16},
    "Clínica Poniente": {"UCI": 8, "UTI": 10, "Médico-quirúrgico": 50, "Pediatría": 14, "Maternidad": 12},
}
OCUPACION_BASE = {"UCI": 0.84, "UTI": 0.79, "Médico-quirúrgico": 0.78, "Pediatría": 0.58, "Maternidad": 0.66}
ALZA_INVIERNO = {"UCI": 0.11, "UTI": 0.12, "Médico-quirúrgico": 0.15, "Pediatría": 0.38, "Maternidad": 0.0}
ESTADA_NORMA = {"UCI": 5.6, "UTI": 4.4, "Médico-quirúrgico": 4.1, "Pediatría": 3.1, "Maternidad": 2.6}
ESTADA_SOBRE_NORMA = {("Clínica Centro", "Médico-quirúrgico"): 0.25}  # historia: estada prolongada
REINGRESO = {"UCI": 0.07, "UTI": 0.06, "Médico-quirúrgico": 0.05, "Pediatría": 0.03, "Maternidad": 0.015}

# --- Pabellones -------------------------------------------------------------------------------------
PABELLONES = {"Clínica Oriente": 8, "Clínica Centro": 6, "Clínica Poniente": 4}
HORAS_POR_DIA = 12
ESPECIALIDADES_QX = {  # participación en las horas de bloque y duración promedio (h, con recambio)
    "Cirugía general": (0.30, 2.1), "Traumatología": (0.25, 2.6), "Ginecología": (0.17, 1.9),
    "Urología": (0.15, 1.8), "Otorrinolaringología": (0.13, 1.5)}
UTILIZACION = {"Clínica Oriente": 0.81, "Clínica Centro": 0.77, "Clínica Poniente": 0.66}
SUSPENSION = {"Clínica Oriente": 0.055, "Clínica Centro": 0.075, "Clínica Poniente": 0.14}
A_LA_HORA = {"Clínica Oriente": 0.83, "Clínica Centro": 0.76, "Clínica Poniente": 0.47}
CAUSAS = {  # causa: (evitable, peso base, peso Poniente)
    "Paciente no preparado o sin exámenes": (1, 0.18, 0.34),
    "Atraso de la cirugía anterior": (1, 0.16, 0.24),
    "Falta de cama crítica o de sala": (1, 0.14, 0.10),
    "Falta de insumo o equipo": (1, 0.08, 0.07),
    "Administrativa (previsión o presupuesto)": (1, 0.12, 0.10),
    "Inasistencia del paciente": (1, 0.10, 0.07),
    "Causa médica del paciente": (0, 0.22, 0.08),
}

# --- Urgencia ---------------------------------------------------------------------------------------
ATENCIONES_URGENCIA = {"Clínica Oriente": 6_400, "Clínica Centro": 5_100, "Clínica Poniente": 4_300}
CATEGORIAS = {  # mezcla, meta de espera (min), espera media base (min), hospitalización, abandono base
    "C1": (0.01, 5, 2, 0.72, 0.0), "C2": (0.07, 30, 14, 0.42, 0.002), "C3": (0.30, 90, 42, 0.16, 0.012),
    "C4": (0.42, 180, 85, 0.035, 0.022), "C5": (0.20, 240, 105, 0.006, 0.035)}

# --- Ambulatorio ------------------------------------------------------------------------------------
ESPECIALIDADES_AMB = {  # boxes por clínica (Oriente, Centro, Poniente), minutos por consulta, no-show base
    "Medicina general": ((6, 5, 6), 15, 0.09), "Pediatría": ((4, 3, 3), 15, 0.08),
    "Traumatología": ((4, 3, 2), 20, 0.10), "Ginecología": ((3, 3, 2), 20, 0.09),
    "Oftalmología": ((2, 2, 1), 20, 0.11), "Dermatología": ((2, 2, 1), 20, 0.21),
    "Cardiología": ((2, 2, 1), 30, 0.08)}
HORAS_BOX_DIA = 11

# --- Apoyo ------------------------------------------------------------------------------------------
UNIDADES_APOYO = {  # (exámenes por atención de urgencia, por día cama, por consulta), meta TAT por origen (min)
    "Laboratorio": ((1.6, 1.1, 0.45), {"Urgencia": 60, "Hospitalizado": 240, "Ambulatorio": 1440}),
    "Imagenología": ((0.42, 0.14, 0.11), {"Urgencia": 120, "Hospitalizado": 480, "Ambulatorio": 2880})}
TAT_BASE = {"Laboratorio": {"Urgencia": 38, "Hospitalizado": 150, "Ambulatorio": 900},
            "Imagenología": {"Urgencia": 70, "Hospitalizado": 300, "Ambulatorio": 1900}}

# --- Producción y costos ----------------------------------------------------------------------------
LINEAS = [  # línea, área, unidad de la prestación
    ("UCI", "Hospitalizado", "día cama"), ("UTI", "Hospitalizado", "día cama"),
    ("Médico-quirúrgico", "Hospitalizado", "día cama"), ("Pediatría", "Hospitalizado", "día cama"),
    ("Maternidad", "Hospitalizado", "día cama"), ("Pabellón", "Pabellones", "cirugía"),
    ("Urgencia", "Urgencia", "atención"), ("Consultas", "Ambulatorio", "consulta"),
    ("Laboratorio", "Apoyo", "examen"), ("Imagenología", "Apoyo", "examen")]
ARANCEL_ISAPRE = {"UCI": 1_350_000, "UTI": 820_000, "Médico-quirúrgico": 365_000, "Pediatría": 340_000,
                  "Maternidad": 330_000, "Consultas": 42_000, "Laboratorio": 9_500, "Imagenología": 62_000}
ARANCEL_CIRUGIA = {"Cirugía general": 2_000_000, "Traumatología": 2_800_000, "Ginecología": 1_750_000,
                   "Urología": 1_650_000, "Otorrinolaringología": 1_300_000}
ARANCEL_URGENCIA = {"C1": 520_000, "C2": 240_000, "C3": 115_000, "C4": 62_000, "C5": 38_000}
FACTOR_PREVISION = {"Isapres": 1.0, "Fonasa": 0.58, "Convenios con empresas": 0.86, "Particulares": 1.12}
MEZCLA_PREVISION = {
    "Clínica Oriente": {"Isapres": 0.60, "Fonasa": 0.20, "Convenios con empresas": 0.12, "Particulares": 0.08},
    "Clínica Centro": {"Isapres": 0.46, "Fonasa": 0.35, "Convenios con empresas": 0.12, "Particulares": 0.07},
    "Clínica Poniente": {"Isapres": 0.30, "Fonasa": 0.55, "Convenios con empresas": 0.10, "Particulares": 0.05}}
# Personal: costo mensual fijo (por cama, por pabellón, por box o por clínica); insumos: por prestación;
# honorarios: % del ingreso.
PERSONAL_POR_CAMA = {"UCI": 12_000_000, "UTI": 7_400_000, "Médico-quirúrgico": 3_500_000,
                     "Pediatría": 4_300_000, "Maternidad": 3_800_000}
INSUMOS = {"UCI": 310_000, "UTI": 150_000, "Médico-quirúrgico": 72_000, "Pediatría": 64_000, "Maternidad": 60_000,
           "Pabellón": 420_000, "Urgencia": 14_000, "Consultas": 2_500, "Laboratorio": 3_100, "Imagenología": 14_500}
HONORARIOS = {"UCI": 0.10, "UTI": 0.10, "Médico-quirúrgico": 0.12, "Pediatría": 0.12, "Maternidad": 0.18,
              "Pabellón": 0.22, "Urgencia": 0.30, "Consultas": 0.58, "Laboratorio": 0.05, "Imagenología": 0.14}
PERSONAL_POR_PABELLON = 24_000_000
PERSONAL_URGENCIA = {"Clínica Oriente": 255_000_000, "Clínica Centro": 210_000_000, "Clínica Poniente": 185_000_000}
PERSONAL_POR_BOX = 2_600_000
PERSONAL_APOYO = {"Laboratorio": 0.30, "Imagenología": 0.32}  # sobre el ingreso de 2025 (dotación fija)

ARCHIVOS = {
    "sucursales": ["sucursal", "empresa", "orden"],
    "lineas": ["linea", "area", "unidad", "orden"],
    "metas": ["indicador", "area", "meta", "sentido", "formato", "orden"],
    "camas": ["fecha", "anio", "mes", "sucursal", "linea", "camas_dotadas", "dias_cama_disponibles",
              "dias_cama_ocupados", "egresos", "dias_estada", "dias_estada_esperados", "reingresos_30d"],
    "pabellones": ["fecha", "anio", "mes", "sucursal", "especialidad", "horas_habilitadas", "horas_programadas",
                   "horas_utilizadas", "cirugias_programadas", "cirugias_realizadas", "cirugias_suspendidas",
                   "primeras_del_dia", "primeras_a_la_hora"],
    "suspensiones": ["fecha", "anio", "mes", "sucursal", "causa", "evitable", "suspendidas"],
    "urgencia": ["fecha", "anio", "mes", "sucursal", "categoria", "meta_minutos", "atenciones", "atenciones_en_meta",
                 "minutos_espera", "abandonos", "hospitalizados", "horas_espera_cama"],
    "ambulatorio": ["fecha", "anio", "mes", "sucursal", "especialidad", "horas_box", "horas_ofertadas",
                    "horas_agendadas", "consultas_agendadas", "consultas_realizadas", "inasistencias",
                    "lista_espera", "dias_tercer_cupo"],
    "apoyo": ["fecha", "anio", "mes", "sucursal", "unidad", "origen", "meta_minutos", "examenes",
              "examenes_en_meta", "minutos_respuesta"],
    "produccion": ["fecha", "anio", "mes", "sucursal", "linea", "prevision", "prestaciones", "ingreso",
                   "costo_personal", "costo_insumos", "costo_honorarios"],
}

METAS = [  # indicador, área, meta, sentido, formato
    ("Ocupación de camas", "Hospitalizado", 0.85, "menor", "pct"),
    ("Índice de estada (IEMA)", "Hospitalizado", 1.0, "menor", "num"),
    ("Reingresos a 30 días", "Hospitalizado", 0.05, "menor", "pct"),
    ("Utilización de pabellón", "Pabellones", 0.80, "mayor", "pct"),
    ("Suspensión de cirugías", "Pabellones", 0.07, "menor", "pct"),
    ("Primera cirugía a la hora", "Pabellones", 0.80, "mayor", "pct"),
    ("Atenciones de urgencia en meta", "Urgencia", 0.85, "mayor", "pct"),
    ("Abandono de urgencia", "Urgencia", 0.03, "menor", "pct"),
    ("Espera de cama desde urgencia", "Urgencia", 4.0, "menor", "horas"),
    ("Inasistencia ambulatoria", "Ambulatorio", 0.10, "menor", "pct"),
    ("Utilización de box", "Ambulatorio", 0.75, "mayor", "pct"),
    ("Exámenes de urgencia en meta", "Apoyo", 0.90, "mayor", "pct"),
    ("Margen de contribución", "Resultado", 0.15, "mayor", "pct"),
]


def dias_del_mes(a: int, m: int) -> int:
    return ((date(a + (m == 12), m % 12 + 1, 1)) - date(a, m, 1)).days


def dias_habiles(a: int, m: int) -> int:
    return sum(1 for d in range(1, dias_del_mes(a, m) + 1) if date(a, m, d).weekday() < 5)


def invierno(m: int) -> float:
    return INVIERNO.get(m, 0.0)


def ruido(rng: random.Random, sd: float = 0.03) -> float:
    return 1 + rng.gauss(0, sd)


def binomial(rng: random.Random, n: int, p: float) -> int:
    """Aproximación normal (n grande), acotada a [0, n]."""
    p = min(max(p, 0.0), 1.0)
    return max(0, min(n, round(n * p + rng.gauss(0, math.sqrt(max(n * p * (1 - p), 0.0))))))


def generar(seed: int = SEMILLA) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    t: dict[str, list[dict]] = {k: [] for k in ARCHIVOS}
    t["sucursales"] = [{"sucursal": s, "empresa": EMPRESA, "orden": i} for i, s in enumerate(CLINICAS, 1)]
    t["lineas"] = [{"linea": n, "area": a, "unidad": u, "orden": i} for i, (n, a, u) in enumerate(LINEAS, 1)]
    t["metas"] = [{"indicador": n, "area": a, "meta": v, "sentido": s, "formato": f, "orden": i}
                  for i, (n, a, v, s, f) in enumerate(METAS, 1)]
    ingreso_apoyo_2025: dict[tuple[str, str], float] = {}

    for a, m in MESES:
        fecha, base = date(a, m, 1).isoformat(), {"anio": a, "mes": m}
        dm, dh, inv = dias_del_mes(a, m), dias_habiles(a, m), invierno(m)
        crecimiento = 1.0 + (0.03 if a == 2026 else 0.0)
        for s in CLINICAS:
            fila = {"fecha": fecha, **base, "sucursal": s}
            prestaciones: dict[str, dict[str, float]] = {}  # línea → {clave: cantidad} para producción

            # Hospitalizado
            ocupacion_mq = 0.0
            for sv in SERVICIOS:
                camas = CAMAS[s][sv] + (round(CAMAS[s][sv] * 0.12) if sv == "Pediatría" and inv >= 0.7 else 0)
                disponibles = camas * dm
                bloqueo = 0.04 if (s, sv) in ESTADA_SOBRE_NORMA else 0.0  # la estada prolongada inmoviliza camas
                ocup = min(0.985, (OCUPACION_BASE[sv] + bloqueo + ALZA_INVIERNO[sv] * inv) * ruido(rng, 0.025) * crecimiento ** 0.3)
                ocupados = round(disponibles * ocup)
                if sv == "Médico-quirúrgico":
                    ocupacion_mq = ocupados / disponibles
                norma = ESTADA_NORMA[sv]
                estada = norma * (1 + ESTADA_SOBRE_NORMA.get((s, sv), rng.uniform(0.0, 0.06)) + 0.05 * inv) * ruido(rng, 0.02)
                egresos = max(1, round(ocupados / estada))
                t["camas"].append({**fila, "linea": sv, "camas_dotadas": camas, "dias_cama_disponibles": disponibles,
                                   "dias_cama_ocupados": ocupados, "egresos": egresos, "dias_estada": ocupados,
                                   "dias_estada_esperados": round(egresos * norma),
                                   "reingresos_30d": binomial(rng, egresos, REINGRESO[sv] * (1.25 if (s, sv) in ESTADA_SOBRE_NORMA else 1))})
                prestaciones[sv] = {"total": ocupados}

            # Pabellones
            habilitadas_total = PABELLONES[s] * HORAS_POR_DIA * dh
            susp_total = 0
            qx: dict[str, float] = {}
            for esp, (part, dur) in ESPECIALIDADES_QX.items():
                habilitadas = round(habilitadas_total * part)
                tasa_susp = SUSPENSION[s] + 0.035 * inv * (1.4 if ocupacion_mq > 0.9 else 1)
                programadas_h = habilitadas * min(0.97, (UTILIZACION[s] + 0.02) / (1 - tasa_susp) * ruido(rng, 0.02))
                cirugias_prog = round(programadas_h / dur)
                suspendidas = binomial(rng, cirugias_prog, tasa_susp)
                realizadas = cirugias_prog - suspendidas
                utilizadas = min(habilitadas, round(realizadas * dur * ruido(rng, 0.03)))
                primeras = round(PABELLONES[s] * part * dh)
                t["pabellones"].append({**fila, "especialidad": esp, "horas_habilitadas": habilitadas,
                                        "horas_programadas": round(programadas_h), "horas_utilizadas": utilizadas,
                                        "cirugias_programadas": cirugias_prog, "cirugias_realizadas": realizadas,
                                        "cirugias_suspendidas": suspendidas, "primeras_del_dia": primeras,
                                        "primeras_a_la_hora": binomial(rng, primeras, A_LA_HORA[s] - 0.05 * inv)})
                susp_total += suspendidas
                qx[esp] = realizadas
            prestaciones["Pabellón"] = qx

            # Causas de suspensión: la falta de cama crece con la ocupación de médico-quirúrgico
            pesos = {}
            for causa, (_ev, p_base, p_pon) in CAUSAS.items():
                w = p_pon if s == "Clínica Poniente" else p_base
                if causa.startswith("Falta de cama"):
                    w *= 1 + 6 * max(0.0, ocupacion_mq - 0.85)
                pesos[causa] = w * ruido(rng, 0.15)
            total_w, restantes = sum(pesos.values()), susp_total
            causas = list(CAUSAS)
            for i, causa in enumerate(causas):
                n = restantes if i == len(causas) - 1 else min(restantes, round(susp_total * pesos[causa] / total_w))
                restantes -= n
                t["suspensiones"].append({**fila, "causa": causa, "evitable": CAUSAS[causa][0], "suspendidas": n})

            # Urgencia: el invierno trae demanda y, con las camas llenas, espera de cama
            total_urg = ATENCIONES_URGENCIA[s] * (1 + 0.38 * inv) * dm / 30 * crecimiento * ruido(rng, 0.03)
            espera_cama = 2.2 + 38 * max(0.0, ocupacion_mq - 0.84)
            urg: dict[str, float] = {}
            for cat, (mezcla, meta, espera, hosp, aband) in CATEGORIAS.items():
                n = round(total_urg * mezcla * ruido(rng, 0.04))
                media = espera * (1 + 0.9 * inv) * (1.15 if s == "Clínica Poniente" else 1) * ruido(rng, 0.05)
                en_meta = binomial(rng, n, 1 - math.exp(-meta / media))
                hospitalizados = binomial(rng, n, hosp)
                t["urgencia"].append({**fila, "categoria": cat, "meta_minutos": meta, "atenciones": n,
                                      "atenciones_en_meta": en_meta, "minutos_espera": round(n * media),
                                      "abandonos": binomial(rng, n, aband * (1 + 1.2 * inv) * (1.45 if s == "Clínica Poniente" else 1)),
                                      "hospitalizados": hospitalizados,
                                      "horas_espera_cama": round(hospitalizados * espera_cama * ruido(rng, 0.08), 1)})
                urg[cat] = n
            prestaciones["Urgencia"] = urg

            # Ambulatorio
            k = CLINICAS.index(s)
            consultas_total = 0
            boxes_total = 0
            for esp, (boxes, minutos, noshow) in ESPECIALIDADES_AMB.items():
                horas_box = boxes[k] * HORAS_BOX_DIA * dh
                boxes_total += boxes[k]
                ofertadas = round(horas_box * 0.74 * ruido(rng, 0.03) * (0.85 if m == 2 else 1))
                ocup_agenda = 0.93 if esp in ("Oftalmología", "Dermatología") else 0.88
                agendadas = round(ofertadas * 60 / minutos * ocup_agenda * ruido(rng, 0.02))
                p_ns = noshow + (0.03 if m in (1, 2) else 0) + (0.02 * inv if esp == "Pediatría" else 0)
                inasistencias = binomial(rng, agendadas, p_ns)
                indice = MESES.index((a, m))
                if esp == "Oftalmología":
                    lista, cupo = round((420 + 28 * indice) * (1.2 - 0.2 * k)), round(38 + 1.3 * indice + rng.uniform(-2, 2))
                else:
                    lista, cupo = round(agendadas * rng.uniform(0.25, 0.4)), round(rng.uniform(6, 15) + 6 * inv * (esp == "Pediatría"))
                t["ambulatorio"].append({**fila, "especialidad": esp, "horas_box": horas_box, "horas_ofertadas": ofertadas,
                                         "horas_agendadas": round(agendadas * minutos / 60),
                                         "consultas_agendadas": agendadas, "consultas_realizadas": agendadas - inasistencias,
                                         "inasistencias": inasistencias, "lista_espera": lista, "dias_tercer_cupo": cupo})
                consultas_total += agendadas - inasistencias
            prestaciones["Consultas"] = {"total": consultas_total}

            # Apoyo: el volumen sale de la operación; imagenología de urgencia en la Clínica Centro se satura en invierno
            volumen_origen = {"Urgencia": total_urg, "Hospitalizado": sum(prestaciones[sv]["total"] for sv in SERVICIOS),
                              "Ambulatorio": consultas_total}
            for unidad, (tasas, metas) in UNIDADES_APOYO.items():
                total_unidad = 0
                for j, origen in enumerate(("Urgencia", "Hospitalizado", "Ambulatorio")):
                    n = round(volumen_origen[origen] * tasas[j] * ruido(rng, 0.03))
                    media = TAT_BASE[unidad][origen] * (1 + 0.25 * inv) * ruido(rng, 0.04)
                    if unidad == "Imagenología" and origen == "Urgencia" and s == "Clínica Centro":
                        media *= 1 + 1.1 * inv
                    t["apoyo"].append({**fila, "unidad": unidad, "origen": origen, "meta_minutos": metas[origen],
                                       "examenes": n, "examenes_en_meta": binomial(rng, n, 1 - math.exp(-metas[origen] / media * 1.6)),
                                       "minutos_respuesta": round(n * media)})
                    total_unidad += n
                prestaciones[unidad] = {"total": total_unidad}

            # Producción: ingresos por previsión y costos directos por línea
            for linea, area, _u in LINEAS:
                cant = prestaciones[linea]
                if linea == "Pabellón":
                    unidades, ingreso_lista = sum(cant.values()), sum(n * ARANCEL_CIRUGIA[e] for e, n in cant.items())
                elif linea == "Urgencia":
                    unidades, ingreso_lista = sum(cant.values()), sum(n * ARANCEL_URGENCIA[c] for c, n in cant.items())
                else:
                    unidades, ingreso_lista = cant["total"], cant["total"] * ARANCEL_ISAPRE[linea]
                if linea in SERVICIOS:
                    personal = PERSONAL_POR_CAMA[linea] * CAMAS[s][linea]
                elif linea == "Pabellón":
                    personal = PERSONAL_POR_PABELLON * PABELLONES[s]
                elif linea == "Urgencia":
                    personal = PERSONAL_URGENCIA[s]
                elif linea == "Consultas":
                    personal = PERSONAL_POR_BOX * boxes_total
                else:
                    clave = (s, linea)
                    if a == 2025 and m == 1:
                        ingreso_apoyo_2025[clave] = ingreso_lista * 0.8
                    personal = ingreso_apoyo_2025[clave] * PERSONAL_APOYO[linea]
                personal *= (1.045 if a == 2026 else 1.0) * ruido(rng, 0.01)
                insumos = unidades * INSUMOS[linea] * ruido(rng, 0.02)
                restantes = unidades
                previsiones = list(MEZCLA_PREVISION[s])
                for i, prev in enumerate(previsiones):
                    share = MEZCLA_PREVISION[s][prev]
                    n = restantes if i == len(previsiones) - 1 else round(unidades * share)
                    restantes -= n
                    f = n / unidades if unidades else 0
                    ingreso = ingreso_lista * f * FACTOR_PREVISION[prev] * (1.04 if a == 2026 else 1.0)
                    t["produccion"].append({**fila, "linea": linea, "prevision": prev, "prestaciones": n,
                                            "ingreso": round(ingreso), "costo_personal": round(personal * f),
                                            "costo_insumos": round(insumos * f),
                                            "costo_honorarios": round(ingreso * HONORARIOS[linea])})
    return t


def escribir(tablas: dict[str, list[dict]], carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, columnas in ARCHIVOS.items():
        with (carpeta / f"{nombre}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=columnas, lineterminator="\n")
            w.writeheader()
            w.writerows(tablas[nombre])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=DATA / "gestion-operacional")
    args = parser.parse_args()
    tablas = generar(args.semilla)
    escribir(tablas, args.salida)
    for nombre in ARCHIVOS:
        print(f"{nombre:14} {len(tablas[nombre]):>6} filas")


if __name__ == "__main__":
    main()
