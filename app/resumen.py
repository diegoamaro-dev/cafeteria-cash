"""Resumen diario (FASE 5). Solo lectura: no escribe nada en la base.

Una venta pertenece al dia de su `created_at` (hora local de la cafeteria),
nunca al de su anulacion. Una venta confirmada el dia A y anulada el dia B
cuenta como anulada en el resumen del dia A.

Todos los importes son enteros de centimos.
"""

from datetime import date

from .db import get_connection


def hoy():
    """Dia local de la cafeteria, como 'YYYY-MM-DD'. Aparte para los tests."""
    return date.today().isoformat()


def resumen_del_dia(fecha):
    """Resumen de las ventas confirmadas el dia `fecha` ('YYYY-MM-DD').

    - ventas validas / efectivo valido: ventas con status 'VALID';
    - anulaciones / total anulado: ventas con status 'VOID', con su importe
      original intacto;
    - unidades por producto: solo de ventas VALID, agrupadas por el nombre
      guardado en la venta (product_name_snapshot), nunca por el nombre actual
      del producto.
    """
    date.fromisoformat(fecha)  # rechaza fechas mal formadas antes de consultar

    conn = get_connection()
    conn.isolation_level = None  # transaccion de lectura explicita
    try:
        # Las consultas ven la misma foto de la base, aunque se cobre una venta
        # a la vez: totales y unidades nunca salen de momentos distintos.
        conn.execute("BEGIN")
        resultado = _resumen_en_conexion(conn, fecha)
        conn.execute("COMMIT")
    finally:
        conn.close()

    return resultado


def _resumen_en_conexion(conn, fecha):
    """El calculo del resumen sobre una conexion ya abierta.

    No abre ni cierra transacciones: lo hace quien llama. Asi el cierre diario
    puede calcular exactamente el mismo resumen dentro de su BEGIN IMMEDIATE.
    """
    por_estado = {
        fila["status"]: fila
        for fila in conn.execute(
            "SELECT status, COUNT(*) AS ventas, SUM(total_cents) AS total"
            " FROM sale"
            " WHERE substr(created_at, 1, 10) = ?"
            " GROUP BY status",
            (fecha,),
        )
    }

    unidades = [
        {"nombre": fila["nombre"], "unidades": fila["unidades"]}
        for fila in conn.execute(
            "SELECT i.product_name_snapshot AS nombre,"
            "       SUM(i.quantity) AS unidades"
            " FROM sale_item i"
            " JOIN sale s ON s.id = i.sale_id"
            " WHERE s.status = 'VALID'"
            "   AND substr(s.created_at, 1, 10) = ?"
            " GROUP BY i.product_name_snapshot"
            " ORDER BY unidades DESC, nombre",
            (fecha,),
        )
    ]

    validas = por_estado.get("VALID")
    anuladas = por_estado.get("VOID")

    return {
        "fecha": fecha,
        "ventas_validas": validas["ventas"] if validas else 0,
        "efectivo_valido_centimos": validas["total"] if validas else 0,
        "ventas_anuladas": anuladas["ventas"] if anuladas else 0,
        "total_anulado_centimos": anuladas["total"] if anuladas else 0,
        "unidades": unidades,
    }
