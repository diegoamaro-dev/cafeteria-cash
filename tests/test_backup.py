r"""Tests del backup (FASE 8).

Todos los backups van a carpetas temporales: BaseTemporal apunta
CAFETERIA_BACKUP_DIR a una carpeta propia de cada test. Nunca se usa la carpeta
real ni se crean datos reales.

    .venv\Scripts\python.exe -m unittest discover -s tests -v
"""

import hashlib
import os
import re
import sqlite3
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_cierre import DESPUES, DIA_A, BaseCierre  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
MOMENTO = datetime(2026, 9, 18, 23, 0, 5)
PATRON_NOMBRE = r"cafeteria_\d{4}-\d{2}-\d{2}_\d{6}(_\d+)?\.sqlite"
TABLAS = ("product", "sale", "sale_item", "daily_close", "daily_close_item", "establishment")


def huella(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def filas(ruta, tabla):
    conn = sqlite3.connect(f"file:{Path(ruta).as_posix()}?mode=ro", uri=True)
    try:
        return conn.execute(f"SELECT * FROM {tabla} ORDER BY rowid").fetchall()
    finally:
        conn.close()


class BaseBackup(BaseCierre):

    def setUp(self):
        super().setUp()
        self.caso_preproduccion()
        self.cerrar(DIA_A)

    def backup(self, momento=MOMENTO):
        from app import backup
        return backup.crear_backup(momento=momento)

    def archivos(self):
        return sorted(p.name for p in self.carpeta_backup.iterdir())


# --------------------------------------------------------------- backup correcto

class TestBackupCorrecto(BaseBackup):

    def test_crea_un_backup_valido_con_nombre_de_fecha_y_hora(self):
        copia = self.backup()
        self.assertEqual(copia["nombre"], "cafeteria_2026-09-18_230005.sqlite")
        self.assertEqual(copia["ruta"], self.carpeta_backup / copia["nombre"])
        self.assertTrue(copia["ruta"].is_file())
        self.assertEqual(copia["bytes"], copia["ruta"].stat().st_size)
        self.assertEqual(self.archivos(), [copia["nombre"]], "sin temporales ni restos")

    def test_el_nombre_por_defecto_usa_la_hora_actual(self):
        from app import backup
        copia = backup.crear_backup()
        self.assertRegex(copia["nombre"], "^" + PATRON_NOMBRE + "$")

    def test_contenido_identico_a_la_base_origen(self):
        copia = self.backup()
        for tabla in TABLAS:
            with self.subTest(tabla=tabla):
                self.assertEqual(filas(copia["ruta"], tabla), filas(self.ruta, tabla))
        self.assertEqual(copia["filas"]["sale"], 2)
        self.assertEqual(copia["filas"]["daily_close"], 1)

    def test_integrity_check_ok(self):
        copia = self.backup()
        conn = sqlite3.connect(copia["ruta"])
        try:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
        finally:
            conn.close()

    def test_contiene_las_tablas_esperadas(self):
        copia = self.backup()
        conn = sqlite3.connect(copia["ruta"])
        try:
            tablas = {f[0] for f in conn.execute("SELECT name FROM sqlite_master"
                                                 " WHERE type = 'table'")}
        finally:
            conn.close()
        self.assertTrue(set(TABLAS) <= tablas)

    def test_no_modifica_la_base_principal(self):
        antes = huella(self.ruta)
        self.backup()
        self.assertEqual(huella(self.ruta), antes)

    def test_usa_la_api_de_backup_de_sqlite(self):
        """Foto coherente: una escritura a medias (sin COMMIT) no entra."""
        conn = sqlite3.connect(self.ruta, isolation_level=None)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO product (name, price_cents) VALUES ('A medias', 1)")
        try:
            copia = self.backup()
        finally:
            conn.execute("ROLLBACK"); conn.close()
        nombres = [f[1] for f in filas(copia["ruta"], "product")]
        self.assertNotIn("A medias", nombres)
        texto = (RAIZ / "app" / "backup.py").read_text(encoding="utf-8")
        self.assertIn(".backup(", texto)
        self.assertNotRegex(texto, r"shutil\.copy")


# ------------------------------------------------------------ historico y nombres

class TestHistorico(BaseBackup):

    def test_dos_backups_en_el_mismo_segundo_no_se_sobrescriben(self):
        primero = self.backup()
        huella_primero = huella(primero["ruta"])
        segundo = self.backup()
        tercero = self.backup()
        self.assertEqual([primero["nombre"], segundo["nombre"], tercero["nombre"]],
                         ["cafeteria_2026-09-18_230005.sqlite",
                          "cafeteria_2026-09-18_230005_2.sqlite",
                          "cafeteria_2026-09-18_230005_3.sqlite"])
        self.assertEqual(huella(primero["ruta"]), huella_primero)
        self.assertEqual(len(self.archivos()), 3)

    def test_backups_consecutivos_conservan_los_anteriores(self):
        primero = self.backup(datetime(2026, 9, 18, 23, 0, 5))
        huella_primero = huella(primero["ruta"])
        self.vender([self.linea(self.id_cafe, "Café", 140, 1)], datetime(2026, 9, 18, 9, 0))
        segundo = self.backup(datetime(2026, 9, 18, 23, 0, 6))

        self.assertEqual(huella(primero["ruta"]), huella_primero, "el anterior no cambia")
        self.assertEqual(len(filas(primero["ruta"], "sale")), 2)
        self.assertEqual(len(filas(segundo["ruta"], "sale")), 3)
        self.assertEqual(self.archivos(), [primero["nombre"], segundo["nombre"]])

    def test_un_archivo_ajeno_con_el_mismo_nombre_no_se_toca(self):
        ajeno = self.carpeta_backup / "cafeteria_2026-09-18_230005.sqlite"
        ajeno.write_bytes(b"no tocar")
        copia = self.backup()
        self.assertEqual(ajeno.read_bytes(), b"no tocar")
        self.assertEqual(copia["nombre"], "cafeteria_2026-09-18_230005_2.sqlite")

    def test_el_codigo_no_borra_backups(self):
        texto = (RAIZ / "app" / "backup.py").read_text(encoding="utf-8")
        # Solo se borra el temporal (.partial) y su -journal, en _borrar().
        self.assertEqual(texto.count(".unlink("), 1)
        self.assertNotRegex(texto, r"os\.remove|rmtree|os\.replace")


# ------------------------------------------------------------- ruta y fallos

class TestRutaYFallos(BaseBackup):

    def test_sin_carpeta_configurada_lo_indica_y_no_inventa_otra(self):
        from app import backup
        for valor in (None, "", "   "):
            with self.subTest(valor=valor):
                with mock.patch.dict(os.environ, {}, clear=False):
                    if valor is None:
                        os.environ.pop("CAFETERIA_BACKUP_DIR", None)
                    else:
                        os.environ["CAFETERIA_BACKUP_DIR"] = valor
                    with self.assertRaises(backup.BackupNoConfigurado) as ctx:
                        backup.crear_backup(momento=MOMENTO)
                self.assertIn("CAFETERIA_BACKUP_DIR", str(ctx.exception))
        self.assertEqual(self.archivos(), [])
        self.assertFalse((RAIZ / "backups").exists())

    def test_carpeta_inexistente_falla_y_no_se_crea(self):
        from app import backup
        inexistente = self.carpeta_backup / "unidad-desconectada" / "sub"
        with mock.patch.dict(os.environ, {"CAFETERIA_BACKUP_DIR": str(inexistente)}):
            with self.assertRaises(backup.BackupFallido) as ctx:
                backup.crear_backup(momento=MOMENTO)
        self.assertIn("no existe o no está disponible", str(ctx.exception))
        self.assertFalse(inexistente.exists())
        self.assertFalse(inexistente.parent.exists())

    def test_la_ruta_es_un_archivo_no_una_carpeta(self):
        from app import backup
        archivo = self.carpeta_backup / "soy-un-archivo"
        archivo.write_text("x")
        with mock.patch.dict(os.environ, {"CAFETERIA_BACKUP_DIR": str(archivo)}):
            with self.assertRaises(backup.BackupFallido):
                backup.crear_backup(momento=MOMENTO)

    def test_si_la_validacion_falla_no_queda_ningun_archivo(self):
        from app import backup
        with mock.patch("app.backup.validar",
                        side_effect=backup.BackupFallido("simulado")):
            with self.assertRaises(backup.BackupFallido):
                self.backup()
        self.assertEqual(self.archivos(), [], "ni backup final ni temporal")

    def test_si_falla_la_escritura_no_queda_ningun_archivo(self):
        from app import backup
        real = sqlite3.connect

        class OrigenQueFalla:
            """Empieza a escribir en el temporal y falla a medias."""
            def backup(self, destino):
                destino.execute("CREATE TABLE a_medias (x)")
                destino.commit()
                raise sqlite3.OperationalError("disco lleno")

            def close(self):
                pass

        def conectar(ruta, *args, **kwargs):
            # El origen se abre con uri=True (mode=ro); el temporal, no.
            return OrigenQueFalla() if kwargs.get("uri") else real(ruta, *args, **kwargs)

        with mock.patch("app.backup.sqlite3.connect", side_effect=conectar):
            with self.assertRaises(backup.BackupFallido) as ctx:
                self.backup()
        self.assertIn("disco", str(ctx.exception))
        self.assertEqual(self.archivos(), [])

    def test_si_falla_el_renombrado_no_queda_ningun_archivo(self):
        from app import backup
        with mock.patch("app.backup.os.rename", side_effect=PermissionError("bloqueado")):
            with self.assertRaises(backup.BackupFallido):
                self.backup()
        self.assertEqual(self.archivos(), [])

    def test_el_temporal_no_parece_un_backup(self):
        """Mientras se escribe, el nombre es tmp-...partial, nunca *.sqlite."""
        from app import backup
        vistos = []
        original = backup.validar

        def espia(ruta):
            vistos.append(Path(ruta).name)
            return original(ruta)

        with mock.patch("app.backup.validar", side_effect=espia):
            self.backup()
        self.assertEqual(len(vistos), 1)
        self.assertRegex(vistos[0], r"^tmp-cafeteria_.*\.partial$")
        self.assertNotRegex(vistos[0], r"\.sqlite$")

    def test_validar_rechaza_archivos_no_validos(self):
        from app import backup
        basura = self.carpeta_backup / "basura.partial"
        basura.write_bytes(b"esto no es SQLite" * 100)
        vacio = self.carpeta_backup / "vacio.partial"
        vacio.write_bytes(b"")
        sin_tablas = self.carpeta_backup / "sin_tablas.partial"
        sqlite3.connect(sin_tablas).execute("CREATE TABLE product (id)").connection.close()
        for ruta, texto in ((basura, "no se abre como SQLite"), (vacio, "vacío"),
                            (sin_tablas, "le faltan tablas"),
                            (self.carpeta_backup / "no-existe", "no existe")):
            with self.subTest(ruta=ruta.name):
                with self.assertRaises(backup.BackupFallido) as ctx:
                    backup.validar(ruta)
                self.assertIn(texto, str(ctx.exception))

    def test_validar_rechaza_un_sqlite_corrupto(self):
        from app import backup
        copia = self.backup()
        corrupto = self.carpeta_backup / "corrupto.partial"
        datos = bytearray(copia["ruta"].read_bytes())
        for i in range(len(datos) // 2, len(datos) // 2 + 2048):   # paginas de datos
            datos[i] = 0xFF
        corrupto.write_bytes(bytes(datos))
        with self.assertRaises(backup.BackupFallido):
            backup.validar(corrupto)


# ----------------------------------------------------------------- ruta web

class BaseWeb(BaseCierre):

    def setUp(self):
        super().setUp()
        from app import cart, create_app
        cart.cancelar()
        self.cliente = create_app().test_client()
        self.caso_preproduccion()
        self.parche = mock.patch("app.resumen.hoy", return_value=DIA_A)
        self.parche.start()
        self.parche_dt = mock.patch("app.cierre.datetime")
        self.parche_dt.start().now.return_value = DESPUES

    def tearDown(self):
        self.parche_dt.stop()
        self.parche.stop()
        super().tearDown()

    def archivos(self):
        return sorted(p.name for p in self.carpeta_backup.iterdir())

    def cerrar_por_la_web(self):
        return self.cliente.post("/cierre", data={"fecha": DIA_A})


class TestBackupManual(BaseWeb):

    def test_pantalla_con_carpeta_y_boton(self):
        html = self.cliente.get("/backup").get_data(as_text=True)
        self.assertIn('id="crear-backup"', html)
        self.assertIn(str(self.carpeta_backup), html)
        self.assertIn("Copia de seguridad", self.cliente.get("/").get_data(as_text=True))

    def test_backup_manual_correcto(self):
        r = self.cliente.post("/backup")
        self.assertEqual(r.status_code, 302)
        html = self.cliente.get(r.headers["Location"]).get_data(as_text=True)
        self.assertRegex(html, "Backup correcto: " + PATRON_NOMBRE)
        self.assertEqual(len(self.archivos()), 1)
        self.assertRegex(self.archivos()[0], "^" + PATRON_NOMBRE + "$")

    def test_backup_manual_sin_carpeta(self):
        os.environ.pop("CAFETERIA_BACKUP_DIR")
        html = self.cliente.get("/backup").get_data(as_text=True)
        self.assertIn('id="sin-carpeta"', html)
        r = self.cliente.post("/backup")
        self.assertEqual(r.status_code, 503)
        self.assertIn("BACKUP FALLIDO", r.get_data(as_text=True))
        self.assertIn("CAFETERIA_BACKUP_DIR", r.get_data(as_text=True))

    def test_backup_manual_con_la_carpeta_no_disponible(self):
        os.environ["CAFETERIA_BACKUP_DIR"] = str(self.carpeta_backup / "desconectada")
        r = self.cliente.post("/backup")
        self.assertEqual(r.status_code, 503)
        self.assertIn("no existe o no está disponible", r.get_data(as_text=True))
        self.assertEqual(self.archivos(), [])

    def test_por_get_no_se_crea_backup(self):
        self.cliente.get("/backup")
        self.assertEqual(self.archivos(), [])


class TestBackupAutomaticoAlCerrar(BaseWeb):

    def test_cerrar_el_dia_crea_el_backup_despues_del_cierre(self):
        r = self.cerrar_por_la_web()
        self.assertEqual(r.status_code, 302)
        html = self.cliente.get(r.headers["Location"]).get_data(as_text=True)
        self.assertIn("C-2026-000001", html)
        self.assertRegex(html, "Backup correcto: " + PATRON_NOMBRE)
        self.assertEqual(len(self.archivos()), 1)
        # El backup se hizo DESPUES de guardar el cierre: lo contiene.
        copia = self.carpeta_backup / self.archivos()[0]
        cierres = filas(copia, "daily_close")
        self.assertEqual(len(cierres), 1)
        self.assertEqual(cierres[0][1], "C-2026-000001")
        self.assertEqual(len(filas(copia, "daily_close_item")), 2)

    def test_la_funcion_de_cierre_no_hace_backup_por_si_sola(self):
        """El backup lo lanza la accion de cerrar el dia (ruta), despues de que
        la transaccion del cierre haya terminado; cierre.py no lo conoce."""
        self.cerrar(DIA_A)
        self.assertEqual(self.archivos(), [])
        self.assertNotIn("backup", (RAIZ / "app" / "cierre.py").read_text(encoding="utf-8"))


class TestFalloDelBackupNoPierdeElCierre(BaseWeb):

    def comprobar_cierre_intacto(self, r):
        from app import cierre, sales
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("BACKUP FALLIDO", html)
        self.assertIn("C-2026-000001 está hecho y guardado", html)
        self.assertIn('id="repetir-backup"', html)
        # El cierre sigue ahi, completo, y el dia cerrado.
        self.assertEqual(self.contar("daily_close"), 1)
        self.assertEqual(self.contar("daily_close_item"), 2)
        self.assertTrue(cierre.dia_esta_cerrado(DIA_A))
        self.assertEqual(cierre.obtener_cierre(DIA_A)["valid_cash_cents"], 445)
        with self.assertRaises(cierre.DiaCerrado):
            sales.confirmar_venta([self.linea(self.id_cafe, "Café", 140, 1)],
                                  momento=datetime(2026, 9, 17, 22, 0))
        # Un segundo intento de cierre no crea otro.
        self.assertEqual(self.cerrar_por_la_web().status_code, 409)
        self.assertEqual(self.contar("daily_close"), 1)

    def test_carpeta_no_disponible(self):
        os.environ["CAFETERIA_BACKUP_DIR"] = str(self.carpeta_backup / "desconectada")
        r = self.cerrar_por_la_web()
        self.comprobar_cierre_intacto(r)
        self.assertIn("no existe o no está disponible", r.get_data(as_text=True))

    def test_sin_carpeta_configurada(self):
        os.environ.pop("CAFETERIA_BACKUP_DIR")
        r = self.cerrar_por_la_web()
        self.comprobar_cierre_intacto(r)
        self.assertIn("CAFETERIA_BACKUP_DIR", r.get_data(as_text=True))

    def test_fallo_inesperado_del_backup(self):
        with mock.patch("app.backup.crear_backup", side_effect=RuntimeError("inesperado")), \
             self.assertLogs("app.routes", level="ERROR"):
            r = self.cerrar_por_la_web()
        self.comprobar_cierre_intacto(r)

    def test_se_puede_reintentar_manualmente_despues(self):
        os.environ["CAFETERIA_BACKUP_DIR"] = str(self.carpeta_backup / "desconectada")
        self.cerrar_por_la_web()
        self.assertEqual(self.archivos(), [])

        os.environ["CAFETERIA_BACKUP_DIR"] = str(self.carpeta_backup)   # "se conecta"
        r = self.cliente.post("/backup")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(self.archivos()), 1)
        copia = self.carpeta_backup / self.archivos()[0]
        self.assertEqual(filas(copia, "daily_close")[0][1], "C-2026-000001")

    def test_el_cierre_cerrado_ofrece_repetir_el_backup(self):
        self.cerrar_por_la_web()
        html = self.cliente.get("/cierre").get_data(as_text=True)
        self.assertIn('id="repetir-backup"', html)


# ------------------------------------------------------------ aislamiento

class TestAislamiento(BaseCierre):

    def test_los_tests_escriben_backups_solo_en_temporales(self):
        """BaseTemporal apunta CAFETERIA_BACKUP_DIR a su carpeta temporal."""
        import tempfile
        carpeta = Path(os.environ["CAFETERIA_BACKUP_DIR"]).resolve()
        self.assertEqual(carpeta, self.carpeta_backup.resolve())
        self.assertTrue(str(carpeta).startswith(str(Path(tempfile.gettempdir()).resolve())))
        self.assertNotEqual(carpeta.drive.upper(), "G:")

    def test_ningun_backup_dentro_del_repositorio(self):
        encontrados = [str(p.relative_to(RAIZ)) for p in RAIZ.rglob("cafeteria_*.sqlite")
                       if ".venv" not in p.parts]
        self.assertEqual(encontrados, [])
        self.assertFalse((RAIZ / "backups").exists())

    def test_la_ruta_real_no_esta_en_el_codigo_ni_en_los_tests(self):
        """La carpeta real solo vive en la configuracion del equipo (y en la
        documentacion de la decision), nunca en app/, scripts/ ni tests/."""
        real = "FACTURACION" + " CAFETERIA"
        unidad = "Mi " + "unidad"
        encontrados = []
        for carpeta in ("app", "scripts", "tests"):
            for f in (RAIZ / carpeta).rglob("*"):
                if f.is_file() and f.suffix in (".py", ".html", ".ps1", ".css"):
                    texto = f.read_text(encoding="utf-8", errors="replace")
                    if real.lower() in texto.lower() or unidad in texto or re.search(
                            r"\bG:[\\/]", texto):
                        encontrados.append(str(f.relative_to(RAIZ)))
        self.assertEqual(encontrados, [])

    def test_los_backups_no_se_versionan(self):
        r = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest("no es un repositorio git")
        self.assertEqual([f for f in r.stdout.splitlines()
                          if re.search(r"\.(sqlite3?|db|partial)$", f)], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
