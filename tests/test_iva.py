r"""Tests del desglose de IVA congelado en el cierre (FASE 7).

Decision explicita: IVA unico del 10 % para todo lo que registra este TPV
temporal. El efectivo valido es IVA incluido; cada cierre congela tipo, base
imponible y cuota, y el PDF los imprime sin recalcularlos.

Valores FICTICIOS. Nunca datos reales.

    .venv\Scripts\python.exe -m unittest discover -s tests -v
"""

import hashlib
import importlib.util
import io
import re
import sqlite3
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_cierre import DIA_A, DIA_B, EMPRESA, SNAPSHOTS  # noqa: E402
from test_pdf import BasePDF, lineas_pdf, tiene_linea  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "congelar_establecimiento_en_cierres.py"
IVA = ("vat_rate_percent", "vat_base_cents", "vat_cents")


def cargar_script():
    spec = importlib.util.spec_from_file_location("congelar", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class TestCalculo(unittest.TestCase):

    def test_ejemplo_de_40_60(self):
        from app.cierre import desglose_iva
        self.assertEqual(desglose_iva(4060), (3691, 369))

    def test_casos_concretos(self):
        from app.cierre import desglose_iva
        casos = {0: (0, 0), 1: (1, 0), 11: (10, 1), 110: (100, 10), 445: (405, 40),
                 775: (705, 70), 8000: (7273, 727), 999_999: (909_090, 90_909)}
        for total, esperado in casos.items():
            with self.subTest(total=total):
                self.assertEqual(desglose_iva(total), esperado)

    def test_exacto_en_centimos_para_todos_los_totales(self):
        """0 .. 100.000 centimos: enteros, base + IVA = total, y la base es el
        centimo mas cercano al valor exacto total / 1,10 (calculado con Fraction)."""
        from app.cierre import desglose_iva
        for total in range(0, 100_001):
            base, cuota = desglose_iva(total)
            self.assertIs(type(base), int)
            self.assertIs(type(cuota), int)
            self.assertEqual(base + cuota, total)
            self.assertGreaterEqual(cuota, 0)
            self.assertLessEqual(abs(Fraction(total * 100, 110) - base), Fraction(1, 2))

    def test_rechaza_totales_no_enteros_o_negativos(self):
        from app.cierre import desglose_iva
        for malo in (-1, 40.6, "4060", None):
            with self.subTest(total=malo), self.assertRaises(ValueError):
                desglose_iva(malo)

    def test_el_calculo_no_usa_float(self):
        texto = (RAIZ / "app" / "cierre.py").read_text(encoding="utf-8")
        self.assertNotRegex(texto, r"\bfloat\s*\(")
        self.assertIn("Decimal", texto)


class BaseIva(BasePDF):

    def vender_40_60(self, fecha=datetime(2026, 9, 17, 10, 0)):
        """29 cafes a 1,40 € = 40,60 €."""
        return self.vender([self.linea(self.id_cafe, "Café", 140, 29)], fecha)

    def iva_guardado(self, fecha=DIA_A):
        return tuple(self.conexion().execute(
            "SELECT vat_rate_percent, vat_base_cents, vat_cents, valid_cash_cents"
            " FROM daily_close WHERE business_date = ?", (fecha,)).fetchone())


class TestCierreCongelaElIva(BaseIva):

    def test_el_cierre_congela_el_10_y_el_desglose(self):
        self.vender_40_60()
        c = self.cerrar(DIA_A)
        self.assertEqual((c["vat_rate_percent"], c["vat_base_cents"], c["vat_cents"]),
                         (10, 3691, 369))
        self.assertEqual(self.iva_guardado(), (10, 3691, 369, 4060))

    def test_base_mas_iva_es_el_efectivo_valido_guardado(self):
        self.caso_preproduccion()                        # 445 validos, 330 anulados
        self.cerrar(DIA_A)
        tipo, base, cuota, efectivo = self.iva_guardado()
        self.assertEqual(base + cuota, efectivo)
        self.assertEqual((tipo, base, cuota, efectivo), (10, 405, 40, 445))

    def test_las_anuladas_no_llevan_iva(self):
        self.caso_preproduccion()
        c = self.cerrar(DIA_A)
        self.assertEqual(c["vat_base_cents"] + c["vat_cents"], c["valid_cash_cents"])
        self.assertNotEqual(c["vat_base_cents"] + c["vat_cents"], c["gross_cents"])

    def test_dia_con_0_euros(self):
        c = self.cerrar(DIA_A)
        self.assertEqual((c["vat_rate_percent"], c["vat_base_cents"], c["vat_cents"]),
                         (10, 0, 0))
        L = lineas_pdf(self.generar(DIA_A).read_bytes())
        self.assertTrue(tiene_linea(L, r"Base imponible\s+0,00 €"))
        self.assertTrue(tiene_linea(L, r"IVA 10 %\s+0,00 €"))
        self.assertTrue(tiene_linea(L, r"TOTAL IVA INCLUIDO\s+0,00 €"))

    def test_la_previsualizacion_muestra_el_mismo_desglose(self):
        from app import cierre
        self.vender_40_60()
        previa = cierre.previsualizar_cierre(DIA_A)
        guardado = self.cerrar(DIA_A)
        self.assertEqual(tuple(previa[k] for k in IVA), tuple(guardado[k] for k in IVA))


class TestPdfIva(BaseIva):

    def setUp(self):
        super().setUp()
        self.vender_40_60()
        self.cerrar(DIA_A)

    def test_bloque_desglose_iva(self):
        L = lineas_pdf(self.generar(DIA_A).read_bytes())
        i = L.index("DESGLOSE IVA")
        self.assertRegex(L[i + 1], r"^Base imponible\s+36,91 €$")
        self.assertRegex(L[i + 2], r"^IVA 10 %\s+3,69 €$")
        self.assertRegex(L[i + 3], r"^TOTAL IVA INCLUIDO\s+40,60 €$")
        self.assertGreater(i, L.index(next(l for l in L if l.startswith("TOTAL EFECTIVO"))))

    def test_el_pdf_imprime_lo_congelado_y_no_recalcula(self):
        antes = self.generar(DIA_A).read_bytes()
        with mock.patch("app.cierre.desglose_iva", side_effect=AssertionError("recalculo")), \
             mock.patch("app.pdf_cierre.cierre.desglose_iva",
                        side_effect=AssertionError("recalculo")):
            despues = self.generar(DIA_A).read_bytes()
        self.assertEqual(despues, antes)

        # Si el valor congelado fuera otro, el PDF mostraria ese valor: lo lee
        # de la base, no lo calcula. (Manipulacion directa solo para el test.)
        conn = self.conexion()
        conn.execute("UPDATE daily_close SET vat_base_cents = 1, vat_cents = 2")
        conn.commit()
        L = lineas_pdf(self.generar(DIA_A).read_bytes())
        self.assertTrue(tiene_linea(L, r"Base imponible\s+0,01 €"))
        self.assertTrue(tiene_linea(L, r"IVA 10 %\s+0,02 €"))

    def test_regenerar_da_los_mismos_bytes(self):
        huellas = {hashlib.sha256(self.generar(DIA_A).read_bytes()).hexdigest()
                   for _ in range(3)}
        self.assertEqual(len(huellas), 1)

    def test_cambiar_despues_cualquier_configuracion_no_altera_el_historico(self):
        """Tipo de IVA del codigo, establecimiento y catalogo: nada cambia el
        cierre guardado ni su PDF."""
        from app import cierre, establecimiento, products
        guardado = cierre.obtener_cierre(DIA_A)
        pdf = self.generar(DIA_A).read_bytes()

        establecimiento.guardar("Otra Titular Ficticia", "NIF-PRUEBA-2",
                                "Otro Bar de Prueba", "Avenida Inventada 99")
        products.actualizar_producto(self.id_cafe, "Café renombrado", 999, 10)
        with mock.patch("app.cierre.TIPO_IVA", 21):
            self.assertEqual(cierre.obtener_cierre(DIA_A), guardado)
            self.assertEqual(self.generar(DIA_A).read_bytes(), pdf)
            L = lineas_pdf(pdf)
            self.assertTrue(tiene_linea(L, r"IVA 10 %\s+3,69 €"))

            # Un cierre nuevo si usaria el tipo vigente en ese momento.
            self.vender_40_60(datetime(2026, 9, 18, 10, 0))
            nuevo = self.cerrar(DIA_B)
        self.assertEqual(nuevo["vat_rate_percent"], 21)
        self.assertEqual(cierre.obtener_cierre(DIA_A), guardado)

    def test_un_cierre_sin_iva_congelado_no_genera_pdf(self):
        from app import pdf_cierre
        conn = self.conexion()
        conn.execute("UPDATE daily_close SET vat_rate_percent = NULL,"
                     " vat_base_cents = NULL, vat_cents = NULL")
        conn.commit()
        for f in self.exports.iterdir():
            f.unlink()
        with self.assertRaises(pdf_cierre.CierreIncompleto) as ctx:
            self.generar(DIA_A)
        self.assertIn("IVA", str(ctx.exception))
        self.assertEqual(list(self.exports.iterdir()), [])


class TestMigracionIva(BaseIva):
    """Un cierre 'antiguo' sin IVA congelado, como C-2026-000001."""

    def setUp(self):
        super().setUp()
        self.script = cargar_script()
        self.caso_preproduccion()                        # 445 validos
        self.cerrar(DIA_A)
        conn = self.conexion()
        conn.execute("UPDATE daily_close SET vat_rate_percent = NULL,"
                     " vat_base_cents = NULL, vat_cents = NULL")
        conn.commit()

    def ejecutar(self, *argv):
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = self.script.main(list(argv))
        return codigo, salida.getvalue()

    def quitar_columnas(self):
        conn = sqlite3.connect(self.ruta)
        for c in IVA:
            conn.execute(f"ALTER TABLE daily_close DROP COLUMN {c}")
        conn.commit(); conn.close()

    def test_sin_aplicar_no_cambia_ni_un_byte(self):
        antes = self.hash_base()
        codigo, salida = self.ejecutar()
        self.assertEqual(codigo, 0)
        self.assertIn("Pendientes (desglose de IVA 10 %) 1 cierre(s): C-2026-000001", salida)
        self.assertEqual(self.hash_base(), antes)

    def test_base_sin_columnas_sin_aplicar_no_cambia_ni_un_byte(self):
        self.quitar_columnas()
        antes = self.hash_base()
        codigo, salida = self.ejecutar()
        self.assertEqual(codigo, 0)
        self.assertEqual(self.hash_base(), antes)
        self.assertIn("Faltan las columnas vat_rate_percent", salida)
        conn = sqlite3.connect(self.ruta)
        columnas = {f[1] for f in conn.execute("PRAGMA table_info(daily_close)")}
        conn.close()
        self.assertFalse(columnas & set(IVA))

    def test_aplicar_congela_el_desglose_del_efectivo_guardado(self):
        codigo, salida = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 0)
        self.assertIn("Completados (desglose de IVA 10 %) 1 cierre(s): C-2026-000001", salida)
        self.assertEqual(self.iva_guardado(), (10, 405, 40, 445))

    def test_usa_el_efectivo_del_cierre_no_las_ventas(self):
        # Ventas alteradas a mano despues del cierre: la migracion las ignora.
        conn = self.conexion()
        conn.execute("UPDATE sale SET total_cents = 99999")
        conn.commit()
        self.ejecutar("--aplicar")
        self.assertEqual(self.iva_guardado(), (10, 405, 40, 445))

    def test_solo_cambian_las_tres_columnas(self):
        q = "SELECT * FROM daily_close"
        antes = dict(self.conexion().execute(q).fetchone())
        items = list(map(tuple, self.conexion().execute("SELECT * FROM daily_close_item")))
        self.ejecutar("--aplicar")
        despues = dict(self.conexion().execute(q).fetchone())
        self.assertEqual({k for k in antes if antes[k] != despues[k]}, set(IVA))
        self.assertEqual(list(map(tuple, self.conexion().execute(
            "SELECT * FROM daily_close_item"))), items)

    def test_idempotente_y_no_toca_cierres_ya_congelados(self):
        self.ejecutar("--aplicar")
        self.vender_40_60(datetime(2026, 9, 18, 10, 0))
        with mock.patch("app.cierre.TIPO_IVA", 21):
            self.cerrar(DIA_B)                           # congelado al 21 (ficticio)
        antes = self.hash_base()
        codigo, salida = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 0)
        self.assertIn("No hay cierres pendientes", salida)
        self.assertEqual(self.hash_base(), antes)
        self.assertEqual(self.iva_guardado(DIA_A)[:3], (10, 405, 40))
        self.assertEqual(self.iva_guardado(DIA_B)[0], 21)

    def test_un_cierre_parcial_detiene_todo(self):
        conn = self.conexion()
        conn.execute("UPDATE daily_close SET vat_rate_percent = 10")
        conn.commit()
        antes = self.hash_base()
        codigo, salida = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 1)
        self.assertIn("C-2026-000001", salida)
        self.assertEqual(self.hash_base(), antes)

    def test_migra_una_base_sin_las_columnas_y_despues_hay_pdf(self):
        from app import pdf_cierre
        self.quitar_columnas()
        codigo, _ = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 0)
        self.assertEqual(self.iva_guardado(), (10, 405, 40, 445))
        L = lineas_pdf(pdf_cierre.generar_pdf_cierre(DIA_A).read_bytes())
        self.assertTrue(tiene_linea(L, r"Base imponible\s+4,05 €"))
        self.assertTrue(tiene_linea(L, r"IVA 10 %\s+0,40 €"))
        self.assertTrue(tiene_linea(L, r"TOTAL IVA INCLUIDO\s+4,45 €"))

    def test_la_salida_no_muestra_importes_ni_datos(self):
        for argv in ((), ("--aplicar",), ("--aplicar",)):
            _, salida = self.ejecutar(*argv)
            with self.subTest(argv=argv):
                self.assertNotIn("€", salida)
                self.assertNotRegex(salida, r"\b(405|40|445)\b")
                for valor in EMPRESA:
                    self.assertNotIn(valor, salida)

    def test_arrancar_la_app_no_rellena_el_iva(self):
        from app import create_app
        create_app()
        self.assertEqual(self.iva_guardado()[:3], (None, None, None))


