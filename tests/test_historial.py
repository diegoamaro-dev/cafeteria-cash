r"""Tests del historial y las anulaciones (FASE 4).

Stdlib unittest, sin dependencias nuevas:

    .venv\Scripts\python.exe -m unittest discover -s tests -v

Reutiliza BaseTemporal de test_sales: cada test tiene su propia base SQLite
temporal y la base real nunca se toca.
"""

import re
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_sales import BaseTemporal  # noqa: E402


class BaseHistorial(BaseTemporal):
    """Base con una venta ya confirmada: 2 x Cafe + 1 x Cafe con leche = 445."""

    def setUp(self):
        super().setUp()
        from app import sales
        self.venta = sales.confirmar_venta(self.venta_de_ejemplo())
        self.venta_id = self.venta["id"]

    def cabecera(self, venta_id=None):
        return self.conexion().execute(
            "SELECT * FROM sale WHERE id = ?", (venta_id or self.venta_id,)
        ).fetchone()

    def lineas(self, venta_id=None):
        return [dict(f) for f in self.conexion().execute(
            "SELECT * FROM sale_item WHERE sale_id = ? ORDER BY id",
            (venta_id or self.venta_id,),
        )]

    def contar(self, tabla):
        return self.conexion().execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


class TestHistorial(BaseHistorial):

    def test_la_venta_aparece_en_el_historial_con_numero_importe_y_estado(self):
        from app import sales
        ventas = sales.listar_ventas()

        self.assertEqual(len(ventas), 1)
        self.assertEqual(ventas[0]["sale_number"], self.venta["sale_number"])
        self.assertEqual(ventas[0]["total_cents"], 445)
        self.assertEqual(ventas[0]["status"], "VALID")
        self.assertIsNone(ventas[0]["voided_at"])

    def test_el_historial_va_de_la_mas_reciente_a_la_mas_antigua(self):
        from app import sales
        segunda = sales.confirmar_venta(self.venta_de_ejemplo())
        tercera = sales.confirmar_venta(self.venta_de_ejemplo())

        numeros = [v["sale_number"] for v in sales.listar_ventas()]
        self.assertEqual(numeros, [tercera["sale_number"],
                                   segunda["sale_number"],
                                   self.venta["sale_number"]])


class TestAnular(BaseHistorial):

    def test_anular_cambia_el_estado_y_registra_la_hora(self):
        from app import sales
        sales.anular_venta(self.venta_id)

        fila = self.cabecera()
        self.assertEqual(fila["status"], "VOID")
        self.assertIsNotNone(fila["voided_at"])

    def test_anular_no_toca_ningun_dato_economico_de_la_venta(self):
        from app import sales
        antes = dict(self.cabecera())
        lineas_antes = self.lineas()

        sales.anular_venta(self.venta_id)

        despues = dict(self.cabecera())
        lineas_despues = self.lineas()

        for campo in ("id", "sale_number", "created_at", "total_cents"):
            with self.subTest(campo=campo):
                self.assertEqual(despues[campo], antes[campo])

        self.assertEqual(len(lineas_despues), len(lineas_antes))
        self.assertEqual(len(lineas_despues), 2)
        # Cada linea, columna por columna: identicas.
        self.assertEqual(lineas_despues, lineas_antes)

        # Y con los valores concretos, por si acaso ambas copias estuvieran mal.
        self.assertEqual([l["quantity"] for l in lineas_despues], [2, 1])
        self.assertEqual([l["product_name_snapshot"] for l in lineas_despues],
                         ["Café", "Café con leche"])
        self.assertEqual([l["unit_price_cents_snapshot"] for l in lineas_despues],
                         [140, 165])
        self.assertEqual([l["subtotal_cents"] for l in lineas_despues], [280, 165])

    def test_solo_cambian_status_y_voided_at(self):
        from app import sales
        antes = dict(self.cabecera())
        sales.anular_venta(self.venta_id)
        despues = dict(self.cabecera())

        cambiadas = {k for k in antes if antes[k] != despues[k]}
        self.assertEqual(cambiadas, {"status", "voided_at"})

    def test_la_anulacion_persiste_al_cerrar_y_abrir_la_conexion(self):
        from app import sales
        sales.anular_venta(self.venta_id)

        conn = sqlite3.connect(self.ruta)
        primera = conn.execute(
            "SELECT status, voided_at FROM sale WHERE id = ?", (self.venta_id,)
        ).fetchone()
        conn.close()

        conn = sqlite3.connect(self.ruta)
        segunda = conn.execute(
            "SELECT status, voided_at FROM sale WHERE id = ?", (self.venta_id,)
        ).fetchone()
        conn.close()

        self.assertEqual(segunda[0], "VOID")
        self.assertIsNotNone(segunda[1])
        self.assertEqual(primera, segunda)

    def test_anular_otra_vez_se_rechaza_y_no_cambia_voided_at(self):
        from datetime import datetime, timedelta
        from app import sales

        sales.anular_venta(self.venta_id, momento=datetime(2026, 9, 18, 10, 0, 0))
        original = self.cabecera()["voided_at"]

        with self.assertRaises(sales.VentaYaAnulada):
            sales.anular_venta(self.venta_id,
                               momento=datetime(2026, 9, 18, 10, 0, 0) + timedelta(hours=3))

        fila = self.cabecera()
        self.assertEqual(fila["status"], "VOID")
        self.assertEqual(fila["voided_at"], original)
        self.assertEqual(original, "2026-09-18 10:00:00")

    def test_anular_un_id_inexistente_no_modifica_ninguna_venta(self):
        from app import sales
        antes = [dict(f) for f in self.conexion().execute("SELECT * FROM sale")]

        with self.assertRaises(sales.VentaNoEncontrada):
            sales.anular_venta(999999)

        despues = [dict(f) for f in self.conexion().execute("SELECT * FROM sale")]
        self.assertEqual(despues, antes)

    def test_una_venta_anulada_no_puede_volver_a_valid(self):
        from app import sales
        sales.anular_venta(self.venta_id)

        # No existe funcion de reactivacion. Y volver a llamar a anular no la
        # devuelve a VALID: la actualizacion esta condicionada a status='VALID'.
        with self.assertRaises(sales.VentaYaAnulada):
            sales.anular_venta(self.venta_id)
        self.assertEqual(self.cabecera()["status"], "VOID")
        self.assertFalse(hasattr(sales, "reactivar_venta"))


