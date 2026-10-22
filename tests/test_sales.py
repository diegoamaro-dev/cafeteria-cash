r"""Tests de la persistencia de ventas (FASE 3).

Stdlib unittest, sin dependencias nuevas:

    .venv\Scripts\python.exe -m unittest discover -s tests -v

Cada test usa una base SQLite temporal propia (CAFETERIA_DB). La base real
nunca se toca.
"""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class BaseTemporal(unittest.TestCase):
    """Monta una base vacia con dos productos antes de cada test."""

    def setUp(self):
        self._conexiones = []
        self._dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ruta = Path(self._dir.name) / "prueba.sqlite"
        self._anterior = os.environ.get("CAFETERIA_DB")
        os.environ["CAFETERIA_DB"] = str(self.ruta)
        # Backups (FASE 8) SIEMPRE en una carpeta temporal propia del test: aunque
        # el equipo tenga CAFETERIA_BACKUP_DIR apuntando a la carpeta real, un
        # test nunca escribe alli.
        self.carpeta_backup = Path(self._dir.name) / "backups"
        self.carpeta_backup.mkdir()
        self._anterior_backup = os.environ.get("CAFETERIA_BACKUP_DIR")
        os.environ["CAFETERIA_BACKUP_DIR"] = str(self.carpeta_backup)

        from app import db
        db.init_db()

        from app import products
        self.id_cafe = products.crear_producto("Café", 140, 10)
        self.id_leche = products.crear_producto("Café con leche", 165, 20)

    def tearDown(self):
        # Windows no borra el directorio temporal con la base aun abierta.
        for conn in self._conexiones:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        if self._anterior is None:
            os.environ.pop("CAFETERIA_DB", None)
        else:
            os.environ["CAFETERIA_DB"] = self._anterior
        if self._anterior_backup is None:
            os.environ.pop("CAFETERIA_BACKUP_DIR", None)
        else:
            os.environ["CAFETERIA_BACKUP_DIR"] = self._anterior_backup
        self._dir.cleanup()

    def conexion(self):
        """Conexion NUEVA e independiente: lee lo que hay de verdad en disco."""
        conn = sqlite3.connect(self.ruta)
        conn.row_factory = sqlite3.Row
        self._conexiones.append(conn)
        return conn

    def venta_de_ejemplo(self):
        return [
            {"producto_id": self.id_cafe, "nombre": "Café",
             "precio_centimos": 140, "cantidad": 2},
            {"producto_id": self.id_leche, "nombre": "Café con leche",
             "precio_centimos": 165, "cantidad": 1},
        ]


class TestTotales(BaseTemporal):

    def test_total_de_la_venta_de_ejemplo_son_445_centimos(self):
        from app.cart import total_centimos
        self.assertEqual(total_centimos(self.venta_de_ejemplo()), 445)


class TestConfirmarVenta(BaseTemporal):

    def test_confirmar_crea_una_cabecera_y_dos_lineas(self):
        from app import sales
        venta = sales.confirmar_venta(self.venta_de_ejemplo())

        conn = self.conexion()
        cabeceras = conn.execute("SELECT * FROM sale").fetchall()
        lineas = conn.execute("SELECT * FROM sale_item ORDER BY id").fetchall()

        self.assertEqual(len(cabeceras), 1)
        self.assertEqual(len(lineas), 2)

        self.assertEqual(cabeceras[0]["total_cents"], 445)
        self.assertEqual(cabeceras[0]["status"], "VALID")
        self.assertEqual(cabeceras[0]["sale_number"], venta["sale_number"])

        self.assertEqual(lineas[0]["quantity"], 2)
        self.assertEqual(lineas[1]["quantity"], 1)
        self.assertEqual(lineas[0]["subtotal_cents"], 280)
        self.assertEqual(lineas[1]["subtotal_cents"], 165)

    def test_los_snapshots_guardan_nombre_y_precio_del_momento(self):
        from app import sales
        sales.confirmar_venta(self.venta_de_ejemplo())

        conn = self.conexion()
        lineas = conn.execute("SELECT * FROM sale_item ORDER BY id").fetchall()

        self.assertEqual(lineas[0]["product_name_snapshot"], "Café")
        self.assertEqual(lineas[0]["unit_price_cents_snapshot"], 140)
        self.assertEqual(lineas[1]["product_name_snapshot"], "Café con leche")
        self.assertEqual(lineas[1]["unit_price_cents_snapshot"], 165)

    def test_la_fecha_y_hora_quedan_guardadas(self):
        from app import sales
        venta = sales.confirmar_venta(self.venta_de_ejemplo())
        datetime.strptime(venta["created_at"], "%Y-%m-%d %H:%M:%S")


