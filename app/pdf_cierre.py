"""PDF A4 del cierre diario (FASE 7). Solo biblioteca estandar, sin dependencias.

Fuente de datos, y ninguna otra: el cierre guardado, `daily_close` y
`daily_close_item` (via cierre.obtener_cierre). La identificacion del
establecimiento y el desglose de IVA salen de lo congelado en el propio cierre:
el IVA nunca se recalcula al generar el PDF.
Nunca se consultan `sale`, `sale_item`, `product`, un resumen recalculado ni
la configuracion actual de `establishment`: el cierre ya es la foto definitiva
del dia, y regenerar su PDF da siempre los mismos bytes.

El PDF es un documento 1.4 minimo: una o varias paginas A4 verticales con las
fuentes estandar Courier y Courier-Bold (no se incrustan: todo visor las trae)
en codificacion WinAnsi, que cubre el espanol y el simbolo del euro. Courier es
monoespaciada, asi que alinear importes a la derecha es contar caracteres.

Es determinista: el mismo cierre produce exactamente los mismos bytes. No
incluye la hora de generacion.

Los contenidos van sin comprimir, asi que el texto se puede comprobar leyendo
el propio archivo.
"""

import os
import textwrap
from pathlib import Path

from . import cierre
from .db import RAIZ
from .money import format_euros

# --- Pagina A4 vertical, en puntos (1/72 de pulgada) -----------------------
ANCHO, ALTO = 595.28, 841.89
MARGEN = 56.69                       # 2 cm
TAM = 11                             # cuerpo de letra
COLUMNAS = 73                        # 73 x 0.6 x 11 pt = 481.8 pt = ancho util
ARRIBA = ALTO - MARGEN
ABAJO = MARGEN + 14                  # deja sitio para el pie de pagina
PIE_Y = 36.0
SIN_DATO = "—"


class CierreNoEncontrado(LookupError):
    """No hay cierre guardado para esa fecha: el dia sigue abierto."""


class CierreIncompleto(LookupError):
    """El cierre no tiene congelados los datos del establecimiento o el IVA."""


class PdfBloqueado(OSError):
    """El PDF anterior esta abierto en otro programa y no se puede sustituir."""


# ---------------------------------------------------------------------------
# Donde y con que nombre
# ---------------------------------------------------------------------------


def directorio_exports():
    """exports/ en la raiz del proyecto (ignorado por Git).

    CAFETERIA_EXPORTS lo redirige; lo usan los tests para no escribir en la
    carpeta real.
    """
    personalizado = os.environ.get("CAFETERIA_EXPORTS")
    return Path(personalizado) if personalizado else RAIZ / "exports"


def nombre_pdf(datos_cierre):
    """cierre_<business_date>_<close_number>.pdf: el mismo al regenerar."""
    return f"cierre_{datos_cierre['business_date']}_{datos_cierre['close_number']}.pdf"


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def generar_pdf_cierre(fecha):
    """Genera (o regenera) el PDF del cierre de `fecha` y devuelve su ruta.

    No escribe nada en la base, no modifica el cierre y no recalcula ventas.
    """
    datos = cierre.obtener_cierre(fecha)
    if datos is None:
        raise CierreNoEncontrado(
            f"No hay cierre del día {fecha}: el día sigue abierto. Ciérralo antes"
            " de generar el PDF."
        )
    faltan = [c for c in cierre.SNAPSHOT_ESTABLECIMIENTO if not datos.get(c)]
    if faltan:
        # Nunca se rellenan con la configuracion actual: eso haria que la
        # cabecera de un cierre historico dependiera del presente.
        raise CierreIncompleto(
            f"El cierre {datos['close_number']} no tiene congelados los datos del"
            " establecimiento. No se genera el PDF."
        )
    if any(datos.get(c) is None for c in cierre.SNAPSHOT_IVA):
        # Igual: nunca se recalcula el IVA de un cierre guardado.
        raise CierreIncompleto(
            f"El cierre {datos['close_number']} no tiene congelado el desglose de"
            " IVA. No se genera el PDF."
        )

    contenido = componer_pdf(datos)

    carpeta = directorio_exports()
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre_pdf(datos)
    temporal = destino.with_name(destino.name + ".tmp")

    # Escritura atomica: primero un temporal, luego se sustituye de golpe.
    # Nunca queda a la vista un PDF a medio escribir.
    temporal.write_bytes(contenido)
    try:
        os.replace(temporal, destino)
    except PermissionError:
        temporal.unlink(missing_ok=True)
        raise PdfBloqueado(
            f"No se puede sustituir {destino.name}: está abierto en otro programa."
            " Ciérralo y vuelve a generarlo."
        )
    return destino


