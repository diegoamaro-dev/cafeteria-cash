"""Venta actual (FASE 2).

La venta actual es TEMPORAL: vive en la memoria del proceso Flask y se pierde
al reiniciar. Todavia no es una venta registrada, asi que no toca SQLite.

Es una caja unica: hay una sola venta actual en curso. Un Lock evita que dos
peticiones simultaneas dejen las cantidades a medias.

Todos los importes son enteros de centimos. Nunca float.
"""

import threading

# --------------------------------------------------------------------------
# Calculo: funciones puras, sin estado. Son las que se testean.
# --------------------------------------------------------------------------


def subtotal_centimos(precio_centimos, cantidad):
    """Subtotal de una linea, en centimos."""
    return int(precio_centimos) * int(cantidad)


def total_centimos(lineas):
    """Total de la venta, en centimos."""
    return sum(subtotal_centimos(l["precio_centimos"], l["cantidad"]) for l in lineas)


def con_subtotales(lineas):
    """Devuelve las lineas con su subtotal calculado, para la plantilla."""
    return [dict(l, subtotal_centimos=subtotal_centimos(l["precio_centimos"], l["cantidad"]))
            for l in lineas]


# --------------------------------------------------------------------------
# Estado: la venta actual en memoria.
# --------------------------------------------------------------------------

_lock = threading.Lock()
_lineas = []  # [{producto_id, nombre, precio_centimos, cantidad}, ...]


def _buscar(producto_id):
    for linea in _lineas:
        if linea["producto_id"] == producto_id:
            return linea
    return None


def lineas():
    """Copia de las lineas actuales, en el orden en que se anadieron."""
    with _lock:
        return [dict(l) for l in _lineas]


def anadir(producto_id, nombre, precio_centimos):
    """Anade una unidad. Si el producto ya esta en la venta, suma 1."""
    with _lock:
        linea = _buscar(producto_id)
        if linea is None:
            _lineas.append({
                "producto_id": producto_id,
                "nombre": nombre,
                "precio_centimos": int(precio_centimos),
                "cantidad": 1,
            })
        else:
            linea["cantidad"] += 1


def cambiar_cantidad(producto_id, delta):
    """Suma delta a la cantidad. Si llega a 0 o menos, elimina la linea."""
    with _lock:
        linea = _buscar(producto_id)
        if linea is None:
            return
        linea["cantidad"] += delta
        if linea["cantidad"] <= 0:
            _lineas.remove(linea)


def eliminar_linea(producto_id):
    """Elimina la linea entera, sea cual sea su cantidad."""
    with _lock:
        linea = _buscar(producto_id)
        if linea is not None:
            _lineas.remove(linea)


def cancelar():
    """Vacia la venta actual. No escribe nada en ningun sitio."""
    with _lock:
        _lineas.clear()
