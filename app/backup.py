"""Copia de seguridad de la base SQLite (FASE 8).

- Carpeta de destino: variable de entorno CAFETERIA_BACKUP_DIR. Es una carpeta
  local cualquiera; si esta sincronizada con una nube (por ejemplo Google Drive
  para escritorio), la sincronizacion la hace ese programa por fuera: aqui no
  hay ninguna integracion ni API. Sin la variable no se hace backup y se avisa:
  nunca se inventa una carpeta alternativa, ni se crea la carpeta si no existe
  (una unidad desconectada no debe convertirse en una carpeta local nueva).
- La copia se hace con la API de backup de SQLite (sqlite3.Connection.backup),
  que da una foto coherente aunque la base este abierta, nunca copiando el
  archivo a pelo.
- Atomica: se escribe en un temporal de la propia carpeta de destino con un
  nombre que no parece un backup (tmp-...partial), se valida y solo entonces se
  renombra al nombre final. Si algo falla, el temporal se borra.
- Validacion antes de darla por buena: el archivo existe, abre como SQLite,
  PRAGMA integrity_check = ok y estan las tablas esenciales.
- Historico: nombre cafeteria_YYYY-MM-DD_HHMMSS.sqlite. Nunca se sobrescribe ni
  se borra un backup anterior: si el nombre ya existe se anade _2, _3...

Solo lee la base principal: no la modifica.
"""

import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from . import db

VARIABLE = "CAFETERIA_BACKUP_DIR"
TABLAS_ESENCIALES = ("product", "sale", "sale_item", "daily_close",
                     "daily_close_item", "establishment")
MAX_INTENTOS_NOMBRE = 100


class BackupNoConfigurado(RuntimeError):
    """No hay carpeta de backup configurada."""


class BackupFallido(RuntimeError):
    """El backup no se ha podido crear o no ha pasado la validacion."""


def carpeta_configurada():
    """La carpeta de CAFETERIA_BACKUP_DIR (sin comprobarla), o None."""
    valor = (os.environ.get(VARIABLE) or "").strip()
    return Path(valor) if valor else None


def carpeta_destino():
    """La carpeta de backup, comprobada. No la crea nunca."""
    carpeta = carpeta_configurada()
    if carpeta is None:
        raise BackupNoConfigurado(
            f"No hay carpeta de backup configurada: define la variable de entorno"
            f" {VARIABLE} con la ruta de la carpeta externa y reinicia la aplicación."
        )
    if not carpeta.is_dir():
        raise BackupFallido(
            f"La carpeta de backup no existe o no está disponible: {carpeta}."
            " Comprueba que la unidad está conectada (y Google Drive iniciado)."
        )
    return carpeta


def nombre_backup(momento):
    return f"cafeteria_{momento:%Y-%m-%d_%H%M%S}.sqlite"


def validar(ruta):
    """Comprueba que `ruta` es un SQLite integro con las tablas esenciales.

    Devuelve {tabla: filas} de las tablas esenciales. Lanza BackupFallido si no.
    """
    ruta = Path(ruta)
    if not ruta.is_file() or ruta.stat().st_size == 0:
        raise BackupFallido(f"El backup no existe o está vacío: {ruta.name}.")
    try:
        conn = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
        try:
            integridad = conn.execute("PRAGMA integrity_check").fetchall()
            if integridad != [("ok",)]:
                raise BackupFallido(
                    f"El backup {ruta.name} no supera integrity_check: {integridad[:3]}.")
            tablas = {f[0] for f in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")}
            faltan = [t for t in TABLAS_ESENCIALES if t not in tablas]
            if faltan:
                raise BackupFallido(
                    f"Al backup {ruta.name} le faltan tablas: {', '.join(faltan)}.")
            return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in TABLAS_ESENCIALES}
        finally:
            conn.close()
    except sqlite3.Error as error:
        raise BackupFallido(f"El backup {ruta.name} no se abre como SQLite: {error}.")


def _borrar(ruta):
    for r in (ruta, Path(f"{ruta}-journal")):
        try:
            r.unlink()
        except OSError:
            pass   # no existe, o no se pudo: un .partial no parece un backup


def crear_backup(momento=None):
    """Crea un backup validado de la base principal y devuelve sus datos.

    {"ruta": Path, "nombre": str, "bytes": int, "filas": {tabla: n}}.
    Lanza BackupNoConfigurado o BackupFallido. Nunca deja un archivo con
    nombre de backup que no haya pasado la validacion.
    """
    carpeta = carpeta_destino()
    origen = db.ruta_base()
    if not origen.is_file():
        raise BackupFallido(f"No existe la base de datos {origen}.")

    momento = momento or datetime.now()
    base = nombre_backup(momento)
    temporal = carpeta / f"tmp-{base[:-len('.sqlite')]}-{uuid.uuid4().hex[:8]}.partial"

    try:
        try:
            src = sqlite3.connect(f"file:{origen.as_posix()}?mode=ro", uri=True)
            try:
                dst = sqlite3.connect(temporal)
                try:
                    src.backup(dst)
                finally:
                    dst.close()
            finally:
                src.close()
        except (sqlite3.Error, OSError) as error:
            raise BackupFallido(f"No se pudo escribir el backup en {carpeta}: {error}.")

        filas = validar(temporal)
        tam = temporal.stat().st_size
        final = _renombrar_sin_sobrescribir(temporal, carpeta, base)
    except BaseException:
        _borrar(temporal)
        raise

    if not final.is_file() or final.stat().st_size != tam:
        raise BackupFallido(f"El backup {final.name} no se encuentra tras renombrarlo.")
    return {"ruta": final, "nombre": final.name, "bytes": tam, "filas": filas}


def _renombrar_sin_sobrescribir(temporal, carpeta, base):
    """Renombra al primer nombre libre: base, base_2, base_3... Nunca sustituye."""
    raiz = base[:-len(".sqlite")]
    for n in range(1, MAX_INTENTOS_NOMBRE + 1):
        final = carpeta / (base if n == 1 else f"{raiz}_{n}.sqlite")
        if final.exists():
            continue
        try:
            # os.rename no sustituye un archivo existente en Windows
            # (FileExistsError); con la comprobacion anterior, tampoco en otros.
            os.rename(temporal, final)
            return final
        except FileExistsError:
            continue
        except OSError as error:
            raise BackupFallido(f"No se pudo dar nombre final al backup: {error}.")
    raise BackupFallido("Demasiados backups con el mismo segundo; inténtalo de nuevo.")
