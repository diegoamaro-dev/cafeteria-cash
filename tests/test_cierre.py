r"""Tests del cierre diario (FASE 6).

Stdlib unittest, sin dependencias nuevas:

    .venv\Scripts\python.exe -m unittest discover -s tests -v

Reutiliza BaseTemporal de test_sales: base SQLite temporal por test, la base
real nunca se toca.

Decision permanente que se comprueba aqui:
    UN DIA CERRADO NO ADMITE NUEVAS VENTAS NI ANULACIONES.
"""

import re
import sqlite3
import sys
import threading
import time
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_sales import BaseTemporal  # noqa: E402

DIA_A = "2026-09-17"
DIA_B = "2026-09-18"
DESPUES = datetime(2026, 9, 18, 23, 0, 0)   # momento del cierre en los tests

# Datos FICTICIOS del establecimiento: (titular, NIF, nombre comercial, direccion).
# Nunca datos reales en los tests. Hacen falta para poder cerrar un dia.
EMPRESA = ("Titular de Pruebas Ficticio", "NIF-PRUEBA-1",
           "Cafetería de Pruebas", "Calle Ficticia 1, 00000 Ciudad de Prueba")
CLAVES = ("name", "tax_id", "trade_name", "address")
SNAPSHOTS = ("holder_name_snapshot", "tax_id_snapshot",
             "trade_name_snapshot", "address_snapshot")


class BaseCierre(BaseTemporal):

    def setUp(self):
        super().setUp()
        from app import establecimiento
        establecimiento.guardar(*EMPRESA, momento=datetime(2026, 9, 1, 9, 0))

    def congelados(self, c):
        return tuple(c[k] for k in SNAPSHOTS)

    def linea(self, producto_id, nombre, precio, cantidad):
        return {"producto_id": producto_id, "nombre": nombre,
                "precio_centimos": precio, "cantidad": cantidad}

    def vender(self, lineas, momento):
        from app import sales
        return sales.confirmar_venta(lineas, momento=momento)

    def caso_preproduccion(self):
        """1 venta VALID de 445 y 1 VOID de 330, ambas del dia A."""
        from app import sales
        v1 = self.vender([self.linea(self.id_cafe, "Café", 140, 2),
                          self.linea(self.id_leche, "Café con leche", 165, 1)],
                         datetime(2026, 9, 17, 19, 44, 19))
        v2 = self.vender([self.linea(self.id_leche, "Café con leche", 165, 2)],
                         datetime(2026, 9, 17, 19, 44, 40))
        sales.anular_venta(v2["id"], momento=datetime(2026, 9, 17, 20, 0, 0))
        return v1, v2

    def cerrar(self, fecha, momento=DESPUES):
        from app import cierre
        return cierre.cerrar_dia(fecha, momento=momento)

    def contar(self, tabla):
        return self.conexion().execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]

    def unidades(self, c):
        return {i["product_name_snapshot"]: i["units"] for i in c["items"]}


# ---------------------------------------------------------------- 1, 2, 3, 10

class TestCierreCasoPreproduccion(BaseCierre):

    def setUp(self):
        super().setUp()
        self.v1, self.v2 = self.caso_preproduccion()
        self.c = self.cerrar(DIA_A)

    def test_cifras_del_cierre(self):
        self.assertEqual(self.c["business_date"], DIA_A)
        self.assertEqual(self.c["valid_sales_count"], 1)
        self.assertEqual(self.c["void_sales_count"], 1)
        self.assertEqual(self.c["gross_cents"], 775)
        self.assertEqual(self.c["void_cents"], 330)
        self.assertEqual(self.c["valid_cash_cents"], 445)
        self.assertEqual(self.unidades(self.c), {"Café": 2, "Café con leche": 1})

    def test_primera_y_ultima_venta_incluyen_la_anulada(self):
        self.assertEqual(self.c["first_sale_number"], self.v1["sale_number"])
        self.assertEqual(self.c["last_sale_number"], self.v2["sale_number"])

    def test_numero_de_cierre(self):
        self.assertEqual(self.c["close_number"], "C-2026-000001")

    def test_bruto_es_valido_mas_anulado(self):
        self.assertEqual(self.c["gross_cents"],
                         self.c["valid_cash_cents"] + self.c["void_cents"])

    def test_la_base_rechaza_un_cierre_con_bruto_incoherente(self):
        conn = self.conexion()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO daily_close (close_number, business_date, closed_at,"
                " valid_sales_count, void_sales_count, gross_cents, void_cents,"
                " valid_cash_cents) VALUES ('C-2026-999999', '2026-01-01',"
                " '2026-01-01 23:00:00', 1, 1, 999, 330, 445)")

    def test_el_cierre_no_modifica_ninguna_venta(self):
        conn = self.conexion()
        ventas = [dict(r) for r in conn.execute("SELECT * FROM sale ORDER BY id")]
        self.assertEqual([v["status"] for v in ventas], ["VALID", "VOID"])
        self.assertEqual(self.contar("sale"), 2)
        self.assertEqual(self.contar("sale_item"), 3)


