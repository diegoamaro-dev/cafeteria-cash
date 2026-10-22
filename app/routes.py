"""Rutas de la aplicacion.

FASE 0: arranque y comprobacion de salud.
FASE 1: gestion de productos y botones en la pantalla principal.
FASE 2: venta actual temporal (anadir, +, -, eliminar linea, cancelar).
FASE 3: cobro en efectivo y persistencia de la venta en SQLite.
FASE 4: historial de ventas y anulacion sin borrado.
FASE 5: resumen del dia (solo lectura).
FASE 6: cierre diario. Un dia cerrado no admite nuevas ventas ni anulaciones.
FASE 7: PDF A4 del cierre y datos del establecimiento.
FASE 8: backup automatico tras cerrar el dia y backup manual.
"""

import logging
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, Response, jsonify, redirect, render_template, request, url_for

from . import backup, cart, cierre, establecimiento, pdf_cierre, products, resumen, sales
from .money import ImporteInvalido, format_euros, parse_euros

bp = Blueprint("main", __name__)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pantalla principal y venta actual
# ---------------------------------------------------------------------------


@bp.route("/")
def index():
    """Botonera de productos activos + venta actual en curso."""
    return _render_index(mensaje=request.args.get("ok"))


@bp.route("/venta/anadir/<int:producto_id>", methods=["POST"])
def anadir_a_venta(producto_id):
    """Cada pulsacion anade una unidad a la venta actual."""
    producto = products.obtener_producto(producto_id)

    # El precio y el nombre se toman SIEMPRE de la base, nunca del formulario:
    # el navegador no decide lo que cuesta un cafe.
    if producto is None:
        return _render_index(error="El producto no existe."), 404
    if not producto["active"]:
        return _render_index(
            error=f"'{producto['name']}' esta desactivado y no puede anadirse."
        ), 409

    cart.anadir(producto["id"], producto["name"], producto["price_cents"])
    return redirect(url_for("main.index"))


@bp.route("/venta/linea/<int:producto_id>/cantidad", methods=["POST"])
def cambiar_cantidad(producto_id):
    """Botones + y -. Al llegar a 0 la linea desaparece."""
    delta = 1 if request.form.get("delta") == "1" else -1
    cart.cambiar_cantidad(producto_id, delta)
    return redirect(url_for("main.index"))


@bp.route("/venta/linea/<int:producto_id>/eliminar", methods=["POST"])
def eliminar_linea(producto_id):
    """Elimina la linea entera antes de confirmar."""
    cart.eliminar_linea(producto_id)
    return redirect(url_for("main.index"))


@bp.route("/venta/cancelar", methods=["POST"])
def cancelar_venta():
    """Vacia la venta actual. No escribe nada en SQLite."""
    cart.cancelar()
    return redirect(url_for("main.index"))


@bp.route("/venta/cobrar", methods=["POST"])
def cobrar_en_efectivo():
    """Confirma la venta en efectivo y la guarda en SQLite.

    La venta actual se vacia UNICAMENTE si la escritura completa ha terminado
    bien. Si algo falla, el carrito se queda tal cual para poder reintentar.
    """
    lineas = cart.lineas()

    try:
        venta = sales.confirmar_venta(lineas)
    except sales.VentaInvalida as error:
        return _render_index(error=str(error)), 400
    except cierre.DiaCerrado as error:
        # La venta actual se conserva: no se ha escrito nada.
        return _render_index(error=str(error)), 409
    except sqlite3.Error as error:
        return _render_index(
            error=f"No se ha podido guardar la venta: {error}."
                  " La venta actual se mantiene, vuelve a intentarlo."
        ), 500

    cart.cancelar()

    return redirect(url_for(
        "main.index",
        ok=f"Venta {venta['sale_number']} registrada — {format_euros(venta['total_cents'])}",
    ))


@bp.route("/health")
def health():
    """Comprobacion automatica del arranque (usada por las pruebas de fase)."""
    return jsonify(status="ok", fase="7")


# ---------------------------------------------------------------------------
# Historial y anulaciones
# ---------------------------------------------------------------------------


@bp.route("/historial")
def historial():
    """Ventas confirmadas, de la mas reciente a la mas antigua."""
    return _render_historial(mensaje=request.args.get("ok"))


@bp.route("/historial/<int:venta_id>/anular", methods=["POST"])
def anular_venta(venta_id):
    """Marca la venta como ANULADA. No borra ni modifica su contenido."""
    try:
        venta = sales.anular_venta(venta_id)
    except sales.VentaNoEncontrada as error:
        return _render_historial(error=str(error)), 404
    except sales.VentaYaAnulada as error:
        return _render_historial(error=str(error)), 409
    except cierre.DiaCerrado as error:
        return _render_historial(error=str(error)), 409

    return redirect(url_for(
        "main.historial",
        ok=f"Venta {venta['sale_number']} anulada a las {venta['voided_at']}.",
    ))


