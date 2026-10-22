r"""Tests del PDF A4 del cierre (FASE 7).

Stdlib unittest, sin dependencias nuevas:

    .venv\Scripts\python.exe -m unittest discover -s tests -v

Base SQLite temporal y carpeta de exportacion temporal por test
(CAFETERIA_DB y CAFETERIA_EXPORTS): ni la base real ni exports/ se tocan.

El PDF va sin comprimir, asi que el texto se lee directamente del archivo:
cada linea del documento es una cadena "( ... ) Tj".
"""

import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_cierre import BaseCierre, CLAVES, DIA_A, DIA_B, EMPRESA, SNAPSHOTS  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
A4 = (595.28, 841.89)


# ---------------------------------------------------------------- lectura PDF

_TJ = re.compile(rb"\(((?:\\.|[^\\)])*)\) Tj")


def lineas_pdf(pdf):
    """Texto de cada linea del PDF, en orden."""
    return [re.sub(rb"\\(.)", rb"\1", m).decode("cp1252") for m in _TJ.findall(pdf)]


def paginas_pdf(pdf):
    return len(re.findall(rb"/Type /Page ", pdf))


def mediaboxes(pdf):
    return [tuple(float(x) for x in m.split()) for m in re.findall(rb"/MediaBox \[([^\]]+)\]", pdf)]


def tiene_linea(lineas, patron):
    return any(re.fullmatch(patron, l) for l in lineas)


class BasePDF(BaseCierre):

    def setUp(self):
        super().setUp()
        self._exports = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.exports = Path(self._exports.name)
        self._anterior_exports = os.environ.get("CAFETERIA_EXPORTS")
        os.environ["CAFETERIA_EXPORTS"] = str(self.exports)

    def tearDown(self):
        if self._anterior_exports is None:
            os.environ.pop("CAFETERIA_EXPORTS", None)
        else:
            os.environ["CAFETERIA_EXPORTS"] = self._anterior_exports
        self._exports.cleanup()
        super().tearDown()

    def generar(self, fecha=DIA_A):
        from app import pdf_cierre
        return pdf_cierre.generar_pdf_cierre(fecha)

    def hash_base(self):
        return hashlib.sha256(self.ruta.read_bytes()).hexdigest()


class BaseCerrado(BasePDF):
    """Caso de preproduccion cerrado: C-2026-000001 del 2026-09-17."""

    def setUp(self):
        super().setUp()
        self.caso_preproduccion()
        self.cierre = self.cerrar(DIA_A)
        self.ruta_pdf = self.generar()
        self.pdf = self.ruta_pdf.read_bytes()
        self.lineas = lineas_pdf(self.pdf)


# --------------------------------------------------------------- 1, 2, 3, 4, 5

class TestArchivo(BaseCerrado):

    def test_se_crea_el_pdf(self):
        self.assertTrue(self.ruta_pdf.is_file())

    def test_nombre_determinista_y_extension_pdf(self):
        self.assertEqual(self.ruta_pdf.name, "cierre_2026-09-17_C-2026-000001.pdf")
        self.assertEqual(self.ruta_pdf.suffix, ".pdf")

    def test_no_esta_vacio(self):
        self.assertGreater(len(self.pdf), 500)

    def test_cabecera_pdf_valida(self):
        self.assertTrue(self.pdf.startswith(b"%PDF-1.4"))
        self.assertTrue(self.pdf.rstrip().endswith(b"%%EOF"))

    def test_una_sola_pagina_a4_vertical(self):
        self.assertEqual(paginas_pdf(self.pdf), 1)
        self.assertEqual(mediaboxes(self.pdf), [(0.0, 0.0) + A4])
        ancho, alto = A4
        self.assertLess(ancho, alto)

    def test_estructura_interna_coherente(self):
        """xref, longitudes de flujo y startxref apuntan donde deben."""
        pdf = self.pdf
        inicio = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
        self.assertEqual(pdf[inicio:inicio + 4], b"xref")
        for i, ofs in enumerate(int(x) for x in re.findall(rb"(\d{10}) 00000 n", pdf)):
            self.assertTrue(pdf[ofs:].startswith(b"%d 0 obj" % (i + 1)))
        for m in re.finditer(rb"<< /Length (\d+) >>\nstream\n", pdf):
            fin = m.end() + int(m.group(1))
            self.assertEqual(pdf[fin:fin + 9], b"endstream")

    def test_queda_en_la_carpeta_de_exportacion(self):
        self.assertEqual(self.ruta_pdf.parent, self.exports)
        self.assertEqual(list(self.exports.iterdir()), [self.ruta_pdf],
                         "solo el PDF, sin temporales")