# ----------------------------------------------------------------------- 4, 5

class TestNumeracionYUnicidad(BaseCierre):

    def test_dos_dias_cerrados_tienen_numeros_correlativos(self):
        self.vender([self.linea(self.id_cafe, "Café", 140, 1)], datetime(2026, 9, 16, 9, 0))
        self.vender([self.linea(self.id_cafe, "Café", 140, 1)], datetime(2026, 9, 17, 9, 0))
        c16 = self.cerrar("2026-09-16")
        c17 = self.cerrar(DIA_A)

        self.assertEqual(c16["close_number"], "C-2026-000001")
        self.assertEqual(c17["close_number"], "C-2026-000002")

    def test_un_dia_no_puede_cerrarse_dos_veces(self):
        from app import cierre
        self.caso_preproduccion()
        primero = self.cerrar(DIA_A)

        with self.assertRaises(cierre.DiaCerrado):
            self.cerrar(DIA_A, momento=datetime(2026, 9, 19, 9, 0))

        self.assertEqual(self.contar("daily_close"), 1)
        self.assertEqual(cierre.obtener_cierre(DIA_A), primero)

    def test_business_date_es_unico_en_el_esquema(self):
        self.cerrar(DIA_A)
        conn = self.conexion()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO daily_close (close_number, business_date, closed_at,"
                " valid_sales_count, void_sales_count, gross_cents, void_cents,"
                " valid_cash_cents) VALUES ('C-2026-000099', ?, '2026-09-18 23:00:00',"
                " 0, 0, 0, 0, 0)", (DIA_A,))

    def test_un_rollback_no_consume_numero_de_cierre(self):
        from app import cierre, resumen
        original = resumen._resumen_en_conexion

        def roto(conn, fecha):
            r = original(conn, fecha)
            r["unidades"] = [{"nombre": "Café", "unidades": 1},
                             {"nombre": "Roto", "unidades": 0}]   # viola units > 0
            return r

        with mock.patch.object(resumen, "_resumen_en_conexion", roto):
            with self.assertRaises(sqlite3.IntegrityError):
                cierre.cerrar_dia("2026-09-16", momento=DESPUES)

        self.assertEqual(self.cerrar(DIA_A)["close_number"], "C-2026-000001")

    def test_no_se_puede_cerrar_un_dia_futuro(self):
        from app import cierre
        with self.assertRaises(cierre.CierreInvalido):
            cierre.cerrar_dia("2026-09-19", momento=datetime(2026, 9, 18, 23, 0))
        self.assertEqual(self.contar("daily_close"), 0)


# -------------------------------------------------------------------------- 6

class TestDiaVacio(BaseCierre):

    def test_se_puede_cerrar_un_dia_sin_ventas(self):
        c = self.cerrar(DIA_A)

        self.assertEqual(c["close_number"], "C-2026-000001")
        for campo in ("valid_sales_count", "void_sales_count",
                      "gross_cents", "void_cents", "valid_cash_cents"):
            with self.subTest(campo=campo):
                self.assertEqual(c[campo], 0)
        self.assertIsNone(c["first_sale_number"])
        self.assertIsNone(c["last_sale_number"])
        self.assertEqual(c["items"], [])
        self.assertEqual(self.contar("daily_close_item"), 0)


# ---------------------------------------------------------------------- 7, 8, 9