class TestPersistencia(BaseTemporal):

    def test_la_venta_sobrevive_a_cerrar_y_abrir_la_conexion(self):
        from app import sales
        venta = sales.confirmar_venta(self.venta_de_ejemplo())

        conn = self.conexion()
        fila = conn.execute("SELECT * FROM sale WHERE sale_number = ?",
                            (venta["sale_number"],)).fetchone()
        conn.close()

        conn = self.conexion()
        fila2 = conn.execute("SELECT * FROM sale WHERE sale_number = ?",
                             (venta["sale_number"],)).fetchone()
        lineas = conn.execute("SELECT COUNT(*) AS n FROM sale_item WHERE sale_id = ?",
                              (fila2["id"],)).fetchone()
        conn.close()

        self.assertIsNotNone(fila)
        self.assertIsNotNone(fila2)
        self.assertEqual(fila2["total_cents"], 445)
        self.assertEqual(lineas["n"], 2)


class TestHistoricoInmutable(BaseTemporal):

    def test_cambiar_el_precio_del_producto_no_altera_la_venta_pasada(self):
        from app import products, sales
        sales.confirmar_venta(self.venta_de_ejemplo())

        products.actualizar_producto(self.id_cafe, "Café", 150)

        conn = self.conexion()
        producto = conn.execute("SELECT price_cents FROM product WHERE id = ?",
                                (self.id_cafe,)).fetchone()
        linea = conn.execute("SELECT * FROM sale_item WHERE product_id = ?",
                             (self.id_cafe,)).fetchone()
        venta = conn.execute("SELECT total_cents FROM sale").fetchone()

        self.assertEqual(producto["price_cents"], 150)
        self.assertEqual(linea["unit_price_cents_snapshot"], 140)
        self.assertEqual(linea["subtotal_cents"], 280)
        self.assertEqual(venta["total_cents"], 445)


class TestNumeracion(BaseTemporal):

    def test_dos_ventas_reciben_numeros_distintos_y_correlativos(self):
        from app import sales
        primera = sales.confirmar_venta(self.venta_de_ejemplo())
        segunda = sales.confirmar_venta(self.venta_de_ejemplo())

        anio = datetime.now().year
        self.assertEqual(primera["sale_number"], "V-%d-000001" % anio)
        self.assertEqual(segunda["sale_number"], "V-%d-000002" % anio)
        self.assertNotEqual(primera["sale_number"], segunda["sale_number"])

    def test_un_rollback_no_consume_numero_de_venta(self):
        """Una venta que falla no llega a existir, asi que no gasta numero.

        El siguiente cobro correcto recibe el numero que habria tenido la
        venta fallida. Lo que nunca se reutiliza es el numero de una venta
        que si llego a confirmarse.
        """
        from app import sales
        sales.confirmar_venta(self.venta_de_ejemplo())

        rota = self.venta_de_ejemplo() + [
            {"producto_id": 999999, "nombre": "Fantasma",
             "precio_centimos": 100, "cantidad": 1}]
        with self.assertRaises(sqlite3.IntegrityError):
            sales.confirmar_venta(rota)

        tercera = sales.confirmar_venta(self.venta_de_ejemplo())
        anio = datetime.now().year

        conn = self.conexion()
        numeros = [f["sale_number"] for f in
                   conn.execute("SELECT sale_number FROM sale ORDER BY id")]

        self.assertEqual(numeros, ["V-%d-000001" % anio, "V-%d-000002" % anio])
        self.assertEqual(tercera["sale_number"], "V-%d-000002" % anio)
        self.assertEqual(len(numeros), len(set(numeros)))

    def test_sale_number_es_unico_en_el_esquema(self):
        from app import sales
        venta = sales.confirmar_venta(self.venta_de_ejemplo())
        conn = self.conexion()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO sale (sale_number, created_at, total_cents, status)"
                " VALUES (?, '2026-01-01 00:00:00', 100, 'VALID')",
                (venta["sale_number"],))
            conn.commit()


class TestAtomicidad(BaseTemporal):

    def test_si_falla_una_linea_no_queda_ninguna_venta(self):
        from app import cart, sales

        cart.cancelar()
        cart.anadir(self.id_cafe, "Café", 140)
        cart.anadir(self.id_cafe, "Café", 140)
        antes = cart.lineas()

        rota = [
            {"producto_id": self.id_cafe, "nombre": "Café",
             "precio_centimos": 140, "cantidad": 2},
            {"producto_id": 999999, "nombre": "Fantasma",
             "precio_centimos": 100, "cantidad": 1},
        ]

        with self.assertRaises(sqlite3.IntegrityError):
            sales.confirmar_venta(rota)

        conn = self.conexion()
        ventas = conn.execute("SELECT COUNT(*) AS n FROM sale").fetchone()["n"]
        lineas = conn.execute("SELECT COUNT(*) AS n FROM sale_item").fetchone()["n"]

        self.assertEqual(ventas, 0, "no puede quedar una cabecera huerfana")
        self.assertEqual(lineas, 0, "no puede quedar ninguna linea suelta")
        self.assertEqual(cart.lineas(), antes, "el carrito no se toca si falla")
        cart.cancelar()

    def test_las_claves_ajenas_estan_activadas(self):
        from app import db
        conn = db.get_connection()
        activadas = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()
        self.assertEqual(activadas, 1)


