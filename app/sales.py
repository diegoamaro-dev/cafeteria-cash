"""Ventas confirmadas (FASE 3) e historial y anulaciones (FASE 4).

Una venta confirmada se escribe en SQLite en UNA sola transaccion: cabecera y
lineas, o nada. Nunca se borra: se anula cambiando `status` a 'VOID'.

FASE 6: un dia cerrado no admite nuevas ventas ni anulaciones. Se comprueba
dentro de la misma transaccion BEGIN IMMEDIATE que escribe, no antes.

Todos los importes son enteros de centimos.
"""

from datetime import datetime

from .cart import subtotal_centimos, total_centimos
from .cierre import exigir_dia_abierto
from .db import get_connection, transaccion

PREFIJO_SERIE = "V"
DIGITOS = 6


class VentaInvalida(ValueError):
    """La venta no se puede confirmar."""


def _siguiente_numero(conn, momento):
    """Numero correlativo del anio en curso: V-2026-000001, V-2026-000002...

    Se llama DENTRO de la transaccion IMMEDIATE, con el bloqueo de escritura
    tomado, para que dos cobros simultaneos no calculen el mismo numero.
    La restriccion UNIQUE de sale_number es la garantia final.

    El numero sale de las ventas ya confirmadas. Si un cobro falla se hace
    rollback completo: no queda venta y el numero no se consume, asi que el
    siguiente cobro correcto recibe ese mismo numero. El numero de una venta
    que si llego a confirmarse no se reutiliza nunca.
    """
    prefijo = f"{PREFIJO_SERIE}-{momento.year}-"

    fila = conn.execute(
        "SELECT sale_number FROM sale WHERE sale_number LIKE ?"
        " ORDER BY sale_number DESC LIMIT 1",
        (prefijo + "%",),
    ).fetchone()

    # El relleno con ceros hace que el orden alfabetico sea el numerico.
    siguiente = 1 if fila is None else int(fila["sale_number"].rsplit("-", 1)[1]) + 1
    return f"{prefijo}{siguiente:0{DIGITOS}d}"


def _validar(lineas):
    if not lineas:
        raise VentaInvalida("No hay productos en la venta.")

    for linea in lineas:
        if int(linea["cantidad"]) <= 0:
            raise VentaInvalida(f"Cantidad invalida en '{linea['nombre']}'.")
        if int(linea["precio_centimos"]) < 0:
            raise VentaInvalida(f"Precio invalido en '{linea['nombre']}'.")


def confirmar_venta(lineas, momento=None):
    """Guarda una venta en efectivo y devuelve sus datos.

    `lineas` son las de la venta actual: producto_id, nombre, precio_centimos
    y cantidad. El nombre y el precio se copian tal cual: son lo que el cliente
    vio en pantalla y lo que pago.

    Si falla cualquier linea se deshace todo y se relanza el error. La venta
    actual NO se toca aqui: el que llama solo debe vaciarla si esto termina bien.
    """
    _validar(lineas)

    momento = momento or datetime.now()
    creado_en = momento.strftime("%Y-%m-%d %H:%M:%S")
    total = total_centimos(lineas)

    with transaccion() as conn:
        # Con el bloqueo de escritura ya tomado: si el dia se cerro antes, se
        # rechaza aqui y el ROLLBACK deja la base sin cabecera ni lineas.
        exigir_dia_abierto(conn, creado_en[:10], "registrar ventas de esa fecha")

        numero = _siguiente_numero(conn, momento)

        cursor = conn.execute(
            "INSERT INTO sale (sale_number, created_at, total_cents, status)"
            " VALUES (?, ?, ?, 'VALID')",
            (numero, creado_en, total),
        )
        venta_id = cursor.lastrowid

        for linea in lineas:
            cantidad = int(linea["cantidad"])
            precio = int(linea["precio_centimos"])
            conn.execute(
                "INSERT INTO sale_item (sale_id, product_id, product_name_snapshot,"
                " unit_price_cents_snapshot, quantity, subtotal_cents)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    venta_id,
                    linea["producto_id"],
                    linea["nombre"],
                    precio,
                    cantidad,
                    subtotal_centimos(precio, cantidad),
                ),
            )

    return {
        "id": venta_id,
        "sale_number": numero,
        "created_at": creado_en,
        "total_cents": total,
    }


# ---------------------------------------------------------------------------
# FASE 4: historial y anulaciones
# ---------------------------------------------------------------------------


class VentaNoEncontrada(LookupError):
    """No existe ninguna venta con ese id."""


class VentaYaAnulada(ValueError):
    """La venta ya estaba anulada. No se ha modificado nada."""


def listar_ventas():
    """Todas las ventas confirmadas, de la mas reciente a la mas antigua.

    Se ordena por id, que es el orden real de confirmacion. created_at depende
    del reloj del portatil y podria no ser monotono si el reloj se ajusta.
    """
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT s.id, s.sale_number, s.created_at, s.total_cents, s.status,"
            "       s.voided_at,"
            "       EXISTS (SELECT 1 FROM daily_close c"
            "               WHERE c.business_date = substr(s.created_at, 1, 10))"
            "         AS dia_cerrado"
            " FROM sale s ORDER BY s.id DESC"
        ).fetchall()
    finally:
        conn.close()


def anular_venta(venta_id, momento=None):
    """Anula una venta VALID. Devuelve su numero y la hora de anulacion.

    Solo cambia `status` a 'VOID' y rellena `voided_at`. No toca el numero, la
    fecha de venta, el total ni ninguna linea: el historico economico queda
    intacto. Nunca borra nada.

    La actualizacion esta condicionada a `status = 'VALID'`, asi que:
    - una venta ya anulada no se vuelve a modificar (voided_at no cambia);
    - una venta anulada no puede volver a VALID por esta via.

    FASE 6: si el dia de la venta (su created_at) ya esta cerrado, se rechaza.
    Todo ocurre dentro de un unico BEGIN IMMEDIATE, asi que un cierre no puede
    colarse entre la comprobacion y la anulacion.
    """
    momento = momento or datetime.now()
    anulada_en = momento.strftime("%Y-%m-%d %H:%M:%S")

    with transaccion() as conn:
        fila = conn.execute(
            "SELECT sale_number, created_at, status, voided_at FROM sale WHERE id = ?",
            (venta_id,),
        ).fetchone()

        if fila is None:
            raise VentaNoEncontrada(f"No existe la venta #{venta_id}.")
        if fila["status"] != "VALID":
            raise VentaYaAnulada(
                f"La venta {fila['sale_number']} ya estaba anulada desde {fila['voided_at']}."
            )

        exigir_dia_abierto(conn, fila["created_at"][:10], "anular ventas de esa fecha")

        cursor = conn.execute(
            "UPDATE sale SET status = 'VOID', voided_at = ?"
            " WHERE id = ? AND status = 'VALID'",
            (anulada_en, venta_id),
        )
        if cursor.rowcount != 1:
            # No deberia ocurrir con el bloqueo tomado; si ocurre, no se toca nada.
            raise VentaYaAnulada(f"La venta {fila['sale_number']} ya no estaba VALID.")

    return {"id": venta_id, "sale_number": fila["sale_number"], "voided_at": anulada_en}
