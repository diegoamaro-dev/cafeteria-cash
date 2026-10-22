"""Cierre diario (FASE 6).

Un cierre es la foto definitiva de un dia de caja. Decision permanente:

    UN DIA CERRADO NO ADMITE NUEVAS VENTAS NI ANULACIONES.

- El cierre no modifica ni borra ninguna venta.
- No existe reapertura, edicion ni borrado de cierres.
- La comprobacion "este dia esta cerrado" se hace DENTRO de la transaccion
  BEGIN IMMEDIATE de cada venta y cada anulacion, y el cierre se escribe dentro
  de su propio BEGIN IMMEDIATE. SQLite solo permite un escritor a la vez, asi
  que cierre y venta/anulacion no pueden ganar los dos una carrera: el que
  llega segundo ve lo que hizo el primero.

Todos los importes son enteros de centimos.

IVA: DECISION EXPLICITA. Todo lo que se registra en este TPV temporal (cafes y
bocadillos) lleva un unico tipo de IVA del 10 %. No hay varios tipos ni IVA por
producto. El efectivo valido es IVA incluido; cada cierre congela el tipo, la
base imponible y la cuota.
"""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from . import establecimiento, resumen
from .db import get_connection, transaccion

PREFIJO_SERIE = "C"
DIGITOS = 6

# Columna de daily_close <- campo de establishment. Se congelan al cerrar.
SNAPSHOT_ESTABLECIMIENTO = {
    "holder_name_snapshot": "name",
    "tax_id_snapshot": "tax_id",
    "trade_name_snapshot": "trade_name",
    "address_snapshot": "address",
}

# Tipo de IVA unico (%) que se congela en cada cierre nuevo. Cambiarlo no afecta
# a los cierres ya guardados: el PDF lee el tipo congelado en cada cierre.
TIPO_IVA = 10

# Columnas del desglose de IVA congelado en daily_close.
SNAPSHOT_IVA = ("vat_rate_percent", "vat_base_cents", "vat_cents")


def desglose_iva(total_centimos, tipo=TIPO_IVA):
    """(base imponible, cuota) en centimos enteros de un total IVA incluido.

    base = total * 100 / (100 + tipo), redondeada al centimo (mitad hacia
    arriba) con Decimal, nunca float; cuota = total - base. Asi
    base + cuota == total siempre, sin descuadres de un centimo.
    Ejemplo al 10 %: 4060 -> (3691, 369).
    """
    if not isinstance(total_centimos, int) or total_centimos < 0:
        raise ValueError(f"Total no valido: {total_centimos!r}")
    base = (Decimal(total_centimos) * 100 / (100 + tipo)).quantize(
        Decimal(1), rounding=ROUND_HALF_UP)
    base = int(base)
    return base, total_centimos - base


class DiaCerrado(ValueError):
    """El dia ya esta cerrado: no admite ventas, anulaciones ni otro cierre."""


class CierreInvalido(ValueError):
    """No se puede cerrar ese dia (por ejemplo, un dia futuro)."""


# ---------------------------------------------------------------------------
# Comprobacion compartida con ventas y anulaciones
# ---------------------------------------------------------------------------


def numero_de_cierre(conn, fecha):
    """close_number del cierre de `fecha`, o None si el dia sigue abierto.

    Se llama con la conexion de la transaccion en curso.
    """
    fila = conn.execute(
        "SELECT close_number FROM daily_close WHERE business_date = ?", (fecha,)
    ).fetchone()
    return fila["close_number"] if fila else None


def exigir_dia_abierto(conn, fecha, accion):
    """Lanza DiaCerrado si `fecha` ya tiene cierre. `accion` es para el mensaje."""
    numero = numero_de_cierre(conn, fecha)
    if numero is not None:
        raise DiaCerrado(
            f"El día {fecha} ya está cerrado ({numero}): no se pueden {accion}."
        )


