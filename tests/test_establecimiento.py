r"""Tests de los datos del establecimiento (FASE 7).

Titular, NIF, nombre comercial y direccion: cabecera del PDF de cierre.
Se guardan en SQLite (tabla establishment), nunca en el codigo ni en Git.

Todos los valores de estos tests son FICTICIOS. Nunca datos reales.

    .venv\Scripts\python.exe -m unittest discover -s tests -v
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

from test_cierre import DIA_A, DIA_B  # noqa: E402
from test_pdf import CLAVES, EMPRESA, BasePDF, lineas_pdf  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
TITULAR, NIF, COMERCIAL, DIRECCION = EMPRESA


def como_tupla(datos):
    return tuple(datos[k] for k in CLAVES)


class TestEnElPDF(BasePDF):

    def setUp(self):
        super().setUp()
        self.caso_preproduccion()
        self.cerrar(DIA_A)

    def test_los_cuatro_datos_aparecen_en_el_pdf(self):
        L = lineas_pdf(self.generar().read_bytes())
        self.assertIn(COMERCIAL, L)
        self.assertIn(f"Titular: {TITULAR}", L)
        self.assertIn(f"NIF: {NIF}", L)
        self.assertIn(DIRECCION, L)

    def test_aparecen_encima_de_los_datos_del_cierre(self):
        L = lineas_pdf(self.generar().read_bytes())
        titulo = L.index("CIERRE DIARIO DE CAJA")
        for linea in (COMERCIAL, f"Titular: {TITULAR}", f"NIF: {NIF}", DIRECCION):
            with self.subTest(linea=linea):
                self.assertLess(L.index(linea), titulo)
        self.assertEqual(L[0], COMERCIAL, "el nombre comercial encabeza el PDF")

    def test_direcciones_largas_se_parten_sin_salirse(self):
        from app import establecimiento
        larga = ("Calle " + "Muy Larga " * 18 + "1, 00000 Ciudad")[:200]
        establecimiento.guardar(TITULAR, NIF, COMERCIAL, larga)
        self.cerrar(DIA_B)                     # el cierre nuevo congela la direccion larga
        L = lineas_pdf(self.generar(DIA_B).read_bytes())
        cabecera = L[:L.index("CIERRE DIARIO DE CAJA")]
        self.assertTrue(all(len(l) <= 73 for l in cabecera))
        despues_nif = cabecera[cabecera.index(f"NIF: {NIF}") + 1:]
        self.assertEqual(" ".join(despues_nif), " ".join(larga.split()))


# Otra configuracion FICTICIA, para cambiar la del establecimiento.
OTRA = ("Otra Titular Ficticia", "NIF-PRUEBA-2",
        "Otro Bar de Prueba", "Avenida Inventada 99, 11111 Otra Ciudad")


def cabecera_pdf(lineas):
    """Las lineas del establecimiento en el PDF, encima del titulo."""
    return lineas[:lineas.index("CIERRE DIARIO DE CAJA")]


class TestReproducibilidadHistorica(BasePDF):
    """Cada cierre congela los cuatro datos del establecimiento: cambiar despues
    la configuracion no altera un cierre historico ni su PDF."""

    def setUp(self):
        super().setUp()
        self.caso_preproduccion()
        self.cerrado = self.cerrar(DIA_A)

    def test_el_cierre_congela_los_cuatro_datos(self):
        from app import cierre
        self.assertEqual(self.congelados(self.cerrado), EMPRESA)
        self.assertEqual(self.congelados(cierre.obtener_cierre(DIA_A)), EMPRESA)
        fila = self.conexion().execute(
            "SELECT holder_name_snapshot, tax_id_snapshot, trade_name_snapshot,"
            " address_snapshot FROM daily_close WHERE business_date = ?", (DIA_A,)).fetchone()
        self.assertEqual(tuple(fila), EMPRESA)

    def test_cambiar_la_configuracion_no_cambia_el_pdf_historico(self):
        from app import establecimiento
        antes = self.generar(DIA_A).read_bytes()

        establecimiento.guardar(*OTRA)
        despues = self.generar(DIA_A).read_bytes()

        self.assertEqual(despues, antes, "mismo cierre, mismos bytes")
        L = lineas_pdf(despues)
        self.assertEqual(cabecera_pdf(L), [COMERCIAL, f"Titular: {TITULAR}",
                                           f"NIF: {NIF}", DIRECCION])
        for valor in OTRA:
            with self.subTest(valor=valor):
                self.assertFalse(any(valor in l for l in L))

    def test_cambiar_la_configuracion_no_cambia_el_cierre_guardado(self):
        from app import cierre, establecimiento
        establecimiento.guardar(*OTRA)
        self.assertEqual(cierre.obtener_cierre(DIA_A), self.cerrado)

    def test_un_cierre_nuevo_usa_la_nueva_configuracion(self):
        from app import cierre, establecimiento
        establecimiento.guardar(*OTRA)
        self.vender([self.linea(self.id_cafe, "Café", 140, 1)], datetime(2026, 9, 18, 9, 0))
        nuevo = self.cerrar(DIA_B)

        self.assertEqual(self.congelados(nuevo), OTRA)
        self.assertEqual(self.congelados(cierre.obtener_cierre(DIA_A)), EMPRESA)

        La = lineas_pdf(self.generar(DIA_A).read_bytes())
        Lb = lineas_pdf(self.generar(DIA_B).read_bytes())
        self.assertEqual(cabecera_pdf(La), [COMERCIAL, f"Titular: {TITULAR}",
                                            f"NIF: {NIF}", DIRECCION])
        self.assertEqual(cabecera_pdf(Lb), [OTRA[2], f"Titular: {OTRA[0]}",
                                            f"NIF: {OTRA[1]}", OTRA[3]])

    def test_regenerar_un_cierre_historico_da_los_mismos_bytes(self):
        from app import establecimiento
        huellas = set()
        for datos in (EMPRESA, OTRA, EMPRESA, OTRA):
            establecimiento.guardar(*datos)
            huellas.add(hashlib.sha256(self.generar(DIA_A).read_bytes()).hexdigest())
        self.assertEqual(len(huellas), 1)
        self.assertEqual(len(list(self.exports.iterdir())), 1, "un solo archivo")

    def test_la_previsualizacion_muestra_lo_que_se_congelaria(self):
        from app import cierre, establecimiento
        establecimiento.guardar(*OTRA)
        previa = cierre.previsualizar_cierre(DIA_B)
        self.assertEqual(self.congelados(previa), OTRA)
        self.assertIsNone(cierre.obtener_cierre(DIA_B), "previsualizar no cierra")


class TestNoSeCierraSinLosCuatroDatos(BasePDF):

    def setUp(self):
        super().setUp()
        self.caso_preproduccion()

    def _sin_fila(self):
        conn = self.conexion()
        conn.execute("DELETE FROM establishment")
        conn.commit()

    def _sin_dato(self, columna, valor):
        conn = self.conexion()
        conn.execute(f"UPDATE establishment SET {columna} = ?", (valor,))
        conn.commit()

    def test_sin_fila_de_establecimiento_no_se_cierra(self):
        from app import cierre, establecimiento
        self._sin_fila()
        with self.assertRaises(establecimiento.SinConfigurar):
            self.cerrar(DIA_A)
        self.assertEqual(self.contar("daily_close"), 0)
        self.assertEqual(self.contar("daily_close_item"), 0)
        self.assertFalse(cierre.dia_esta_cerrado(DIA_A))

    def test_falta_cualquiera_de_los_cuatro_datos_y_no_se_cierra(self):
        from app import establecimiento
        # trade_name admite NULL (base migrada); los demas, cadena vacia.
        casos = (("trade_name", None, "Nombre comercial"), ("name", "", "Titular"),
                 ("tax_id", "", "NIF"), ("address", "", "Dirección"))
        for columna, valor, etiqueta in casos:
            with self.subTest(columna=columna):
                establecimiento.guardar(*EMPRESA)
                self._sin_dato(columna, valor)
                with self.assertRaises(establecimiento.SinConfigurar) as ctx:
                    self.cerrar(DIA_A)
                self.assertIn(etiqueta, str(ctx.exception))
                self.assertEqual(self.contar("daily_close"), 0)

    def test_un_intento_fallido_no_consume_numero_de_cierre(self):
        from app import establecimiento
        self._sin_fila()
        with self.assertRaises(establecimiento.SinConfigurar):
            self.cerrar(DIA_A)
        establecimiento.guardar(*EMPRESA)
        self.assertEqual(self.cerrar(DIA_A)["close_number"], "C-2026-000001")

    def test_el_dia_sigue_abierto_y_admite_ventas(self):
        from app import establecimiento
        self._sin_fila()
        with self.assertRaises(establecimiento.SinConfigurar):
            self.cerrar(DIA_A)
        self.vender([self.linea(self.id_cafe, "Café", 140, 1)], datetime(2026, 9, 17, 21, 0))
        self.assertEqual(self.contar("sale"), 3)

    def test_por_la_web_no_hay_boton_y_el_post_se_rechaza(self):
        from app import create_app
        self._sin_fila()
        cliente = create_app().test_client()
        with mock.patch("app.resumen.hoy", return_value=DIA_A), \
             mock.patch("app.cierre.datetime") as dt:
            dt.now.return_value = datetime(2026, 9, 17, 23, 0)
            html = cliente.get("/cierre").get_data(as_text=True)
            r = cliente.post("/cierre", data={"fecha": DIA_A})
        self.assertIn('id="faltan-datos-establecimiento"', html)
        self.assertNotIn("CERRAR DÍA", html)
        self.assertEqual(r.status_code, 409)
        self.assertIn("Faltan datos del establecimiento", r.get_data(as_text=True))
        self.assertEqual(self.contar("daily_close"), 0)


class TestPersistencia(BasePDF):

    def test_sobreviven_al_reinicio(self):
        from app import create_app, establecimiento
        create_app()                                   # arranque nuevo
        conn = sqlite3.connect(self.ruta)              # conexion nueva e independiente
        fila = conn.execute("SELECT name, tax_id, trade_name, address FROM establishment").fetchone()
        conn.close()
        self.assertEqual(fila, EMPRESA)
        self.assertEqual(como_tupla(establecimiento.obtener()), EMPRESA)

    def test_viajan_con_la_base_en_una_copia_de_seguridad(self):
        """Estan en SQLite: una copia de la base (futuro backup) contiene la
        configuracion y los datos congelados en cada cierre, y regenera el mismo
        PDF aunque en la copia se cambie o falte la configuracion."""
        from app import establecimiento, pdf_cierre
        self.caso_preproduccion()
        self.cerrar(DIA_A)
        original = self.generar(DIA_A).read_bytes()

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            copia = Path(tmp) / "copia.sqlite"
            origen = sqlite3.connect(self.ruta)
            destino = sqlite3.connect(copia)
            origen.backup(destino)
            origen.close(); destino.close()

            # "Restaurar": trabajar sobre la copia.
            with mock.patch.dict(os.environ, {"CAFETERIA_DB": str(copia)}):
                datos = establecimiento.obtener()
                conn = sqlite3.connect(copia)
                congelados = conn.execute(
                    "SELECT holder_name_snapshot, tax_id_snapshot, trade_name_snapshot,"
                    " address_snapshot FROM daily_close").fetchall()
                conn.close()
                restaurado = pdf_cierre.generar_pdf_cierre(DIA_A).read_bytes()

                establecimiento.guardar("Otra Titular Ficticia", "NIF-PRUEBA-2",
                                        "Otro Bar de Prueba", "Avenida Inventada 99")
                tras_cambio = pdf_cierre.generar_pdf_cierre(DIA_A).read_bytes()

                conn = sqlite3.connect(copia)
                conn.execute("DELETE FROM establishment"); conn.commit(); conn.close()
                sin_configuracion = pdf_cierre.generar_pdf_cierre(DIA_A).read_bytes()

        self.assertEqual(como_tupla(datos), EMPRESA)
        self.assertEqual(congelados, [EMPRESA])
        self.assertEqual(restaurado, original)
        self.assertEqual(tras_cambio, original)
        self.assertEqual(sin_configuracion, original)

    def test_una_sola_fila(self):
        from app import establecimiento
        establecimiento.guardar("A", "B", "C", "D")
        establecimiento.guardar("E", "F", "G", "H")
        conn = self.conexion()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM establishment").fetchone()[0], 1)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO establishment (id, name, tax_id, trade_name, address,"
                         " updated_at) VALUES (2, 'x', 'y', 'z', 'w', '2026-01-01 00:00:00')")


class TestMigracion(unittest.TestCase):
    """Una base con la tabla de tres campos recibe `trade_name` sin perder nada."""

    def test_se_anade_el_nombre_comercial_y_hasta_completarlo_no_hay_pdf(self):
        from app import db, establecimiento
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            ruta = Path(tmp) / "tres_campos.sqlite"
            with mock.patch.dict(os.environ, {"CAFETERIA_DB": str(ruta)}):
                conn = sqlite3.connect(ruta)
                conn.executescript("""
                    CREATE TABLE establishment (
                        id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT NOT NULL,
                        tax_id TEXT NOT NULL, address TEXT NOT NULL, updated_at TEXT NOT NULL);
                    INSERT INTO establishment VALUES
                        (1, 'Titular Viejo Ficticio', 'NIF-PRUEBA-9', 'Calle Vieja 9',
                         '2026-09-18 18:45:36');
                """)
                conn.commit(); conn.close()

                db.init_db()
                db.init_db()   # idempotente

                conn = sqlite3.connect(ruta)
                columnas = [c[1] for c in conn.execute("PRAGMA table_info(establishment)")]
                fila = conn.execute("SELECT name, tax_id, address, trade_name"
                                    " FROM establishment").fetchone()
                conn.close()

                with self.assertRaises(establecimiento.SinConfigurar) as ctx:
                    establecimiento.obtener_obligatorio()

                establecimiento.guardar("Titular Viejo Ficticio", "NIF-PRUEBA-9",
                                        "Bar Viejo de Prueba", "Calle Vieja 9")
                completos = establecimiento.obtener_obligatorio()

        self.assertEqual(columnas.count("trade_name"), 1)
        self.assertEqual(fila, ("Titular Viejo Ficticio", "NIF-PRUEBA-9", "Calle Vieja 9", None))
        self.assertIn("Nombre comercial", str(ctx.exception))
        self.assertEqual(completos["trade_name"], "Bar Viejo de Prueba")


class TestValidacion(BasePDF):

    def test_los_cuatro_campos_son_obligatorios(self):
        from app import establecimiento
        for args in (("", "N", "C", "D"), ("T", "  ", "C", "D"),
                     ("T", "N", "", "D"), ("T", "N", "C", "")):
            with self.subTest(args=args), self.assertRaises(establecimiento.DatosInvalidos):
                establecimiento.guardar(*args)

    def test_longitudes_maximas(self):
        from app import establecimiento
        for args in (("x" * 101, "N", "C", "D"), ("T", "x" * 21, "C", "D"),
                     ("T", "N", "x" * 101, "D"), ("T", "N", "C", "x" * 201)):
            with self.subTest(args=[len(a) for a in args]), \
                 self.assertRaises(establecimiento.DatosInvalidos):
                establecimiento.guardar(*args)

    def test_rechaza_caracteres_que_el_pdf_no_puede_mostrar(self):
        from app import establecimiento
        with self.assertRaises(establecimiento.DatosInvalidos):
            establecimiento.guardar("T", "N", "Café ☕", "D")
        # Mayusculas acentuadas, ñ, º, raya y "S/N": todo cabe en WinAnsi.
        establecimiento.guardar("TITULAR ÁÉÍÓÚ ÑANDÚ", "N", "BAR Nº 1 — PRUEBA", "RÚA FICTICIA S/N")

    def test_un_error_no_modifica_los_datos_guardados(self):
        from app import establecimiento
        with self.assertRaises(establecimiento.DatosInvalidos):
            establecimiento.guardar("", "", "", "")
        self.assertEqual(como_tupla(establecimiento.obtener()), EMPRESA)


class TestRutaWeb(BasePDF):

    def setUp(self):
        super().setUp()
        from app import create_app
        self.cliente = create_app().test_client()

    def test_formulario_con_los_datos_actuales(self):
        html = self.cliente.get("/establecimiento").get_data(as_text=True)
        for nombre, valor in zip(("titular", "nif", "nombre_comercial", "direccion"), EMPRESA):
            with self.subTest(campo=nombre):
                self.assertRegex(html, rf'name="{nombre}"[^>]*value="{re.escape(valor)}"')

    def test_guardar_por_la_web(self):
        from app import establecimiento
        r = self.cliente.post("/establecimiento", data={
            "titular": "Nueva Titular Ficticia", "nif": "NIF-PRUEBA-3",
            "nombre_comercial": "Nuevo Bar de Prueba", "direccion": "Plaza Falsa 3"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(como_tupla(establecimiento.obtener()),
                         ("Nueva Titular Ficticia", "NIF-PRUEBA-3", "Nuevo Bar de Prueba",
                          "Plaza Falsa 3"))

    def test_datos_invalidos_por_la_web(self):
        r = self.cliente.post("/establecimiento", data={
            "titular": "x", "nif": "y", "nombre_comercial": "", "direccion": "z"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Nombre comercial: es obligatorio", r.get_data(as_text=True))


class TestNadaEnGitHub(unittest.TestCase):
    """Ni datos personales ni de negocio en el repositorio."""

    def test_sin_valores_por_defecto_en_el_esquema_ni_en_el_codigo(self):
        from app import db, establecimiento
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            with mock.patch.dict(os.environ, {"CAFETERIA_DB": str(Path(tmp) / "nueva.sqlite")}):
                db.init_db()
                self.assertIsNone(establecimiento.obtener(), "una base nueva no trae datos")
        definicion = re.search(r"CREATE TABLE IF NOT EXISTS establishment \((.*?)\);",
                               db.ESQUEMA, re.S).group(1)
        self.assertNotIn("DEFAULT", definicion.upper())

    def _versionados(self):
        if shutil.which("git") is None or not (RAIZ / ".git").exists():
            self.skipTest("no es un repositorio git")
        r = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True)
        return r.stdout.splitlines()

    def test_no_se_versiona_ninguna_base_ni_archivo_de_configuracion(self):
        prohibidas = (".sqlite", ".sqlite3", ".db", ".pdf", ".env", ".json", ".ini",
                      ".cfg", ".toml", ".yaml", ".yml", ".csv")
        self.assertEqual([f for f in self._versionados() if f.lower().endswith(prohibidas)], [])

    def test_la_base_y_los_pdf_quedan_fuera_de_git(self):
        self._versionados()
        for ruta in ("data/cafeteria.sqlite", "exports/cierre_2026-09-17_C-2026-000001.pdf"):
            with self.subTest(ruta=ruta):
                r = subprocess.run(["git", "check-ignore", "-q", ruta], cwd=RAIZ)
                self.assertEqual(r.returncode, 0)

    def _datos_reales_locales(self):
        """Los datos del establecimiento de la base REAL del portatil, si existe.

        Se abre en solo lectura: el test nunca escribe en la base real. Incluye
        la configuracion y lo congelado en los cierres. Los valores solo se usan
        en memoria para buscarlos; nunca se imprimen.
        """
        from app import db
        ruta = db.RUTA_POR_DEFECTO
        if not ruta.exists():
            self.skipTest("no hay base local real (p. ej. clon limpio)")
        conn = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
        valores = set()
        try:
            consultas = ("SELECT name, tax_id, trade_name, address FROM establishment",
                         "SELECT holder_name_snapshot, tax_id_snapshot, trade_name_snapshot,"
                         " address_snapshot FROM daily_close")
            for sql in consultas:
                try:
                    for fila in conn.execute(sql):
                        valores.update(v for v in fila if v)
                except sqlite3.OperationalError:
                    pass   # base anterior sin esa tabla o columna
        finally:
            conn.close()
        # Los valores muy cortos darian falsos positivos (p. ej. "S.L.").
        valores = {v for v in valores if len(v) >= 6}
        if not valores:
            self.skipTest("la base local no tiene datos del establecimiento")
        return valores

    def test_los_datos_reales_del_establecimiento_no_estan_en_git(self):
        """Ni en archivos versionados, ni en archivos nuevos no ignorados, ni en
        el historial, ni en los mensajes de commit. Solo se informa de DONDE
        aparecen, nunca de su valor."""
        versionados = self._versionados()
        valores = self._datos_reales_locales()

        nuevos = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                                cwd=RAIZ, capture_output=True, text=True).stdout.splitlines()
        encontrados = []
        for f in versionados + nuevos:
            try:
                texto = (RAIZ / f).read_text(encoding="utf-8")
            except (UnicodeDecodeError, FileNotFoundError):
                continue
            if any(v in texto for v in valores):
                encontrados.append(f)

        historial = subprocess.run(["git", "log", "--all", "-p", "--format=%B"], cwd=RAIZ,
                                   capture_output=True, encoding="utf-8",
                                   errors="replace").stdout
        if any(v in historial for v in valores):
            encontrados.append("<historial de Git o mensajes de commit>")
        self.assertEqual(encontrados, [], "datos reales del establecimiento en Git")

    def test_ningun_archivo_versionado_contiene_un_nif_o_cif(self):
        """DNI (8 cifras + letra), NIE (X/Y/Z + 7 cifras + letra) o CIF
        (letra + 7 cifras + control). Si alguien pega uno real en el codigo o
        en la documentacion, este test falla."""
        patron = re.compile(r"\b(\d{8}[A-Z]|[XYZ]\d{7}[A-Z]|[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J])\b")
        encontrados = []
        for f in self._versionados():
            try:
                texto = (RAIZ / f).read_text(encoding="utf-8")
            except (UnicodeDecodeError, FileNotFoundError):
                continue
            for n, l in enumerate(texto.splitlines(), 1):
                if patron.search(l):
                    encontrados.append(f"{f}:{n}: {l.strip()[:80]}")
        self.assertEqual(encontrados, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
