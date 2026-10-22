r"""Tests del resumen diario (FASE 5).

Stdlib unittest, sin dependencias nuevas:

    .venv\Scripts\python.exe -m unittest discover -s tests -v

Reutiliza BaseTemporal de test_sales: base SQLite temporal por test, la base
real nunca se toca.
"""

import sqlite3
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_sales import BaseTemporal  # noqa: E402

DIA_A = "2026-09-17"
DIA_B = "2026-09-18"


class BaseResumen(BaseTemporal):

    def vender(self, lineas, momento):
        from app import sales
        return sales.confirmar_venta(lineas, momento=momento)

    def linea(self, producto_id, nombre, precio, cantidad):
        return {"producto_id": producto_id, "nombre": nombre,
                "precio_centimos": precio, "cantidad": cantidad}

    def caso_preproduccion(self):
        """Reproduce la base de preproduccion: 4,45 VALID y 3,30 anulada el dia B."""
        from app import sales
        v1 = self.vender([self.linea(self.id_cafe, "Café", 140, 2),
                          self.linea(self.id_leche, "Café con leche", 165, 1)],
                         datetime(2026, 9, 17, 19, 44, 19))
        v2 = self.vender([self.linea(self.id_leche, "Café con leche", 165, 2)],
                         datetime(2026, 9, 17, 19, 44, 40))
        sales.anular_venta(v2["id"], momento=datetime(2026, 9, 18, 16, 47, 22))
        return v1, v2

    def resumen(self, fecha):
        from app import resumen
        return resumen.resumen_del_dia(fecha)

    def unidades(self, r):
        return {u["nombre"]: u["unidades"] for u in r["unidades"]}


class TestDiaSinVentas(BaseResumen):

    def test_un_dia_sin_ventas_da_todo_a_cero(self):
        r = self.resumen(DIA_A)

        self.assertEqual(r["fecha"], DIA_A)
        self.assertEqual(r["ventas_validas"], 0)
        self.assertEqual(r["efectivo_valido_centimos"], 0)
        self.assertEqual(r["ventas_anuladas"], 0)
        self.assertEqual(r["total_anulado_centimos"], 0)
        self.assertEqual(r["unidades"], [])


class TestCasoPreproduccion(BaseResumen):

    def test_una_valida_de_445_y_una_anulada_de_330(self):
        self.caso_preproduccion()
        r = self.resumen(DIA_A)

        self.assertEqual(r["ventas_validas"], 1)
        self.assertEqual(r["efectivo_valido_centimos"], 445)
        self.assertEqual(r["ventas_anuladas"], 1)
        self.assertEqual(r["total_anulado_centimos"], 330)
        self.assertEqual(self.unidades(r), {"Café": 2, "Café con leche": 1})


class TestUnidades(BaseResumen):

    def test_las_unidades_cuentan_solo_ventas_validas(self):
        from app import sales
        self.vender([self.linea(self.id_cafe, "Café", 140, 3)],
                    datetime(2026, 9, 17, 9, 0, 0))
        anulada = self.vender([self.linea(self.id_cafe, "Café", 140, 5),
                               self.linea(self.id_leche, "Café con leche", 165, 4)],
                              datetime(2026, 9, 17, 10, 0, 0))
        sales.anular_venta(anulada["id"], momento=datetime(2026, 9, 17, 10, 5, 0))

        r = self.resumen(DIA_A)
        # Solo las 3 unidades de la venta valida. "Café con leche" solo aparecia
        # en la anulada, asi que ni siquiera figura.
        self.assertEqual(self.unidades(r), {"Café": 3})

    def test_la_anulada_suma_su_importe_en_anulado_pero_no_sus_unidades(self):
        from app import sales
        anulada = self.vender([self.linea(self.id_leche, "Café con leche", 165, 2)],
                              datetime(2026, 9, 17, 11, 0, 0))
        sales.anular_venta(anulada["id"], momento=datetime(2026, 9, 17, 11, 1, 0))

        r = self.resumen(DIA_A)
        self.assertEqual(r["total_anulado_centimos"], 330)
        self.assertEqual(r["ventas_anuladas"], 1)
        self.assertEqual(r["ventas_validas"], 0)
        self.assertEqual(r["efectivo_valido_centimos"], 0)
        self.assertEqual(r["unidades"], [])

    def test_la_misma_linea_repartida_en_varias_ventas_se_suma(self):
        self.vender([self.linea(self.id_cafe, "Café", 140, 2)], datetime(2026, 9, 17, 8, 0))
        self.vender([self.linea(self.id_cafe, "Café", 140, 1)], datetime(2026, 9, 17, 9, 0))
        self.vender([self.linea(self.id_cafe, "Café", 140, 4)], datetime(2026, 9, 17, 10, 0))

        r = self.resumen(DIA_A)
        self.assertEqual(self.unidades(r), {"Café": 7})
        self.assertEqual(r["efectivo_valido_centimos"], 7 * 140)