# -------------------------------------------------------------------------- 6

class TestContenido(BaseCerrado):

    def test_datos_del_cierre(self):
        L = self.lineas
        self.assertTrue(tiene_linea(L, r"Nº de cierre\s+C-2026-000001"))
        self.assertTrue(tiene_linea(L, r"Fecha del cierre\s+2026-09-17"))
        self.assertTrue(tiene_linea(L, r"Hora de cierre\s+" + re.escape(self.cierre["closed_at"])))
        self.assertTrue(tiene_linea(L, r"Primera venta\s+V-2026-000001"))
        self.assertTrue(tiene_linea(L, r"Última venta\s+V-2026-000002"))
        self.assertTrue(tiene_linea(L, r"Ventas válidas\s+1"))
        self.assertTrue(tiene_linea(L, r"Anulaciones\s+1"))

    def test_tabla_de_unidades(self):
        self.assertTrue(tiene_linea(self.lineas, r"Producto\s+Unidades"))
        self.assertTrue(tiene_linea(self.lineas, r"Café\s+2"))
        self.assertTrue(tiene_linea(self.lineas, r"Café con leche\s+1"))

    def test_totales(self):
        self.assertTrue(tiene_linea(self.lineas, r"Total bruto\s+7,75 €"))
        self.assertTrue(tiene_linea(self.lineas, r"Total anulado\s+3,30 €"))
        self.assertTrue(tiene_linea(self.lineas, r"TOTAL EFECTIVO VÁLIDO\s+4,45 €"))

    def test_el_euro_y_los_acentos_van_en_winansi(self):
        self.assertIn(b"\x80", self.pdf)            # €
        self.assertIn(b"Caf\xe9", self.pdf)          # é
        self.assertIn(b"/Encoding /WinAnsiEncoding", self.pdf)

    def test_importes_alineados_a_la_derecha(self):
        for l in self.lineas:
            if l.endswith(" €") and l.startswith(("Total", "TOTAL")):
                self.assertEqual(len(l), 73)


# -------------------------------------------------------------------------- 7

class TestDiaVacio(BasePDF):

    def test_un_dia_vacio_genera_un_pdf_valido(self):
        self.cerrar(DIA_A)
        pdf = self.generar().read_bytes()
        L = lineas_pdf(pdf)

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(paginas_pdf(pdf), 1)
        self.assertTrue(tiene_linea(L, r"Primera venta\s+—"))
        self.assertTrue(tiene_linea(L, r"Última venta\s+—"))
        self.assertTrue(tiene_linea(L, r"Ventas válidas\s+0"))
        self.assertTrue(tiene_linea(L, r"Anulaciones\s+0"))
        self.assertIn("Sin unidades vendidas.", L)
        self.assertTrue(tiene_linea(L, r"Total bruto\s+0,00 €"))
        self.assertTrue(tiene_linea(L, r"Total anulado\s+0,00 €"))
        self.assertTrue(tiene_linea(L, r"TOTAL EFECTIVO VÁLIDO\s+0,00 €"))


# -------------------------------------------------------------------------- 8