def dia_esta_cerrado(fecha):
    """Consulta suelta, para la interfaz. La garantia real esta en la logica."""
    conn = get_connection()
    try:
        return numero_de_cierre(conn, fecha) is not None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Calculo: el mismo para la previsualizacion y para el cierre definitivo
# ---------------------------------------------------------------------------


def _calcular_cierre(conn, fecha):
    """Cifras del cierre de `fecha` sobre una conexion ya abierta.

    Reutiliza el calculo del resumen diario (FASE 5): no lo duplica.
    Devuelve las mismas claves que las columnas de daily_close.
    """
    r = resumen._resumen_en_conexion(conn, fecha)

    # Primera y ultima venta del dia por orden de confirmacion (id), no por
    # reloj, incluyan o no ventas anuladas despues.
    primera = conn.execute(
        "SELECT sale_number FROM sale WHERE substr(created_at, 1, 10) = ?"
        " ORDER BY id ASC LIMIT 1", (fecha,)).fetchone()
    ultima = conn.execute(
        "SELECT sale_number FROM sale WHERE substr(created_at, 1, 10) = ?"
        " ORDER BY id DESC LIMIT 1", (fecha,)).fetchone()

    validas = r["efectivo_valido_centimos"]
    anuladas = r["total_anulado_centimos"]
    base, cuota = desglose_iva(validas)

    return {
        "business_date": fecha,
        "first_sale_number": primera["sale_number"] if primera else None,
        "last_sale_number": ultima["sale_number"] if ultima else None,
        "valid_sales_count": r["ventas_validas"],
        "void_sales_count": r["ventas_anuladas"],
        "gross_cents": validas + anuladas,
        "void_cents": anuladas,
        "valid_cash_cents": validas,
        "vat_rate_percent": TIPO_IVA,
        "vat_base_cents": base,
        "vat_cents": cuota,
        "items": [
            {"product_name_snapshot": u["nombre"], "units": u["unidades"]}
            for u in r["unidades"]
        ],
    }


def _snapshot_establecimiento(conn, exigir):
    """Los cuatro datos del establecimiento que se congelarian en el cierre.

    Con `exigir`, si falta alguno lanza establecimiento.SinConfigurar. Sin el,
    devuelve None en los que falten (para mostrarlo en la previsualizacion).
    """
    datos = establecimiento.leer(conn)
    if exigir:
        establecimiento.exigir_completos(datos)
    datos = datos or {}
    return {columna: datos.get(campo) or None
            for columna, campo in SNAPSHOT_ESTABLECIMIENTO.items()}


def previsualizar_cierre(fecha):
    """Lo que se guardaria si se cerrara `fecha` ahora. No escribe nada.

    Incluye los datos del establecimiento que quedarian congelados (None en los
    que falten: sin ellos no se puede cerrar).
    """
    date.fromisoformat(fecha)
    conn = get_connection()
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        datos = _calcular_cierre(conn, fecha)
        datos.update(_snapshot_establecimiento(conn, exigir=False))
        conn.execute("COMMIT")
    finally:
        conn.close()
    return datos


# ---------------------------------------------------------------------------
# Cierre definitivo
# ---------------------------------------------------------------------------


def _siguiente_numero(conn, fecha):
    """C-2026-000001, C-2026-000002... correlativo por anio del dia cerrado.

    Dentro del BEGIN IMMEDIATE: dos cierres no pueden calcular el mismo numero.
    Sale de los cierres ya confirmados, asi que un rollback no consume numero y
    un numero confirmado no se reutiliza nunca. UNIQUE es la garantia final.
    """
    prefijo = f"{PREFIJO_SERIE}-{fecha[:4]}-"
    fila = conn.execute(
        "SELECT close_number FROM daily_close WHERE close_number LIKE ?"
        " ORDER BY close_number DESC LIMIT 1",
        (prefijo + "%",),
    ).fetchone()
    siguiente = 1 if fila is None else int(fila["close_number"].rsplit("-", 1)[1]) + 1
    return f"{prefijo}{siguiente:0{DIGITOS}d}"