class TestPersistenciaYReproducibilidad(BaseCierre):

    def setUp(self):
        super().setUp()
        self.caso_preproduccion()
        self.cerrado = self.cerrar(DIA_A)

    def test_el_cierre_sobrevive_a_cerrar_y_abrir_la_conexion(self):
        conn = sqlite3.connect(self.ruta)
        conn.row_factory = sqlite3.Row
        cab = dict(conn.execute("SELECT * FROM daily_close").fetchone())
        items = [dict(r) for r in conn.execute(
            "SELECT product_name_snapshot, units FROM daily_close_item ORDER BY id")]
        conn.close()

        self.assertEqual(cab["close_number"], "C-2026-000001")
        self.assertEqual(cab["gross_cents"], 775)
        self.assertEqual(cab["valid_cash_cents"], 445)
        self.assertEqual(cab["void_cents"], 330)
        self.assertEqual({i["product_name_snapshot"]: i["units"] for i in items},
                         {"Café": 2, "Café con leche": 1})

    def test_el_cierre_sobrevive_a_reiniciar_la_aplicacion(self):
        from app import cierre, create_app
        create_app()   # arranque nuevo: init_db de nuevo sobre la misma base
        self.assertEqual(cierre.obtener_cierre(DIA_A), self.cerrado)

    def test_leerlo_varias_veces_da_siempre_lo_mismo(self):
        from app import cierre
        lecturas = [cierre.obtener_cierre(DIA_A) for _ in range(5)]
        for lectura in lecturas:
            self.assertEqual(lectura, self.cerrado)

    def test_la_previsualizacion_coincidia_con_lo_guardado(self):
        from app import cierre
        # Recalcular desde las ventas da lo mismo que lo guardado.
        recalculado = cierre.previsualizar_cierre(DIA_A)
        guardado = {k: v for k, v in self.cerrado.items()
                    if k not in ("id", "close_number", "closed_at")}
        self.assertEqual(recalculado, guardado)

    def test_cambiar_nombres_y_precios_no_altera_el_cierre(self):
        from app import cierre, products
        products.actualizar_producto(self.id_cafe, "Café solo", 150)
        products.actualizar_producto(self.id_leche, "Cortado largo", 199)
        products.cambiar_estado(self.id_leche, False)

        self.assertEqual(cierre.obtener_cierre(DIA_A), self.cerrado)
        self.assertEqual(self.unidades(cierre.obtener_cierre(DIA_A)),
                         {"Café": 2, "Café con leche": 1})

    def test_obtener_cierre_no_recalcula_desde_las_ventas(self):
        """Se lee solo de daily_close y daily_close_item, nunca de sale."""
        from app import cierre, db
        sentencias = []
        original = db.get_connection

        def espiada():
            c = original(); c.set_trace_callback(sentencias.append); return c

        with mock.patch("app.cierre.get_connection", espiada):
            cierre.obtener_cierre(DIA_A)

        tablas = " ".join(s.upper() for s in sentencias)
        self.assertIn("DAILY_CLOSE", tablas)
        self.assertNotRegex(tablas, r"FROM SALE\b|JOIN SALE\b|FROM PRODUCT\b")


# ------------------------------------------------------------------------- 11

class TestAtomicidadDelCierre(BaseCierre):

    def test_si_falla_una_linea_del_cierre_no_queda_nada(self):
        from app import cierre, resumen
        self.caso_preproduccion()
        original = resumen._resumen_en_conexion

        def roto(conn, fecha):
            r = original(conn, fecha)
            r["unidades"] = r["unidades"] + [{"nombre": "Roto", "unidades": 0}]
            return r

        with mock.patch.object(resumen, "_resumen_en_conexion", roto):
            with self.assertRaises(sqlite3.IntegrityError):
                cierre.cerrar_dia(DIA_A, momento=DESPUES)

        self.assertEqual(self.contar("daily_close"), 0, "no puede quedar cabecera")
        self.assertEqual(self.contar("daily_close_item"), 0, "no pueden quedar lineas")
        self.assertIsNone(cierre.obtener_cierre(DIA_A))

        # El dia sigue abierto: se puede seguir vendiendo en el.
        self.vender([self.linea(self.id_cafe, "Café", 140, 1)], datetime(2026, 9, 17, 21, 0))
        self.assertEqual(self.contar("sale"), 3)


# ---------------------------------------------------------------- 12, 13, 14