class TestCarritoVacio(BaseTemporal):

    def test_cobrar_sin_lineas_se_rechaza_y_no_crea_venta(self):
        from app import sales
        with self.assertRaises(sales.VentaInvalida):
            sales.confirmar_venta([])

        conn = self.conexion()
        self.assertEqual(
            conn.execute("SELECT COUNT(*) AS n FROM sale").fetchone()["n"], 0)


class TestImportesEnteros(BaseTemporal):

    def test_todo_lo_guardado_son_enteros_de_centimos(self):
        from app import sales
        sales.confirmar_venta(self.venta_de_ejemplo())

        conn = self.conexion()
        venta = conn.execute("SELECT total_cents FROM sale").fetchone()
        lineas = conn.execute("SELECT * FROM sale_item").fetchall()

        self.assertIsInstance(venta["total_cents"], int)
        for l in lineas:
            self.assertIsInstance(l["unit_price_cents_snapshot"], int)
            self.assertIsInstance(l["subtotal_cents"], int)
            self.assertIsInstance(l["quantity"], int)

    def test_el_total_guardado_coincide_con_la_suma_de_subtotales(self):
        from app import sales
        sales.confirmar_venta(self.venta_de_ejemplo())

        conn = self.conexion()
        total = conn.execute("SELECT total_cents FROM sale").fetchone()[0]
        suma = conn.execute("SELECT SUM(subtotal_cents) FROM sale_item").fetchone()[0]
        self.assertEqual(total, suma)
        self.assertEqual(total, 445)

    def test_las_restricciones_rechazan_cantidades_y_precios_invalidos(self):
        from app import sales
        sales.confirmar_venta(self.venta_de_ejemplo())

        conn = self.conexion()
        venta_id = conn.execute("SELECT id FROM sale").fetchone()[0]

        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO sale_item (sale_id, product_id, product_name_snapshot,"
                " unit_price_cents_snapshot, quantity, subtotal_cents)"
                " VALUES (?, ?, 'X', 100, 0, 0)", (venta_id, self.id_cafe))

        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO sale_item (sale_id, product_id, product_name_snapshot,"
                " unit_price_cents_snapshot, quantity, subtotal_cents)"
                " VALUES (?, ?, 'X', -1, 1, 0)", (venta_id, self.id_cafe))


class TestRutaCobro(BaseTemporal):
    """La ruta web: la venta actual se vacia solo si el guardado va bien."""

    def setUp(self):
        super().setUp()
        from app import cart
        cart.cancelar()
        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()

    def tearDown(self):
        from app import cart
        cart.cancelar()
        super().tearDown()

    def test_cobro_correcto_guarda_la_venta_y_vacia_el_carrito(self):
        from app import cart
        cart.anadir(self.id_cafe, "Café", 140)
        cart.anadir(self.id_cafe, "Café", 140)
        cart.anadir(self.id_leche, "Café con leche", 165)

        respuesta = self.cliente.post("/venta/cobrar")

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(cart.lineas(), [], "el carrito debe quedar vacio")

        conn = self.conexion()
        venta = conn.execute("SELECT * FROM sale").fetchone()
        self.assertEqual(venta["total_cents"], 445)

    def test_si_falla_el_guardado_el_carrito_NO_se_vacia(self):
        from app import cart
        cart.anadir(self.id_cafe, "Café", 140)
        antes = cart.lineas()

        # Se rompe la integridad por debajo: el producto deja de existir,
        # asi que insertar su linea violara la clave ajena.
        conn = self.conexion()
        conn.execute("DELETE FROM product WHERE id = ?", (self.id_cafe,))
        conn.commit()

        respuesta = self.cliente.post("/venta/cobrar")

        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(cart.lineas(), antes, "el carrito debe mantenerse intacto")

        conn = self.conexion()
        self.assertEqual(
            conn.execute("SELECT COUNT(*) AS n FROM sale").fetchone()["n"], 0,
            "no puede quedar una venta a medias")
        self.assertEqual(
            conn.execute("SELECT COUNT(*) AS n FROM sale_item").fetchone()["n"], 0)

    def test_cobrar_con_el_carrito_vacio_devuelve_400_y_no_crea_venta(self):
        respuesta = self.cliente.post("/venta/cobrar")

        self.assertEqual(respuesta.status_code, 400)
        conn = self.conexion()
        self.assertEqual(
            conn.execute("SELECT COUNT(*) AS n FROM sale").fetchone()["n"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
