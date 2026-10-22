r"""Migracion controlada de cierres antiguos (FASE 7): congela en ellos los datos
del establecimiento y el desglose de IVA que no tienen.

Desde la FASE 7, cada cierre guarda al cerrarse:
- titular, NIF, nombre comercial y direccion (`daily_close.*_snapshot`);
- tipo de IVA, base imponible y cuota (`daily_close.vat_*`). IVA unico del 10 %
  (decision explicita del usuario).
El PDF los lee solo del propio cierre. Los cierres creados antes tienen esas
columnas a NULL, y su PDF se rechaza: nunca se rellenan en silencio al arrancar.

Este script es la unica forma de completarlos, y se ejecuta a mano, una vez:

    .venv\Scripts\python.exe scripts\congelar_establecimiento_en_cierres.py
        -> solo informa: que cierres estan pendientes y que columnas faltan.
           Estrictamente de solo lectura: abre la base en modo `mode=ro` y no
           modifica ni un byte (tampoco el esquema).

    .venv\Scripts\python.exe scripts\congelar_establecimiento_en_cierres.py --aplicar
        -> aplica la migracion de esquema si hace falta (init_db) y, en los
           cierres pendientes:
           - copia los cuatro datos ACTUALES de `establishment`;
           - congela el IVA del 10 % y el desglose de SU PROPIO efectivo valido
             guardado (`valid_cash_cents`), nunca recalculado desde las ventas.

Garantias:
- cada grupo (establecimiento / IVA) solo se completa en cierres que lo tienen
  entero a NULL; un cierre ya congelado no se modifica nunca, ni siquiera
  ejecutandolo otra vez;
- solo escribe esas columnas: cifras, numero, fechas y desglose de unidades
  intactos;
- si hay cierres sin datos del establecimiento y la configuracion esta
  incompleta, no escribe nada;
- todo en una transaccion BEGIN IMMEDIATE: o se completa todo o nada;
- no imprime datos fiscales ni personales, solo numeros de cierre.

Usa la base de CAFETERIA_DB si esta definida; si no, data/cafeteria.sqlite.
Haz una copia de la base antes de aplicarlo.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, establecimiento  # noqa: E402
from app.cierre import (SNAPSHOT_ESTABLECIMIENTO, SNAPSHOT_IVA, TIPO_IVA,  # noqa: E402
                        desglose_iva)

# Grupo -> columnas de daily_close que se congelan juntas.
GRUPOS = {
    "establecimiento": tuple(SNAPSHOT_ESTABLECIMIENTO),
    "iva": SNAPSHOT_IVA,
}
TITULOS = {"establecimiento": "datos del establecimiento",
           "iva": f"desglose de IVA {TIPO_IVA} %"}


class CierreParcial(RuntimeError):
    """Un cierre tiene parte de un grupo congelado y parte no: no se toca nada."""


def _todas_nulas(columnas):
    return " AND ".join(f"{c} IS NULL" for c in columnas)


def _pendientes(conn, grupos=GRUPOS):
    """{grupo: [(id, close_number, valid_cash_cents)]}. CierreParcial si alguno
    tiene un grupo a medias."""
    resultado = {}
    for grupo, columnas in grupos.items():
        todas = _todas_nulas(columnas)
        alguna = " OR ".join(f"{c} IS NULL" for c in columnas)
        parciales = [f[0] for f in conn.execute(
            f"SELECT close_number FROM daily_close WHERE ({alguna})"
            f" AND NOT ({todas}) ORDER BY id")]
        if parciales:
            raise CierreParcial(
                f"Cierres con {TITULOS[grupo]} incompletos: " + ", ".join(parciales)
                + ". Revisar a mano; no se ha modificado nada.")
        resultado[grupo] = conn.execute(
            f"SELECT id, close_number, valid_cash_cents FROM daily_close"
            f" WHERE {todas} ORDER BY id").fetchall()
    return resultado


def inspeccionar():
    """Solo lectura: (columnas que faltan, {grupo: [cierres pendientes]}).

    Abre la base con `mode=ro`: no ejecuta init_db() ni ninguna escritura, asi
    que no modifica ni un byte del archivo. Si faltan las columnas de un grupo,
    todos los cierres estan pendientes de ese grupo.
    """
    ruta = db.ruta_base()
    if not ruta.exists():
        raise FileNotFoundError(f"No existe la base {ruta}.")
    conn = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
    try:
        existentes = {f[1] for f in conn.execute("PRAGMA table_info(daily_close)")}
        if not existentes:                        # base anterior a la FASE 6
            return [], {grupo: [] for grupo in GRUPOS}
        todos = [f[0] for f in conn.execute(
            "SELECT close_number FROM daily_close ORDER BY id")]
        faltan, pendientes, completos = [], {}, {}
        for grupo, columnas in GRUPOS.items():
            ausentes = [c for c in columnas if c not in existentes]
            if ausentes:
                faltan += ausentes
                pendientes[grupo] = list(todos)
            else:
                completos[grupo] = columnas
        # Solo se consultan los grupos cuyas columnas ya existen.
        for grupo, filas in _pendientes(conn, completos).items():
            pendientes[grupo] = [numero for _, numero, _ in filas]
        return faltan, {grupo: pendientes[grupo] for grupo in GRUPOS}
    finally:
        conn.close()


def completar(aplicar=False):
    """{grupo: numeros de cierre pendientes (y, con `aplicar`, completados)}.

    Sin `aplicar` es estrictamente de solo lectura (ver inspeccionar()).
    """
    if not aplicar:
        return inspeccionar()[1]
    db.init_db()   # anade las columnas *_snapshot y vat_* si la base es anterior

    with db.transaccion() as conn:
        pendientes = _pendientes(conn)

        if pendientes["establecimiento"]:
            # Los datos vigentes AHORA. Si falta alguno, SinConfigurar y ROLLBACK.
            empresa = establecimiento.exigir_completos(establecimiento.leer(conn))
            valores = [empresa[campo] for campo in SNAPSHOT_ESTABLECIMIENTO.values()]
            columnas = GRUPOS["establecimiento"]
            asignacion = ", ".join(f"{c} = ?" for c in columnas)
            for id_cierre, numero, _ in pendientes["establecimiento"]:
                cursor = conn.execute(
                    f"UPDATE daily_close SET {asignacion}"
                    f" WHERE id = ? AND {_todas_nulas(columnas)}",
                    (*valores, id_cierre))
                if cursor.rowcount != 1:
                    raise RuntimeError(f"No se pudo completar {numero}; no se ha modificado nada.")

        for id_cierre, numero, efectivo in pendientes["iva"]:
            # Desde el efectivo guardado en el propio cierre, no desde las ventas.
            base, cuota = desglose_iva(efectivo, TIPO_IVA)
            cursor = conn.execute(
                "UPDATE daily_close SET vat_rate_percent = ?, vat_base_cents = ?,"
                f" vat_cents = ? WHERE id = ? AND {_todas_nulas(SNAPSHOT_IVA)}",
                (TIPO_IVA, base, cuota, id_cierre))
            if cursor.rowcount != 1:
                raise RuntimeError(f"No se pudo completar {numero}; no se ha modificado nada.")

        return {grupo: [numero for _, numero, _ in filas]
                for grupo, filas in pendientes.items()}


def main(argv):
    aplicar = "--aplicar" in argv
    print(f"Base: {db.ruta_base()}")
    faltan = []
    try:
        if aplicar:
            cierres = completar(aplicar=True)
        else:
            faltan, cierres = inspeccionar()
    except (CierreParcial, establecimiento.SinConfigurar, FileNotFoundError) as error:
        print(f"ERROR: {error}")
        return 1
    if faltan:
        print(f"Faltan las columnas {', '.join(faltan)} en daily_close."
              " No se han creado: se crearan con --aplicar.")
    if not any(cierres.values()):
        print("No hay cierres pendientes: todos tienen los datos congelados.")
        return 0
    verbo = "Completados" if aplicar else "Pendientes"
    for grupo, numeros in cierres.items():
        if numeros:
            print(f"{verbo} ({TITULOS[grupo]}) {len(numeros)} cierre(s): {', '.join(numeros)}")
    if not aplicar:
        print("No se ha modificado nada. Para completarlos: --aplicar")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