# ---------------------------------------------------------------------------
# Composicion: lineas de texto monoespaciado
# ---------------------------------------------------------------------------


def _linea(texto, negrita=False, tam=TAM):
    return {"tipo": "texto", "texto": texto, "negrita": negrita, "tam": tam}


def _regla():
    return {"tipo": "regla"}


def _vacio():
    return {"tipo": "vacio"}


def _alto(item):
    if item["tipo"] == "texto":
        return max(item["tam"] + 3, 14)
    return 8 if item["tipo"] == "regla" else 10


def _dos_columnas(izquierda, derecha, ancho=COLUMNAS):
    hueco = ancho - len(derecha) - 1
    if len(izquierda) > hueco:
        izquierda = izquierda[: hueco - 1] + "…"
    return izquierda.ljust(ancho - len(derecha)) + derecha


def _campo(etiqueta, valor):
    return f"{etiqueta:<22}{valor}"


def _grupos(c):
    """Bloques que no se parten entre paginas, en orden."""
    # Identificacion del establecimiento congelada en el cierre, siempre encima
    # de los datos del cierre.
    cabecera = [_linea(t, negrita=True, tam=13)
                for t in textwrap.wrap(c["trade_name_snapshot"], 60)]
    cabecera += [_linea(t) for t in
                 textwrap.wrap(f"Titular: {c['holder_name_snapshot']}", COLUMNAS)]
    cabecera.append(_linea(f"NIF: {c['tax_id_snapshot']}"))
    cabecera += [_linea(t) for t in textwrap.wrap(c["address_snapshot"], COLUMNAS)]
    cabecera += [
        _regla(),
        _linea("CIERRE DIARIO DE CAJA", negrita=True, tam=15),
        _vacio(),
        _linea(_campo("Nº de cierre", c["close_number"]), negrita=True),
        _linea(_campo("Fecha del cierre", c["business_date"])),
        _linea(_campo("Hora de cierre", c["closed_at"])),
        _linea(_campo("Primera venta", c["first_sale_number"] or SIN_DATO)),
        _linea(_campo("Última venta", c["last_sale_number"] or SIN_DATO)),
        _linea(_campo("Ventas válidas", str(c["valid_sales_count"]))),
        _linea(_campo("Anulaciones", str(c["void_sales_count"]))),
        _vacio(),
        _linea("UNIDADES VENDIDAS (solo ventas válidas)", negrita=True),
    ]

    cabecera_tabla = [
        _regla(),
        _linea(_dos_columnas("Producto", "Unidades"), negrita=True),
        _regla(),
    ]

    if c["items"]:
        filas = [[_linea(_dos_columnas(i["product_name_snapshot"], str(i["units"])))]
                 for i in c["items"]]
    else:
        filas = [[_linea("Sin unidades vendidas.")]]

    totales = [
        _regla(),
        _vacio(),
        _linea("TOTALES", negrita=True),
        _linea(_dos_columnas("Total bruto", format_euros(c["gross_cents"]))),
        _linea(_dos_columnas("Total anulado", format_euros(c["void_cents"]))),
        _regla(),
        _linea(_dos_columnas("TOTAL EFECTIVO VÁLIDO", format_euros(c["valid_cash_cents"])),
               negrita=True),
        _vacio(),
        # Desglose congelado en el cierre: se imprime, no se recalcula.
        _linea("DESGLOSE IVA", negrita=True),
        _linea(_dos_columnas("Base imponible", format_euros(c["vat_base_cents"]))),
        _linea(_dos_columnas(f"IVA {c['vat_rate_percent']} %", format_euros(c["vat_cents"]))),
        _regla(),
        _linea(_dos_columnas("TOTAL IVA INCLUIDO", format_euros(c["valid_cash_cents"])),
               negrita=True),
        _vacio(),
        _linea("Bruto = efectivo válido + anulado. Solo efectivo: los pagos con",
               tam=9),
        _linea("tarjeta no forman parte de este cierre. Generado a partir del cierre",
               tam=9),
        _linea("guardado; regenerarlo reproduce el mismo contenido.", tam=9),
    ]

    return cabecera, cabecera_tabla, filas, totales


