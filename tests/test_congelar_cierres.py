r"""Tests de la migracion controlada de cierres antiguos (FASE 7).

scripts/congelar_establecimiento_en_cierres.py completa, una sola vez y a mano,
los cuatro datos del establecimiento en los cierres creados antes de que el
cierre los congelara (columnas *_snapshot a NULL).

Valores FICTICIOS. Nunca datos reales.

    .venv\Scripts\python.exe -m unittest discover -s tests -v
"""

import importlib.util
import io
import re
import sqlite3
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_cierre import DIA_A, DIA_B, EMPRESA, SNAPSHOTS  # noqa: E402
from test_pdf import BasePDF, lineas_pdf  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "congelar_establecimiento_en_cierres.py"
OTRA = ("Otra Titular Ficticia", "NIF-PRUEBA-2", "Otro Bar de Prueba", "Avenida Inventada 99")


def cargar_script():
    spec = importlib.util.spec_from_file_location("congelar", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class BaseMigracion(BasePDF):
    """Un cierre 'antiguo' (sin datos congelados) del dia A, como C-2026-000001."""

    def setUp(self):
        super().setUp()
        self.script = cargar_script()
        self.caso_preproduccion()
        self.cerrar(DIA_A)
        conn = self.conexion()
        # Simula un cierre anterior a la congelacion: columnas a NULL. En la
        # aplicacion no existe ningun UPDATE de daily_close; aqui es el montaje.
        conn.execute("UPDATE daily_close SET " + ", ".join(f"{c} = NULL" for c in SNAPSHOTS))
        conn.commit()

    def fila(self, fecha=DIA_A):
        return dict(self.conexion().execute(
            "SELECT * FROM daily_close WHERE business_date = ?", (fecha,)).fetchone())

    def ejecutar(self, *argv):
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = self.script.main(list(argv))
        return codigo, salida.getvalue()


class TestMigracionControlada(BaseMigracion):

    def test_sin_aplicar_solo_informa_y_no_escribe(self):
        antes = self.hash_base()
        codigo, salida = self.ejecutar()
        self.assertEqual(codigo, 0)
        self.assertIn("Pendientes (datos del establecimiento) 1 cierre(s): C-2026-000001", salida)
        self.assertEqual(self.hash_base(), antes)

    def test_aplicar_congela_la_configuracion_actual(self):
        from app import cierre
        codigo, salida = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 0)
        self.assertIn("Completados (datos del establecimiento) 1 cierre(s)", salida)
        self.assertEqual(self.congelados(cierre.obtener_cierre(DIA_A)), EMPRESA)

    def test_la_salida_no_muestra_los_datos_del_establecimiento(self):
        for argv in ((), ("--aplicar",), ("--aplicar",)):
            _, salida = self.ejecutar(*argv)
            for valor in EMPRESA:
                with self.subTest(argv=argv, valor=valor):
                    self.assertNotIn(valor, salida)

    def test_solo_cambian_las_cuatro_columnas(self):
        antes = self.fila()
        items_antes = list(map(tuple, self.conexion().execute("SELECT * FROM daily_close_item")))
        self.ejecutar("--aplicar")
        despues = self.fila()
        cambiadas = {k for k in antes if antes[k] != despues[k]}
        self.assertEqual(cambiadas, set(SNAPSHOTS))
        self.assertEqual(
            list(map(tuple, self.conexion().execute("SELECT * FROM daily_close_item"))),
            items_antes)

    def test_es_idempotente_y_no_recongela_con_otra_configuracion(self):
        from app import cierre, establecimiento
        self.ejecutar("--aplicar")
        establecimiento.guardar(*OTRA)
        codigo, salida = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 0)
        self.assertIn("No hay cierres pendientes", salida)
        self.assertEqual(self.congelados(cierre.obtener_cierre(DIA_A)), EMPRESA)

    def test_no_toca_un_cierre_que_ya_tenia_los_datos_congelados(self):
        from app import cierre, establecimiento
        establecimiento.guardar(*OTRA)
        self.vender([self.linea(self.id_cafe, "Café", 140, 1)], datetime(2026, 9, 18, 9, 0))
        self.cerrar(DIA_B)                     # congelado con OTRA
        establecimiento.guardar(*EMPRESA)
        self.ejecutar("--aplicar")
        self.assertEqual(self.congelados(cierre.obtener_cierre(DIA_A)), EMPRESA)
        self.assertEqual(self.congelados(cierre.obtener_cierre(DIA_B)), OTRA)

    def test_sin_configuracion_completa_no_escribe_nada(self):
        conn = self.conexion()
        conn.execute("UPDATE establishment SET trade_name = NULL")
        conn.commit()
        antes = self.hash_base()
        codigo, salida = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 1)
        self.assertIn("Faltan datos del establecimiento", salida)
        self.assertEqual(self.hash_base(), antes)

    def test_un_cierre_parcial_detiene_todo(self):
        conn = self.conexion()
        conn.execute("UPDATE daily_close SET tax_id_snapshot = 'NIF-PRUEBA-X'")
        conn.commit()
        antes = self.hash_base()
        codigo, salida = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 1)
        self.assertIn("C-2026-000001", salida)
        self.assertEqual(self.hash_base(), antes)

    def test_antes_el_pdf_se_rechaza_y_despues_se_genera_estable(self):
        from app import establecimiento, pdf_cierre
        with self.assertRaises(pdf_cierre.CierreIncompleto):
            self.generar(DIA_A)
        self.ejecutar("--aplicar")
        pdf = self.generar(DIA_A).read_bytes()
        self.assertEqual(lineas_pdf(pdf)[0], EMPRESA[2])
        establecimiento.guardar(*OTRA)
        self.assertEqual(self.generar(DIA_A).read_bytes(), pdf)

    def test_base_fase6_sin_columnas_sin_aplicar_no_cambia_ni_un_byte(self):
        """Base FASE 6 sin columnas snapshot -> ejecutar sin --aplicar ->
        SHA-256 de SQLite identico antes/despues."""
        conn = sqlite3.connect(self.ruta)
        for c in SNAPSHOTS:
            conn.execute(f"ALTER TABLE daily_close DROP COLUMN {c}")
        conn.commit(); conn.close()

        antes = self.hash_base()
        codigo, salida = self.ejecutar()
        despues = self.hash_base()

        self.assertEqual(codigo, 0)
        self.assertEqual(despues, antes)
        self.assertIn("Faltan las columnas holder_name_snapshot", salida)
        self.assertIn("No se han creado", salida)
        self.assertIn("Pendientes (datos del establecimiento) 1 cierre(s): C-2026-000001", salida)
        conn = sqlite3.connect(self.ruta)
        columnas = {f[1] for f in conn.execute("PRAGMA table_info(daily_close)")}
        conn.close()
        self.assertFalse(columnas & set(SNAPSHOTS), "sin --aplicar no se crean columnas")

    def test_migra_una_base_sin_las_columnas(self):
        """Una base de la FASE 6 (sin *_snapshot) recibe las columnas y se completa."""
        from app import cierre
        conn = sqlite3.connect(self.ruta)
        for c in SNAPSHOTS:
            conn.execute(f"ALTER TABLE daily_close DROP COLUMN {c}")
        conn.commit(); conn.close()
        codigo, _ = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 0)
        self.assertEqual(self.congelados(cierre.obtener_cierre(DIA_A)), EMPRESA)