class TestBloqueoTrasElCierre(BaseCierre):

    def setUp(self):
        super().setUp()
        self.v1, self.v2 = self.caso_preproduccion()
        self.cerrar(DIA_A)

    def test_no_se_puede_registrar_una_venta_del_dia_cerrado(self):
        from app import cart, cierre, sales
        cart.cancelar()
        cart.anadir(self.id_cafe, "Café", 140)
        antes = cart.lineas()
        ventas, lineas = self.contar("sale"), self.contar("sale_item")

        with self.assertRaises(cierre.DiaCerrado):
            sales.confirmar_venta(cart.lineas(), momento=datetime(2026, 9, 17, 22, 0))

        self.assertEqual(self.contar("sale"), ventas, "ninguna cabecera nueva")
        self.assertEqual(self.contar("sale_item"), lineas, "ninguna linea nueva")
        self.assertEqual(cart.lineas(), antes, "el carrito no se toca")
        cart.cancelar()

    def test_no_se_puede_anular_una_venta_del_dia_cerrado(self):
        from app import cierre, sales
        with self.assertRaises(cierre.DiaCerrado):
            sales.anular_venta(self.v1["id"], momento=datetime(2026, 9, 18, 9, 0))

        fila = self.conexion().execute(
            "SELECT status, voided_at FROM sale WHERE id = ?", (self.v1["id"],)).fetchone()
        self.assertEqual(fila["status"], "VALID")
        self.assertIsNone(fila["voided_at"])

    def test_una_venta_anulada_del_dia_cerrado_sigue_anulada(self):
        from app import sales
        antes = self.conexion().execute(
            "SELECT status, voided_at FROM sale WHERE id = ?", (self.v2["id"],)).fetchone()
        with self.assertRaises(sales.VentaYaAnulada):
            sales.anular_venta(self.v2["id"])
        despues = self.conexion().execute(
            "SELECT status, voided_at FROM sale WHERE id = ?", (self.v2["id"],)).fetchone()
        self.assertEqual(tuple(despues), tuple(antes))
        self.assertEqual(despues["status"], "VOID")

    def test_otro_dia_sigue_funcionando_con_normalidad(self):
        from app import sales
        otra = self.vender([self.linea(self.id_cafe, "Café", 140, 1)],
                           datetime(2026, 9, 18, 10, 0))
        sales.anular_venta(otra["id"], momento=datetime(2026, 9, 18, 10, 5))

        fila = self.conexion().execute(
            "SELECT status FROM sale WHERE id = ?", (otra["id"],)).fetchone()
        self.assertEqual(fila["status"], "VOID")
        self.cerrar(DIA_B)   # y el dia B se puede cerrar despues


# ------------------------------------------------------------------------- 15