def cerrar_dia(fecha, momento=None):
    """Cierra `fecha` definitivamente y devuelve el cierre guardado.

    Todo en una unica transaccion BEGIN IMMEDIATE: comprobar que sigue abierto,
    congelar los datos del establecimiento, calcular, numerar, guardar cabecera
    y desglose. Si algo falla (tambien si faltan datos del establecimiento),
    ROLLBACK completo: no queda cierre parcial y el dia sigue abierto.
    """
    dia = date.fromisoformat(fecha)
    momento = momento or datetime.now()
    if dia > momento.date():
        raise CierreInvalido(f"No se puede cerrar un día futuro ({fecha}).")
    cerrado_en = momento.strftime("%Y-%m-%d %H:%M:%S")

    with transaccion() as conn:
        existente = numero_de_cierre(conn, fecha)
        if existente is not None:
            raise DiaCerrado(
                f"El día {fecha} ya está cerrado ({existente}). No se crea otro cierre."
            )

        # Los datos del establecimiento vigentes AHORA, en la misma transaccion.
        empresa = _snapshot_establecimiento(conn, exigir=True)
        datos = _calcular_cierre(conn, fecha)
        numero = _siguiente_numero(conn, fecha)

        cursor = conn.execute(
            "INSERT INTO daily_close (close_number, business_date, closed_at,"
            " first_sale_number, last_sale_number, valid_sales_count,"
            " void_sales_count, gross_cents, void_cents, valid_cash_cents,"
            " holder_name_snapshot, tax_id_snapshot, trade_name_snapshot,"
            " address_snapshot, vat_rate_percent, vat_base_cents, vat_cents)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (numero, fecha, cerrado_en,
             datos["first_sale_number"], datos["last_sale_number"],
             datos["valid_sales_count"], datos["void_sales_count"],
             datos["gross_cents"], datos["void_cents"], datos["valid_cash_cents"],
             empresa["holder_name_snapshot"], empresa["tax_id_snapshot"],
             empresa["trade_name_snapshot"], empresa["address_snapshot"],
             datos["vat_rate_percent"], datos["vat_base_cents"], datos["vat_cents"]),
        )
        cierre_id = cursor.lastrowid

        for item in datos["items"]:
            conn.execute(
                "INSERT INTO daily_close_item (daily_close_id, product_name_snapshot, units)"
                " VALUES (?, ?, ?)",
                (cierre_id, item["product_name_snapshot"], item["units"]),
            )

    return obtener_cierre(fecha)


def obtener_cierre(fecha):
    """El cierre guardado de `fecha`, tal cual esta en la base, o None.

    Se lee solo de daily_close y daily_close_item: nunca se recalcula desde las
    ventas, ni desde el catalogo actual, ni desde la configuracion actual del
    establecimiento (sus cuatro datos van congelados en el propio cierre), ni
    se recalcula el IVA (tipo, base y cuota van congelados).
    """
    conn = get_connection()
    try:
        cabecera = conn.execute(
            "SELECT id, close_number, business_date, closed_at, first_sale_number,"
            " last_sale_number, valid_sales_count, void_sales_count, gross_cents,"
            " void_cents, valid_cash_cents, holder_name_snapshot, tax_id_snapshot,"
            " trade_name_snapshot, address_snapshot, vat_rate_percent,"
            " vat_base_cents, vat_cents"
            " FROM daily_close WHERE business_date = ?",
            (fecha,),
        ).fetchone()
        if cabecera is None:
            return None

        cierre = dict(cabecera)
        cierre["items"] = [
            {"product_name_snapshot": f["product_name_snapshot"], "units": f["units"]}
            for f in conn.execute(
                "SELECT product_name_snapshot, units FROM daily_close_item"
                " WHERE daily_close_id = ? ORDER BY units DESC, product_name_snapshot",
                (cierre["id"],),
            )
        ]
        return cierre
    finally:
        conn.close()
