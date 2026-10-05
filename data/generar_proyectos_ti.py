"""Genera data/proyectos-ti/: la cartera de proyectos de TI de tres empresas ficticias, estilo Jira.

Son las mismas tres empresas de los otros reportes de la vitrina (Manufactura, Energía y Salud).
Cada una tiene un área de TI con cinco equipos (Datos, Integraciones, Plataforma, Producto y QA)
que ejecutan cuatro proyectos en paralelo con sprints de dos semanas. Simulamos día hábil a día
hábil desde enero de 2025 hasta la fecha de corte (30 de septiembre de 2026):

- **Cartera:** el alcance de cada proyecto (en puntos de historia) se planifica para que calce
  con la capacidad de sus equipos entre el inicio y la fecha comprometida.
- **Flujo:** cada persona toma la siguiente issue de la cola de su equipo, la trabaja según su
  dedicación (algunas personas reparten la semana entre dos equipos) y la pasa a revisión; la
  revisión dura de uno a tres días. Así nacen los estados `por_hacer → en_curso → en_revision →
  hecho` con fecha y hora, como una exportación del historial de Jira.
- **Dependencias:** parte de las issues necesitan algo de otro equipo. Si a mitad del trabajo
  lo que necesitan no está terminado, pasan a `bloqueado` y la persona toma otra cosa; vuelven
  a la cola de uno a tres días después de que el otro equipo termina (el traspaso).
- **Sprints:** el equipo compromete al inicio de cada sprint lo que lleva en curso más lo que
  espera empezar, hasta su velocidad reciente. Lo comprometido que llega a `hecho` dentro del
  sprint mide la previsibilidad.
- **Pronóstico:** para cada proyecto abierto al corte, 10.000 simulaciones de Monte Carlo del
  throughput semanal de las últimas 12 semanas dan la fecha de término P50, P85 y P95.

Tres historias quedan sembradas: la ficha clínica de Salud crece en alcance y su P85 se aleja de
la fecha comprometida; en Energía, Integraciones (con un equipo corto y tareas subestimadas)
concentra cerca del 41% de las horas bloqueadas; la migración de ERP de Manufactura avanza con
un flujo estable y una previsibilidad cercana al 92%.

Montos en CLP. Reproducible (semilla fija). Días hábiles de lunes a viernes, sin feriados.
Ningún dato real de ningún empleador.

Uso:
    python data/generar_proyectos_ti.py
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

SEMILLA = 42
INICIO = date(2025, 1, 6)  # primer lunes de 2025: arranca el primer sprint
CORTE = date(2026, 9, 30)  # fecha de los datos: lo posterior se pronostica
SPRINT_DIAS = 14
HORAS_DIA = 8
DIAS_POR_PUNTO = 1.5  # días de esfuerzo de una persona a tiempo completo por punto de historia
SIMULACIONES = 10_000
VENTANA_THROUGHPUT = 12  # semanas de historia que alimentan el Monte Carlo
EQUIPOS = ("Datos", "Integraciones", "Plataforma", "Producto", "QA")
ROL_Y_TARIFA = {  # CLP por hora, costo interno cargado
    "Datos": ("Ingeniería de datos", 38_000),
    "Integraciones": ("Desarrollo de integraciones", 36_000),
    "Plataforma": ("Plataforma y nube", 40_000),
    "Producto": ("Desarrollo de producto", 34_000),
    "QA": ("Calidad (QA)", 28_000),
}
TIPOS = {"historia": (0.65, {2: 0.30, 3: 0.35, 5: 0.25, 8: 0.10}),
         "tarea": (0.20, {1: 0.35, 2: 0.40, 3: 0.25}),
         "bug": (0.15, {1: 0.55, 2: 0.45})}
FRACCION_DIVIDIDA = 0.15  # personas que reparten la semana entre dos equipos


@dataclass(frozen=True)
class Proyecto:
    codigo: str
    nombre: str
    inicio: date
    fin: date
    peso: float  # prioridad relativa al repartir la capacidad de los equipos
    mezcla: dict[str, float]  # fracción de los puntos que hace cada equipo
    crecimiento: tuple[date, float] | None = None  # (fecha, alcance agregado como fracción del original)


@dataclass(frozen=True)
class Industria:
    empresa: str
    dotacion: dict[str, int]
    sigma: float  # variabilidad de la duración de una issue (lognormal)
    utilizacion: float  # fracción de la capacidad disponible que se planifica
    soporte: float  # probabilidad de que una persona dedique el día a soporte (sin avance en proyectos)
    compromiso: float  # cuánto compromete el equipo por sprint, como múltiplo de su velocidad reciente
    sobretiempo: dict[str, float]  # equipos que trabajan más horas que su jornada para recuperar atraso
    prob_dependencia: float
    traspaso: dict[str, tuple[int, int]]  # días hábiles que tarda en reanudarse lo que bloqueó cada equipo
    max_puntos: int  # tamaño máximo de una historia: los equipos que parten historias grandes son más previsibles
    sesgo_bloqueante: dict[str, float]  # de qué equipo depende una issue cuando depende de otro
    subestimacion: dict[str, float]  # equipos cuyas issues toman más de lo estimado
    proyectos: tuple[Proyecto, ...]


def _mezcla(datos: float, integ: float, plat: float, prod: float, qa: float) -> dict[str, float]:
    return dict(zip(EQUIPOS, (datos, integ, plat, prod, qa)))


INDUSTRIAS = {
    "Manufactura": Industria(
        empresa="Manufacturas Ejemplo S.A.",
        dotacion={"Datos": 5, "Integraciones": 4, "Plataforma": 4, "Producto": 6, "QA": 3},
        sigma=0.15, utilizacion=0.80, soporte=0.10, compromiso=0.70, sobretiempo={}, prob_dependencia=0.08,
        traspaso={}, max_puntos=5,
        sesgo_bloqueante=_mezcla(0.30, 0.20, 0.25, 0.20, 0.05), subestimacion={},
        proyectos=(
            Proyecto("MAN-ERP", "Migración de ERP", date(2025, 3, 3), date(2026, 12, 18), 1.4,
                     _mezcla(0.15, 0.25, 0.15, 0.30, 0.15)),
            Proyecto("MAN-LOT", "Trazabilidad de lotes en planta", date(2025, 1, 6), date(2025, 11, 28), 1.0,
                     _mezcla(0.30, 0.20, 0.10, 0.25, 0.15)),
            Proyecto("MAN-POR", "Portal de distribuidores", date(2025, 9, 1), date(2026, 6, 26), 1.0,
                     _mezcla(0.10, 0.15, 0.15, 0.45, 0.15)),
            Proyecto("MAN-PRE", "Mantenimiento predictivo", date(2026, 2, 2), date(2027, 1, 29), 0.8,
                     _mezcla(0.45, 0.15, 0.15, 0.15, 0.10)),
        ),
    ),
    "Energia": Industria(
        empresa="Energía Ejemplo S.A.",
        dotacion={"Datos": 5, "Integraciones": 3, "Plataforma": 4, "Producto": 6, "QA": 3},
        sigma=0.40, utilizacion=0.84, soporte=0.12, compromiso=1.05, sobretiempo={"Integraciones": 1.20}, prob_dependencia=0.20,
        traspaso={"Integraciones": (4, 8)}, max_puntos=8,  # Integraciones despliega en ventanas semanales
        sesgo_bloqueante=_mezcla(0.15, 0.45, 0.22, 0.13, 0.05), subestimacion={"Integraciones": 1.25},
        proyectos=(
            Proyecto("ENE-TEL", "Telemetría de centrales", date(2025, 2, 3), date(2026, 3, 27), 1.2,
                     _mezcla(0.30, 0.25, 0.20, 0.10, 0.15)),
            Proyecto("ENE-DES", "Despacho en tiempo real", date(2025, 6, 2), date(2026, 11, 27), 1.2,
                     _mezcla(0.20, 0.30, 0.15, 0.20, 0.15)),
            Proyecto("ENE-FAC", "Facturación de clientes libres", date(2025, 10, 6), date(2026, 10, 30), 1.0,
                     _mezcla(0.15, 0.25, 0.10, 0.35, 0.15)),
            Proyecto("ENE-CIB", "Ciberseguridad OT", date(2026, 1, 5), date(2026, 12, 18), 0.8,
                     _mezcla(0.10, 0.20, 0.45, 0.10, 0.15)),
        ),
    ),
    "Salud": Industria(
        empresa="Red Asistencial Ejemplo S.A.",
        dotacion={"Datos": 5, "Integraciones": 4, "Plataforma": 4, "Producto": 6, "QA": 3},
        sigma=0.35, utilizacion=0.82, soporte=0.15, compromiso=0.95, sobretiempo={"Producto": 1.10}, prob_dependencia=0.15,
        traspaso={}, max_puntos=8,
        sesgo_bloqueante=_mezcla(0.30, 0.22, 0.23, 0.20, 0.05), subestimacion={},
        proyectos=(
            Proyecto("SAL-FIC", "Ficha clínica electrónica", date(2025, 4, 7), date(2026, 10, 30), 1.5,
                     _mezcla(0.15, 0.25, 0.10, 0.35, 0.15), crecimiento=(date(2025, 12, 1), 0.28)),
            Proyecto("SAL-AGE", "Agenda en línea", date(2025, 1, 6), date(2025, 9, 26), 1.0,
                     _mezcla(0.10, 0.20, 0.15, 0.40, 0.15)),
            Proyecto("SAL-LAB", "Integración con laboratorio", date(2025, 8, 4), date(2026, 5, 29), 0.9,
                     _mezcla(0.20, 0.30, 0.15, 0.20, 0.15)),
            Proyecto("SAL-CAM", "Tablero de camas", date(2026, 3, 2), date(2026, 12, 18), 0.8,
                     _mezcla(0.40, 0.10, 0.10, 0.30, 0.10)),
        ),
    ),
}

ESTADOS = ("por_hacer", "en_curso", "en_revision", "bloqueado", "hecho")
ARCHIVOS = {
    "empresas": ["industria", "empresa", "orden"],
    "equipos": ["equipo", "orden", "foco"],
    "proyectos": ["proyecto", "industria", "nombre", "inicio", "fin_comprometido", "puntos_planificados",
                  "puntos_agregados", "presupuesto_horas", "presupuesto_monto"],
    "personas_ti": ["persona_ti", "industria", "equipo_principal", "rol", "tarifa_hora"],
    "asignaciones": ["persona_ti", "industria", "equipo", "dedicacion", "desde"],
    "sprints": ["sprint", "numero", "inicio", "fin"],
    "issues": ["issue", "industria", "proyecto", "equipo", "tipo", "epica_padre", "puntos", "creado",
               "fecha_inicio", "fecha_fin", "estado_al_corte", "dias_ciclo", "horas_bloqueado", "sprint"],
    "transiciones": ["issue", "industria", "proyecto", "equipo", "estado_desde", "estado_hasta", "fecha_hora"],
    "dependencias": ["issue_bloqueante", "issue_bloqueado", "industria", "proyecto", "equipo_bloqueante",
                     "equipo_bloqueado", "creada", "resuelta", "horas_bloqueado"],
    "compromisos": ["sprint", "industria", "equipo", "proyecto", "issue", "puntos", "completada"],
    "worklogs": ["fecha", "persona_ti", "industria", "equipo", "proyecto", "issue", "horas"],
    "capacidad_semanal": ["semana", "industria", "equipo", "horas_capacidad"],
    "flujo_semanal": ["semana", "industria", "proyecto", "equipo", "estado", "issues", "puntos"],
    "pronostico_termino": ["proyecto", "industria", "estado", "issues_pendientes", "throughput_semanal",
                           "fin_comprometido", "fecha_p50", "fecha_p85", "fecha_p95", "atraso_p85_dias"],
    "pronostico_distribucion": ["proyecto", "industria", "semana_termino", "probabilidad"],
}
FOCO = {"Datos": "Modelos, pipelines y reportería", "Integraciones": "APIs e interfaces entre sistemas",
        "Plataforma": "Infraestructura, nube y seguridad", "Producto": "Funcionalidades y experiencia de usuario",
        "QA": "Pruebas y aseguramiento de calidad"}


# --- calendario -------------------------------------------------------------------------------


def habil(d: date) -> bool:
    return d.weekday() < 5


def dias_habiles(desde: date, hasta: date) -> list[date]:
    salida, d = [], desde
    while d <= hasta:
        if habil(d):
            salida.append(d)
        d += timedelta(days=1)
    return salida


def sumar_habiles(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if habil(d):
            n -= 1
    return d


def lunes(d: date) -> date:
    return d - timedelta(days=d.weekday())


def sprints() -> list[dict]:
    salida, inicio, n = [], INICIO, 1
    while inicio <= CORTE:
        salida.append({"sprint": f"S{n:02d}", "numero": n, "inicio": inicio.isoformat(),
                       "fin": (inicio + timedelta(days=SPRINT_DIAS - 3)).isoformat()})  # cierra el viernes
        inicio += timedelta(days=SPRINT_DIAS)
        n += 1
    return salida


def hora(d: date, orden: int) -> str:
    """Marca de tiempo del día: los eventos del mismo día quedan en orden (9:00, 10:30, ...)."""
    minutos = 9 * 60 + 90 * min(orden, 5)
    return f"{d.isoformat()}T{minutos // 60:02d}:{minutos % 60:02d}:00"


def elegir(rng: random.Random, pesos: dict) -> object:
    return rng.choices(list(pesos), weights=list(pesos.values()))[0]


# --- dimensiones ------------------------------------------------------------------------------


def personas(rng: random.Random) -> tuple[list[dict], list[dict]]:
    filas, asignaciones = [], []
    for industria, ind in INDUSTRIAS.items():
        n = 0
        for equipo in EQUIPOS:
            rol, tarifa = ROL_Y_TARIFA[equipo]
            for _ in range(ind.dotacion[equipo]):
                n += 1
                persona = f"TI-{industria[0]}{n:03d}"
                filas.append({"persona_ti": persona, "industria": industria, "equipo_principal": equipo,
                              "rol": rol, "tarifa_hora": tarifa})
                if rng.random() < FRACCION_DIVIDIDA:
                    otro = rng.choice([e for e in EQUIPOS if e != equipo])
                    partes = [(equipo, 0.5), (otro, 0.5)]
                else:
                    partes = [(equipo, 1.0)]
                for eq, dedicacion in partes:
                    asignaciones.append({"persona_ti": persona, "industria": industria, "equipo": eq,
                                         "dedicacion": dedicacion, "desde": INICIO.isoformat()})
    return filas, asignaciones


def capacidad_diaria(asignaciones: list[dict]) -> dict[tuple[str, str], float]:
    """Personas-día por (industria, equipo)."""
    cap = defaultdict(float)
    for a in asignaciones:
        cap[(a["industria"], a["equipo"])] += a["dedicacion"]
    return cap


def planificar(cap: dict[tuple[str, str], float]) -> dict[tuple[str, str], float]:
    """Puntos que cada proyecto planifica con cada equipo para terminar en su fecha comprometida.

    Reparte la capacidad de cada equipo, día a día, entre los proyectos activos según peso × mezcla.
    """
    plan = defaultdict(float)
    for industria, ind in INDUSTRIAS.items():
        for d in dias_habiles(INICIO, max(p.fin for p in ind.proyectos)):
            activos = [p for p in ind.proyectos if p.inicio <= d <= p.fin]
            for equipo in EQUIPOS:
                total = sum(p.peso * p.mezcla[equipo] for p in activos)
                if not total:
                    continue
                puntos_dia = cap[(industria, equipo)] * (1 - ind.soporte) / DIAS_POR_PUNTO * ind.utilizacion
                for p in activos:
                    plan[(p.codigo, equipo)] += puntos_dia * p.peso * p.mezcla[equipo] / total
    return plan


# --- backlog ----------------------------------------------------------------------------------


@dataclass
class Issue:
    clave: str
    industria: str
    proyecto: str
    equipo: str
    tipo: str
    epica: str
    puntos: int
    creado: date
    orden: float
    bloqueantes: list
    inicio: date | None = None
    fin: date | None = None
    restante: float = 0.0
    bloquear_en: float | None = None  # esfuerzo restante al que descubre la dependencia
    bloqueado_desde: date | None = None
    lista_desde: date | None = None  # vuelve a la cola tras el traspaso
    horas_bloqueado: float = 0.0
    eventos: list | None = None


def backlog(rng: random.Random, plan: dict[tuple[str, str], float]) -> tuple[list[Issue], list[dict]]:
    issues, epicas, numero = [], [], Counter()

    def nueva(**campos) -> Issue:
        prefijo = campos["proyecto"].split("-")[1]  # clave al estilo Jira: correlativo por proyecto
        numero[prefijo] += 1
        return Issue(clave=f"{prefijo}-{numero[prefijo]}", bloqueantes=[], eventos=[], **campos)

    for industria, ind in INDUSTRIAS.items():
        for p in ind.proyectos:
            planificados = sum(plan[(p.codigo, e)] for e in EQUIPOS)
            tandas = [(p.inicio, 1.0, 0.0)]
            if p.crecimiento:
                tandas.append((p.crecimiento[0], p.crecimiento[1], 1.0))
            for creado, fraccion, desplazamiento in tandas:
                n_epicas = max(3, round(planificados * fraccion / 70))
                claves_epica = []
                for k in range(n_epicas):
                    epica = nueva(industria=industria, proyecto=p.codigo, equipo="Producto", tipo="epica",
                                  epica="", puntos=0, creado=creado, orden=desplazamiento + k / n_epicas)
                    epicas.append(epica)
                    claves_epica.append(epica)
                for equipo in EQUIPOS:
                    meta, acumulado = plan[(p.codigo, equipo)] * fraccion, 0
                    propias = []
                    while acumulado < meta:
                        tipo = elegir(rng, {t: v[0] for t, v in TIPOS.items()})
                        puntos = elegir(rng, {k: v for k, v in TIPOS[tipo][1].items() if k <= ind.max_puntos})
                        k = min(n_epicas - 1, int(rng.random() * n_epicas))
                        propias.append((k + rng.random(), tipo, puntos, claves_epica[k].clave))
                        acumulado += puntos
                    for orden, tipo, puntos, epica in sorted(propias):
                        issues.append(nueva(industria=industria, proyecto=p.codigo, equipo=equipo, tipo=tipo,
                                            epica=epica, puntos=puntos, creado=creado,
                                            orden=desplazamiento + orden / n_epicas))
    return issues, epicas


def dependencias(rng: random.Random, issues: list[Issue]) -> list[tuple[Issue, Issue]]:
    """Cada issue depende, con cierta probabilidad, de una issue de otro equipo en un punto parecido del proyecto."""
    por_proyecto_equipo = defaultdict(list)
    for i in issues:
        por_proyecto_equipo[(i.proyecto, i.equipo)].append(i)
    pares = []
    for i in issues:
        ind = INDUSTRIAS[i.industria]
        if rng.random() >= ind.prob_dependencia:
            continue
        sesgo = {e: w for e, w in ind.sesgo_bloqueante.items() if e != i.equipo and por_proyecto_equipo[(i.proyecto, e)]}
        if not sesgo:
            continue
        candidatas = por_proyecto_equipo[(i.proyecto, elegir(rng, sesgo))]
        cercanas = [c for c in candidatas if i.orden - 0.10 <= c.orden <= i.orden and c.creado <= i.creado]
        if not cercanas:
            continue
        bloqueante = rng.choice(cercanas)
        i.bloqueantes.append(bloqueante)
        pares.append((bloqueante, i))
    return pares


# --- simulación -------------------------------------------------------------------------------


def simular(rng: random.Random, issues: list[Issue], asignaciones: list[dict]) -> list[dict]:
    """Avanza día hábil a día hábil. Devuelve los worklogs; las issues quedan con sus eventos."""
    proyectos = {p.codigo: p for ind in INDUSTRIAS.values() for p in ind.proyectos}
    colas = defaultdict(list)  # (industria, equipo, proyecto) -> issues sin empezar, en orden
    for i in sorted(issues, key=lambda x: (x.proyecto, x.equipo, x.orden)):
        colas[(i.industria, i.equipo, i.proyecto)].append(i)
    reanudables = defaultdict(list)  # (industria, equipo) -> issues desbloqueadas que vuelven a la cola
    bloqueadas = []
    revision = defaultdict(list)  # fecha -> issues que salen de revisión ese día
    slots = [{"persona": a["persona_ti"], "industria": a["industria"], "equipo": a["equipo"],
              "dedicacion": a["dedicacion"], "issue": None} for a in asignaciones]
    worklogs = []

    def evento(i: Issue, d: date, desde: str, hasta: str) -> None:
        i.eventos.append((d, desde, hasta))

    def tomar(s: dict, d: date) -> Issue | None:
        listas = [x for x in reanudables[(s["industria"], s["equipo"])] if x.lista_desde <= d]
        if listas:
            i = listas[0]
            reanudables[(s["industria"], s["equipo"])].remove(i)
            evento(i, d, "bloqueado", "en_curso")
            i.horas_bloqueado += HORAS_DIA * len(dias_habiles(i.bloqueado_desde, d - timedelta(days=1)))
            i.bloqueado_desde = None
            return i
        pesos = {}
        for codigo, p in proyectos.items():
            cola = colas.get((s["industria"], s["equipo"], codigo))
            if cola and p.inicio <= d and cola[0].creado <= d:
                pesos[codigo] = p.peso * p.mezcla[s["equipo"]]
        if not pesos:
            return None
        i = colas[(s["industria"], s["equipo"], elegir(rng, pesos))].pop(0)
        ind = INDUSTRIAS[i.industria]
        factor = ind.subestimacion.get(i.equipo, 1.0)
        i.restante = i.puntos * DIAS_POR_PUNTO * factor * rng.lognormvariate(-ind.sigma**2 / 2, ind.sigma)
        if i.bloqueantes:
            i.bloquear_en = i.restante * rng.uniform(0.3, 0.7)
        i.inicio = d
        evento(i, d, "por_hacer", "en_curso")
        return i

    for d in dias_habiles(INICIO, CORTE):
        for i in revision.pop(d, []):
            evento(i, d, "en_revision", "hecho")
            i.fin = d
        for i in list(bloqueadas):
            if all(b.fin and b.fin < d for b in i.bloqueantes):
                bloqueadas.remove(i)
                ultimo = max(i.bloqueantes, key=lambda b: b.fin)
                i.lista_desde = sumar_habiles(ultimo.fin, rng.randint(*INDUSTRIAS[i.industria].traspaso.get(
                    ultimo.equipo, (1, 3))))
                reanudables[(i.industria, i.equipo)].append(i)
        for s in slots:
            if s["issue"] is None:
                s["issue"] = tomar(s, d)
            i = s["issue"]
            ind = INDUSTRIAS[s["industria"]]
            if i is None or rng.random() < ind.soporte:
                continue
            extra = ind.sobretiempo.get(s["equipo"], 1.0)
            worklogs.append({"fecha": d.isoformat(), "persona_ti": s["persona"], "industria": s["industria"],
                             "equipo": s["equipo"], "proyecto": i.proyecto, "issue": i.clave,
                             "horas": round(HORAS_DIA * s["dedicacion"] * extra, 1)})
            i.restante -= s["dedicacion"] * extra
            pendientes = [b for b in i.bloqueantes if not (b.fin and b.fin <= d)]
            if i.bloquear_en is not None and i.restante <= i.bloquear_en and pendientes:
                i.bloquear_en = None
                i.bloqueado_desde = sumar_habiles(d, 1)
                evento(i, i.bloqueado_desde, "en_curso", "bloqueado")
                bloqueadas.append(i)
                s["issue"] = None
            elif i.restante <= 0:
                evento(i, d, "en_curso", "en_revision")
                revision[sumar_habiles(d, rng.randint(1, 3))].append(i)
                s["issue"] = None
    for i in bloqueadas + [x for lista in reanudables.values() for x in lista]:
        if i.bloqueado_desde and i.bloqueado_desde <= CORTE:  # sigue bloqueada al corte
            i.horas_bloqueado += HORAS_DIA * len(dias_habiles(i.bloqueado_desde, CORTE))
    return worklogs


# --- salidas ----------------------------------------------------------------------------------


def estado_en(i: Issue, momento: date) -> str | None:
    """Estado de la issue al cierre del día `momento` (None si aún no existe)."""
    if i.creado > momento:
        return None
    estado = "por_hacer"
    for d, _, hasta in i.eventos:
        if d <= momento:
            estado = hasta
    return estado


def sprint_de(d: date, lista: list[dict]) -> str:
    for s in lista:
        if date.fromisoformat(s["inicio"]) <= d <= date.fromisoformat(s["inicio"]) + timedelta(days=SPRINT_DIAS - 1):
            return s["sprint"]
    return lista[-1]["sprint"]


def compromisos(issues: list[Issue], lista: list[dict], cap: dict[tuple[str, str], float]) -> list[dict]:
    """Lo que cada equipo compromete al inicio de cada sprint y si lo termina dentro del sprint.

    Compromete lo que lleva en curso (salvo lo bloqueado) más las issues que empieza en la primera
    semana del sprint, en orden, hasta su velocidad reciente (promedio de los tres sprints anteriores)
    por el factor de compromiso de la empresa. Lo que se suma después no cuenta como comprometido.
    """
    filas = []
    for industria, ind in INDUSTRIAS.items():
        for equipo in EQUIPOS:
            propias = [i for i in issues if i.industria == industria and i.equipo == equipo]
            historia = []
            for s in lista:
                inicio = date.fromisoformat(s["inicio"])
                fin = inicio + timedelta(days=SPRINT_DIAS - 1)
                if fin > CORTE:
                    break
                capacidad = cap[(industria, equipo)] * 10 * (1 - ind.soporte) / DIAS_POR_PUNTO
                velocidad = sum(historia[-3:]) / len(historia[-3:]) if historia else capacidad
                velocidad *= ind.compromiso
                arrastre = [i for i in propias if i.inicio and i.inicio < inicio and not (i.fin and i.fin < inicio)
                            and estado_en(i, inicio - timedelta(days=1)) != "bloqueado"]
                planificacion = inicio + timedelta(days=4)  # lo que arranca la primera semana se planificó
                nuevas = sorted((i for i in propias if i.inicio and inicio <= i.inicio <= planificacion),
                                key=lambda i: i.inicio)
                elegidas, total = [], 0
                for i in arrastre + nuevas:
                    if total + i.puntos > velocidad and elegidas:
                        break
                    elegidas.append(i)
                    total += i.puntos
                for i in elegidas:
                    filas.append({"sprint": s["sprint"], "industria": industria, "equipo": equipo,
                                  "proyecto": i.proyecto, "issue": i.clave, "puntos": i.puntos,
                                  "completada": int(bool(i.fin and i.fin <= fin))})
                historia.append(sum(i.puntos for i in propias if i.fin and inicio <= i.fin <= fin))
    return filas


def pronostico(rng: random.Random, issues: list[Issue]) -> tuple[list[dict], list[dict]]:
    filas, distribucion = [], []
    semanas = [lunes(CORTE) - timedelta(weeks=k) for k in range(VENTANA_THROUGHPUT, 0, -1)]
    for industria, ind in INDUSTRIAS.items():
        for p in ind.proyectos:
            propias = [i for i in issues if i.proyecto == p.codigo]
            pendientes = sum(1 for i in propias if not i.fin)
            hechas = [i.fin for i in propias if i.fin]
            base = {"proyecto": p.codigo, "industria": industria, "issues_pendientes": pendientes,
                    "fin_comprometido": p.fin.isoformat()}
            if not pendientes:
                termino = max(hechas)
                filas.append(base | {"estado": "Terminado", "throughput_semanal": "",
                                     "fecha_p50": termino.isoformat(), "fecha_p85": termino.isoformat(),
                                     "fecha_p95": termino.isoformat(), "atraso_p85_dias": (termino - p.fin).days})
                continue
            if p.inicio > CORTE:
                continue
            muestra = [sum(1 for f in hechas if s <= f < s + timedelta(days=7)) for s in semanas]
            if not any(muestra):
                muestra = [1]
            resultados = Counter()
            for _ in range(SIMULACIONES):
                restantes, semana = pendientes, 0
                while restantes > 0:
                    restantes -= rng.choice(muestra)
                    semana += 1
                resultados[semana] += 1
            orden = sorted(resultados.elements())

            def percentil(q: float, orden: list[int] = orden) -> date:
                return CORTE + timedelta(weeks=orden[min(len(orden) - 1, math.ceil(q * len(orden)) - 1)])

            p85 = percentil(0.85)
            filas.append(base | {"estado": "En curso", "throughput_semanal": round(sum(muestra) / len(muestra), 2),
                                 "fecha_p50": percentil(0.50).isoformat(), "fecha_p85": p85.isoformat(),
                                 "fecha_p95": percentil(0.95).isoformat(), "atraso_p85_dias": (p85 - p.fin).days})
            for semana, veces in sorted(resultados.items()):
                distribucion.append({"proyecto": p.codigo, "industria": industria,
                                     "semana_termino": (lunes(CORTE) + timedelta(weeks=semana)).isoformat(),
                                     "probabilidad": round(veces / SIMULACIONES, 4)})
    return filas, distribucion


def flujo_semanal(issues: list[Issue]) -> list[dict]:
    filas = []
    semana = INICIO
    while semana <= CORTE:
        cierre = min(semana + timedelta(days=6), CORTE)
        conteo, puntos = Counter(), Counter()
        for i in issues:
            estado = estado_en(i, cierre)
            if estado:
                clave = (i.industria, i.proyecto, i.equipo, estado)
                conteo[clave] += 1
                puntos[clave] += i.puntos
        for (industria, proyecto, equipo, estado), n in sorted(conteo.items()):
            filas.append({"semana": semana.isoformat(), "industria": industria, "proyecto": proyecto,
                          "equipo": equipo, "estado": estado, "issues": n,
                          "puntos": puntos[(industria, proyecto, equipo, estado)]})
        semana += timedelta(days=7)
    return filas


def generar(seed: int = SEMILLA) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    filas_personas, asignaciones = personas(rng)
    cap = capacidad_diaria(asignaciones)
    plan = planificar(cap)
    issues, epicas = backlog(rng, plan)
    pares = dependencias(rng, issues)
    worklogs = simular(rng, issues, asignaciones)
    lista_sprints = sprints()

    # Las épicas empiezan con su primera issue y terminan con la última, si todas terminaron.
    hijas = defaultdict(list)
    for i in issues:
        hijas[i.epica].append(i)
    for e in epicas:
        propias = hijas[e.clave]
        inicios = [i.inicio for i in propias if i.inicio]
        if inicios:
            e.inicio = min(inicios)
            e.eventos.append((e.inicio, "por_hacer", "en_curso"))
            if all(i.fin for i in propias):
                e.fin = max(i.fin for i in propias)
                e.eventos.append((e.fin, "en_curso", "hecho"))

    proyectos, tarifa = [], {}
    for f in filas_personas:
        tarifa[(f["industria"], f["equipo_principal"])] = f["tarifa_hora"]
    for industria, ind in INDUSTRIAS.items():
        for p in ind.proyectos:
            planificados = round(sum(plan[(p.codigo, e)] for e in EQUIPOS))
            horas = {e: plan[(p.codigo, e)] * DIAS_POR_PUNTO * HORAS_DIA for e in EQUIPOS}
            proyectos.append({
                "proyecto": p.codigo, "industria": industria, "nombre": p.nombre, "inicio": p.inicio.isoformat(),
                "fin_comprometido": p.fin.isoformat(), "puntos_planificados": planificados,
                "puntos_agregados": round(planificados * p.crecimiento[1]) if p.crecimiento else 0,
                "presupuesto_horas": round(sum(horas.values())),
                "presupuesto_monto": int(round(sum(h * tarifa[(industria, e)] for e, h in horas.items()), -6)),
            })

    filas_issues, transiciones = [], []
    for i in sorted(epicas + issues, key=lambda x: (x.proyecto, int(x.clave.split("-")[1]))):
        eventos = sorted(i.eventos, key=lambda e: e[0])
        por_dia = Counter()
        for d, desde, hasta in eventos:
            transiciones.append({"issue": i.clave, "industria": i.industria, "proyecto": i.proyecto,
                                 "equipo": i.equipo, "estado_desde": desde, "estado_hasta": hasta,
                                 "fecha_hora": hora(d, por_dia[d])})
            por_dia[d] += 1
        filas_issues.append({
            "issue": i.clave, "industria": i.industria, "proyecto": i.proyecto, "equipo": i.equipo,
            "tipo": i.tipo, "epica_padre": i.epica, "puntos": i.puntos if i.tipo != "epica" else "",
            "creado": i.creado.isoformat(), "fecha_inicio": i.inicio.isoformat() if i.inicio else "",
            "fecha_fin": i.fin.isoformat() if i.fin else "", "estado_al_corte": estado_en(i, CORTE),
            "dias_ciclo": (i.fin - i.inicio).days if i.fin and i.inicio and i.tipo != "epica" else "",
            "horas_bloqueado": round(i.horas_bloqueado) if i.tipo != "epica" else "",
            "sprint": sprint_de(i.fin or CORTE, lista_sprints) if i.inicio and i.tipo != "epica" else "",
        })

    filas_dependencias = []
    for bloqueante, bloqueado in pares:
        filas_dependencias.append({
            "issue_bloqueante": bloqueante.clave, "issue_bloqueado": bloqueado.clave,
            "industria": bloqueado.industria, "proyecto": bloqueado.proyecto,
            "equipo_bloqueante": bloqueante.equipo, "equipo_bloqueado": bloqueado.equipo,
            "creada": bloqueado.creado.isoformat(),
            "resuelta": bloqueante.fin.isoformat() if bloqueante.fin else "",
            "horas_bloqueado": round(bloqueado.horas_bloqueado / len(bloqueado.bloqueantes)),
        })

    capacidad = []
    semana = INICIO
    while semana <= CORTE:
        for industria in INDUSTRIAS:
            for equipo in EQUIPOS:
                capacidad.append({"semana": semana.isoformat(), "industria": industria, "equipo": equipo,
                                  "horas_capacidad": round(cap[(industria, equipo)] * HORAS_DIA * 5, 1)})
        semana += timedelta(days=7)

    termino, distribucion = pronostico(rng, issues)
    return {
        "empresas": [{"industria": k, "empresa": v.empresa, "orden": n} for n, (k, v) in enumerate(INDUSTRIAS.items(), 1)],
        "equipos": [{"equipo": e, "orden": n, "foco": FOCO[e]} for n, e in enumerate(EQUIPOS, 1)],
        "proyectos": proyectos, "personas_ti": filas_personas, "asignaciones": asignaciones,
        "sprints": lista_sprints, "issues": filas_issues, "transiciones": transiciones,
        "dependencias": filas_dependencias, "compromisos": compromisos(issues, lista_sprints, cap),
        "worklogs": worklogs, "capacidad_semanal": capacidad, "flujo_semanal": flujo_semanal(issues),
        "pronostico_termino": termino, "pronostico_distribucion": distribucion,
    }


def escribir(tablas: dict[str, list[dict]], carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, campos in ARCHIVOS.items():
        with (carpeta / f"{nombre}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
            w.writeheader()
            w.writerows(tablas[nombre])


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los datos sintéticos del reporte de proyectos de TI.")
    parser.add_argument("--seed", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=Path(__file__).parent / "proyectos-ti")
    args = parser.parse_args()
    tablas = generar(args.seed)
    escribir(tablas, args.salida)
    for nombre, filas in tablas.items():
        print(f"{nombre:24} {len(filas):7d} filas")


if __name__ == "__main__":
    main()
