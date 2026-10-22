"""Datos del establecimiento (FASE 7): cabecera del PDF de cierre.

- titular (nombre o razon social)   -> columna `name`
- NIF                               -> columna `tax_id`
- nombre comercial                  -> columna `trade_name`
- direccion                         -> columna `address`

Se guardan en SQLite, en una unica fila de la tabla `establishment`: no estan
en el codigo, ni en las plantillas, ni en Git, y viajan con la base de datos en
el backup. Los cuatro son obligatorios para generar el PDF.

No hay usuarios ni sistema general de configuracion: solo estos datos.
"""

from datetime import datetime

from .db import get_connection

CAMPOS = ("name", "tax_id", "trade_name", "address")
LIMITES = {"name": 100, "tax_id": 20, "trade_name": 100, "address": 200}
ETIQUETAS = {"name": "Titular", "tax_id": "NIF",
             "trade_name": "Nombre comercial", "address": "Dirección"}


class DatosInvalidos(ValueError):
    """Los datos del establecimiento no son validos."""


class SinConfigurar(LookupError):
    """Faltan datos del establecimiento."""


def _limpiar(campo, valor):
    texto = " ".join((valor or "").split())   # sin espacios ni saltos sobrantes
    etiqueta = ETIQUETAS[campo]
    if not texto:
        raise DatosInvalidos(f"{etiqueta}: es obligatorio.")
    if len(texto) > LIMITES[campo]:
        raise DatosInvalidos(f"{etiqueta}: máximo {LIMITES[campo]} caracteres.")
    try:
        # El PDF usa las fuentes estandar con codificacion WinAnsi (cp1252):
        # un caracter que no se pueda representar saldria como "?".
        texto.encode("cp1252")
    except UnicodeEncodeError:
        raise DatosInvalidos(f"{etiqueta}: contiene caracteres que el PDF no puede mostrar.")
    return texto


def leer(conn):
    """Los datos guardados, sobre una conexion ya abierta, o None si no hay fila.

    Lo usa el cierre dentro de su BEGIN IMMEDIATE para congelar exactamente los
    datos vigentes en ese instante.
    """
    fila = conn.execute(
        "SELECT name, tax_id, trade_name, address, updated_at"
        " FROM establishment WHERE id = 1"
    ).fetchone()
    return dict(fila) if fila else None


def obtener():
    """Los datos guardados como dict, o None si aun no hay ninguna fila."""
    conn = get_connection()
    try:
        return leer(conn)
    finally:
        conn.close()


def exigir_completos(datos):
    """Devuelve `datos` si estan los cuatro; si no, SinConfigurar."""
    faltan = [ETIQUETAS[c] for c in CAMPOS if not (datos or {}).get(c)]
    if faltan:
        raise SinConfigurar(
            "Faltan datos del establecimiento (" + ", ".join(faltan) + ")."
            " Configúralos en Productos → Datos del establecimiento."
        )
    return datos


def obtener_obligatorio():
    """Los datos completos, o SinConfigurar si falta alguno."""
    return exigir_completos(obtener())


def guardar(titular, nif, nombre_comercial, direccion, momento=None):
    """Crea o sustituye la unica fila de datos del establecimiento."""
    datos = {
        "name": _limpiar("name", titular),
        "tax_id": _limpiar("tax_id", nif),
        "trade_name": _limpiar("trade_name", nombre_comercial),
        "address": _limpiar("address", direccion),
    }
    actualizado = (momento or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO establishment (id, name, tax_id, trade_name, address, updated_at)"
                " VALUES (1, ?, ?, ?, ?, ?)"
                " ON CONFLICT (id) DO UPDATE SET name = excluded.name,"
                " tax_id = excluded.tax_id, trade_name = excluded.trade_name,"
                " address = excluded.address, updated_at = excluded.updated_at",
                (datos["name"], datos["tax_id"], datos["trade_name"],
                 datos["address"], actualizado),
            )
    finally:
        conn.close()
    return dict(datos, updated_at=actualizado)
