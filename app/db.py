"""Acceso a la base de datos SQLite local.

La base vive fuera del codigo, en data/cafeteria.sqlite, y NUNCA se versiona.
Codigo en GitHub, datos en el portatil + backups externos.

La ruta se puede redirigir con la variable de entorno CAFETERIA_DB. Se usa en
los tests para no escribir ventas de prueba en la base real.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIO_DATOS = RAIZ / "data"
RUTA_POR_DEFECTO = DIRECTORIO_DATOS / "cafeteria.sqlite"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS product (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    price_cents   INTEGER NOT NULL CHECK (price_cents >= 0),
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_product_visible
    ON product (active, display_order, name);

-- Cabecera de una venta confirmada. No se borra nunca: solo cambia status.
-- voided_at es NULL mientras la venta es valida; al anularla guarda la hora.
CREATE TABLE IF NOT EXISTS sale (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_number TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL,
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    status      TEXT    NOT NULL DEFAULT 'VALID' CHECK (status IN ('VALID', 'VOID')),
    voided_at   TEXT    NULL
);

CREATE INDEX IF NOT EXISTS idx_sale_fecha ON sale (created_at);

-- Lineas de la venta. Nombre y precio se copian en el momento del cobro:
-- una venta historica no puede depender del estado actual del producto.
CREATE TABLE IF NOT EXISTS sale_item (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id                   INTEGER NOT NULL REFERENCES sale (id),
    product_id                INTEGER NOT NULL REFERENCES product (id),
    product_name_snapshot     TEXT    NOT NULL,
    unit_price_cents_snapshot INTEGER NOT NULL CHECK (unit_price_cents_snapshot >= 0),
    quantity                  INTEGER NOT NULL CHECK (quantity > 0),
    subtotal_cents            INTEGER NOT NULL CHECK (subtotal_cents >= 0)
);

CREATE INDEX IF NOT EXISTS idx_sale_item_venta ON sale_item (sale_id);

-- Cierre diario. Foto definitiva de un dia: una vez creado no se modifica ni se
-- borra, y el dia ya no admite nuevas ventas ni anulaciones.
-- first/last_sale_number son NULL si ese dia no hubo ninguna venta.
-- *_snapshot: los cuatro datos del establecimiento vigentes al cerrar. El PDF
-- los lee de aqui, nunca de la configuracion actual. Admiten NULL solo porque
-- se anadieron con ALTER TABLE; cerrar_dia() los exige.
-- vat_*: desglose de IVA congelado al cerrar (IVA unico del 10 %, decision
-- explicita). valid_cash_cents es IVA incluido y
-- vat_base_cents + vat_cents = valid_cash_cents. NULL solo en cierres
-- anteriores a este cambio (se completan con
-- scripts/congelar_establecimiento_en_cierres.py --aplicar).
CREATE TABLE IF NOT EXISTS daily_close (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    close_number      TEXT    NOT NULL UNIQUE,
    business_date     TEXT    NOT NULL UNIQUE,
    closed_at         TEXT    NOT NULL,
    first_sale_number TEXT    NULL,
    last_sale_number  TEXT    NULL,
    valid_sales_count INTEGER NOT NULL CHECK (valid_sales_count >= 0),
    void_sales_count  INTEGER NOT NULL CHECK (void_sales_count >= 0),
    gross_cents       INTEGER NOT NULL CHECK (gross_cents >= 0),
    void_cents        INTEGER NOT NULL CHECK (void_cents >= 0),
    valid_cash_cents  INTEGER NOT NULL CHECK (valid_cash_cents >= 0),
    holder_name_snapshot TEXT NULL,
    tax_id_snapshot      TEXT NULL,
    trade_name_snapshot  TEXT NULL,
    address_snapshot     TEXT NULL,
    vat_rate_percent     INTEGER NULL,
    vat_base_cents       INTEGER NULL,
    vat_cents            INTEGER NULL,
    CHECK (gross_cents = valid_cash_cents + void_cents)
);

-- Unidades validas por producto congeladas en el cierre, con el nombre que
-- tenian en las ventas. Nunca se reconstruyen desde el catalogo actual.
CREATE TABLE IF NOT EXISTS daily_close_item (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    daily_close_id        INTEGER NOT NULL REFERENCES daily_close (id),
    product_name_snapshot TEXT    NOT NULL,
    units                 INTEGER NOT NULL CHECK (units > 0),
    UNIQUE (daily_close_id, product_name_snapshot)
);

-- Identificacion del establecimiento para la cabecera del PDF de cierre.
-- Una sola fila (id = 1). Sin valores por defecto: nada de esto vive en el
-- codigo ni en Git, solo en esta base local (y por tanto en su backup).
--   name       = titular (nombre o razon social)
--   tax_id     = NIF
--   trade_name = nombre comercial. Admite NULL solo porque se anadio despues
--                con ALTER TABLE; el codigo la exige para generar el PDF.
CREATE TABLE IF NOT EXISTS establishment (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    name       TEXT    NOT NULL,
    tax_id     TEXT    NOT NULL,
    address    TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    trade_name TEXT    NULL
);
"""