class TestSinCierre(BasePDF):

    def test_un_dia_sin_cierre_se_rechaza(self):
        from app import pdf_cierre
        self.caso_preproduccion()
        with self.assertRaises(pdf_cierre.CierreNoEncontrado):
            self.generar(DIA_A)
        self.assertEqual(list(self.exports.iterdir()), [], "no se crea ningun archivo")

    def test_un_cierre_sin_datos_congelados_no_genera_pdf(self):
        """Un cierre anterior a la congelacion (NULL) no se rellena con la
        configuracion actual: se rechaza."""
        from app import pdf_cierre
        conn = self.conexion()
        conn.execute(
            "INSERT INTO daily_close (close_number, business_date, closed_at,"
            " valid_sales_count, void_sales_count, gross_cents, void_cents, valid_cash_cents)"
            " VALUES ('C-2026-000001', ?, '2026-09-17 23:00:00', 0, 0, 0, 0, 0)", (DIA_A,))
        conn.commit()
        with self.assertRaises(pdf_cierre.CierreIncompleto):
            self.generar(DIA_A)
        self.assertEqual(list(self.exports.iterdir()), [])

    def test_el_pdf_no_necesita_la_configuracion_actual(self):
        """Tras cerrar, borrar la configuracion no impide regenerar el PDF."""
        self.cerrar(DIA_A)
        antes = self.generar(DIA_A).read_bytes()
        self.conexion().execute("DELETE FROM establishment").connection.commit()
        self.assertEqual(self.generar(DIA_A).read_bytes(), antes)


# ---------------------------------------------------------------------- 9, 10

class TestRegeneracion(BaseCerrado):

    def test_regenerar_varias_veces_da_exactamente_lo_mismo(self):
        for _ in range(3):
            ruta = self.generar()
            self.assertEqual(ruta, self.ruta_pdf)
            self.assertEqual(ruta.read_bytes(), self.pdf)
        self.assertEqual(len(list(self.exports.iterdir())), 1)

    def test_cambiar_productos_o_ventas_despues_no_altera_el_pdf(self):
        from app import products, sales
        products.actualizar_producto(self.id_cafe, "Café solo", 150)
        products.actualizar_producto(self.id_leche, "Cortado largo", 199)
        products.cambiar_estado(self.id_leche, False)
        # Ventas de otro dia, que no pueden afectar a este cierre...
        otra = self.vender([self.linea(self.id_cafe, "Café solo", 150, 9)],
                           datetime(2026, 9, 18, 10, 0))
        sales.anular_venta(otra["id"], momento=datetime(2026, 9, 18, 10, 1))
        # ...e incluso alterando a mano las ventas del dia cerrado: el PDF no las lee.
        conn = self.conexion()
        conn.execute("UPDATE sale_item SET product_name_snapshot = 'MANIPULADO'")
        conn.execute("UPDATE sale SET total_cents = 1")
        conn.commit()

        self.assertEqual(self.generar().read_bytes(), self.pdf)


# ------------------------------------------------------------------------- 11

class TestSoloLectura(BaseCerrado):

    def test_generar_el_pdf_no_escribe_en_sqlite(self):
        antes = self.hash_base()
        for _ in range(3):
            self.generar()
        self.assertEqual(self.hash_base(), antes)

    def test_solo_lee_el_cierre(self):
        """Solo daily_close y daily_close_item: ni sale, ni sale_item, ni product,
        ni la configuracion actual de establishment."""
        from app import db
        sentencias = []
        original = db.get_connection

        def espiada():
            c = original(); c.set_trace_callback(sentencias.append); return c

        with mock.patch("app.cierre.get_connection", espiada), \
             mock.patch("app.establecimiento.get_connection", espiada), \
             mock.patch("app.db.get_connection", espiada):
            self.generar()

        sql = " ".join(s.upper() for s in sentencias)
        self.assertIn("FROM DAILY_CLOSE", sql)
        self.assertIn("FROM DAILY_CLOSE_ITEM", sql)
        self.assertNotRegex(sql, r"\b(FROM|JOIN) (SALE|SALE_ITEM|PRODUCT|ESTABLISHMENT)\b")
        escrituras = [s for s in sentencias
                      if s.strip().split()[0].upper() in ("INSERT", "UPDATE", "DELETE", "REPLACE",
                                                          "CREATE", "ALTER", "DROP")]
        self.assertEqual(escrituras, [])


