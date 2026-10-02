"""Genera data/workforce/: dotación, ausentismo y cobertura de tres empresas ficticias.

Son las mismas tres industrias del reporte Presupuesto vs. Real (Manufactura, Energía y Salud),
cada una con las sedes que allá aparecen como sucursales, unas 1.400 personas en total.
Simulamos 2025 y 2026 día hábil a día hábil:

- **Dotación:** cada persona tiene industria, sede, unidad, estamento, sexo, edad y antigüedad.
  Los egresos (voluntarios, involuntarios y jubilaciones) son más probables el primer año, y
  cada egreso abre una vacante que se llena uno o dos meses después.
- **Ausentismo:** cada día hábil una persona presente puede iniciar un episodio. El riesgo
  depende de la industria, el estamento, el sexo, la edad, el mes, la carga de su unidad y
  sede y una fragilidad individual (algunas personas se ausentan mucho más que otras: es lo
  que mide el Factor Bradford). Salud sigue el orden de magnitud de la Dipres (2024) y del NHS
  a escala de una clínica privada; Energía y Manufactura, con plantillas más masculinas y
  turnos distintos, quedan más abajo.
- **Cobertura:** las horas ausentes de las unidades operativas se cubren con sobretiempo, pool
  interno o personal externo. Desde julio de 2025 una sede de cada empresa pilotea un pool
  interno; las otras dos sedes siguen igual y sirven de grupo de control.
- **Pronóstico 2027:** tasa por sede, unidad y estamento ajustada por credibilidad de
  Bühlmann-Straub (las celdas chicas se acercan a la tasa de su estamento en la empresa) y
  simulación de episodios para obtener los días P50 y P90 de cada mes.

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
INICIO_PILOTO = date(2025, 7, 1)  # la sede piloto de cada empresa instala su pool interno desde aquí


@dataclass(frozen=True)
class Estamento:
    orden: int
    tasa: float  # fracción objetivo de días hábiles perdidos (sin licencias parentales)
    pct_mujeres: float
    valor_hora: int  # CLP


@dataclass(frozen=True)
class Industria:
    empresa: str
    sedes: dict[str, tuple[int, float]]  # sede → (dotación inicial, carga sobre el riesgo de ausencia)
    piloto: str  # sede que instala el pool interno
    unidades: dict[str, dict[str, float]]  # unidad → peso de cada estamento en la unidad
    peso_unidad: dict[str, float]
    carga_unidad: dict[str, float]  # turnos, exposición, esfuerzo físico
    requiere_cobertura: dict[str, float]  # fracción de las horas ausentes que hay que cubrir
    estamentos: dict[str, Estamento]
    rotacion_anual: float


# Orden común de los estamentos en las tres empresas (Auxiliares solo existe en Salud, Operarios fuera de ella).
ORDEN_ESTAMENTOS = {"Directivos": 1, "Profesionales": 2, "Administrativos": 3, "Auxiliares": 4, "Técnicos": 5,
                    "Operarios": 6}


def _estamentos(filas: dict[str, tuple[float, float, int]]) -> dict[str, Estamento]:
    return {n: Estamento(ORDEN_ESTAMENTOS[n], t, m, v) for n, (t, m, v) in filas.items()}


INDUSTRIAS = {
    "Manufactura": Industria(
        empresa="Manufacturas Ejemplo S.A.",
        sedes={"Santiago": (220, 1.0), "Concepción": (150, 1.05), "Antofagasta": (80, 1.10)},
        piloto="Concepción",
        unidades={
            "Producción": {"Operarios": 0.70, "Técnicos": 0.20, "Profesionales": 0.08, "Directivos": 0.02},
            "Mantenimiento industrial": {"Técnicos": 0.55, "Operarios": 0.35, "Profesionales": 0.08, "Directivos": 0.02},
            "Calidad": {"Profesionales": 0.40, "Técnicos": 0.55, "Directivos": 0.05},
            "Bodega y logística": {"Operarios": 0.75, "Administrativos": 0.20, "Directivos": 0.05},
            "Ventas": {"Profesionales": 0.40, "Administrativos": 0.55, "Directivos": 0.05},
            "Administración y finanzas": {"Profesionales": 0.35, "Administrativos": 0.55, "Directivos": 0.10},
        },
        peso_unidad={"Producción": 0.40, "Mantenimiento industrial": 0.12, "Calidad": 0.08, "Bodega y logística": 0.18,
                     "Ventas": 0.10, "Administración y finanzas": 0.12},
        carga_unidad={"Producción": 1.15, "Mantenimiento industrial": 1.10, "Calidad": 0.95, "Bodega y logística": 1.10,
                      "Ventas": 0.85, "Administración y finanzas": 0.85},
        requiere_cobertura={"Producción": 0.95, "Mantenimiento industrial": 0.8, "Calidad": 0.6,
                            "Bodega y logística": 0.85, "Ventas": 0.3, "Administración y finanzas": 0.2},
        estamentos=_estamentos({"Directivos": (0.020, 0.30, 28_000), "Profesionales": (0.038, 0.40, 13_000),
                                "Administrativos": (0.052, 0.65, 6_500), "Técnicos": (0.075, 0.20, 8_000),
                                "Operarios": (0.085, 0.25, 5_800)}),
        rotacion_anual=0.16,
    ),
    "Energia": Industria(
        empresa="Energía Ejemplo S.A.",
        sedes={"Zona Norte": (150, 1.05), "Zona Centro": (130, 1.0), "Zona Sur": (90, 0.95)},
        piloto="Zona Norte",
        unidades={
            "Operación de centrales": {"Profesionales": 0.25, "Técnicos": 0.35, "Operarios": 0.37, "Directivos": 0.03},
            "Mantenimiento": {"Profesionales": 0.15, "Técnicos": 0.45, "Operarios": 0.37, "Directivos": 0.03},
            "Transmisión": {"Profesionales": 0.25, "Técnicos": 0.50, "Operarios": 0.22, "Directivos": 0.03},
            "Centro de despacho": {"Profesionales": 0.55, "Técnicos": 0.40, "Directivos": 0.05},
            "Comercial": {"Profesionales": 0.45, "Administrativos": 0.50, "Directivos": 0.05},
            "Gestión corporativa": {"Profesionales": 0.35, "Administrativos": 0.55, "Directivos": 0.10},
        },
        peso_unidad={"Operación de centrales": 0.28, "Mantenimiento": 0.24, "Transmisión": 0.14,
                     "Centro de despacho": 0.08, "Comercial": 0.12, "Gestión corporativa": 0.14},
        carga_unidad={"Operación de centrales": 1.10, "Mantenimiento": 1.15, "Transmisión": 1.05,
                      "Centro de despacho": 0.95, "Comercial": 0.85, "Gestión corporativa": 0.85},
        requiere_cobertura={"Operación de centrales": 1.0, "Mantenimiento": 0.8, "Transmisión": 0.7,
                            "Centro de despacho": 1.0, "Comercial": 0.3, "Gestión corporativa": 0.2},
        estamentos=_estamentos({"Directivos": (0.018, 0.25, 32_000), "Profesionales": (0.032, 0.30, 16_000),
                                "Administrativos": (0.050, 0.60, 7_000), "Técnicos": (0.055, 0.12, 9_000),
                                "Operarios": (0.065, 0.08, 7_500)}),
        rotacion_anual=0.09,
    ),
    "Salud": Industria(
        empresa="Red Asistencial Ejemplo S.A.",
        sedes={"Clínica Oriente": (210, 0.95), "Clínica Centro": (240, 1.0), "Clínica Poniente": (160, 1.10)},
        piloto="Clínica Oriente",
        unidades={
            "Urgencia": {"Profesionales": 0.35, "Técnicos": 0.45, "Auxiliares": 0.17, "Directivos": 0.03},
            "Hospitalización": {"Profesionales": 0.30, "Técnicos": 0.45, "Auxiliares": 0.22, "Directivos": 0.03},
            "Pabellón": {"Profesionales": 0.40, "Técnicos": 0.40, "Auxiliares": 0.17, "Directivos": 0.03},
            "UCI": {"Profesionales": 0.42, "Técnicos": 0.43, "Auxiliares": 0.12, "Directivos": 0.03},
            "Ambulatorio": {"Profesionales": 0.40, "Técnicos": 0.30, "Administrativos": 0.27, "Directivos": 0.03},
            "Apoyo": {"Administrativos": 0.70, "Auxiliares": 0.20, "Directivos": 0.10},
        },
        peso_unidad={"Urgencia": 0.18, "Hospitalización": 0.26, "Pabellón": 0.14, "UCI": 0.12, "Ambulatorio": 0.15,
                     "Apoyo": 0.15},
        carga_unidad={"Urgencia": 1.20, "Hospitalización": 1.10, "Pabellón": 1.0, "UCI": 1.25, "Ambulatorio": 0.85,
                      "Apoyo": 0.90},
        requiere_cobertura={"Urgencia": 0.95, "Hospitalización": 0.95, "Pabellón": 0.9, "UCI": 1.0, "Ambulatorio": 0.6,
                            "Apoyo": 0.2},
        estamentos=_estamentos({"Directivos": (0.022, 0.45, 30_000), "Profesionales": (0.045, 0.70, 15_000),
                                "Administrativos": (0.060, 0.70, 6_500), "Auxiliares": (0.080, 0.65, 5_500),
                                "Técnicos": (0.090, 0.80, 7_500)}),
        rotacion_anual=0.13,
    ),
}
SEDES = {sede: (ind, datos) for ind, i in INDUSTRIAS.items() for sede, datos in i.sedes.items()}
DISPERSION_CELDA = 0.15  # efecto propio de cada sede × unidad × estamento (lognormal)

# Costo de una hora cubierta, como múltiplo del valor hora del estamento.
FACTOR_SOBRETIEMPO = 1.5  # recargo legal del 50%
FACTOR_POOL = 1.1  # pool interno: sueldo base más un costo de coordinación
FACTOR_EXTERNO = 1.8  # empresa externa: margen y menor productividad inicial

FORMA_FRAGILIDAD = 0.8  # gamma de media 1: muchas personas casi sin ausencias y unas pocas con muchas
RIESGO_SEXO = {"F": 1.25, "M": 0.68}  # razón ≈ 1,8 como en la Dipres
ESTACIONALIDAD = {1: 0.85, 2: 0.6, 3: 0.95, 4: 1.1, 5: 1.4, 6: 1.35, 7: 1.15, 8: 1.0,
                  9: 0.95, 10: 0.95, 11: 0.95, 12: 0.85}

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

EGRESO_MOTIVOS = {"Voluntario": 0.68, "Involuntario": 0.27}  # el resto, jubilación si tiene 60+
JUBILACION_ANUAL = 0.25  # riesgo adicional de egreso desde los 63 años


@dataclass
class Persona:
    id_persona: str
    industria: str
    sede: str
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


def crear_persona(rng: random.Random, n: int, industria: str, sede: str, unidad: str, estamento: str,
                  ingreso: date) -> Persona:
    e = INDUSTRIAS[industria].estamentos[estamento]
    sexo = "F" if rng.random() < e.pct_mujeres else "M"
    edad_ingreso = max(21, min(60, int(rng.gauss(38 if estamento == "Directivos" else 31, 9))))
    nacimiento = date(ingreso.year - edad_ingreso, rng.randint(1, 12), rng.randint(1, 28))
    jornada = 22 if estamento != "Directivos" and rng.random() < 0.08 else 44
    return Persona(f"P{n:04d}", industria, sede, unidad, estamento, sexo, nacimiento, ingreso, jornada,
                   fragilidad=rng.gammavariate(FORMA_FRAGILIDAD, 1 / FORMA_FRAGILIDAD))


def poblacion_inicial(rng: random.Random) -> list[Persona]:
    personas = []
    for industria, ind in INDUSTRIAS.items():
        for sede, (dotacion, _) in ind.sedes.items():
            for _ in range(dotacion):
                unidad = elegir(rng, ind.peso_unidad)
                estamento = elegir(rng, ind.unidades[unidad])
                antiguedad = min(30.0, rng.expovariate(1 / 6))
                ingreso = CALENTAMIENTO - timedelta(days=int(antiguedad * 365) + 1)
                personas.append(crear_persona(rng, len(personas) + 1, industria, sede, unidad, estamento, ingreso))
    return personas


def efectos_celda(rng: random.Random) -> dict[tuple[str, str, str], float]:
    """Riesgo propio de cada sede × unidad × estamento: lo que la credibilidad intenta estimar."""
    return {(s, u, e): carga * ind.carga_unidad[u] * math.exp(rng.gauss(0, DISPERSION_CELDA))
            for ind in INDUSTRIAS.values() for s, (_, carga) in ind.sedes.items()
            for u in ind.unidades for e in ind.estamentos}


def riesgo_diario(p: Persona, dia: date, media_episodio: float, celda: float) -> float:
    """Probabilidad de iniciar un episodio no parental hoy."""
    e = INDUSTRIAS[p.industria].estamentos[p.estamento]
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
    pesos = {g: w * (1.8 if invierno and dia.month in (5, 6, 7) else 1.0)
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

    def registrar(p: Persona, inicio: date, dias: int, tipo: str, grupo: str) -> None:
        fin = sumar_habiles(inicio, dias)
        tope = min(fin, FIN, p.fecha_egreso or FIN)
        p.ocupada_hasta = fin
        if inicio < INICIO:  # calentamiento: solo deja a la persona ocupada, fuera del periodo del reporte
            return
        id_ep = f"E{len(episodios) + 1:05d}"
        episodios.append({"id_episodio": id_ep, "id_persona": p.id_persona, "fecha_inicio": inicio.isoformat(),
                          "fecha_termino": fin.isoformat(), "dias_habiles": dias, "tipo": tipo,
                          "grupo_diagnostico": grupo})
        for d in dias_habiles(inicio, tope):
            diaria.append({"fecha": d.isoformat(), "id_persona": p.id_persona, "id_episodio": id_ep,
                           "horas": round(p.horas_dia(), 1)})

    for dia in dias_habiles(CALENTAMIENTO, FIN):
        # Vacantes que se llenan hoy.
        for ingreso, salida in [v for v in vacantes if v[0] <= dia]:
            vacantes.remove((ingreso, salida))
            personas.append(crear_persona(rng, len(personas) + 1, salida.industria, salida.sede, salida.unidad,
                                          salida.estamento, dia))
        for p in personas:
            if p.fecha_ingreso > dia or (p.fecha_egreso and p.fecha_egreso < dia):
                continue
            # Egreso: más probable el primer año y, para jubilación, desde los 60.
            anios = (dia - p.fecha_ingreso).days / 365
            rotacion_diaria = INDUSTRIAS[p.industria].rotacion_anual / 261
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
            if rng.random() < riesgo_diario(p, dia, media, celdas[(p.sede, p.unidad, p.estamento)]):
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
    return {"id_persona": p.id_persona, "industria": p.industria, "sede": p.sede, "unidad": p.unidad,
            "estamento": p.estamento, "sexo": p.sexo, "fecha_nacimiento": p.fecha_nacimiento.isoformat(),
            "fecha_ingreso": p.fecha_ingreso.isoformat(),
            "fecha_egreso": p.fecha_egreso.isoformat() if p.fecha_egreso else "",
            "motivo_egreso": p.motivo_egreso, "jornada_horas": p.jornada_horas}


def mezcla_cobertura(sede: str, dia: date) -> dict[str, float]:
    """Cómo se reparten las horas a cubrir. El piloto de cada empresa se instala en tres meses."""
    base = {"sobretiempo": 0.65, "pool": 0.0, "externo": 0.20, "no_cubiertas": 0.15}
    piloto = {"sobretiempo": 0.20, "pool": 0.57, "externo": 0.10, "no_cubiertas": 0.13}
    industria = SEDES[sede][0]
    if sede != INDUSTRIAS[industria].piloto or dia < INICIO_PILOTO:
        return base
    meses = (dia.year - INICIO_PILOTO.year) * 12 + dia.month - INICIO_PILOTO.month
    avance = min(1.0, (meses + 1) / 3)
    return {k: base[k] + (piloto[k] - base[k]) * avance for k in base}


def valor_hora_unidad(ind: Industria, unidad: str) -> float:
    """Valor hora promedio de la unidad según su dotación típica. Quien cubre no es necesariamente
    del estamento ausente, y así el costo por hora no salta cuando cambia la mezcla de ausencias."""
    pesos = ind.unidades[unidad]
    return sum(ind.estamentos[e].valor_hora * w for e, w in pesos.items()) / sum(pesos.values())


def cobertura(sim: dict, seed: int = SEMILLA) -> list[dict]:
    rng = random.Random(seed + 1)
    por_id = {p.id_persona: p for p in sim["_personas"]}
    horas = defaultdict(float)
    for f in sim["ausencia_diaria"]:
        p = por_id[f["id_persona"]]
        horas[(f["fecha"][:7], p.industria, p.sede, p.unidad, p.estamento)] += f["horas"]
    filas = []
    for (periodo, industria, sede, unidad, estamento), h in sorted(horas.items()):
        anio, mes = map(int, periodo.split("-"))
        ind = INDUSTRIAS[industria]
        requeridas = h * ind.requiere_cobertura[unidad]
        mezcla = mezcla_cobertura(sede, date(anio, mes, 1))
        ruido = {k: max(0.0, v * (1 + rng.gauss(0, 0.08))) for k, v in mezcla.items()}
        total = sum(ruido.values())
        partes = {k: round(requeridas * v / total, 1) for k, v in ruido.items()}
        valor = valor_hora_unidad(ind, unidad)
        filas.append({
            "anio": anio, "mes": mes, "industria": industria, "sede": sede, "unidad": unidad, "estamento": estamento,
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


def tabla_sedes() -> list[dict]:
    filas, orden = [], 0
    for industria, ind in INDUSTRIAS.items():
        for sede, (dotacion, _) in ind.sedes.items():
            orden += 1
            filas.append({"sede": sede, "industria": industria, "empresa": ind.empresa, "orden": orden,
                          "dotacion_inicial": dotacion, "piloto": int(sede == ind.piloto)})
    return filas


def tabla_unidades() -> list[dict]:
    filas, orden = [], 0
    for industria, ind in INDUSTRIAS.items():
        for unidad in ind.unidades:
            orden += 1
            filas.append({"unidad": unidad, "industria": industria, "orden": orden,
                          "requiere_cobertura": ind.requiere_cobertura[unidad]})
    return filas


def tabla_estamentos() -> list[dict]:
    """El valor hora depende de la empresa: queda en el costo de cada fila de cobertura_mensual."""
    return [{"estamento": n, "orden": o, "factor_sobretiempo": FACTOR_SOBRETIEMPO, "factor_pool": FACTOR_POOL,
             "factor_externo": FACTOR_EXTERNO} for n, o in sorted(ORDEN_ESTAMENTOS.items(), key=lambda x: x[1])]


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth: suficiente para los λ chicos de una celda-mes."""
    limite, k, prod = math.exp(-lam), 0, rng.random()
    while prod > limite:
        k += 1
        prod *= rng.random()
    return k