# Columnas anadidas despues de que existieran bases con datos.
# CREATE TABLE IF NOT EXISTS no altera tablas ya creadas, asi que en una base
# antigua hay que anadirlas con ALTER TABLE. SQLite no tiene
# "ADD COLUMN IF NOT EXISTS": se comprueba antes con PRAGMA table_info.
MIGRACIONES = [
    ("sale", "voided_at", "ALTER TABLE sale ADD COLUMN voided_at TEXT NULL"),
    ("establishment", "trade_name",
     "ALTER TABLE establishment ADD COLUMN trade_name TEXT NULL"),
    ("daily_close", "holder_name_snapshot",
     "ALTER TABLE daily_close ADD COLUMN holder_name_snapshot TEXT NULL"),
    ("daily_close", "tax_id_snapshot",
     "ALTER TABLE daily_close ADD COLUMN tax_id_snapshot TEXT NULL"),
    ("daily_close", "trade_name_snapshot",
     "ALTER TABLE daily_close ADD COLUMN trade_name_snapshot TEXT NULL"),
    ("daily_close", "address_snapshot",
     "ALTER TABLE daily_close ADD COLUMN address_snapshot TEXT NULL"),
    ("daily_close", "vat_rate_percent",
     "ALTER TABLE daily_close ADD COLUMN vat_rate_percent INTEGER NULL"),
    ("daily_close", "vat_base_cents",
     "ALTER TABLE daily_close ADD COLUMN vat_base_cents INTEGER NULL"),
    ("daily_close", "vat_cents",
     "ALTER TABLE daily_close ADD COLUMN vat_cents INTEGER NULL"),
]


def ruta_base():
    """Ruta del archivo SQLite en uso."""
    personalizada = os.environ.get("CAFETERIA_DB")
    return Path(personalizada) if personalizada else RUTA_POR_DEFECTO


def get_connection():
    """Devuelve una conexion a la base, creando el directorio si hace falta."""
    ruta = ruta_base()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaccion():
    """Transaccion explicita con BEGIN IMMEDIATE.

    IMMEDIATE toma el bloqueo de escritura al empezar: dos cobros simultaneos
    no pueden calcular el mismo numero de venta.

    Si algo falla dentro del bloque se hace ROLLBACK completo y se relanza el
    error: nunca queda una venta a medias.
    """
    conn = get_connection()
    conn.isolation_level = None  # control manual de la transaccion
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
    finally:
        conn.close()


def _columnas(conn, tabla):
    return {fila["name"] for fila in conn.execute(f"PRAGMA table_info({tabla})")}


def init_db():
    """Crea las tablas que falten y aplica las migraciones pendientes.

    Es idempotente y nunca borra datos: se puede ejecutar en cada arranque.
    """
    conn = get_connection()
    try:
        with conn:
            conn.executescript(ESQUEMA)
            for tabla, columna, sql in MIGRACIONES:
                if columna not in _columnas(conn, tabla):
                    conn.execute(sql)
    finally:
        conn.close()
