"""No valida el contenido de datos.html (eso se revisa a mano en el navegador) --
valida que data/ejemplos-web.json tenga la forma que datos.js espera: las 3
semillas, los campos por fila, y que el join no haya perdido ninguna clave de
presupuesto (misma completitud de grilla que el motor real).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCRIPT = DATA_DIR / "exportar_ejemplos_web.py"
SEMILLAS_ESPERADAS = {"42", "7", "123"}
CAMPOS_ESPERADOS = {
    "anio", "mes", "centro_costo", "componente", "grupo_cuenta",
    "monto_presupuesto", "monto_real",
}


def _generar(tmp_path: Path) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    ruta_salida = tmp_path / "ejemplos-web.json"
    subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=DATA_DIR.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    # El script escribe siempre en data/ejemplos-web.json (sin flag de salida,
    # a diferencia de generar_datos_sinteticos.py) -- lo copiamos a tmp_path
    # para no depender del estado dejado en el repo entre tests.
    generado = DATA_DIR / "ejemplos-web.json"
    ruta_salida.write_text(generado.read_text(encoding="utf-8"), encoding="utf-8")
    return json.loads(ruta_salida.read_text(encoding="utf-8"))


def test_incluye_las_tres_semillas_esperadas(tmp_path):
    ejemplos = _generar(tmp_path)
    assert set(ejemplos.keys()) == SEMILLAS_ESPERADAS


def test_cada_fila_tiene_los_campos_esperados(tmp_path):
    ejemplos = _generar(tmp_path)
    for filas in ejemplos.values():
        assert len(filas) > 0
        assert set(filas[0].keys()) == CAMPOS_ESPERADOS


def test_no_pierde_filas_de_presupuesto_en_el_join(tmp_path):
    ejemplos = _generar(tmp_path)
    for filas in ejemplos.values():
        # 6 centros de costo x 3 componentes x 12 meses (ver CENTROS en
        # generar_datos_sinteticos.py) -- si el join perdiera una clave de
        # presupuesto, este conteo bajaría.
        assert len(filas) == 6 * 3 * 12


def test_montos_no_son_negativos(tmp_path):
    ejemplos = _generar(tmp_path)
    for filas in ejemplos.values():
        assert all(f["monto_presupuesto"] >= 0 and f["monto_real"] >= 0 for f in filas)


def test_misma_semilla_reproduce_los_mismos_datos(tmp_path):
    a = _generar(tmp_path / "a")
    b = _generar(tmp_path / "b")
    assert a == b