class TestCarrera(BaseCierre):
    """Un cierre en curso tiene el bloqueo de escritura. Una venta o anulacion
    que llega a la vez ESPERA, y cuando por fin entra ve el dia ya cerrado.

    Si la comprobacion del dia se hiciera antes de tomar el bloqueo, la venta
    pasaria la comprobacion con el dia aun abierto y se escribiria despues del
    cierre. Estos tests fallarian en ese caso.
    """

    def _cierre_a_medias(self, fecha):
        """Abre un BEGIN IMMEDIATE que inserta el cierre y aun no hace COMMIT."""
        conn = sqlite3.connect(self.ruta, isolation_level=None)
        self._conexiones.append(conn)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO daily_close (close_number, business_date, closed_at,"
            " valid_sales_count, void_sales_count, gross_cents, void_cents,"
            " valid_cash_cents) VALUES ('C-2026-000001', ?, '2026-09-17 23:00:00',"
            " 0, 0, 0, 0, 0)", (fecha,))
        return conn

    def _en_paralelo(self, funcion):
        resultado = {}

        def ejecutar():
            try:
                resultado["valor"] = funcion()
            except Exception as error:   # noqa: BLE001 - se examina en el test
                resultado["error"] = error

        hilo = threading.Thread(target=ejecutar)
        hilo.start()
        return hilo, resultado

    def test_una_venta_que_llega_durante_el_cierre_espera_y_se_rechaza(self):
        from app import cierre, sales
        conn = self._cierre_a_medias(DIA_A)

        hilo, resultado = self._en_paralelo(lambda: sales.confirmar_venta(
            [self.linea(self.id_cafe, "Café", 140, 1)],
            momento=datetime(2026, 9, 17, 22, 0)))
        time.sleep(0.6)
        self.assertTrue(hilo.is_alive(), "la venta debe esperar al bloqueo del cierre")

        conn.execute("COMMIT")
        hilo.join(10)

        self.assertIsInstance(resultado.get("error"), cierre.DiaCerrado)
        self.assertEqual(self.contar("sale"), 0)
        self.assertEqual(self.contar("sale_item"), 0)

    def test_una_anulacion_que_llega_durante_el_cierre_espera_y_se_rechaza(self):
        from app import cierre, sales
        venta = self.vender([self.linea(self.id_cafe, "Café", 140, 1)],
                            datetime(2026, 9, 17, 9, 0))
        conn = self._cierre_a_medias(DIA_A)

        hilo, resultado = self._en_paralelo(lambda: sales.anular_venta(venta["id"]))
        time.sleep(0.6)
        self.assertTrue(hilo.is_alive(), "la anulacion debe esperar al bloqueo del cierre")

        conn.execute("COMMIT")
        hilo.join(10)

        self.assertIsInstance(resultado.get("error"), cierre.DiaCerrado)
        fila = self.conexion().execute(
            "SELECT status, voided_at FROM sale WHERE id = ?", (venta["id"],)).fetchone()
        self.assertEqual((fila["status"], fila["voided_at"]), ("VALID", None))

    def test_un_cierre_que_llega_durante_una_venta_la_incluye(self):
        """Al reves: la venta tiene el bloqueo y el cierre espera. El cierre
        incluye la venta, porque ve la base despues de su COMMIT."""
        from app import cierre
        conn = sqlite3.connect(self.ruta, isolation_level=None)
        self._conexiones.append(conn)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO sale (sale_number, created_at, total_cents, status)"
                     " VALUES ('V-2026-000001', '2026-09-17 22:00:00', 140, 'VALID')")
        conn.execute("INSERT INTO sale_item (sale_id, product_id, product_name_snapshot,"
                     " unit_price_cents_snapshot, quantity, subtotal_cents)"
                     " VALUES (last_insert_rowid(), ?, 'Café', 140, 1, 140)", (self.id_cafe,))

        hilo, resultado = self._en_paralelo(
            lambda: cierre.cerrar_dia(DIA_A, momento=DESPUES))
        time.sleep(0.6)
        self.assertTrue(hilo.is_alive(), "el cierre debe esperar a la venta")

        conn.execute("COMMIT")
        hilo.join(10)

        c = resultado.get("valor")
        self.assertIsNotNone(c, resultado.get("error"))
        self.assertEqual(c["valid_sales_count"], 1)
        self.assertEqual(c["valid_cash_cents"], 140)


# ------------------------------------------------------------------ migracion