class TestUnicaEscrituraSobreCierres(unittest.TestCase):

    def test_solo_el_script_de_migracion_actualiza_cierres_y_solo_lo_congelado(self):
        """Fuera de app/ (que no tiene ninguno), los unicos UPDATE de daily_close
        del repositorio son los del script de migracion: uno para los datos del
        establecimiento (*_snapshot) y otro para el IVA (vat_*)."""
        patron = re.compile(r"(DELETE\s+FROM|UPDATE)\s+(daily_close|daily_close_item)\b",
                            re.IGNORECASE)
        encontrados = sorted(
            str(a.relative_to(RAIZ))
            for carpeta in ("app", "scripts")
            for a in (RAIZ / carpeta).rglob("*.py")
            if patron.search(a.read_text(encoding="utf-8")))
        self.assertEqual(encontrados, [str(Path("scripts/congelar_establecimiento_en_cierres.py"))])

        modulo = cargar_script()
        from app.cierre import SNAPSHOT_ESTABLECIMIENTO
        self.assertEqual(tuple(SNAPSHOT_ESTABLECIMIENTO), SNAPSHOTS)
        texto = SCRIPT.read_text(encoding="utf-8")
        self.assertNotRegex(texto, r"DELETE\s+FROM")
        self.assertIn("WHERE id = ? AND {_todas_nulas(columnas)}", texto)
        self.assertTrue(hasattr(modulo, "completar"))

        # Dos UPDATE: uno por grupo, cada uno solo sobre sus columnas.
        self.assertEqual(texto.count("UPDATE daily_close SET"), 2)
        self.assertIn('f"UPDATE daily_close SET {asignacion}"', texto)
        self.assertIn('"UPDATE daily_close SET vat_rate_percent = ?, vat_base_cents = ?,"', texto)
        self.assertIn('f" vat_cents = ? WHERE id = ? AND {_todas_nulas(SNAPSHOT_IVA)}"', texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