class TestSinBorrado(BaseHistorial):

    def test_el_numero_de_filas_no_cambia_al_anular(self):
        from app import sales
        sales.confirmar_venta(self.venta_de_ejemplo())

        ventas_antes = self.contar("sale")
        lineas_antes = self.contar("sale_item")

        sales.anular_venta(self.venta_id)

        self.assertEqual(self.contar("sale"), ventas_antes)
        self.assertEqual(self.contar("sale_item"), lineas_antes)

    def test_la_anulacion_no_ejecuta_ningun_delete(self):
        """Se captura cada sentencia SQL que la anulacion envia a SQLite."""
        from app import db, sales

        sentencias = []
        original = db.get_connection

        def conexion_espiada():
            conn = original()
            conn.set_trace_callback(sentencias.append)
            return conn

        with mock.patch.object(db, "get_connection", conexion_espiada):
            sales.anular_venta(self.venta_id)

        normalizadas = [s.strip().upper() for s in sentencias]
        self.assertTrue(normalizadas, "no se ha capturado ninguna sentencia")
        self.assertFalse([s for s in normalizadas if s.startswith("DELETE")],
                         "la anulacion no puede borrar nada")
        escrituras = [s for s in normalizadas
                      if s.split()[0] in ("INSERT", "UPDATE", "DELETE", "REPLACE")]
        self.assertEqual(len(escrituras), 1, f"se esperaba un solo UPDATE: {escrituras}")
        self.assertTrue(escrituras[0].startswith("UPDATE SALE SET STATUS = 'VOID'"))
        # El trace muestra la sentencia con los parametros ya sustituidos.
        self.assertRegex(escrituras[0], r"WHERE ID = \d+ AND STATUS = 'VALID'$")

    def test_el_codigo_de_la_aplicacion_no_contiene_delete_sobre_ventas(self):
        """Salvaguarda: si alguien anade un DELETE sobre ventas, este test falla."""
        raiz_app = Path(__file__).resolve().parent.parent / "app"
        prohibido = re.compile(r"DELETE\s+FROM\s+(sale|sale_item)\b", re.IGNORECASE)

        encontrados = []
        for archivo in raiz_app.rglob("*.py"):
            for n, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
                if prohibido.search(linea):
                    encontrados.append(f"{archivo.name}:{n}: {linea.strip()}")

        self.assertEqual(encontrados, [])


