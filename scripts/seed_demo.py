r"""Datos de demostracion para presentar la aplicacion (rama tfc).

Crea una base SQLite **de demostracion**, con datos TOTALMENTE FICTICIOS, para
poder ensenar la aplicacion sin usar datos reales:

    .venv\Scripts\python.exe scripts\seed_demo.py
        -> crea data/demo.sqlite si no existe.

    .venv\Scripts\python.exe scripts\seed_demo.py --reset
        -> la borra y la vuelve a crear desde cero.

    .venv\Scripts\python.exe scripts\seed_demo.py --ruta otra/ruta.sqlite
        -> usa otra ruta (la usan los tests).

Luego se arranca la aplicacion contra esa base:

    $env:CAFETERIA_DB = "data\demo.sqlite"
    powershell -ExecutionPolicy Bypass -File scripts\start.ps1

Que crea:
- el establecimiento ficticio de la demo;
- un catalogo de 10 productos de cafeteria;
- dos dias ya CERRADOS, con ventas y alguna anulada, para ensenar el historial,
  el resumen, el cierre y el PDF;
- un dia ABIERTO con ventas, para poder cerrar el dia en directo.

Como lo hace:
- usa las funciones de la propia aplicacion (products, sales, cierre), nunca SQL
  a mano: asi los datos demo son coherentes de verdad y no se duplica aqui la
  logica de negocio;
- no crea backups: el backup se dispara en la ruta web, no en cierre.cerrar_dia.

Proteccion: se niega a escribir sobre la base real (data/cafeteria.sqlite) y
sobre cualquier base que ya contenga ventas que no haya creado el.
"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

RUTA_POR_DEFECTO = RAIZ / "data" / "demo.sqlite"
BASE_REAL = RAIZ / "data" / "cafeteria.sqlite"

# --- Datos FICTICIOS. Ningun dato real del establecimiento. ----------------
ESTABLECIMIENTO = {
    "titular": "NOME APELIDOS DEMO",
    "nif": "NIF-DEMO-0001",          # a proposito, sin forma de NIF/NIE/CIF real
    "nombre_comercial": "CAFETERÍA DEMO",
    "direccion": "Rúa Exemplo 1, 00000 Cidade",
}

# (nombre, precio en centimos). Precios de cafeteria, inventados.
PRODUCTOS = [
    ("Café", 140),
    ("Café con leite", 165),
    ("Cortado", 145),
    ("Descafeinado", 150),
    ("Infusión", 160),
    ("Auga", 120),
    ("Zume natural", 230),
    ("Refresco", 210),
    ("Tostada", 250),
    ("Bocadillo", 450),
]

# Ventas por dia: cada venta es una lista de (indice de producto, cantidad).
# El ultimo campo dice si la venta se anula despues.
VENTAS_DIA_1 = [
    ([(0, 2), (8, 1)], False),
    ([(1, 1)], False),
    ([(9, 1), (7, 1)], False),
    ([(0, 1), (2, 1)], True),       # anulada: error de cobro
    ([(5, 2)], False),
    ([(3, 1), (4, 1)], False),
    ([(0, 3), (8, 2)], False),
]
VENTAS_DIA_2 = [
    ([(1, 2)], False),
    ([(6, 1), (8, 1)], False),
    ([(0, 1)], False),
    ([(9, 2), (7, 2)], False),
    ([(2, 1), (4, 1)], False),
    ([(0, 2), (1, 1)], True),       # anulada
    ([(5, 1), (6, 1)], False),
    ([(0, 4)], False),
]
VENTAS_DIA_ABIERTO = [
    ([(0, 2), (8, 1)], False),
    ([(1, 1), (9, 1)], False),
    ([(5, 1)], False),
    ([(0, 1), (2, 2)], False),
]


class SeedRechazado(RuntimeError):
    """No se puede sembrar ahi: protege la base real y los datos existentes."""


def _comprobar_destino(ruta, reset):
    """No escribir nunca sobre la base real ni sobre datos ajenos."""
    if ruta.resolve() == BASE_REAL.resolve():
        raise SeedRechazado(
            f"Negado: {ruta} es la base real de la aplicación. Los datos demo van"
            " a otra base (por defecto data/demo.sqlite)."
        )
    if ruta.exists() and not reset:
        raise SeedRechazado(
            f"{ruta} ya existe. Usa --reset para borrarla y recrearla, o indica"
            " otra ruta con --ruta."
        )


def _hora(dia, h, m):
    return datetime.combine(dia, datetime.min.time()).replace(hour=h, minute=m)


def _vender(ids, guion, dia, desde_hora):
    """Crea las ventas de un dia. Devuelve los ids de las que hay que anular."""
    from app import sales

    anular = []
    for n, (lineas, se_anula) in enumerate(guion):
        venta = sales.confirmar_venta(
            [{"producto_id": ids[i][0], "nombre": ids[i][1],
              "precio_centimos": ids[i][2], "cantidad": c} for i, c in lineas],
            momento=_hora(dia, desde_hora + (n * 20) // 60, (n * 20) % 60),
        )
        if se_anula:
            anular.append(venta["id"])
    return anular


def sembrar(ruta=RUTA_POR_DEFECTO, reset=False, hoy=None):
    """Crea la base de demostracion y devuelve un resumen de lo creado."""
    ruta = Path(ruta)
    _comprobar_destino(ruta, reset)

    if reset and ruta.exists():
        ruta.unlink()
    ruta.parent.mkdir(parents=True, exist_ok=True)

    os.environ["CAFETERIA_DB"] = str(ruta)

    from app import cierre, db, establecimiento, products, sales
    db.init_db()

    establecimiento.guardar(
        ESTABLECIMIENTO["titular"], ESTABLECIMIENTO["nif"],
        ESTABLECIMIENTO["nombre_comercial"], ESTABLECIMIENTO["direccion"],
    )

    ids = []
    for orden, (nombre, precio) in enumerate(PRODUCTOS, start=1):
        ids.append((products.crear_producto(nombre, precio, orden * 10), nombre, precio))

    hoy = hoy or date.today()
    dia_1, dia_2 = hoy - timedelta(days=2), hoy - timedelta(days=1)

    cerrados = []
    for dia, guion in ((dia_1, VENTAS_DIA_1), (dia_2, VENTAS_DIA_2)):
        for venta_id in _vender(ids, guion, dia, 9):
            sales.anular_venta(venta_id, momento=_hora(dia, 20, 30))
        cerrados.append(cierre.cerrar_dia(dia.isoformat(), momento=_hora(dia, 21, 0)))

    # El dia de hoy queda ABIERTO, para poder cerrarlo delante del tribunal.
    _vender(ids, VENTAS_DIA_ABIERTO, hoy, 9)

    return {
        "ruta": ruta,
        "productos": len(ids),
        "dias_cerrados": [c["business_date"] for c in cerrados],
        "cierres": [c["close_number"] for c in cerrados],
        "dia_abierto": hoy.isoformat(),
        "ventas_dia_abierto": len(VENTAS_DIA_ABIERTO),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Crea datos de demostración ficticios.")
    p.add_argument("--ruta", default=str(RUTA_POR_DEFECTO),
                   help="base de demostración a crear (por defecto data/demo.sqlite)")
    p.add_argument("--reset", action="store_true",
                   help="borrar la base de demostración y recrearla desde cero")
    args = p.parse_args(argv)

    try:
        r = sembrar(Path(args.ruta), reset=args.reset)
    except SeedRechazado as error:
        print(f"ERROR: {error}")
        return 1

    print(f"Base de demostración creada: {r['ruta']}")
    print(f"  establecimiento : {ESTABLECIMIENTO['nombre_comercial']} (ficticio)")
    print(f"  productos       : {r['productos']}")
    print(f"  días cerrados   : {', '.join(r['dias_cerrados'])}"
          f"  ({', '.join(r['cierres'])})")
    print(f"  día abierto     : {r['dia_abierto']} con {r['ventas_dia_abierto']} ventas")
    print()
    print("Para arrancar la aplicación con estos datos:")
    print(f'  $env:CAFETERIA_DB = "{r["ruta"]}"')
    print("  powershell -ExecutionPolicy Bypass -File scripts\\start.ps1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
