"""Genera data/workforce/: dotación, ausentismo y cobertura de una red de clínicas ficticia.

"Red Asistencial Ejemplo S.A." tiene tres clínicas (Norte, Centro y Sur) y unas 600 personas.
Simulamos 2025 y 2026 día hábil a día hábil:

- **Dotación:** cada persona tiene clínica, unidad, estamento, sexo, edad y antigüedad. Los
  egresos (voluntarios, involuntarios y jubilaciones) son más probables el primer año, y cada
  egreso abre una vacante que se llena uno o dos meses después.
- **Ausentismo:** cada día hábil una persona presente puede iniciar un episodio. El riesgo
  depende del estamento, el sexo, la edad, el mes y una fragilidad individual (algunas personas
  se ausentan mucho más que otras: es lo que mide el Factor Bradford). La calibración sigue el
  orden de magnitud de la Dipres (2024) y del NHS, a escala de una clínica privada.
- **Cobertura:** las horas ausentes de las unidades clínicas se cubren con sobretiempo, pool
  interno o personal externo. Desde julio de 2025 la Clínica Norte pilotea un pool interno;
  Centro y Sur siguen igual y sirven de grupo de control.
- **Pronóstico 2027:** tasa por clínica, unidad y estamento ajustada por credibilidad de
  Bühlmann-Straub (las celdas chicas se acercan a la tasa de su estamento) y simulación de
  episodios para obtener los días P50 y P90 de cada mes.

Días hábiles = lunes a viernes (no descontamos feriados). Reproducible (semilla fija).
Ningún dato real de ningún empleador.

Uso:
    python data/generar_workforce.py
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

SEMILLA = 42
INICIO = date(2025, 1, 1)
CALENTAMIENTO = date(2024, 7, 1)  # se simula desde aquí para que enero no parta sin episodios en curso
FIN = date(2026, 12, 31)
ANIO_PRONOSTICO = 2027
SIMULACIONES = 1000
INICIO_PILOTO = date(2025, 7, 1)  # Clínica Norte: pool interno desde aquí

CLINICAS = {"Norte": 210, "Centro": 240, "Sur": 160}  # dotación inicial

# Unidad → peso de cada estamento en la unidad.
UNIDADES = {
    "Urgencia": {"Profesionales": 0.35, "Técnicos": 0.45, "Auxiliares": 0.17, "Directivos": 0.03},
    "Hospitalización": {"Profesionales": 0.30, "Técnicos": 0.45, "Auxiliares": 0.22, "Directivos": 0.03},
    "Pabellón": {"Profesionales": 0.40, "Técnicos": 0.40, "Auxiliares": 0.17, "Directivos": 0.03},
    "UCI": {"Profesionales": 0.42, "Técnicos": 0.43, "Auxiliares": 0.12, "Directivos": 0.03},
    "Ambulatorio": {"Profesionales": 0.40, "Técnicos": 0.30, "Administrativos": 0.27, "Directivos": 0.03},
    "Apoyo": {"Administrativos": 0.70, "Auxiliares": 0.20, "Directivos": 0.10},
}
PESO_UNIDAD = {"Urgencia": 0.18, "Hospitalización": 0.26, "Pabellón": 0.14, "UCI": 0.12,
               "Ambulatorio": 0.15, "Apoyo": 0.15}
# Carga de cada unidad sobre el riesgo de ausencia (turnos, exposición, esfuerzo físico).
CARGA_UNIDAD = {"Urgencia": 1.20, "Hospitalización": 1.10, "Pabellón": 1.0, "UCI": 1.25,
                "Ambulatorio": 0.85, "Apoyo": 0.90}
CARGA_CLINICA = {"Norte": 1.0, "Centro": 1.05, "Sur": 0.95}
DISPERSION_CELDA = 0.15  # efecto propio de cada clínica × unidad × estamento (lognormal)

# Fracción de las horas ausentes que hay que cubrir (en Apoyo casi todo puede esperar).
REQUIERE_COBERTURA = {"Urgencia": 0.95, "Hospitalización": 0.95, "Pabellón": 0.9, "UCI": 1.0,
                      "Ambulatorio": 0.6, "Apoyo": 0.2}


@dataclass(frozen=True)
class Estamento:
    orden: int
    tasa: float  # fracción objetivo de días hábiles perdidos (sin licencias parentales)
    pct_mujeres: float
    valor_hora: int  # CLP


ESTAMENTOS = {
    "Directivos": Estamento(1, 0.022, 0.45, 30_000),
    "Profesionales": Estamento(2, 0.045, 0.70, 15_000),
    "Administrativos": Estamento(3, 0.060, 0.70, 6_500),
    "Auxiliares": Estamento(4, 0.080, 0.65, 5_500),
    "Técnicos": Estamento(5, 0.090, 0.80, 7_500),
}
# Costo de una hora cubierta, como múltiplo del valor hora del estamento.
FACTOR_SOBRETIEMPO = 1.5  # recargo legal del 50%
FACTOR_POOL = 1.1  # pool interno: sueldo base más un costo de coordinación
FACTOR_EXTERNO = 1.8  # empresa externa: margen y menor productividad inicial

FORMA_FRAGILIDAD = 0.8  # gamma de media 1: muchas personas casi sin ausencias y unas pocas con muchas
RIESGO_SEXO = {"F": 1.25, "M": 0.68}  # razón ≈ 1,8 como en la Dipres
ESTACIONALIDAD = {1: 0.85, 2: 0.65, 3: 0.95, 4: 1.0, 5: 1.25, 6: 1.25, 7: 1.2, 8: 1.1,
                  9: 1.0, 10: 1.0, 11: 1.0, 12: 0.9}

# Licencias comunes: (participación en los episodios, duración media en días hábiles, sensible al invierno)
DIAGNOSTICOS = {
    "Respiratorio": (0.35, 5.0, True),
    "Otros": (0.30, 8.0, False),
    "Musculoesquelético": (0.20, 13.0, False),
    "Salud mental": (0.15, 24.0, False),
}
# Otros tipos de ausencia: (participación en los episodios no parentales, duración media)
OTROS_TIPOS = {"Permiso administrativo": (0.14, 1.0), "Accidente laboral": (0.03, 12.0),
               "Sin goce": (0.02, 3.0)}
DURACION_PARENTAL = 120  # pre y postnatal, en días hábiles
PROB_PARENTAL_ANUAL = 0.03  # mujeres de 25 a 40 años

ROTACION_ANUAL = 0.13
EGRESO_MOTIVOS = {"Voluntario": 0.68, "Involuntario": 0.27}  # el resto, jubilación si tiene 60+
JUBILACION_ANUAL = 0.25  # riesgo adicional de egreso desde los 63 años


@dataclass
class Persona:
    id_persona: str
    clinica: str
    unidad: str
    estamento: str
    sexo: str
    fecha_nacimiento: date
    fecha_ingreso: date
    jornada_horas: int
    fragilidad: float
    fecha_egreso: date | None = None
    motivo_egreso: str = ""
    ocupada_hasta: date = field(default=date.min)

    def edad(self, dia: date) -> int:
        return dia.year - self.fecha_nacimiento.year - ((dia.month, dia.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))

    def horas_dia(self) -> float:
        return self.jornada_horas / 5


def dias_habiles(desde: date, hasta: date):
    dia = desde
    while dia <= hasta:
        if dia.weekday() < 5:
            yield dia
        dia += timedelta(days=1)


def sumar_habiles(desde: date, n: int) -> date:
    """Último día hábil de un episodio de n días hábiles que empieza en `desde`."""
    dia, contados = desde, 1
    while contados < n:
        dia += timedelta(days=1)
        if dia.weekday() < 5:
            contados += 1
    return dia


def elegir(rng: random.Random, pesos: dict[str, float]) -> str:
    return rng.choices(list(pesos), weights=list(pesos.values()))[0]


def duracion(rng: random.Random, media: float) -> int:
    """Geométrica con la media pedida (mínimo 1 día): muchas cortas y una cola larga."""
    if media <= 1:
        return 1
    p = 1 / media
    return 1 + int(math.log(1 - rng.random()) / math.log(1 - p))


def crear_persona(rng: random.Random, n: int, clinica: str, unidad: str, estamento: str, ingreso: date) -> Persona:
    e = ESTAMENTOS[estamento]
    sexo = "F" if rng.random() < e.pct_mujeres else "M"
    edad_ingreso = max(21, min(60, int(rng.gauss(38 if estamento == "Directivos" else 31, 9))))
    nacimiento = date(ingreso.year - edad_ingreso, rng.randint(1, 12), rng.randint(1, 28))
    jornada = 22 if estamento != "Directivos" and rng.random() < 0.08 else 44
    return Persona(f"P{n:04d}", clinica, unidad, estamento, sexo, nacimiento, ingreso, jornada,
                   fragilidad=rng.gammavariate(FORMA_FRAGILIDAD, 1 / FORMA_FRAGILIDAD))


def poblacion_inicial(rng: random.Random) -> list[Persona]:
    personas = []
    for clinica, dotacion in CLINICAS.items():
        for _ in range(dotacion):
            unidad = elegir(rng, PESO_UNIDAD)
            estamento = elegir(rng, UNIDADES[unidad])
            antiguedad = min(30.0, rng.expovariate(1 / 6))
            ingreso = CALENTAMIENTO - timedelta(days=int(antiguedad * 365) + 1)
            personas.append(crear_persona(rng, len(personas) + 1, clinica, unidad, estamento, ingreso))
    return personas


def efectos_celda(rng: random.Random) -> dict[tuple[str, str, str], float]:
    """Riesgo propio de cada clínica × unidad × estamento: lo que la credibilidad intenta estimar."""
    return {(c, u, e): CARGA_CLINICA[c] * CARGA_UNIDAD[u] * math.exp(rng.gauss(0, DISPERSION_CELDA))
            for c in CLINICAS for u in UNIDADES for e in ESTAMENTOS}


def riesgo_diario(p: Persona, dia: date, media_episodio: float, celda: float) -> float:
    """Probabilidad de iniciar un episodio no parental hoy."""
    e = ESTAMENTOS[p.estamento]
    edad = p.edad(dia)
    factor_edad = 1 + 0.015 * max(0, edad - 45) - 0.01 * max(0, 30 - edad)
    return (e.tasa / media_episodio * RIESGO_SEXO[p.sexo] * factor_edad * ESTACIONALIDAD[dia.month]
            * p.fragilidad * celda)


def media_episodio_no_parental() -> float:
    peso_licencias = 1 - sum(w for w, _ in OTROS_TIPOS.values())
    media_lic = sum(w * d for w, d, _ in DIAGNOSTICOS.values())
    return peso_licencias * media_lic + sum(w * d for w, d in OTROS_TIPOS.values())


def tipo_y_diagnostico(rng: random.Random, dia: date) -> tuple[str, str, float]:
    r = rng.random()
    acumulado = 0.0
    for tipo, (peso, media) in OTROS_TIPOS.items():
        acumulado += peso
        if r < acumulado:
            return tipo, "No aplica", media
    pesos = {g: w * (1.8 if invierno and dia.month in (5, 6, 7, 8) else 1.0)
             for g, (w, _, invierno) in DIAGNOSTICOS.items()}
    grupo = elegir(rng, pesos)
    return "Licencia común", grupo, DIAGNOSTICOS[grupo][1]


def simular(seed: int = SEMILLA) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    celdas = efectos_celda(rng)
    personas = poblacion_inicial(rng)
    media = media_episodio_no_parental()
    episodios: list[dict] = []
    diaria: list[dict] = []
    vacantes: list[tuple[date, Persona]] = []  # (fecha de ingreso del reemplazo, persona que egresó)
    rotacion_diaria = ROTACION_ANUAL / 261

    def registrar(p: Persona, inicio: date, dias: int, tipo: str, grupo: str) -> None:
        fin = sumar_habiles(inicio, dias)
        tope = min(fin, FIN, p.fecha_egreso or FIN)
        p.ocupada_hasta = fin
        if fin < INICIO:  # calentamiento: solo cuenta lo que sigue en curso el 1 de enero
            return
        id_ep = f"E{len(episodios) + 1:05d}"
        episodios.append({"id_episodio": id_ep, "id_persona": p.id_persona, "fecha_inicio": inicio.isoformat(),
                          "fecha_termino": fin.isoformat(), "dias_habiles": dias, "tipo": tipo,
                          "grupo_diagnostico": grupo})
        for d in dias_habiles(max(inicio, INICIO), tope):
            diaria.append({"fecha": d.isoformat(), "id_persona": p.id_persona, "id_episodio": id_ep,
                           "horas": round(p.horas_dia(), 1)})

    for dia in dias_habiles(CALENTAMIENTO, FIN):
        # Vacantes que se llenan hoy.
        for ingreso, salida in [v for v in vacantes if v[0] <= dia]:
            vacantes.remove((ingreso, salida))
            personas.append(crear_persona(rng, len(personas) + 1, salida.clinica, salida.unidad, salida.estamento, dia))
        for p in personas:
            if p.fecha_ingreso > dia or (p.fecha_egreso and p.fecha_egreso < dia):
                continue
            # Egreso: más probable el primer año y, para jubilación, desde los 60.
            anios = (dia - p.fecha_ingreso).days / 365
            prob = rotacion_diaria * (2.2 if anios < 1 else 1.0) + (JUBILACION_ANUAL / 261 if p.edad(dia) >= 63 else 0)
            if rng.random() < prob:
                r = rng.random()
                if p.edad(dia) >= 60 and r < 0.6:
                    motivo = "Jubilación"
                else:
                    motivo = "Voluntario" if r < EGRESO_MOTIVOS["Voluntario"] / sum(EGRESO_MOTIVOS.values()) else "Involuntario"
                p.fecha_egreso, p.motivo_egreso = dia, motivo
                vacantes.append((dia + timedelta(days=rng.randint(30, 75)), p))
                continue
            if p.ocupada_hasta >= dia:
                continue
            if p.sexo == "F" and 25 <= p.edad(dia) <= 40 and rng.random() < PROB_PARENTAL_ANUAL / 261:
                registrar(p, dia, DURACION_PARENTAL, "Licencia parental", "No aplica")
                continue
            if rng.random() < riesgo_diario(p, dia, media, celdas[(p.clinica, p.unidad, p.estamento)]):
                tipo, grupo, media_tipo = tipo_y_diagnostico(rng, dia)
                registrar(p, dia, duracion(rng, media_tipo), tipo, grupo)

    # Un egreso corta el episodio en curso: no hay ausencias después de la fecha de egreso.
    personas = [p for p in personas if not (p.fecha_egreso and p.fecha_egreso < INICIO)]
    egreso = {p.id_persona: (p.fecha_egreso or FIN).isoformat() for p in personas}
    diaria = [f for f in diaria if f["id_persona"] in egreso and f["fecha"] <= egreso[f["id_persona"]]]
    con_dias = {f["id_episodio"] for f in diaria}
    episodios = [e for e in episodios if e["id_episodio"] in con_dias]
    return {
        "personas": [fila_persona(p) for p in personas],
        "episodios": episodios,
        "ausencia_diaria": sorted(diaria, key=lambda f: (f["fecha"], f["id_persona"])),
        "_personas": personas,
    }


def fila_persona(p: Persona) -> dict:
    return {"id_persona": p.id_persona, "clinica": p.clinica, "unidad": p.unidad, "estamento": p.estamento,
            "sexo": p.sexo, "fecha_nacimiento": p.fecha_nacimiento.isoformat(),
            "fecha_ingreso": p.fecha_ingreso.isoformat(),
            "fecha_egreso": p.fecha_egreso.isoformat() if p.fecha_egreso else "",
            "motivo_egreso": p.motivo_egreso, "jornada_horas": p.jornada_horas}


def mezcla_cobertura(clinica: str, dia: date) -> dict[str, float]:
    """Cómo se reparten las horas a cubrir. El piloto de Norte se instala en tres meses."""
    base = {"sobretiempo": 0.65, "pool": 0.0, "externo": 0.20, "no_cubiertas": 0.15}
    piloto = {"sobretiempo": 0.20, "pool": 0.57, "externo": 0.10, "no_cubiertas": 0.13}
    if clinica != "Norte" or dia < INICIO_PILOTO:
        return base
    meses = (dia.year - INICIO_PILOTO.year) * 12 + dia.month - INICIO_PILOTO.month
    avance = min(1.0, (meses + 1) / 3)
    return {k: base[k] + (piloto[k] - base[k]) * avance for k in base}


def cobertura(sim: dict, seed: int = SEMILLA) -> list[dict]:
    rng = random.Random(seed + 1)
    por_id = {p.id_persona: p for p in sim["_personas"]}
    horas = defaultdict(float)
    for f in sim["ausencia_diaria"]:
        p = por_id[f["id_persona"]]
        horas[(f["fecha"][:7], p.clinica, p.unidad, p.estamento)] += f["horas"]
    filas = []
    for (periodo, clinica, unidad, estamento), h in sorted(horas.items()):
        anio, mes = map(int, periodo.split("-"))
        requeridas = h * REQUIERE_COBERTURA[unidad]
        mezcla = mezcla_cobertura(clinica, date(anio, mes, 1))
        ruido = {k: max(0.0, v * (1 + rng.gauss(0, 0.08))) for k, v in mezcla.items()}
        total = sum(ruido.values())
        partes = {k: round(requeridas * v / total, 1) for k, v in ruido.items()}
        valor = ESTAMENTOS[estamento].valor_hora
        filas.append({
            "anio": anio, "mes": mes, "clinica": clinica, "unidad": unidad, "estamento": estamento,
            "horas_ausencia": round(h, 1), "horas_requeridas": round(requeridas, 1),
            "horas_sobretiempo": partes["sobretiempo"], "horas_pool": partes["pool"],
            "horas_externo": partes["externo"], "horas_no_cubiertas": partes["no_cubiertas"],
            "costo_sobretiempo": round(partes["sobretiempo"] * valor * FACTOR_SOBRETIEMPO),
            "costo_pool": round(partes["pool"] * valor * FACTOR_POOL),
            "costo_externo": round(partes["externo"] * valor * FACTOR_EXTERNO),
        })
    return filas


def disponibilidad(sim: dict) -> list[dict]:
    """Días y horas hábiles en que cada persona estaba contratada, por mes: el denominador de la tasa."""
    filas = []
    for p in sim["_personas"]:
        desde, hasta = max(p.fecha_ingreso, INICIO), min(p.fecha_egreso or FIN, FIN)
        por_mes = defaultdict(int)
        for d in dias_habiles(desde, hasta):
            por_mes[d.replace(day=1)] += 1
        for mes, dias in sorted(por_mes.items()):
            filas.append({"fecha": mes.isoformat(), "id_persona": p.id_persona, "dias_habiles": dias,
                          "horas": round(dias * p.horas_dia(), 1)})
    return sorted(filas, key=lambda f: (f["fecha"], f["id_persona"]))


def tabla_clinicas() -> list[dict]:
    return [{"clinica": c, "orden": i, "dotacion_inicial": n} for i, (c, n) in enumerate(CLINICAS.items(), 1)]


def tabla_unidades() -> list[dict]:
    return [{"unidad": u, "orden": i, "requiere_cobertura": REQUIERE_COBERTURA[u]}
            for i, u in enumerate(UNIDADES, 1)]


def tabla_estamentos() -> list[dict]:
    return [{"estamento": n, "orden": e.orden, "valor_hora": e.valor_hora, "factor_sobretiempo": FACTOR_SOBRETIEMPO,
             "factor_pool": FACTOR_POOL, "factor_externo": FACTOR_EXTERNO}
            for n, e in sorted(ESTAMENTOS.items(), key=lambda x: x[1].orden)]


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth: suficiente para los λ chicos de una celda-mes."""
    limite, k, prod = math.exp(-lam), 0, rng.random()
    while prod > limite:
        k += 1
        prod *= rng.random()
    return k


