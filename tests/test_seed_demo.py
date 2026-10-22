r"""Tests de los datos de demostracion (rama tfc).

scripts/seed_demo.py crea una base de demostracion con datos TOTALMENTE
FICTICIOS para poder ensenar la aplicacion sin usar datos reales.

    .venv\Scripts\python.exe -m unittest discover -s tests -v

Cada test usa una base temporal propia: ni la base real ni data/demo.sqlite se
tocan.
"""

import importlib.util
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def cargar_seed():
    """Importa el script por ruta: vive en scripts/, no es un paquete."""
    ruta = RAIZ / "scripts" / "seed_demo.py"
    spec = importlib.util.spec_from_file_location("seed_demo", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class BaseSeed(unittest.TestCase):

    def setUp(self):
        self.seed = cargar_seed()
        self._dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ruta = Path(self._dir.name) / "demo.sqlite"
        self._entorno = mock.patch.dict(os.environ, {}, clear=False)
        self._entorno.start()
        self._anterior_db = os.environ.get("CAFETERIA_DB")

    def tearDown(self):
        self._entorno.stop()
        if self._anterior_db is None:
            os.environ.pop("CAFETERIA_DB", None)
        else:
            os.environ["CAFETERIA_DB"] = self._anterior_db
        self._dir.cleanup()

    def sembrar(self, **kwargs):
        kwargs.setdefault("hoy", date(2026, 10, 22))
        return self.seed.sembrar(self.ruta, **kwargs)

    def conexion(self):
        conn = sqlite3.connect(self.ruta)
        conn.row_factory = sqlite3.Row
        self.addCleanup(conn.close)
        return conn

    def contar(self, tabla):
        return self.conexion().execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


class TestProteccion(BaseSeed):
    """Lo primero: no tocar nunca la base real."""

    def test_se_niega_a_escribir_en_la_base_real(self):
        with self.assertRaises(self.seed.SeedRechazado) as ctx:
            self.seed.sembrar(RAIZ / "data" / "cafeteria.sqlite", reset=True)
        self.assertIn("base real", str(ctx.exception))

    def test_no_sobrescribe_una_base_existente_sin_reset(self):
        self.sembrar()
        antes = self.ruta.read_bytes()
        with self.assertRaises(self.seed.SeedRechazado):
            self.sembrar()
        self.assertEqual(self.ruta.read_bytes(), antes)

    def test_la_base_real_no_se_toca_al_sembrar(self):
        real = RAIZ / "data" / "cafeteria.sqlite"
        if not real.exists():
            self.skipTest("no hay base real en este equipo")
        import hashlib
        antes = hashlib.sha256(real.read_bytes()).hexdigest()
        self.sembrar()
        self.assertEqual(hashlib.sha256(real.read_bytes()).hexdigest(), antes)


class TestContenido(BaseSeed):

    def setUp(self):
        super().setUp()
        self.resumen = self.sembrar()

    def test_crea_los_diez_productos(self):
        self.assertEqual(self.contar("product"), 10)
        nombres = [f["name"] for f in
                   self.conexion().execute("SELECT name FROM product ORDER BY display_order")]
        self.assertEqual(nombres[0], "Café")
        self.assertIn("Bocadillo", nombres)

    def test_crea_el_establecimiento_ficticio(self):
        fila = self.conexion().execute(
            "SELECT name, tax_id, trade_name, address FROM establishment").fetchone()
        self.assertEqual(fila["trade_name"], "CAFETERÍA DEMO")
        self.assertEqual(fila["name"], "NOME APELIDOS DEMO")
        self.assertEqual(fila["tax_id"], "NIF-DEMO-0001")

    def test_dos_dias_cerrados_con_numeracion_correlativa(self):
        self.assertEqual(self.contar("daily_close"), 2)
        numeros = [f["close_number"] for f in
                   self.conexion().execute("SELECT close_number FROM daily_close ORDER BY id")]
        self.assertEqual(numeros, ["C-2026-000001", "C-2026-000002"])
        self.assertEqual(self.resumen["cierres"], numeros)

    def test_hay_ventas_validas_y_anuladas(self):
        conn = self.conexion()
        validas = conn.execute("SELECT COUNT(*) FROM sale WHERE status='VALID'").fetchone()[0]
        anuladas = conn.execute("SELECT COUNT(*) FROM sale WHERE status='VOID'").fetchone()[0]
        self.assertGreater(validas, 10)
        self.assertEqual(anuladas, 2, "una anulada en cada día cerrado")

    def test_el_dia_de_hoy_queda_abierto_y_con_ventas(self):
        """Para poder cerrar el dia en directo durante la demo."""
        conn = self.conexion()
        cerrado = conn.execute("SELECT 1 FROM daily_close WHERE business_date = ?",
                               (self.resumen["dia_abierto"],)).fetchone()
        ventas = conn.execute(
            "SELECT COUNT(*) FROM sale WHERE substr(created_at,1,10) = ?",
            (self.resumen["dia_abierto"],)).fetchone()[0]

        self.assertIsNone(cerrado, "el día de hoy NO debe estar cerrado")
        self.assertEqual(ventas, 4)

    def test_los_cierres_tienen_los_datos_congelados_y_generan_pdf(self):
        from app import pdf_cierre
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as exports:
            with mock.patch.dict(os.environ, {"CAFETERIA_DB": str(self.ruta),
                                              "CAFETERIA_EXPORTS": exports}):
                for fecha in self.resumen["dias_cerrados"]:
                    pdf = pdf_cierre.generar_pdf_cierre(fecha).read_bytes()
                    self.assertTrue(pdf.startswith(b"%PDF"))
                    self.assertIn("CAFETERÍA DEMO".encode("cp1252"), pdf)

    def test_las_cifras_de_los_cierres_cuadran(self):
        for c in self.conexion().execute("SELECT * FROM daily_close"):
            with self.subTest(cierre=c["close_number"]):
                self.assertEqual(c["gross_cents"],
                                 c["valid_cash_cents"] + c["void_cents"])
                self.assertGreater(c["valid_cash_cents"], 0)
                self.assertGreater(c["void_cents"], 0, "cada día tiene una anulada")


class TestRepetible(BaseSeed):

    def test_con_reset_se_recrea_igual(self):
        primera = self.sembrar()
        segunda = self.sembrar(reset=True)
        self.assertEqual(primera["cierres"], segunda["cierres"])
        self.assertEqual(self.contar("product"), 10)
        self.assertEqual(self.contar("daily_close"), 2)


class TestSinDatosReales(unittest.TestCase):
    """El script no puede contener datos reales ni rutas personales."""

    def setUp(self):
        self.texto = (RAIZ / "scripts" / "seed_demo.py").read_text(encoding="utf-8")

    def test_el_nif_demo_no_tiene_forma_de_nif_real(self):
        patron = re.compile(r"\b(\d{8}[A-Z]|[XYZ]\d{7}[A-Z]|[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J])\b")
        self.assertIsNone(patron.search(self.texto))

    def test_no_contiene_rutas_personales(self):
        # Las cadenas van partidas a proposito: si aparecieran enteras aqui,
        # este propio archivo seria un falso positivo para el test de
        # aislamiento de test_backup.py, que rastrea esos literales.
        for patron in (r"[A-Z]:\\Users\\", "Mi " + "unidad", "FACTURA" + "CION"):
            with self.subTest(patron=patron):
                self.assertIsNone(re.search(patron, self.texto, re.IGNORECASE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