class TestMigracion(unittest.TestCase):
    """init_db debe anadir voided_at a una base de la FASE 3 sin perder datos."""

    ESQUEMA_FASE_3 = """
        CREATE TABLE product (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            display_order INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE sale (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_number TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL,
            total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
            status TEXT NOT NULL DEFAULT 'VALID' CHECK (status IN ('VALID', 'VOID')));
        CREATE TABLE sale_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL REFERENCES sale (id),
            product_id INTEGER NOT NULL REFERENCES product (id),
            product_name_snapshot TEXT NOT NULL,
            unit_price_cents_snapshot INTEGER NOT NULL CHECK (unit_price_cents_snapshot >= 0),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            subtotal_cents INTEGER NOT NULL CHECK (subtotal_cents >= 0));
        INSERT INTO product (name, price_cents) VALUES ('Café', 140), ('Café con leche', 165);
        INSERT INTO sale (sale_number, created_at, total_cents)
            VALUES ('V-2026-000001', '2026-09-17 19:44:19', 445),
                   ('V-2026-000002', '2026-09-17 19:44:40', 330);
        INSERT INTO sale_item (sale_id, product_id, product_name_snapshot,
                               unit_price_cents_snapshot, quantity, subtotal_cents)
            VALUES (1, 1, 'Café', 140, 2, 280), (1, 2, 'Café con leche', 165, 1, 165),
                   (2, 2, 'Café con leche', 165, 2, 330);
    """

    def setUp(self):
        import os
        import tempfile
        self._dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ruta = Path(self._dir.name) / "fase3.sqlite"
        self._anterior = os.environ.get("CAFETERIA_DB")
        os.environ["CAFETERIA_DB"] = str(self.ruta)

        conn = sqlite3.connect(self.ruta)
        conn.executescript(self.ESQUEMA_FASE_3)
        conn.commit()
        conn.close()

    def tearDown(self):
        import os
        if self._anterior is None:
            os.environ.pop("CAFETERIA_DB", None)
        else:
            os.environ["CAFETERIA_DB"] = self._anterior
        self._dir.cleanup()

    def _leer(self):
        conn = sqlite3.connect(self.ruta)
        try:
            columnas = [c[1] for c in conn.execute("PRAGMA table_info(sale)")]
            ventas = conn.execute("SELECT id, sale_number, created_at, total_cents, status"
                                  " FROM sale ORDER BY id").fetchall()
            lineas = conn.execute("SELECT * FROM sale_item ORDER BY id").fetchall()
            return columnas, ventas, lineas
        finally:
            conn.close()

    def test_la_migracion_anade_voided_at_sin_perder_ventas(self):
        from app import db
        columnas_antes, ventas_antes, lineas_antes = self._leer()
        self.assertNotIn("voided_at", columnas_antes)

        db.init_db()

        columnas, ventas, lineas = self._leer()
        self.assertIn("voided_at", columnas)
        self.assertEqual(ventas, ventas_antes)
        self.assertEqual(lineas, lineas_antes)

        conn = sqlite3.connect(self.ruta)
        nulos = conn.execute("SELECT COUNT(*) FROM sale WHERE voided_at IS NULL").fetchone()[0]
        conn.close()
        self.assertEqual(nulos, 2, "las ventas existentes quedan con voided_at NULL")

    def test_la_migracion_es_idempotente(self):
        from app import db
        db.init_db()
        db.init_db()
        db.init_db()

        columnas, ventas, _ = self._leer()
        self.assertEqual(columnas.count("voided_at"), 1)
        self.assertEqual(len(ventas), 2)

    def test_base_nueva_y_base_migrada_tienen_las_mismas_columnas(self):
        import os
        import tempfile
        from app import db

        db.init_db()
        columnas_migrada, _, _ = self._leer()

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as otro:
            os.environ["CAFETERIA_DB"] = str(Path(otro) / "nueva.sqlite")
            db.init_db()
            conn = sqlite3.connect(os.environ["CAFETERIA_DB"])
            columnas_nueva = [c[1] for c in conn.execute("PRAGMA table_info(sale)")]
            conn.close()
            os.environ["CAFETERIA_DB"] = str(self.ruta)

        self.assertEqual(columnas_nueva, columnas_migrada)


class TestRutaAnular(BaseHistorial):

    def setUp(self):
        super().setUp()
        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()

    def test_el_historial_muestra_la_venta_valida_con_boton_anular(self):
        html = self.cliente.get("/historial").get_data(as_text=True)

        self.assertIn(self.venta["sale_number"], html)
        self.assertIn("4,45 €", html)
        self.assertIn("VÁLIDA", html)
        self.assertIn("ANULAR", html)
        self.assertIn("confirm(", html)

    def test_anular_por_la_web_redirige_con_confirmacion(self):
        respuesta = self.cliente.post(f"/historial/{self.venta_id}/anular")
        self.assertEqual(respuesta.status_code, 302)

        html = self.cliente.get(respuesta.headers["Location"]).get_data(as_text=True)
        self.assertIn(f"Venta {self.venta['sale_number']} anulada", html)
        self.assertIn("ANULADA", html)
        self.assertEqual(self.cabecera()["status"], "VOID")

    def test_una_venta_anulada_no_muestra_boton_anular(self):
        self.cliente.post(f"/historial/{self.venta_id}/anular")
        html = self.cliente.get("/historial").get_data(as_text=True)

        self.assertIn("ANULADA", html)
        self.assertNotIn(">ANULAR<", html)
        self.assertNotIn(f"/historial/{self.venta_id}/anular", html)

    def test_anular_dos_veces_por_la_web_devuelve_409(self):
        self.cliente.post(f"/historial/{self.venta_id}/anular")
        original = self.cabecera()["voided_at"]

        respuesta = self.cliente.post(f"/historial/{self.venta_id}/anular")

        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("ya estaba anulada", respuesta.get_data(as_text=True))
        self.assertEqual(self.cabecera()["voided_at"], original)

    def test_anular_un_id_inexistente_por_la_web_devuelve_404(self):
        respuesta = self.cliente.post("/historial/999999/anular")

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(self.cabecera()["status"], "VALID")

    def test_anular_por_get_no_esta_permitido(self):
        respuesta = self.cliente.get(f"/historial/{self.venta_id}/anular")

        self.assertEqual(respuesta.status_code, 405)
        self.assertEqual(self.cabecera()["status"], "VALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