class TestMigracion(unittest.TestCase):
    """Una base de la FASE 5, con ventas, recibe las tablas de cierre sin perder nada."""

    def test_init_db_crea_las_tablas_de_cierre_sin_tocar_las_ventas(self):
        import os
        import tempfile
        from app import db

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            ruta = Path(tmp) / "fase5.sqlite"
            anterior = os.environ.get("CAFETERIA_DB")
            os.environ["CAFETERIA_DB"] = str(ruta)
            try:
                db.init_db()
                conn = sqlite3.connect(ruta)
                conn.executescript("""
                    DROP TABLE daily_close_item; DROP TABLE daily_close;
                    INSERT INTO product (name, price_cents) VALUES ('Café', 140);
                    INSERT INTO sale (sale_number, created_at, total_cents)
                        VALUES ('V-2026-000001', '2026-09-17 19:44:19', 140);
                    INSERT INTO sale_item (sale_id, product_id, product_name_snapshot,
                        unit_price_cents_snapshot, quantity, subtotal_cents)
                        VALUES (1, 1, 'Café', 140, 1, 140);
                """)
                antes = (list(conn.execute("SELECT * FROM sale")),
                         list(conn.execute("SELECT * FROM sale_item")))
                conn.close()

                db.init_db()

                conn = sqlite3.connect(ruta)
                tablas = {r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                despues = (list(conn.execute("SELECT * FROM sale")),
                           list(conn.execute("SELECT * FROM sale_item")))
                conn.close()
            finally:
                if anterior is None:
                    os.environ.pop("CAFETERIA_DB", None)
                else:
                    os.environ["CAFETERIA_DB"] = anterior

        self.assertIn("daily_close", tablas)
        self.assertIn("daily_close_item", tablas)
        self.assertEqual(despues, antes)


# ------------------------------------------------------------ salvaguarda

class TestSinEdicionNiBorrado(unittest.TestCase):

    def test_el_codigo_no_actualiza_ni_borra_cierres(self):
        """No existe reapertura, edicion ni borrado de cierres."""
        raiz_app = Path(__file__).resolve().parent.parent / "app"
        prohibido = re.compile(
            r"(DELETE\s+FROM|UPDATE)\s+(daily_close|daily_close_item)\b", re.IGNORECASE)
        encontrados = [
            f"{a.name}:{n}: {l.strip()}"
            for a in raiz_app.rglob("*.py")
            for n, l in enumerate(a.read_text(encoding="utf-8").splitlines(), 1)
            if prohibido.search(l)
        ]
        self.assertEqual(encontrados, [])


# ------------------------------------------------------------------------- 16

class TestRutaCierre(BaseCierre):

    def setUp(self):
        super().setUp()
        from app import cart, create_app
        cart.cancelar()
        self.cliente = create_app().test_client()
        self.caso_preproduccion()
        self.parche = mock.patch("app.resumen.hoy", return_value=DIA_A)
        self.parche.start()
        # El cierre por la web usa la hora real; se fija para no cerrar "un dia futuro".
        self.parche_dt = mock.patch("app.cierre.datetime")
        dt = self.parche_dt.start()
        dt.now.return_value = DESPUES

    def tearDown(self):
        self.parche_dt.stop()
        self.parche.stop()
        from app import cart
        cart.cancelar()
        super().tearDown()

    def test_previsualizacion_correcta_y_con_boton(self):
        html = self.cliente.get("/cierre").get_data(as_text=True)

        self.assertIn("PREVISUALIZACIÓN", html)
        self.assertIn('id="business-date">2026-09-17<', html)
        self.assertIn('id="first-sale">V-2026-000001<', html)
        self.assertIn('id="last-sale">V-2026-000002<', html)
        self.assertIn('id="valid-count">1<', html)
        self.assertIn('id="void-count">1<', html)
        self.assertIn('id="gross">7,75 €<', html)
        self.assertIn('id="void">3,30 €<', html)
        self.assertIn('id="valid-cash">4,45 €<', html)
        self.assertIn("CERRAR DÍA", html)
        self.assertIn("confirm(", html)
        self.assertIn("ya no se podrán registrar ni anular ventas de esa fecha", html)
        self.assertEqual(self.contar("daily_close"), 0, "previsualizar no cierra")

    def test_cerrar_por_la_web(self):
        r = self.cliente.post("/cierre", data={"fecha": DIA_A})
        self.assertEqual(r.status_code, 302)

        html = self.cliente.get(r.headers["Location"]).get_data(as_text=True)
        self.assertIn("Día 2026-09-17 cerrado: C-2026-000001.", html)
        self.assertIn("DÍA CERRADO", html)
        self.assertIn('id="close-number">C-2026-000001<', html)
        self.assertIn('id="valid-cash">4,45 €<', html)
        self.assertNotIn("CERRAR DÍA</button>", html)
        self.assertEqual(self.contar("daily_close"), 1)

    def test_un_segundo_post_no_crea_otro_cierre(self):
        from app import cierre
        self.cliente.post("/cierre", data={"fecha": DIA_A})
        primero = cierre.obtener_cierre(DIA_A)

        r = self.cliente.post("/cierre", data={"fecha": DIA_A})

        self.assertEqual(r.status_code, 409)
        self.assertIn("ya está cerrado", r.get_data(as_text=True))
        self.assertEqual(self.contar("daily_close"), 1)
        self.assertEqual(cierre.obtener_cierre(DIA_A), primero)

    def test_una_fecha_anterior_a_ayer_no_se_cierra_por_la_web(self):
        # Hoy es el 17 en esta clase: se admiten el 17 y el 16, no el 15.
        r = self.cliente.post("/cierre", data={"fecha": "2026-09-15"})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.contar("daily_close"), 0)

    def test_cobrar_con_el_dia_cerrado_devuelve_409_y_conserva_el_carrito(self):
        from app import cart
        self.cliente.post("/cierre", data={"fecha": DIA_A})
        cart.anadir(self.id_cafe, "Café", 140)
        antes = cart.lineas()

        with mock.patch("app.sales.datetime") as dt:
            dt.now.return_value = datetime(2026, 9, 17, 23, 30)
            r = self.cliente.post("/venta/cobrar")

        self.assertEqual(r.status_code, 409)
        self.assertIn("ya está cerrado", r.get_data(as_text=True))
        self.assertEqual(cart.lineas(), antes)
        self.assertEqual(self.contar("sale"), 2)

    def test_anular_con_el_dia_cerrado_devuelve_409(self):
        self.cliente.post("/cierre", data={"fecha": DIA_A})
        r = self.cliente.post("/historial/1/anular")

        self.assertEqual(r.status_code, 409)
        fila = self.conexion().execute("SELECT status FROM sale WHERE id = 1").fetchone()
        self.assertEqual(fila["status"], "VALID")

    def test_la_interfaz_no_ofrece_acciones_sobre_un_dia_cerrado(self):
        self.cliente.post("/cierre", data={"fecha": DIA_A})

        historial = self.cliente.get("/historial").get_data(as_text=True)
        self.assertNotIn("/historial/1/anular", historial)
        self.assertIn("Día cerrado", historial)

        inicio = self.cliente.get("/").get_data(as_text=True)
        self.assertIn('id="aviso-dia-cerrado"', inicio)
        self.assertRegex(inicio, r'class="boton-cobrar"\s+disabled')


