"""Genera data/contratistas/: mantenimiento y estados de pago de contratistas de tres empresas ficticias.

Son las mismas tres industrias y nueve sedes de los otros reportes de la vitrina (Manufactura,
Energía y Salud). Cada empresa externaliza el mantenimiento de sus activos en cuatro contratistas
y les paga unos CLP 200 millones al mes. Simulamos 2025 y 2026:

- **Órdenes de trabajo (OT):** las preventivas salen de un plan por activo (mensual, bimestral o
  trimestral según criticidad) y los contratistas riesgosos cumplen menos y más tarde; las
  correctivas son fallas con tasa 1/MTBF del tipo de activo, con tiempo de respuesta y de
  reparación (MTTR). Es la forma de una extracción de OT de SAP PM.
- **Estados de pago (EP):** cada mes el contratista cobra las OT que cerró, a la tarifa del
  contrato. Sobre eso inyectamos cinco anomalías etiquetadas: cobro sin OT, OT abierta, cantidad
  sobre lo ejecutado, precio sobre la tarifa y doble cobro. Uno o dos contratistas por empresa
  concentran la mayoría.
- **Control:** hasta junio de 2025 nadie cruza el EP con las OT y las anomalías llegan a ~8,5% de
  lo facturado, con un mes de pico en Energía. Desde julio de 2025 el control rechaza lo
  observado antes de pagar y las anomalías bajan a ~3%.
- **Observaciones:** no las escribe el generador: salen de sql/reglas_auditoria.sql, que
  sql/auditar.py corre sobre sqlite3. Los tests exigen que las reglas encuentren exactamente las
  anomalías inyectadas.

Montos en CLP. Reproducible (semilla fija). Ningún dato real de ningún empleador.

Uso:
    python data/generar_contratistas.py
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

SEMILLA = 42
INICIO = date(2025, 1, 1)
FIN = date(2026, 12, 31)
INICIO_CONTROL = date(2025, 7, 1)
FACTURACION_MENSUAL = 200_000_000  # CLP por empresa, sin contar lo que inflan las anomalías
TASA_ANOMALIA = {"pre": 0.085, "post": 0.03}  # monto observado / facturación legítima del mes
PICOS = {("Energia", date(2025, 3, 1)): 0.15}  # el mes que destapa el problema
PESO_RIESGOSOS = 0.78  # fracción de lo observado que generan los contratistas riesgosos
PESOS_ANOMALIA = {"sin_ot": 0.25, "sobre_cantidad": 0.25, "sobre_precio": 0.20, "duplicada": 0.20,
                  "ot_abierta": 0.10}
FRECUENCIA_MESES = {"A": 1, "B": 2, "C": 3}  # mantención preventiva según criticidad
REPARACION_HORAS = {"A": 10.0, "B": 7.0, "C": 4.0}  # media de la reparación correctiva
SERVICIO_PREVENTIVO, SERVICIO_CORRECTIVO = "Mantención preventiva", "Reparación correctiva"


@dataclass(frozen=True)
class TipoActivo:
    nombre: str
    por_sede: int
    criticidad: str
    mtbf_dias: int  # objetivo: días promedio entre fallas de un activo
    factor_precio: float  # costo relativo del servicio
    contratista: str
    riesgoso: bool


@dataclass(frozen=True)
class Industria:
    empresa: str
    sedes: tuple[str, ...]
    tipos: tuple[TipoActivo, ...]


INDUSTRIAS = {
    "Manufactura": Industria(
        empresa="Manufacturas Ejemplo S.A.",
        sedes=("Santiago", "Concepción", "Antofagasta"),
        tipos=(
            TipoActivo("Línea de envasado", 4, "A", 45, 1.4, "Automatización Ejemplo SpA", False),
            TipoActivo("Compresor", 6, "B", 90, 0.8, "Aire Comprimido Ejemplo Ltda.", False),
            TipoActivo("Caldera", 2, "A", 120, 1.6, "Térmica Ejemplo Ltda.", False),
            TipoActivo("Montacargas", 10, "C", 60, 0.5, "Grúas y Equipos Ejemplo Ltda.", True),
        ),
    ),
    "Energia": Industria(
        empresa="Energía Ejemplo S.A.",
        sedes=("Zona Norte", "Zona Centro", "Zona Sur"),
        tipos=(
            TipoActivo("Estanque granel", 8, "A", 180, 1.0, "Montajes Ejemplo Norte Ltda.", True),
            TipoActivo("Red de distribución", 6, "B", 60, 1.2, "Redes Ejemplo SpA", False),
            TipoActivo("Subestación", 2, "A", 240, 2.5, "Eléctrica Ejemplo S.A.", False),
            TipoActivo("Válvulas y reguladores", 10, "C", 90, 0.4, "Servicios Ejemplo Sur Ltda.", True),
        ),
    ),
    "Salud": Industria(
        empresa="Red Asistencial Ejemplo S.A.",
        sedes=("Clínica Oriente", "Clínica Centro", "Clínica Poniente"),
        tipos=(
            TipoActivo("Climatización", 8, "B", 90, 0.8, "Clima Ejemplo Ltda.", True),
            TipoActivo("Equipo clínico", 12, "A", 120, 1.2, "Biomédica Ejemplo SpA", False),
            TipoActivo("Grupo electrógeno", 2, "A", 200, 1.5, "Respaldo Energético Ejemplo Ltda.", False),
            TipoActivo("Ascensor", 4, "B", 75, 0.9, "Ascensores Ejemplo S.A.", False),
        ),
    ),
}

ARCHIVOS = {
    "sedes": ["sede", "industria", "empresa", "orden"],
    "contratistas": ["id_contratista", "contratista", "industria", "especialidad", "perfil"],
    "activos": ["id_activo", "sede", "tipo_activo", "criticidad", "mtbf_objetivo_dias", "id_contratista"],
    "tarifas": ["id_contratista", "servicio", "unidad", "precio_unitario"],
    "ordenes_trabajo": ["id_ot", "id_activo", "sede", "id_contratista", "clase", "servicio", "fecha_programada",
                        "fecha_inicio", "fecha_cierre", "estado", "horas_ejecutadas", "cantidad_ejecutada",
                        "horas_detencion"],
    "estados_pago": ["id_linea", "periodo", "id_contratista", "sede", "id_ot", "servicio", "cantidad_cobrada",
                     "precio_cobrado", "monto", "anomalia_inyectada"],
    "observaciones": ["id_linea", "periodo", "id_contratista", "sede", "id_ot", "regla", "monto_observado",
                      "resolucion"],
}

_spec = importlib.util.spec_from_file_location("auditar", Path(__file__).resolve().parent.parent / "sql" / "auditar.py")
auditar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auditar)


def mes(d: date) -> date:
    return d.replace(day=1)


def sumar_meses(d: date, n: int) -> date:
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, min(d.day, 28))


def meses() -> list[date]:
    salida, m = [], INICIO
    while m <= FIN:
        salida.append(m)
        m = sumar_meses(m, 1)
    return salida


def elegir(rng: random.Random, pesos: dict[str, float]) -> str:
    return rng.choices(list(pesos), weights=list(pesos.values()))[0]


def media_horas(rng: random.Random, media: float) -> float:
    """Duración lognormal con la media pedida (cv ~0,6), redondeada a media hora."""
    sigma = 0.55
    valor = rng.lognormvariate(math.log(media) - sigma**2 / 2, sigma)
    return max(0.5, round(valor * 2) / 2)


def dimensiones() -> tuple[list[dict], list[dict], list[dict], dict[str, TipoActivo]]:
    sedes, contratistas, activos, tipo_de = [], [], [], {}
    orden = 0
    for n_ind, (industria, ind) in enumerate(INDUSTRIAS.items()):
        for sede in ind.sedes:
            orden += 1
            sedes.append({"sede": sede, "industria": industria, "empresa": ind.empresa, "orden": orden})
        for n_tipo, tipo in enumerate(ind.tipos, start=1):
            id_c = f"C{n_ind + 1}{n_tipo}"
            tipo_de[id_c] = tipo
            contratistas.append({"id_contratista": id_c, "contratista": tipo.contratista, "industria": industria,
                                 "especialidad": tipo.nombre, "perfil": "Riesgoso" if tipo.riesgoso else "Limpio"})
            for sede in ind.sedes:
                for k in range(1, tipo.por_sede + 1):
                    activos.append({"id_activo": f"A-{len(activos) + 1:04d}", "sede": sede,
                                    "tipo_activo": tipo.nombre, "criticidad": tipo.criticidad,
                                    "mtbf_objetivo_dias": tipo.mtbf_dias, "id_contratista": id_c})
    return sedes, contratistas, activos, tipo_de


def ordenes(rng: random.Random, activos: list[dict], tipo_de: dict[str, TipoActivo]) -> list[dict]:
    ots = []

    def nueva(activo: dict, **campos) -> None:
        ots.append({"id_ot": f"OT-{len(ots) + 1:06d}", "id_activo": activo["id_activo"], "sede": activo["sede"],
                    "id_contratista": activo["id_contratista"], **campos})

    for activo in activos:
        tipo = tipo_de[activo["id_contratista"]]
        # Preventivas: cumplimiento a tiempo, atraso o nunca ejecutada (queda abierta en el backlog).
        a_tiempo, atrasada = (0.70, 0.22) if tipo.riesgoso else (0.92, 0.06)
        frecuencia = FRECUENCIA_MESES[tipo.criticidad]
        programada = date(2025, rng.randint(1, frecuencia), rng.randint(1, 28))
        while programada <= FIN:
            r = rng.random()
            campos = {"clase": "Preventiva", "servicio": SERVICIO_PREVENTIVO,
                      "fecha_programada": programada.isoformat()}
            if r < a_tiempo + atrasada:
                inicio = programada + timedelta(days=rng.randint(0, 6) if r < a_tiempo else rng.randint(8, 40))
                horas = media_horas(rng, 3.0 if tipo.criticidad == "C" else 5.0)
                if inicio <= FIN:
                    campos |= {"fecha_inicio": inicio.isoformat(), "fecha_cierre": inicio.isoformat(),
                               "estado": "Cerrada", "horas_ejecutadas": horas, "cantidad_ejecutada": 1,
                               "horas_detencion": 0}
            nueva(activo, **({"fecha_inicio": "", "fecha_cierre": "", "estado": "Abierta", "horas_ejecutadas": 0,
                              "cantidad_ejecutada": 0, "horas_detencion": 0} | campos))
            programada = sumar_meses(programada, frecuencia)
        # Correctivas: fallas con tasa 1/MTBF; respuesta más lenta y reparación más larga si es riesgoso.
        def dia(x: float) -> date:  # días (con fracción) desde INICIO → fecha
            return INICIO + timedelta(days=int(x))

        falla = rng.expovariate(1 / tipo.mtbf_dias)
        while dia(falla) <= FIN:
            respuesta = rng.uniform(12, 48) if tipo.riesgoso else rng.uniform(2, 12)
            horas = media_horas(rng, REPARACION_HORAS[tipo.criticidad] * (1.3 if tipo.riesgoso else 1.0))
            inicio = falla + respuesta / 24
            cierre = dia(inicio + horas / 24)
            campos = {"clase": "Correctiva", "servicio": SERVICIO_CORRECTIVO, "fecha_programada": dia(falla).isoformat(),
                      "fecha_inicio": dia(inicio).isoformat(), "fecha_cierre": cierre.isoformat(),
                      "estado": "Cerrada", "horas_ejecutadas": horas, "cantidad_ejecutada": horas,
                      "horas_detencion": round(respuesta + horas, 1)}
            if cierre > FIN:
                campos |= {"fecha_cierre": "", "estado": "Abierta", "horas_ejecutadas": 0, "cantidad_ejecutada": 0}
            nueva(activo, **campos)
            falla += max(1.0, rng.expovariate(1 / tipo.mtbf_dias))
    return ots


def tarifas(ots: list[dict], contratistas: list[dict], tipo_de: dict[str, TipoActivo]) -> list[dict]:
    """Precio base por tipo de activo, escalado para que cada empresa facture ~FACTURACION_MENSUAL."""
    base = {SERVICIO_PREVENTIVO: 1.0, SERVICIO_CORRECTIVO: 0.15}  # una visita ≈ 7 horas de reparación
    industria = {c["id_contratista"]: c["industria"] for c in contratistas}
    volumen = {i: 0.0 for i in INDUSTRIAS}
    for ot in ots:
        if ot["estado"] == "Cerrada":
            volumen[industria[ot["id_contratista"]]] += (
                base[ot["servicio"]] * tipo_de[ot["id_contratista"]].factor_precio * float(ot["cantidad_ejecutada"]))
    escala = {i: FACTURACION_MENSUAL * len(meses()) / v for i, v in volumen.items()}
    filas = []
    for c in contratistas:
        tipo = tipo_de[c["id_contratista"]]
        for servicio, unidad in ((SERVICIO_PREVENTIVO, "visita"), (SERVICIO_CORRECTIVO, "hora")):
            precio = base[servicio] * tipo.factor_precio * escala[c["industria"]]
            filas.append({"id_contratista": c["id_contratista"], "servicio": servicio, "unidad": unidad,
                          "precio_unitario": int(round(precio, -3))})
    return filas


def linea(periodo: date, id_c: str, sede: str, id_ot: str, servicio: str, cantidad: float, precio: int,
          anomalia: str = "") -> dict:
    return {"periodo": periodo.isoformat(), "id_contratista": id_c, "sede": sede, "id_ot": id_ot,
            "servicio": servicio, "cantidad_cobrada": cantidad, "precio_cobrado": precio,
            "monto": round(cantidad * precio), "anomalia_inyectada": anomalia}


def estados_pago(rng: random.Random, ots: list[dict], contratistas: list[dict],
                 tarifa: dict[tuple[str, str], int]) -> list[dict]:
    industria = {c["id_contratista"]: c["industria"] for c in contratistas}
    riesgoso = {c["id_contratista"]: c["perfil"] == "Riesgoso" for c in contratistas}
    sedes_de = {i: ind.sedes for i, ind in INDUSTRIAS.items()}
    abiertas = {}  # OT que nunca se cierran: candidatas a cobro anticipado
    for ot in ots:
        if ot["estado"] == "Abierta" and ot["fecha_programada"] < "2026-10-01":
            abiertas.setdefault(ot["id_contratista"], []).append(ot)
    for lista in abiertas.values():
        rng.shuffle(lista)
    por_mes = {}
    for ot in ots:
        if ot["estado"] == "Cerrada":
            por_mes.setdefault(mes(date.fromisoformat(ot["fecha_cierre"])), []).append(ot)

    lineas, falsas = [], 0
    for periodo in meses():
        del_mes = [linea(periodo, ot["id_contratista"], ot["sede"], ot["id_ot"], ot["servicio"],
                         float(ot["cantidad_ejecutada"]), tarifa[(ot["id_contratista"], ot["servicio"])])
                   for ot in sorted(por_mes.get(periodo, []), key=lambda o: (o["id_contratista"], o["id_ot"]))]
        legitimo = {i: 0 for i in INDUSTRIAS}
        for f in del_mes:
            legitimo[industria[f["id_contratista"]]] += f["monto"]
        extra = []
        for ind in INDUSTRIAS:
            tasa = PICOS.get((ind, periodo), TASA_ANOMALIA["pre" if periodo < INICIO_CONTROL else "post"])
            presupuesto = legitimo[ind] * tasa * rng.uniform(0.75, 1.25)
            ids = [c["id_contratista"] for c in contratistas if c["industria"] == ind]
            malos = [i for i in ids if riesgoso[i]]
            buenos = [i for i in ids if not riesgoso[i]]
            peso = {i: PESO_RIESGOSOS / len(malos) for i in malos}
            peso |= {i: (1 - PESO_RIESGOSOS) / len(buenos) for i in buenos}
            desde = sumar_meses(periodo, -2).isoformat()
            previas_de = {i: [f for f in lineas if f["id_contratista"] == i and not f["anomalia_inyectada"]
                              and f["periodo"] >= desde] for i in ids}
            acumulado = 0.0
            while acumulado < presupuesto:
                id_c = elegir(rng, peso)
                propias = [f for f in del_mes if f["id_contratista"] == id_c]
                previas = previas_de[id_c]
                tipo = elegir(rng, PESOS_ANOMALIA)
                limpias = [f for f in propias if not f["anomalia_inyectada"]]
                if tipo in ("sobre_cantidad", "sobre_precio") and not limpias:
                    tipo = "sin_ot"
                if tipo == "duplicada" and not (previas or limpias):
                    tipo = "sin_ot"
                corte = sumar_meses(periodo, 1).isoformat()
                vencidas = [ot for ot in abiertas.get(id_c, []) if ot["fecha_programada"] < corte]
                if tipo == "ot_abierta" and not vencidas:
                    tipo = "sin_ot"
                if tipo == "sobre_cantidad":
                    f = rng.choice(limpias)
                    nueva = (f["cantidad_cobrada"] + 1 if f["servicio"] == SERVICIO_PREVENTIVO
                             else round(f["cantidad_cobrada"] * rng.uniform(1.3, 1.9) * 2) / 2 + 0.5)
                    acumulado += (nueva - f["cantidad_cobrada"]) * f["precio_cobrado"]
                    f.update(linea(periodo, id_c, f["sede"], f["id_ot"], f["servicio"], nueva,
                                   f["precio_cobrado"], tipo))
                elif tipo == "sobre_precio":
                    f = rng.choice(limpias)
                    nuevo = int(round(f["precio_cobrado"] * rng.uniform(1.10, 1.30), -3))
                    acumulado += (nuevo - f["precio_cobrado"]) * f["cantidad_cobrada"]
                    f.update(linea(periodo, id_c, f["sede"], f["id_ot"], f["servicio"], f["cantidad_cobrada"],
                                   nuevo, tipo))
                elif tipo == "duplicada":
                    f = rng.choice(previas or limpias)
                    if f in previas:
                        previas.remove(f)
                    nueva = linea(periodo, id_c, f["sede"], f["id_ot"], f["servicio"], f["cantidad_cobrada"],
                                  f["precio_cobrado"], tipo)
                    acumulado += nueva["monto"]
                    extra.append(nueva)
                elif tipo == "ot_abierta":
                    ot = vencidas[-1]
                    abiertas[id_c].remove(ot)
                    cantidad = 1.0 if ot["servicio"] == SERVICIO_PREVENTIVO else media_horas(rng, 8.0)
                    nueva = linea(periodo, id_c, ot["sede"], ot["id_ot"], ot["servicio"], cantidad,
                                  tarifa[(id_c, ot["servicio"])], tipo)
                    acumulado += nueva["monto"]
                    extra.append(nueva)
                else:  # sin_ot: sin referencia o con un número de OT que no existe
                    servicio = rng.choice((SERVICIO_PREVENTIVO, SERVICIO_CORRECTIVO))
                    cantidad = 1.0 if servicio == SERVICIO_PREVENTIVO else media_horas(rng, 8.0)
                    id_ot = ""
                    if rng.random() < 0.3:
                        falsas += 1
                        id_ot = f"OT-{900000 + falsas:06d}"
                    nueva = linea(periodo, id_c, rng.choice(sedes_de[industria[id_c]]), id_ot, servicio,
                                  cantidad, tarifa[(id_c, servicio)], "sin_ot")
                    acumulado += nueva["monto"]
                    extra.append(nueva)
        lineas.extend(del_mes + extra)
    for n, f in enumerate(lineas, start=1):
        f["id_linea"] = f"EP-{n:06d}"
    return lineas


def generar(seed: int = SEMILLA) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    sedes, contratistas, activos, tipo_de = dimensiones()
    ots = ordenes(rng, activos, tipo_de)
    precios = tarifas(ots, contratistas, tipo_de)
    tarifa = {(t["id_contratista"], t["servicio"]): t["precio_unitario"] for t in precios}
    lineas = estados_pago(rng, ots, contratistas, tarifa)
    tablas = {"sedes": sedes, "contratistas": contratistas, "activos": activos, "tarifas": precios,
              "ordenes_trabajo": ots, "estados_pago": lineas}
    tablas["observaciones"] = auditar.auditar(tablas)
    return tablas


def escribir(tablas: dict[str, list[dict]], carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, campos in ARCHIVOS.items():
        with (carpeta / f"{nombre}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
            w.writeheader()
            w.writerows(tablas[nombre])


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los datos sintéticos del reporte de contratistas.")
    parser.add_argument("--seed", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=Path(__file__).parent / "contratistas")
    args = parser.parse_args()
    tablas = generar(args.seed)
    escribir(tablas, args.salida)
    for nombre, filas in tablas.items():
        print(f"{nombre:16} {len(filas):7d} filas")


if __name__ == "__main__":
    main()