def pronostico(sim: dict, seed: int = SEMILLA) -> list[dict]:
    """Bühlmann-Straub por celda (sede × unidad × estamento) y años 2025-2026.

    X_ij = tasa del año j en la celda i, con peso w_ij = días hábiles disponibles. El colectivo
    es la tasa del estamento en toda la empresa. Z_i = w_i / (w_i + k), con k = EPV / VHM
    estimados de los mismos datos. Excluye licencias parentales, como la Dipres.
    """
    rng = random.Random(seed + 2)
    personas = sim["_personas"]
    parental = {e["id_episodio"] for e in sim["episodios"] if e["tipo"] == "Licencia parental"}
    perdidos = defaultdict(float)
    por_id = {p.id_persona: p for p in personas}
    for f in sim["ausencia_diaria"]:
        if f["id_episodio"] not in parental:
            p = por_id[f["id_persona"]]
            perdidos[(p.industria, p.sede, p.unidad, p.estamento, int(f["fecha"][:4]))] += 1
    disponibles = defaultdict(float)
    for p in personas:
        desde, hasta = max(p.fecha_ingreso, INICIO), min(p.fecha_egreso or FIN, FIN)
        for anio in (2025, 2026):
            a, b = max(desde, date(anio, 1, 1)), min(hasta, date(anio, 12, 31))
            if a <= b:
                disponibles[(p.industria, p.sede, p.unidad, p.estamento, anio)] += sum(1 for _ in dias_habiles(a, b))

    celdas = sorted({k[:4] for k in disponibles})
    w = {c: sum(disponibles[(*c, a)] for a in (2025, 2026)) for c in celdas}
    x = {c: sum(perdidos[(*c, a)] for a in (2025, 2026)) / w[c] for c in celdas}

    # Estimadores de Bühlmann-Straub por empresa y estamento.
    k_est, colectivo = {}, {}
    for grupo in sorted({(c[0], c[3]) for c in celdas}):
        cs = [c for c in celdas if (c[0], c[3]) == grupo]
        w_tot = sum(w[c] for c in cs)
        mu = sum(w[c] * x[c] for c in cs) / w_tot
        colectivo[grupo] = mu
        epv_num = sum(disponibles[(*c, a)] * (perdidos[(*c, a)] / disponibles[(*c, a)] - x[c]) ** 2
                      for c in cs for a in (2025, 2026) if disponibles[(*c, a)])
        epv = epv_num / max(1, sum(1 for c in cs for a in (2025, 2026) if disponibles[(*c, a)]) - len(cs))
        denom = w_tot - sum(w[c] ** 2 for c in cs) / w_tot
        vhm = (sum(w[c] * (x[c] - mu) ** 2 for c in cs) - (len(cs) - 1) * epv) / denom if denom else 0
        k_est[grupo] = epv / vhm if vhm > 0 else float("inf")

    # Duraciones observadas por empresa y estamento, para simular episodios.
    duraciones = defaultdict(list)
    for e in sim["episodios"]:
        if e["tipo"] != "Licencia parental":
            p = por_id[e["id_persona"]]
            duraciones[(p.industria, p.estamento)].append(e["dias_habiles"])
    media_dur = {g: sum(d) / len(d) for g, d in duraciones.items()}

    activos = defaultdict(int)
    for p in personas:
        if p.fecha_egreso is None and p.fecha_ingreso <= FIN:
            activos[(p.industria, p.sede, p.unidad, p.estamento)] += 1
    peso_mes = sum(ESTACIONALIDAD.values()) / 12

    filas = []
    for c in celdas:
        grupo = (c[0], c[3])
        z = w[c] / (w[c] + k_est[grupo]) if math.isfinite(k_est[grupo]) else 0.0
        tasa = z * x[c] + (1 - z) * colectivo[grupo]
        for mes in range(1, 13):
            habiles = sum(1 for _ in dias_habiles(date(ANIO_PRONOSTICO, mes, 1),
                                                  date(ANIO_PRONOSTICO + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)))
            dias_esperados = tasa * activos[c] * habiles * ESTACIONALIDAD[mes] / peso_mes
            lam = dias_esperados / media_dur[grupo] if grupo in media_dur else 0.0
            sims = sorted(sum(rng.choice(duraciones[grupo]) for _ in range(_poisson(rng, lam)))
                          for _ in range(SIMULACIONES)) if lam else [0] * SIMULACIONES
            media_sim = sum(sims) / SIMULACIONES
            varianza = sum((v - media_sim) ** 2 for v in sims) / (SIMULACIONES - 1)
            filas.append({
                "anio": ANIO_PRONOSTICO, "mes": mes, "industria": c[0], "sede": c[1], "unidad": c[2],
                "estamento": c[3], "dotacion": activos[c], "dias_habiles": habiles,
                "tasa_observada": round(x[c], 4), "anios_persona": round(w[c] / 261, 1),
                "z_credibilidad": round(z, 3), "tasa_credibilidad": round(tasa, 4),
                "dias_esperados": round(dias_esperados, 1), "dias_p50": sims[SIMULACIONES // 2],
                "dias_p90": sims[int(SIMULACIONES * 0.9)], "varianza_dias": round(varianza, 1),
            })
    return filas


ARCHIVOS = {
    "personas": ["id_persona", "industria", "sede", "unidad", "estamento", "sexo", "fecha_nacimiento",
                 "fecha_ingreso", "fecha_egreso", "motivo_egreso", "jornada_horas"],
    "episodios": ["id_episodio", "id_persona", "fecha_inicio", "fecha_termino", "dias_habiles", "tipo",
                  "grupo_diagnostico"],
    "ausencia_diaria": ["fecha", "id_persona", "id_episodio", "horas"],
    "disponibilidad_mensual": ["fecha", "id_persona", "dias_habiles", "horas"],
    "cobertura_mensual": ["anio", "mes", "industria", "sede", "unidad", "estamento", "horas_ausencia",
                          "horas_requeridas", "horas_sobretiempo", "horas_pool", "horas_externo",
                          "horas_no_cubiertas", "costo_sobretiempo", "costo_pool", "costo_externo"],
    "sedes": ["sede", "industria", "empresa", "orden", "dotacion_inicial", "piloto"],
    "unidades": ["unidad", "industria", "orden", "requiere_cobertura"],
    "estamentos": ["estamento", "orden", "factor_sobretiempo", "factor_pool", "factor_externo"],
    "pronostico": ["anio", "mes", "industria", "sede", "unidad", "estamento", "dotacion", "dias_habiles",
                   "tasa_observada", "anios_persona", "z_credibilidad", "tasa_credibilidad", "dias_esperados",
                   "dias_p50", "dias_p90", "varianza_dias"],
}


def generar(seed: int = SEMILLA) -> dict[str, list[dict]]:
    sim = simular(seed)
    return {
        "personas": sim["personas"],
        "episodios": sim["episodios"],
        "ausencia_diaria": sim["ausencia_diaria"],
        "disponibilidad_mensual": disponibilidad(sim),
        "cobertura_mensual": cobertura(sim, seed),
        "sedes": tabla_sedes(),
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