class TestFechas(BaseResumen):

    def test_ventas_de_otra_fecha_no_se_mezclan(self):
        self.vender([self.linea(self.id_cafe, "Café", 140, 1)], datetime(2026, 9, 16, 23, 59, 59))
        self.vender([self.linea(self.id_cafe, "Café", 140, 2)], datetime(2026, 9, 17, 0, 0, 0))
        self.vender([self.linea(self.id_cafe, "Café", 140, 3)], datetime(2026, 9, 17, 23, 59, 59))
        self.vender([self.linea(self.id_cafe, "Café", 140, 4)], datetime(2026, 9, 18, 0, 0, 0))

        r16 = self.resumen("2026-09-16")
        r17 = self.resumen(DIA_A)
        r18 = self.resumen(DIA_B)

        # Los limites exactos del dia: 00:00:00 y 23:59:59 pertenecen al dia.
        self.assertEqual((r16["ventas_validas"], self.unidades(r16)), (1, {"Café": 1}))
        self.assertEqual((r17["ventas_validas"], self.unidades(r17)), (2, {"Café": 5}))
        self.assertEqual((r18["ventas_validas"], self.unidades(r18)), (1, {"Café": 4}))
        self.assertEqual(r17["efectivo_valido_centimos"], 5 * 140)

    def test_venta_del_dia_A_anulada_el_dia_B_pertenece_al_dia_A(self):
        self.caso_preproduccion()

        r_a = self.resumen(DIA_A)
        r_b = self.resumen(DIA_B)

        self.assertEqual(r_a["ventas_anuladas"], 1)
        self.assertEqual(r_a["total_anulado_centimos"], 330)

        # El dia de la anulacion no recibe nada: ni venta ni anulacion.
        self.assertEqual(r_b["ventas_validas"], 0)
        self.assertEqual(r_b["ventas_anuladas"], 0)
        self.assertEqual(r_b["total_anulado_centimos"], 0)
        self.assertEqual(r_b["unidades"], [])

    def test_una_fecha_mal_formada_se_rechaza(self):
        with self.assertRaises(ValueError):
            self.resumen("17/09/2026")


class TestSnapshots(BaseResumen):

    def test_cambiar_nombre_o_precio_del_producto_no_altera_el_resumen(self):
        from app import products
        self.caso_preproduccion()
        antes = self.resumen(DIA_A)

        products.actualizar_producto(self.id_cafe, "Café solo", 150)
        products.actualizar_producto(self.id_leche, "Cortado largo", 199)

        despues = self.resumen(DIA_A)
        self.assertEqual(despues, antes)
        self.assertEqual(self.unidades(despues), {"Café": 2, "Café con leche": 1})
        self.assertEqual(despues["efectivo_valido_centimos"], 445)


class TestEnteros(BaseResumen):

    def test_todos_los_importes_y_cantidades_son_enteros(self):
        self.caso_preproduccion()
        r = self.resumen(DIA_A)

        for campo in ("ventas_validas", "efectivo_valido_centimos",
                      "ventas_anuladas", "total_anulado_centimos"):
            with self.subTest(campo=campo):
                self.assertIs(type(r[campo]), int)
        for u in r["unidades"]:
            self.assertIs(type(u["unidades"]), int)

    def test_los_ceros_de_un_dia_vacio_tambien_son_enteros(self):
        r = self.resumen(DIA_A)
        for campo in ("ventas_validas", "efectivo_valido_centimos",
                      "ventas_anuladas", "total_anulado_centimos"):
            self.assertIs(type(r[campo]), int)