def _paginar(c):
    cabecera, cabecera_tabla, filas, totales = _grupos(c)
    continuacion = [
        _linea(f"CIERRE {c['close_number']} · {c['business_date']} (continuación)",
               negrita=True),
        _vacio(),
    ]

    grupos = [("cabecera", cabecera), ("tabla", cabecera_tabla)]
    grupos += [("fila", f) for f in filas]
    grupos.append(("totales", totales))

    paginas, actual, y = [], [], ARRIBA
    for tipo, items in grupos:
        alto = sum(_alto(i) for i in items)
        if actual and y - alto < ABAJO:
            paginas.append(actual)
            actual, y = list(continuacion), ARRIBA - sum(_alto(i) for i in continuacion)
            if tipo == "fila":
                actual += cabecera_tabla
                y -= sum(_alto(i) for i in cabecera_tabla)
        actual += items
        y -= alto
    paginas.append(actual)
    return paginas


# ---------------------------------------------------------------------------
# Escritura del PDF
# ---------------------------------------------------------------------------


def _cadena(texto):
    """Cadena literal PDF en WinAnsi (cp1252), con \\ ( ) escapados."""
    datos = texto.encode("cp1252", errors="replace")
    return datos.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _num(valor):
    return f"{valor:.2f}".encode("ascii")


def _contenido_pagina(items, pie_izquierda, pie_derecha):
    salida, y = [], ARRIBA
    for item in items:
        alto = _alto(item)
        if item["tipo"] == "texto":
            fuente = b"/F2" if item["negrita"] else b"/F1"
            salida.append(b"BT " + fuente + b" " + str(item["tam"]).encode() + b" Tf "
                          + _num(MARGEN) + b" " + _num(y - item["tam"]) + b" Td ("
                          + _cadena(item["texto"]) + b") Tj ET")
        elif item["tipo"] == "regla":
            medio = y - alto / 2
            salida.append(b"0.6 w " + _num(MARGEN) + b" " + _num(medio) + b" m "
                          + _num(ANCHO - MARGEN) + b" " + _num(medio) + b" l S")
        y -= alto

    pie = _dos_columnas(pie_izquierda, pie_derecha, ancho=int(COLUMNAS * TAM / 9))
    salida.append(b"BT /F1 9 Tf " + _num(MARGEN) + b" " + _num(PIE_Y)
                  + b" Td (" + _cadena(pie) + b") Tj ET")
    return b"\n".join(salida) + b"\n"


def componer_pdf(c):
    """Bytes del PDF. Funcion pura: mismo cierre, mismos bytes."""
    paginas = _paginar(c)
    total = len(paginas)
    pie_izq = f"Cierre {c['close_number']} · {c['business_date']}"

    fecha = c["closed_at"].replace("-", "").replace(":", "").replace(" ", "")
    objetos = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold /Encoding /WinAnsiEncoding >>",
        5: b"<< /Title (" + _cadena(f"Cierre {c['close_number']} {c['business_date']}")
           + b") /Producer (Cafeteria Cash) /CreationDate (D:" + fecha.encode("ascii") + b") >>",
    }

    hijos = []
    for n, items in enumerate(paginas):
        num_pagina, num_contenido = 6 + 2 * n, 7 + 2 * n
        hijos.append(f"{num_pagina} 0 R".encode())
        flujo = _contenido_pagina(items, pie_izq, f"Página {n + 1} de {total}")
        objetos[num_pagina] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 " + _num(ANCHO) + b" "
            + _num(ALTO) + b"] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >>"
            b" /Contents " + str(num_contenido).encode() + b" 0 R >>"
        )
        objetos[num_contenido] = (b"<< /Length " + str(len(flujo)).encode() + b" >>\nstream\n"
                                  + flujo + b"endstream")
    objetos[2] = (b"<< /Type /Pages /Kids [" + b" ".join(hijos) + b"] /Count "
                  + str(total).encode() + b" >>")

    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones = {}
    for numero in sorted(objetos):
        posiciones[numero] = len(salida)
        salida += str(numero).encode() + b" 0 obj\n" + objetos[numero] + b"\nendobj\n"

    inicio_xref = len(salida)
    cantidad = max(objetos) + 1
    salida += b"xref\n0 " + str(cantidad).encode() + b"\n0000000000 65535 f \n"
    for numero in range(1, cantidad):
        salida += f"{posiciones[numero]:010d} 00000 n \n".encode()
    salida += (b"trailer\n<< /Size " + str(cantidad).encode() + b" /Root 1 0 R /Info 5 0 R >>\n"
               b"startxref\n" + str(inicio_xref).encode() + b"\n%%EOF\n")
    return bytes(salida)
