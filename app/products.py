"""Operaciones sobre productos (FASE 1).

Un producto no se borra nunca: se desactiva. En cuanto existan ventas
historicas, borrarlo dejaria lineas de venta huerfanas.
"""

from .db import get_connection

LONGITUD_MAXIMA_NOMBRE = 60


class DatosInvalidos(ValueError):
    """Los datos del producto no son validos."""


def _validar_nombre(nombre):
    limpio = (nombre or "").strip()
    if not limpio:
        raise DatosInvalidos("El nombre es obligatorio.")
    if len(limpio) > LONGITUD_MAXIMA_NOMBRE:
        raise DatosInvalidos(
            f"El nombre no puede superar {LONGITUD_MAXIMA_NOMBRE} caracteres."
        )
    return limpio


def _validar_orden(orden):
    if orden is None or str(orden).strip() == "":
        return None
    try:
        return int(str(orden).strip())
    except ValueError:
        raise DatosInvalidos("El orden debe ser un numero entero.")


def listar_productos(solo_activos=False):
    """Devuelve los productos ordenados por orden visual y nombre."""
    sql = "SELECT id, name, price_cents, active, display_order FROM product"
    if solo_activos:
        sql += " WHERE active = 1"
    sql += " ORDER BY display_order, name COLLATE NOCASE, id"

    conn = get_connection()
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def obtener_producto(producto_id):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT id, name, price_cents, active, display_order"
            " FROM product WHERE id = ?",
            (producto_id,),
        ).fetchone()
    finally:
        conn.close()


def crear_producto(nombre, precio_centimos, orden=None):
    """Crea un producto activo y devuelve su id."""
    nombre = _validar_nombre(nombre)
    orden = _validar_orden(orden)

    conn = get_connection()
    try:
        with conn:
            if orden is None:
                fila = conn.execute(
                    "SELECT COALESCE(MAX(display_order), 0) + 10 AS siguiente FROM product"
                ).fetchone()
                orden = fila["siguiente"]

            cursor = conn.execute(
                "INSERT INTO product (name, price_cents, active, display_order)"
                " VALUES (?, ?, 1, ?)",
                (nombre, int(precio_centimos), orden),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def actualizar_producto(producto_id, nombre, precio_centimos, orden=None):
    """Edita nombre, precio y orden visual. No cambia el estado activo."""
    nombre = _validar_nombre(nombre)
    orden = _validar_orden(orden)

    conn = get_connection()
    try:
        with conn:
            if orden is None:
                cursor = conn.execute(
                    "UPDATE product SET name = ?, price_cents = ? WHERE id = ?",
                    (nombre, int(precio_centimos), producto_id),
                )
            else:
                cursor = conn.execute(
                    "UPDATE product SET name = ?, price_cents = ?, display_order = ?"
                    " WHERE id = ?",
                    (nombre, int(precio_centimos), orden, producto_id),
                )
            if cursor.rowcount == 0:
                raise DatosInvalidos("El producto no existe.")
    finally:
        conn.close()


def cambiar_estado(producto_id, activo):
    """Activa o desactiva un producto. Nunca lo borra."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE product SET active = ? WHERE id = ?",
                (1 if activo else 0, producto_id),
            )
            if cursor.rowcount == 0:
                raise DatosInvalidos("El producto no existe.")
    finally:
        conn.close()