class TestMigracionConjunta(BaseIva):
    """Un cierre de la FASE 6: ni datos del establecimiento ni IVA congelados."""

    def setUp(self):
        super().setUp()
        self.script = cargar_script()
        self.caso_preproduccion()                        # 445 validos
        self.cerrar(DIA_A)
        conn = sqlite3.connect(self.ruta)
        for c in IVA + SNAPSHOTS:
            conn.execute(f"ALTER TABLE daily_close DROP COLUMN {c}")
        conn.commit(); conn.close()

    def ejecutar(self, *argv):
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = self.script.main(list(argv))
        return codigo, salida.getvalue()

    def test_sin_aplicar_no_modifica_ni_un_byte(self):
        antes = self.hash_base()
        codigo, salida = self.ejecutar()
        self.assertEqual(codigo, 0)
        self.assertEqual(self.hash_base(), antes)
        self.assertIn("No se han creado", salida)
        self.assertIn("Pendientes (datos del establecimiento) 1 cierre(s): C-2026-000001", salida)
        self.assertIn("Pendientes (desglose de IVA 10 %) 1 cierre(s): C-2026-000001", salida)

    def test_aplicar_completa_los_dos_grupos_en_una_ejecucion(self):
        from app import cierre
        codigo, salida = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 0)
        c = cierre.obtener_cierre(DIA_A)
        self.assertEqual(self.congelados(c), EMPRESA)
        self.assertEqual(self.iva_guardado(), (10, 405, 40, 445))
        L = lineas_pdf(self.generar(DIA_A).read_bytes())
        self.assertTrue(tiene_linea(L, r"TOTAL IVA INCLUIDO\s+4,45 €"))

    def test_sin_configuracion_no_escribe_ni_el_iva(self):
        """Todo o nada: si falta el establecimiento, tampoco se congela el IVA."""
        from app import db
        db.init_db()
        conn = self.conexion()
        conn.execute("DELETE FROM establishment")
        conn.commit()
        antes = self.hash_base()
        codigo, salida = self.ejecutar("--aplicar")
        self.assertEqual(codigo, 1)
        self.assertIn("Faltan datos del establecimiento", salida)
        self.assertEqual(self.hash_base(), antes)
        self.assertEqual(self.iva_guardado()[:3], (None, None, None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
