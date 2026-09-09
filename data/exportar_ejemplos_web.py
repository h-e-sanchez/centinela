"""Genera data/ejemplos-web.json: 2-3 corridas reales del motor, para que
datos.html las explore en el navegador.

No reimplementa el generador en JavaScript a propósito: el RNG de JS no
reproduce `random.Random` de Python, así que "generar en vivo" con una semilla
en el navegador daría números *distintos* al CLI — engañoso para un repo cuyo
punto es mostrar exactamente lo que calcula el motor real. En cambio, la
clasificación ok/alerta/crítica y los subtotales por grupo sí se reimplementan
en `datos.js`, porque son aritmética simple (comparación de umbrales, sumas) —
eso sí es seguro de espejar entre Python y JS sin que diverjan con el tiempo.

Reutiliza generar_presupuesto/generar_real tal cual (no los reimplementa) —
una sola fuente de verdad para la generación de datos.

Uso:
    python data/exportar_ejemplos_web.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

# Import directo del script hermano -- al ejecutar "python data/exportar_ejemplos_web.py",
# Python agrega automáticamente el directorio del script (data/) a sys.path[0], así que
# no hace falta manipular sys.path a mano.
from generar_datos_sinteticos import generar_presupuesto, generar_real

SEMILLAS = [42, 7, 123]
ANIO = 2026
MESES = 12


def combinar(presupuesto: list[dict], real: list[dict]) -> list[dict]:
    """Cruza presupuesto y real por clave -- mismo criterio de completitud de
    grilla que motor.calcular_desviaciones: toda clave de presupuesto aparece,
    con monto_real=0 si no hay dato real para ella.
    """
    real_por_clave = {
        (f["anio"], f["mes"], f["centro_costo"], f["componente"]): f["monto"] for f in real
    }
    filas = []
    for f in presupuesto:
        clave = (f["anio"], f["mes"], f["centro_costo"], f["componente"])
        filas.append({
            "anio": f["anio"],
            "mes": f["mes"],
            "centro_costo": f["centro_costo"],
            "componente": f["componente"],
            "grupo_cuenta": f["grupo_cuenta"],
            "monto_presupuesto": f["monto"],
            "monto_real": real_por_clave.get(clave, 0.0),
        })
    return filas


def main() -> None:
    ejemplos = {}
    for seed in SEMILLAS:
        rng_presupuesto = random.Random(seed)
        presupuesto = generar_presupuesto(ANIO, MESES, rng_presupuesto)
        rng_real = random.Random(seed + 1)
        real = generar_real(presupuesto, rng_real)
        ejemplos[str(seed)] = combinar(presupuesto, real)

    ruta = Path(__file__).resolve().parent / "ejemplos-web.json"
    ruta.write_text(json.dumps(ejemplos, ensure_ascii=False), encoding="utf-8")
    total_filas = sum(len(v) for v in ejemplos.values())
    print(f"Escrito {ruta} — {len(ejemplos)} ejemplos, {total_filas} filas en total.")


if __name__ == "__main__":
    main()