# ---------------------------------------------------------------------- 12, 13

class TestUbicacionYGit(unittest.TestCase):

    def test_por_defecto_se_guarda_en_exports_de_la_raiz(self):
        from app import pdf_cierre
        with mock.patch.dict(os.environ):
            os.environ.pop("CAFETERIA_EXPORTS", None)
            self.assertEqual(pdf_cierre.directorio_exports(), RAIZ / "exports")

    def test_exports_esta_en_gitignore(self):
        reglas = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("/exports/", reglas)

    def test_git_ignora_los_pdf_de_exports(self):
        if shutil.which("git") is None or not (RAIZ / ".git").exists():
            self.skipTest("no es un repositorio git")
        r = subprocess.run(
            ["git", "check-ignore", "-q", "exports/cierre_2026-09-17_C-2026-000001.pdf"],
            cwd=RAIZ)
        self.assertEqual(r.returncode, 0, "exports/ debe estar ignorado")

    def test_ningun_pdf_esta_versionado(self):
        if shutil.which("git") is None or not (RAIZ / ".git").exists():
            self.skipTest("no es un repositorio git")
        r = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True)
        self.assertEqual([f for f in r.stdout.splitlines() if f.lower().endswith(".pdf")], [])


# ------------------------------------------------------------ varias paginas

class TestVariasPaginas(BasePDF):

    def test_muchos_productos_se_reparten_en_paginas_a4(self):
        from app import cierre
        nombres = [f"Producto de prueba número {n:02d}" for n in range(1, 81)]
        conn = sqlite3.connect(self.ruta)
        conn.execute(
            "INSERT INTO daily_close (close_number, business_date, closed_at,"
            " valid_sales_count, void_sales_count, gross_cents, void_cents, valid_cash_cents,"
            " holder_name_snapshot, tax_id_snapshot, trade_name_snapshot, address_snapshot,"
            " vat_rate_percent, vat_base_cents, vat_cents)"
            " VALUES ('C-2026-000001', ?, '2026-09-17 23:00:00', 80, 0, 8000, 0, 8000,"
            " ?, ?, ?, ?, 10, 7273, 727)",
            (DIA_A, EMPRESA[0], EMPRESA[1], EMPRESA[2], EMPRESA[3]))
        for n in nombres:
            conn.execute("INSERT INTO daily_close_item (daily_close_id, product_name_snapshot,"
                         " units) VALUES (1, ?, 1)", (n,))
        conn.commit(); conn.close()
        self.assertEqual(len(cierre.obtener_cierre(DIA_A)["items"]), 80)

        pdf = self.generar().read_bytes()
        L = lineas_pdf(pdf)
        paginas = paginas_pdf(pdf)

        self.assertGreater(paginas, 1)
        self.assertEqual(mediaboxes(pdf), [(0.0, 0.0) + A4] * paginas)
        for n in nombres:
            self.assertTrue(tiene_linea(L, re.escape(n) + r"\s+1"), n)
        self.assertTrue(any(f"Página {paginas} de {paginas}" in l for l in L))
        self.assertTrue(any("(continuación)" in l for l in L))
        self.assertTrue(tiene_linea(L, r"TOTAL EFECTIVO VÁLIDO\s+80,00 €"))

    def test_nombres_muy_largos_no_se_salen_de_la_pagina(self):
        from app import pdf_cierre
        c = {"close_number": "C-2026-000001", "business_date": DIA_A,
             "closed_at": "2026-09-17 23:00:00", "first_sale_number": None,
             "last_sale_number": None, "valid_sales_count": 0, "void_sales_count": 0,
             "gross_cents": 0, "void_cents": 0, "valid_cash_cents": 0,
             "vat_rate_percent": 10, "vat_base_cents": 0, "vat_cents": 0,
             "items": [{"product_name_snapshot": "X" * 120, "units": 3}]}
        c.update(zip(SNAPSHOTS, EMPRESA))
        L = lineas_pdf(pdf_cierre.componer_pdf(c))
        fila = [l for l in L if l.startswith("XXX")][0]
        self.assertEqual(len(fila), 73)
        self.assertTrue(fila.endswith(" 3"))