# ---------------------------------------------------------------------------
# Resumen del dia
# ---------------------------------------------------------------------------


@bp.route("/resumen")
def resumen_del_dia():
    """Resumen del dia local actual. Solo consulta: no cierra nada."""
    return render_template(
        "summary.html",
        r=resumen.resumen_del_dia(resumen.hoy()),
    )


# ---------------------------------------------------------------------------
# Cierre diario
# ---------------------------------------------------------------------------


def _hoy_y_ayer():
    """Las dos unicas fechas que la interfaz permite consultar y cerrar.

    Ayer existe para poder cerrar despues de medianoche. Las ventas siguen
    perteneciendo estrictamente a la fecha natural de su created_at.
    """
    hoy = resumen.hoy()
    ayer = (date.fromisoformat(hoy) - timedelta(days=1)).isoformat()
    return hoy, ayer


@bp.route("/cierre")
def cierre_del_dia():
    """Cierre de hoy (por defecto) o de ayer (?dia=ayer). Ninguna otra fecha."""
    hoy, ayer = _hoy_y_ayer()
    fecha = ayer if request.args.get("dia") == "ayer" else hoy
    return _render_cierre(fecha, mensaje=request.args.get("ok"))


@bp.route("/cierre", methods=["POST"])
def cerrar_dia():
    """Cierra exactamente el dia que se previsualizo, si es hoy o ayer.

    Si la previsualizacion se abrio a las 23:59 y se pulsa a las 00:00:05, se
    cierra el dia que se vio (ya "ayer"), nunca el dia nuevo sin haberlo visto.
    """
    hoy, ayer = _hoy_y_ayer()
    fecha = request.form.get("fecha", "")

    if fecha not in (hoy, ayer):
        return _render_cierre(
            hoy,
            error=f"Desde esta pantalla solo se puede cerrar hoy ({hoy}) o ayer ({ayer}),"
                  f" no {fecha or '(sin fecha)'}.",
        ), 409

    try:
        guardado = cierre.cerrar_dia(fecha)
    except (cierre.DiaCerrado, establecimiento.SinConfigurar) as error:
        # No se crea un segundo cierre ni se actualiza el existente. Sin los
        # datos del establecimiento no se cierra: el dia sigue abierto.
        return _render_cierre(fecha, error=str(error)), 409

    # El cierre YA esta guardado (su transaccion termino). El backup va despues
    # y, falle como falle, no puede deshacerlo: aqui ya no se toca el cierre.
    cerrado = f"Día {guardado['business_date']} cerrado: {guardado['close_number']}."
    try:
        copia = backup.crear_backup()
    except Exception as error:   # cualquier fallo del backup, tambien inesperado
        if not isinstance(error, (backup.BackupNoConfigurado, backup.BackupFallido)):
            log.exception("Fallo inesperado del backup tras el cierre")
        return _render_cierre(
            fecha,
            mensaje=f"{cerrado} El cierre está hecho y guardado.",
            error=f"BACKUP FALLIDO: el cierre {guardado['close_number']} está hecho y"
                  f" guardado, pero no se ha podido crear el backup. {error} Cuando esté"
                  " resuelto, repite el backup con «CREAR BACKUP AHORA».",
        )

    return redirect(url_for(
        "main.cierre_del_dia",
        dia="ayer" if fecha == ayer else None,
        ok=f"{cerrado} Backup correcto: {copia['nombre']}.",
    ))