# -------------------------------------------------- cierre despues de medianoche

class TestCierreDespuesDeMedianoche(BaseCierre):
    """Son las 00:30 del dia B. El dia A (ayer) sigue abierto y se cierra ahora.

    La interfaz de cierre permite cerrar hoy o ayer para poder hacer el cierre
    despues de medianoche; las ventas siguen perteneciendo estrictamente a su
    fecha natural de created_at.
    """

    A_MENOS_1 = "2026-09-16"
    A = DIA_A                       # 2026-09-17, ayer
    B = DIA_B                       # 2026-09-18, hoy
    FUTURO = "2026-09-19"
    AHORA = datetime(2026, 9, 18, 0, 30, 0)

    def setUp(self):
        super().setUp()
        from app import cart, create_app
        cart.cancelar()
        self.cliente = create_app().test_client()

        # Dia A: la situacion de preproduccion (445 valido + 330 anulado).
        self.caso_preproduccion()
        # Dia B, 00:05: una venta despues de medianoche pertenece a B.
        self.venta_b = self.vender([self.linea(self.id_cafe, "Café", 140, 3)],
                                   datetime(2026, 9, 18, 0, 5, 0))

        self.parche_hoy = mock.patch("app.resumen.hoy", return_value=self.B)
        self.parche_hoy.start()
        self.parche_dt = mock.patch("app.cierre.datetime")
        self.parche_dt.start().now.return_value = self.AHORA

    def tearDown(self):
        self.parche_dt.stop()
        self.parche_hoy.stop()
        super().tearDown()

    def pagina(self, url):
        r = self.cliente.get(url)
        self.assertEqual(r.status_code, 200)
        return r.get_data(as_text=True)

    # 1 y 2
    def test_a_las_0030_se_visualiza_y_se_cierra_el_dia_anterior(self):
        from app import cierre
        html = self.pagina("/cierre?dia=ayer")
        self.assertIn('id="business-date">2026-09-17<', html)
        self.assertIn("CERRAR DÍA", html)

        r = self.cliente.post("/cierre", data={"fecha": self.A})
        self.assertEqual(r.status_code, 302)

        c = cierre.obtener_cierre(self.A)
        self.assertEqual(c["business_date"], self.A)
        self.assertEqual(c["closed_at"], "2026-09-18 00:30:00")
        self.assertEqual(c["valid_cash_cents"], 445)

    def test_la_venta_de_las_0005_no_entra_en_el_cierre_del_dia_anterior(self):
        from app import cierre
        self.cliente.post("/cierre", data={"fecha": self.A})
        c = cierre.obtener_cierre(self.A)

        # Solo las ventas de A: la de las 00:05 de B no aparece.
        self.assertEqual(c["valid_sales_count"], 1)
        self.assertEqual(c["gross_cents"], 775)
        self.assertEqual(c["last_sale_number"], "V-2026-000002")
        self.assertEqual(self.unidades(c), {"Café": 2, "Café con leche": 1})

        # Y sigue perteneciendo a B, que continua abierto y admite ventas.
        p = cierre.previsualizar_cierre(self.B)
        self.assertEqual(p["valid_sales_count"], 1)
        self.assertEqual(p["first_sale_number"], self.venta_b["sale_number"])
        self.assertEqual(p["valid_cash_cents"], 420)
        self.assertFalse(cierre.dia_esta_cerrado(self.B))

    # 3 y 4
    def test_por_defecto_muestra_hoy(self):
        html = self.pagina("/cierre")
        self.assertIn('id="business-date">2026-09-18<', html)
        self.assertRegex(html, r'class="activo" id="ver-hoy"')

    def test_seleccionar_ayer_muestra_el_dia_anterior(self):
        html = self.pagina("/cierre?dia=ayer")
        self.assertIn('id="business-date">2026-09-17<', html)
        self.assertRegex(html, r'class="activo" id="ver-ayer"')
        self.assertIn('id="valid-cash">4,45 €<', html)

    def test_el_control_solo_ofrece_hoy_y_ayer(self):
        html = self.pagina("/cierre")
        self.assertIn("Hoy (2026-09-18)", html)
        self.assertIn("Ayer (2026-09-17)", html)
        self.assertNotIn('type="date"', html)

    def test_por_get_no_se_puede_ver_otra_fecha(self):
        for url in ("/cierre?dia=2026-09-16", "/cierre?dia=anteayer",
                    "/cierre?fecha=2026-09-16"):
            with self.subTest(url=url):
                html = self.pagina(url)
                self.assertIn('id="business-date">2026-09-18<', html)

    # 5 y 6
    def test_post_para_ayer_funciona_y_vuelve_a_la_vista_de_ayer(self):
        r = self.cliente.post("/cierre", data={"fecha": self.A})
        self.assertEqual(r.status_code, 302)
        self.assertIn("dia=ayer", r.headers["Location"])

        html = self.pagina(r.headers["Location"])
        self.assertIn("Día 2026-09-17 cerrado: C-2026-000001.", html)
        self.assertIn("DÍA CERRADO", html)

    def test_post_para_hoy_funciona(self):
        from app import cierre
        r = self.cliente.post("/cierre", data={"fecha": self.B})
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("dia=ayer", r.headers["Location"])
        self.assertEqual(cierre.obtener_cierre(self.B)["valid_cash_cents"], 420)

    def test_cerrar_ayer_y_hoy_da_numeros_correlativos(self):
        from app import cierre
        self.cliente.post("/cierre", data={"fecha": self.A})
        self.cliente.post("/cierre", data={"fecha": self.B})
        self.assertEqual(cierre.obtener_cierre(self.A)["close_number"], "C-2026-000001")
        self.assertEqual(cierre.obtener_cierre(self.B)["close_number"], "C-2026-000002")

    # 7
    def test_post_para_anteayer_se_rechaza(self):
        r = self.cliente.post("/cierre", data={"fecha": self.A_MENOS_1})
        self.assertEqual(r.status_code, 409)
        self.assertIn("solo se puede cerrar hoy (2026-09-18) o ayer (2026-09-17)",
                      r.get_data(as_text=True))
        self.assertEqual(self.contar("daily_close"), 0)

    # 8
    def test_fecha_futura_se_rechaza(self):
        r = self.cliente.post("/cierre", data={"fecha": self.FUTURO})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.contar("daily_close"), 0)

    def test_fecha_vacia_o_mal_formada_se_rechaza(self):
        for fecha in ("", "ayer", "18/09/2026", "2026-9-17"):
            with self.subTest(fecha=fecha):
                r = self.cliente.post("/cierre", data={"fecha": fecha})
                self.assertEqual(r.status_code, 409)
        self.assertEqual(self.contar("daily_close"), 0)

    def test_la_funcion_interna_sigue_pudiendo_cerrar_fechas_anteriores(self):
        """cerrar_dia() conserva su capacidad para operaciones controladas."""
        from app import cierre
        c = cierre.cerrar_dia(self.A_MENOS_1, momento=self.AHORA)
        self.assertEqual(c["business_date"], self.A_MENOS_1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
