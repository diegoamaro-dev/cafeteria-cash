"""Cafeteria Cash — aplicacion Flask.

FASE 1: productos. Todavia no hay ventas, cierres, PDF ni backups.
"""

from flask import Flask

from .db import DIRECTORIO_DATOS, init_db, ruta_base
from .money import format_euros

# Base de demostracion. Si la aplicacion esta usando EXACTAMENTE este archivo,
# la interfaz lo advierte en todas las pantallas. Se mira la ruta real en uso y
# no una variable aparte: asi el aviso no puede decir lo que no es.
RUTA_DEMO = DIRECTORIO_DATOS / "demo.sqlite"


def create_app():
    """Crea y devuelve la aplicacion Flask."""
    app = Flask(__name__)

    # La base se crea si no existe. Es idempotente y no borra datos.
    init_db()

    app.jinja_env.filters["euros"] = format_euros
    app.jinja_env.globals["modo_demo"] = ruta_base().resolve() == RUTA_DEMO.resolve()

    from . import routes
    app.register_blueprint(routes.bp)

    return app