@bp.route("/cierre/pdf")
def pdf_del_cierre():
    """Genera (o regenera) y abre el PDF del cierre de hoy o de ayer.

    Solo para dias ya cerrados. No escribe en la base: lee solo el cierre
    guardado (con los datos del establecimiento congelados en el) y escribe el
    archivo en exports/.
    """
    hoy, ayer = _hoy_y_ayer()
    fecha = ayer if request.args.get("dia") == "ayer" else hoy
    try:
        ruta = pdf_cierre.generar_pdf_cierre(fecha)
    except (pdf_cierre.CierreNoEncontrado, pdf_cierre.CierreIncompleto,
            pdf_cierre.PdfBloqueado) as error:
        return _render_cierre(fecha, error=str(error)), 409

    # Se devuelve el contenido y no el archivo abierto: en Windows un archivo
    # abierto no se puede sustituir al regenerarlo.
    return Response(
        ruta.read_bytes(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{ruta.name}"'},
    )


# ---------------------------------------------------------------------------
# Backup manual
# ---------------------------------------------------------------------------


@bp.route("/backup")
def pantalla_backup():
    return _render_backup(mensaje=request.args.get("ok"))


@bp.route("/backup", methods=["POST"])
def crear_backup():
    """Backup manual de la base actual. Sirve tambien para repetir el backup
    de un cierre cuyo backup automatico fallo."""
    try:
        copia = backup.crear_backup()
    except (backup.BackupNoConfigurado, backup.BackupFallido) as error:
        return _render_backup(error=f"BACKUP FALLIDO: {error}"), 503
    return redirect(url_for(
        "main.pantalla_backup",
        ok=f"Backup correcto: {copia['nombre']} ({copia['bytes']} bytes), validado.",
    ))


# ---------------------------------------------------------------------------
# Datos del establecimiento (cabecera del PDF)
# ---------------------------------------------------------------------------


@bp.route("/establecimiento")
def datos_establecimiento():
    return render_template(
        "establishment.html",
        datos=establecimiento.obtener() or {},
        mensaje=request.args.get("ok"),
        error=None,
    )


@bp.route("/establecimiento", methods=["POST"])
def guardar_establecimiento():
    formulario = {
        "name": request.form.get("titular", ""),
        "tax_id": request.form.get("nif", ""),
        "trade_name": request.form.get("nombre_comercial", ""),
        "address": request.form.get("direccion", ""),
    }
    try:
        establecimiento.guardar(formulario["name"], formulario["tax_id"],
                                formulario["trade_name"], formulario["address"])
    except establecimiento.DatosInvalidos as error:
        return render_template("establishment.html", datos=formulario,
                               mensaje=None, error=str(error)), 400
    return redirect(url_for("main.datos_establecimiento",
                            ok="Datos del establecimiento guardados."))


# ---------------------------------------------------------------------------
# Gestion de productos
# ---------------------------------------------------------------------------


@bp.route("/productos")
def productos():
    """Pantalla de gestion: muestra activos e inactivos."""
    return _render_productos(mensaje=request.args.get("ok"))


@bp.route("/productos/nuevo", methods=["POST"])
def crear_producto():
    nombre = request.form.get("nombre", "")
    precio = request.form.get("precio", "")
    orden = request.form.get("orden", "")

    try:
        products.crear_producto(nombre, parse_euros(precio), orden)
    except (ImporteInvalido, products.DatosInvalidos) as error:
        return _render_productos(
            error=str(error),
            formulario={"nombre": nombre, "precio": precio, "orden": orden},
        ), 400

    return redirect(url_for("main.productos", ok=f"Producto '{nombre.strip()}' creado."))


@bp.route("/productos/<int:producto_id>/editar", methods=["POST"])
def editar_producto(producto_id):
    nombre = request.form.get("nombre", "")
    precio = request.form.get("precio", "")
    orden = request.form.get("orden", "")

    try:
        products.actualizar_producto(producto_id, nombre, parse_euros(precio), orden)
    except (ImporteInvalido, products.DatosInvalidos) as error:
        return _render_productos(error=f"Producto #{producto_id}: {error}"), 400

    return redirect(url_for("main.productos", ok=f"Producto '{nombre.strip()}' actualizado."))


@bp.route("/productos/<int:producto_id>/estado", methods=["POST"])
def cambiar_estado(producto_id):
    """Activa o desactiva. El producto NO se borra de la base."""
    activar = request.form.get("activar") == "1"

    try:
        products.cambiar_estado(producto_id, activar)
    except products.DatosInvalidos as error:
        return _render_productos(error=str(error)), 400

    accion = "activado" if activar else "desactivado"
    return redirect(url_for("main.productos", ok=f"Producto #{producto_id} {accion}."))


# ---------------------------------------------------------------------------


def _render_index(mensaje=None, error=None):
    lineas = cart.lineas()
    return render_template(
        "index.html",
        productos=products.listar_productos(solo_activos=True),
        lineas=cart.con_subtotales(lineas),
        total_centimos=cart.total_centimos(lineas),
        hoy_cerrado=cierre.dia_esta_cerrado(resumen.hoy()),
        mensaje=mensaje,
        error=error,
    )


def _render_cierre(fecha, mensaje=None, error=None):
    hoy, ayer = _hoy_y_ayer()
    guardado = cierre.obtener_cierre(fecha)
    return render_template(
        "close.html",
        hoy=hoy,
        ayer=ayer,
        fecha=fecha,
        cierre=guardado,
        previsualizacion=None if guardado else cierre.previsualizar_cierre(fecha),
        mensaje=mensaje,
        error=error,
    )


def _render_backup(mensaje=None, error=None):
    return render_template(
        "backup.html",
        carpeta=backup.carpeta_configurada(),
        variable=backup.VARIABLE,
        mensaje=mensaje,
        error=error,
    )


def _render_historial(mensaje=None, error=None):
    return render_template(
        "history.html",
        ventas=sales.listar_ventas(),
        mensaje=mensaje,
        error=error,
    )


def _render_productos(mensaje=None, error=None, formulario=None):
    return render_template(
        "products.html",
        productos=products.listar_productos(),
        mensaje=mensaje,
        error=error,
        formulario=formulario or {},
    )
