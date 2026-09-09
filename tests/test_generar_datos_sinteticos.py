"""No valida ningún archivo `.pbix` (paso manual, ver docs/how-to-pbi.md) — valida
que el par presupuesto/real generado sea internamente consistente y reproducible.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCRIPT = DATA_DIR / "generar_datos_sinteticos.py"


def _generar(tmp_path: Path, seed: int = 42, meses: int = 6) -> tuple[list[dict], list[dict]]:
    salida_presupuesto = tmp_path / "presupuesto.csv"
    salida_real = tmp_path / "real.csv"
    subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--meses", str(meses),
            "--seed", str(seed),
            "--salida-presupuesto", str(salida_presupuesto),
            "--salida-real", str(salida_real),
        ],
        cwd=DATA_DIR.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    with salida_presupuesto.open(newline="", encoding="utf-8") as f:
        presupuesto = list(csv.DictReader(f))
    with salida_real.open(newline="", encoding="utf-8") as f:
        real = list(csv.DictReader(f))
    return presupuesto, real


def test_presupuesto_y_real_tienen_el_mismo_numero_de_filas(tmp_path):
    presupuesto, real = _generar(tmp_path)
    assert len(presupuesto) == len(real)
    assert len(presupuesto) > 0


def test_real_referencia_solo_claves_existentes_en_presupuesto(tmp_path):
    presupuesto, real = _generar(tmp_path)
    claves_presupuesto = {(f["anio"], f["mes"], f["centro_costo"], f["componente"]) for f in presupuesto}
    claves_real = {(f["anio"], f["mes"], f["centro_costo"], f["componente"]) for f in real}
    assert claves_real == claves_presupuesto


def test_montos_no_son_negativos(tmp_path):
    _, real = _generar(tmp_path)
    assert all(float(f["monto"]) >= 0 for f in real)


def test_misma_semilla_reproduce_los_mismos_datos(tmp_path):
    a_presupuesto, a_real = _generar(tmp_path / "a", seed=7)
    b_presupuesto, b_real = _generar(tmp_path / "b", seed=7)
    assert a_presupuesto == b_presupuesto
    assert a_real == b_real


def test_semillas_distintas_producen_reales_distintos(tmp_path):
    _, real_1 = _generar(tmp_path / "s1", seed=1)
    _, real_2 = _generar(tmp_path / "s2", seed=2)
    assert real_1 != real_2


def test_columnas_esperadas(tmp_path):
    presupuesto, real = _generar(tmp_path)
    columnas_esperadas = {"anio", "mes", "centro_costo", "componente", "grupo_cuenta", "monto"}
    assert set(presupuesto[0].keys()) == columnas_esperadas
    assert set(real[0].keys()) == columnas_esperadas


def test_incluye_una_linea_de_ingresos(tmp_path):
    presupuesto, _ = _generar(tmp_path)
    grupos = {f["grupo_cuenta"] for f in presupuesto}
    assert grupos == {"Ingresos", "Costos", "Gastos Operacionales"}


def test_ingresos_superan_a_costos_y_gastos_en_presupuesto(tmp_path):
    # No es un requisito duro del motor, pero sí de los datos de ejemplo: un
    # negocio sintético con Resultado Operacional negativo todos los meses no
    # sirve para demostrar el caso "ok" del semáforo.
    presupuesto, _ = _generar(tmp_path, meses=1)
    por_grupo = {}
    for f in presupuesto:
        por_grupo[f["grupo_cuenta"]] = por_grupo.get(f["grupo_cuenta"], 0.0) + float(f["monto"])
    resultado_operacional = (
        por_grupo["Ingresos"] - por_grupo["Costos"] - por_grupo["Gastos Operacionales"]
    )
    assert resultado_operacional > 0