# ------------------------------------------------------------------------- 14

class TestRutaWeb(BasePDF):

    def setUp(self):
        super().setUp()
        from app import create_app
        self.cliente = create_app().test_client()
        self.caso_preproduccion()
        self.p_hoy = mock.patch("app.resumen.hoy", return_value=DIA_B)
        self.p_hoy.start()

    def tearDown(self):
        self.p_hoy.stop()
        super().tearDown()

    def test_un_dia_abierto_no_genera_pdf(self):
        r = self.cliente.get("/cierre/pdf?dia=ayer")
        self.assertEqual(r.status_code, 409)
        self.assertIn("sigue abierto", r.get_data(as_text=True))
        self.assertEqual(list(self.exports.iterdir()), [])

    def test_un_dia_cerrado_devuelve_el_pdf(self):
        self.cerrar(DIA_A)
        r = self.cliente.get("/cierre/pdf?dia=ayer")

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.mimetype, "application/pdf")
        self.assertIn('inline; filename="cierre_2026-09-17_C-2026-000001.pdf"',
                      r.headers["Content-Disposition"])
        guardado = (self.exports / "cierre_2026-09-17_C-2026-000001.pdf").read_bytes()
        self.assertEqual(r.data, guardado)

    def test_la_pagina_de_cierre_solo_ofrece_el_pdf_si_esta_cerrado(self):
        abierto = self.cliente.get("/cierre?dia=ayer").get_data(as_text=True)
        self.assertNotIn('id="abrir-pdf"', abierto)

        self.cerrar(DIA_A)
        cerrado = self.cliente.get("/cierre?dia=ayer").get_data(as_text=True)
        self.assertIn('id="abrir-pdf"', cerrado)
        self.assertIn("/cierre/pdf?dia=ayer", cerrado)
        self.assertIn('id="ver-hoy"', cerrado)          # los controles siguen
        self.assertIn('id="ver-ayer"', cerrado)

    def test_por_la_web_solo_hoy_o_ayer(self):
        self.cerrar("2026-09-16")
        for url in ("/cierre/pdf?dia=2026-09-16", "/cierre/pdf?fecha=2026-09-16"):
            with self.subTest(url=url):
                r = self.cliente.get(url)
                # Cualquier otro parametro es "hoy", que esta abierto.
                self.assertEqual(r.status_code, 409)
        self.assertEqual(list(self.exports.iterdir()), [])

    def test_un_cierre_sin_datos_congelados_la_web_lo_explica(self):
        conn = self.conexion()
        conn.execute(
            "INSERT INTO daily_close (close_number, business_date, closed_at,"
            " valid_sales_count, void_sales_count, gross_cents, void_cents, valid_cash_cents)"
            " VALUES ('C-2026-000001', ?, '2026-09-17 23:00:00', 0, 0, 0, 0, 0)", (DIA_A,))
        conn.commit()
        r = self.cliente.get("/cierre/pdf?dia=ayer")
        self.assertEqual(r.status_code, 409)
        self.assertIn("no tiene congelados los datos del establecimiento",
                      r.get_data(as_text=True))

if __name__ == "__main__":
    unittest.main(verbosity=2)
