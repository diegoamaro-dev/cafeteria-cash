"""Manejo de importes monetarios.

Los importes se guardan y se operan SIEMPRE como enteros de centimos.
Nunca se usa float: 0.1 + 0.2 != 0.3 en coma flotante y eso acabaria
produciendo descuadres en los totales y en el cierre diario.

Para leer y escribir texto se usa Decimal, que es exacto en base 10.
"""

from decimal import Decimal, InvalidOperation

# Tope defensivo: esto es una cafeteria, no una joyeria.
MAX_CENTIMOS = 999_999  # 9.999,99 EUR


class ImporteInvalido(ValueError):
    """El texto introducido no es un importe valido."""


def parse_euros(texto):
    """Convierte texto ("1,40", "1.40", "1,40 €") en centimos (int).

    Acepta coma o punto decimal y un maximo de 2 decimales.
    Lanza ImporteInvalido con un mensaje para mostrar al usuario.
    """
    if texto is None:
        raise ImporteInvalido("El precio es obligatorio.")

    limpio = str(texto).strip().replace("€", "").replace("EUR", "").strip()
    limpio = limpio.replace(" ", "").replace(",", ".")

    if not limpio:
        raise ImporteInvalido("El precio es obligatorio.")

    try:
        valor = Decimal(limpio)
    except InvalidOperation:
        raise ImporteInvalido(f"'{texto}' no es un precio valido. Ejemplo: 1,40")

    if not valor.is_finite():
        raise ImporteInvalido(f"'{texto}' no es un precio valido. Ejemplo: 1,40")

    if valor < 0:
        raise ImporteInvalido("El precio no puede ser negativo.")

    if -valor.as_tuple().exponent > 2:
        raise ImporteInvalido("El precio no puede tener mas de 2 decimales.")

    centimos = int(valor.scaleb(2))

    if centimos > MAX_CENTIMOS:
        raise ImporteInvalido(f"El precio no puede superar {format_euros(MAX_CENTIMOS)}.")

    return centimos


def format_euros(centimos):
    """Convierte centimos (int) en texto espanol: 140 -> '1,40 €'."""
    signo = "-" if centimos < 0 else ""
    centimos = abs(int(centimos))
    return f"{signo}{centimos // 100},{centimos % 100:02d} €"
