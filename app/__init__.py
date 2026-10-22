"""Cafeteria Cash — aplicacion Flask.

FASE 1: productos. Todavia no hay ventas, cierres, PDF ni backups.
"""

from flask import Flask

from .db import init_db
from .money import format_euros


def create_app():
    """Crea y devuelve la aplicacion Flask."""
    app = Flask(__name__)

    # La base se crea si no existe. Es idempotente y no borra datos.
    init_db()

    app.jinja_env.filters["euros"] = format_euros

    from . import routes
    app.register_blueprint(routes.bp)

    return app