class TestCoherenciaConSQLite(BaseResumen):
    """Gate: el resumen coincide con los datos guardados, calculados por otra via."""

    def test_el_resumen_coincide_con_un_calculo_independiente(self):
        from app import sales
        self.caso_preproduccion()
        self.vender([self.linea(self.id_cafe, "Café", 140, 1)], datetime(2026, 9, 17, 12, 0))
        otra = self.vender([self.linea(self.id_cafe, "Café", 140, 3)], datetime(2026, 9, 17, 13, 0))
        sales.anular_venta(otra["id"])
        self.vender([self.linea(self.id_cafe, "Café", 140, 9)], datetime(2026, 9, 18, 9, 0))

        # Calculo independiente en Python a partir de las filas crudas.
        conn = self.conexion()
        ventas = [dict(v) for v in conn.execute("SELECT * FROM sale")
                  if v["created_at"][:10] == DIA_A]
        validas = [v for v in ventas if v["status"] == "VALID"]
        anuladas = [v for v in ventas if v["status"] == "VOID"]
        ids_validas = {v["id"] for v in validas}
        esperado_unidades = {}
        for l in conn.execute("SELECT * FROM sale_item"):
            if l["sale_id"] in ids_validas:
                nombre = l["product_name_snapshot"]
                esperado_unidades[nombre] = esperado_unidades.get(nombre, 0) + l["quantity"]

        r = self.resumen(DIA_A)
        self.assertEqual(r["ventas_validas"], len(validas))
        self.assertEqual(r["efectivo_valido_centimos"], sum(v["total_cents"] for v in validas))
        self.assertEqual(r["ventas_anuladas"], len(anuladas))
        self.assertEqual(r["total_anulado_centimos"], sum(v["total_cents"] for v in anuladas))
        self.assertEqual(self.unidades(r), esperado_unidades)

        # Y el efectivo valido cuadra con la suma de las lineas validas.
        suma_lineas = conn.execute(
            "SELECT SUM(i.subtotal_cents) FROM sale_item i JOIN sale s ON s.id = i.sale_id"
            " WHERE s.status = 'VALID' AND substr(s.created_at, 1, 10) = ?", (DIA_A,)
        ).fetchone()[0]
        self.assertEqual(r["efectivo_valido_centimos"], suma_lineas)


class TestSoloLectura(BaseResumen):

    def test_calcular_el_resumen_no_escribe_nada(self):
        """Se capturan todas las sentencias SQL: solo puede haber lecturas."""
        from app import db
        self.caso_preproduccion()

        sentencias = []
        original = db.get_connection

        def conexion_espiada():
            conn = original()
            conn.set_trace_callback(sentencias.append)
            return conn

        with mock.patch.object(db, "get_connection", conexion_espiada), \
             mock.patch("app.resumen.get_connection", conexion_espiada):
            self.resumen(DIA_A)

        primeras = [s.strip().split()[0].upper() for s in sentencias if s.strip()]
        self.assertTrue(primeras)
        escrituras = [p for p in primeras
                      if p in ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "ALTER", "DROP")]
        self.assertEqual(escrituras, [], f"el resumen no debe escribir: {sentencias}")


class TestRutaResumen(BaseResumen):

    def setUp(self):
        super().setUp()
        from app import create_app
        self.cliente = create_app().test_client()

    def pagina(self, fecha):
        with mock.patch("app.resumen.hoy", return_value=fecha):
            respuesta = self.cliente.get("/resumen")
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.get_data(as_text=True)

    def test_la_ruta_muestra_el_resumen_del_dia(self):
        self.caso_preproduccion()
        html = self.pagina(DIA_A)

        self.assertIn(DIA_A, html)
        self.assertIn('id="efectivo-valido">4,45 €<', html)
        self.assertIn('id="ventas-validas">1<', html)
        self.assertIn('id="total-anulado">3,30 €<', html)
        self.assertIn('id="ventas-anuladas">1<', html)
        self.assertRegex(html, r'producto">Café</td>\s*<td class="importe unidades">2<')
        self.assertRegex(html, r'producto">Café con leche</td>\s*<td class="importe unidades">1<')

    def test_la_ruta_de_un_dia_vacio_muestra_ceros(self):
        self.caso_preproduccion()
        html = self.pagina(DIA_B)

        self.assertIn(DIA_B, html)
        self.assertIn('id="efectivo-valido">0,00 €<', html)
        self.assertIn('id="ventas-validas">0<', html)
        self.assertIn('id="total-anulado">0,00 €<', html)
        self.assertIn("No hay unidades vendidas", html)

    def test_la_ruta_no_modifica_la_base(self):
        self.caso_preproduccion()
        conn = self.conexion()
        antes = [list(conn.execute("SELECT * FROM sale ORDER BY id")),
                 list(conn.execute("SELECT * FROM sale_item ORDER BY id"))]
        self.pagina(DIA_A)
        despues = [list(conn.execute("SELECT * FROM sale ORDER BY id")),
                   list(conn.execute("SELECT * FROM sale_item ORDER BY id"))]
        self.assertEqual(despues, antes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