def pronostico(sim: dict, seed: int = SEMILLA) -> list[dict]:
    """Bühlmann-Straub por celda (clínica × unidad × estamento) y años 2025-2026.

    X_ij = tasa del año j en la celda i, con peso w_ij = días hábiles disponibles. El colectivo
    es la tasa del estamento en toda la red. Z_i = w_i / (w_i + k), con k = EPV / VHM estimados
    de los mismos datos. Excluye licencias parentales, como la Dipres.
    """
    rng = random.Random(seed + 2)
    personas = sim["_personas"]
    parental = {e["id_episodio"] for e in sim["episodios"] if e["tipo"] == "Licencia parental"}
    perdidos = defaultdict(float)
    por_id = {p.id_persona: p for p in personas}
    for f in sim["ausencia_diaria"]:
        if f["id_episodio"] not in parental:
            p = por_id[f["id_persona"]]
            perdidos[(p.clinica, p.unidad, p.estamento, int(f["fecha"][:4]))] += 1
    disponibles = defaultdict(float)
    for p in personas:
        desde, hasta = max(p.fecha_ingreso, INICIO), min(p.fecha_egreso or FIN, FIN)
        for anio in (2025, 2026):
            a, b = max(desde, date(anio, 1, 1)), min(hasta, date(anio, 12, 31))
            if a <= b:
                disponibles[(p.clinica, p.unidad, p.estamento, anio)] += sum(1 for _ in dias_habiles(a, b))

    celdas = sorted({k[:3] for k in disponibles})
    w = {c: sum(disponibles[(*c, a)] for a in (2025, 2026)) for c in celdas}
    x = {c: sum(perdidos[(*c, a)] for a in (2025, 2026)) / w[c] for c in celdas}

    # Estimadores de Bühlmann-Straub por estamento.
    k_est, colectivo = {}, {}
    for est in ESTAMENTOS:
        cs = [c for c in celdas if c[2] == est]
        w_tot = sum(w[c] for c in cs)
        mu = sum(w[c] * x[c] for c in cs) / w_tot
        colectivo[est] = mu
        epv_num = sum(disponibles[(*c, a)] * (perdidos[(*c, a)] / disponibles[(*c, a)] - x[c]) ** 2
                      for c in cs for a in (2025, 2026) if disponibles[(*c, a)])
        epv = epv_num / max(1, sum(1 for c in cs for a in (2025, 2026) if disponibles[(*c, a)]) - len(cs))
        denom = w_tot - sum(w[c] ** 2 for c in cs) / w_tot
        vhm = (sum(w[c] * (x[c] - mu) ** 2 for c in cs) - (len(cs) - 1) * epv) / denom if denom else 0
        k_est[est] = epv / vhm if vhm > 0 else float("inf")

    # Duraciones observadas por estamento, para simular episodios.
    duraciones = defaultdict(list)
    for e in sim["episodios"]:
        if e["tipo"] != "Licencia parental":
            duraciones[por_id[e["id_persona"]].estamento].append(e["dias_habiles"])
    media_dur = {est: sum(d) / len(d) for est, d in duraciones.items()}

    activos = defaultdict(int)
    for p in personas:
        if p.fecha_egreso is None and p.fecha_ingreso <= FIN:
            activos[(p.clinica, p.unidad, p.estamento)] += 1
    peso_mes = sum(ESTACIONALIDAD.values()) / 12

    filas = []
    for c in celdas:
        est = c[2]
        z = w[c] / (w[c] + k_est[est]) if math.isfinite(k_est[est]) else 0.0
        tasa = z * x[c] + (1 - z) * colectivo[est]
        for mes in range(1, 13):
            habiles = sum(1 for _ in dias_habiles(date(ANIO_PRONOSTICO, mes, 1),
                                                  date(ANIO_PRONOSTICO + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)))
            dias_esperados = tasa * activos[c] * habiles * ESTACIONALIDAD[mes] / peso_mes
            lam = dias_esperados / media_dur[est]
            sims = sorted(sum(rng.choice(duraciones[est]) for _ in range(_poisson(rng, lam)))
                          for _ in range(SIMULACIONES))
            media_sim = sum(sims) / SIMULACIONES
            varianza = sum((v - media_sim) ** 2 for v in sims) / (SIMULACIONES - 1)
            filas.append({
                "anio": ANIO_PRONOSTICO, "mes": mes, "clinica": c[0], "unidad": c[1], "estamento": est,
                "dotacion": activos[c], "dias_habiles": habiles, "tasa_observada": round(x[c], 4),
                "anios_persona": round(w[c] / 261, 1), "z_credibilidad": round(z, 3),
                "tasa_credibilidad": round(tasa, 4), "dias_esperados": round(dias_esperados, 1),
                "dias_p50": sims[SIMULACIONES // 2], "dias_p90": sims[int(SIMULACIONES * 0.9)],
                "varianza_dias": round(varianza, 1),
            })
    return filas


ARCHIVOS = {
    "personas": ["id_persona", "clinica", "unidad", "estamento", "sexo", "fecha_nacimiento", "fecha_ingreso",
                 "fecha_egreso", "motivo_egreso", "jornada_horas"],
    "episodios": ["id_episodio", "id_persona", "fecha_inicio", "fecha_termino", "dias_habiles", "tipo",
                  "grupo_diagnostico"],
    "ausencia_diaria": ["fecha", "id_persona", "id_episodio", "horas"],
    "disponibilidad_mensual": ["fecha", "id_persona", "dias_habiles", "horas"],
    "cobertura_mensual": ["anio", "mes", "clinica", "unidad", "estamento", "horas_ausencia", "horas_requeridas",
                          "horas_sobretiempo", "horas_pool", "horas_externo", "horas_no_cubiertas",
                          "costo_sobretiempo", "costo_pool", "costo_externo"],
    "clinicas": ["clinica", "orden", "dotacion_inicial"],
    "unidades": ["unidad", "orden", "requiere_cobertura"],
    "estamentos": ["estamento", "orden", "valor_hora", "factor_sobretiempo", "factor_pool", "factor_externo"],
    "pronostico": ["anio", "mes", "clinica", "unidad", "estamento", "dotacion", "dias_habiles", "tasa_observada",
                   "anios_persona", "z_credibilidad", "tasa_credibilidad", "dias_esperados", "dias_p50", "dias_p90",
                   "varianza_dias"],
}


def generar(seed: int = SEMILLA) -> dict[str, list[dict]]:
    sim = simular(seed)
    return {
        "personas": sim["personas"],
        "episodios": sim["episodios"],
        "ausencia_diaria": sim["ausencia_diaria"],
        "disponibilidad_mensual": disponibilidad(sim),
        "cobertura_mensual": cobertura(sim, seed),
        "clinicas": tabla_clinicas(),
        "unidades": tabla_unidades(),
        "estamentos": tabla_estamentos(),
        "pronostico": pronostico(sim, seed),
    }


def escribir(tablas: dict[str, list[dict]], carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, campos in ARCHIVOS.items():
        with (carpeta / f"{nombre}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
            w.writeheader()
            w.writerows(tablas[nombre])


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los datos sintéticos del reporte Workforce.")
    parser.add_argument("--seed", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=Path(__file__).parent / "workforce")
    args = parser.parse_args()
    tablas = generar(args.seed)
    escribir(tablas, args.salida)
    for nombre, filas in tablas.items():
        print(f"{nombre:20} {len(filas):7d} filas")


if __name__ == "__main__":
    main()
