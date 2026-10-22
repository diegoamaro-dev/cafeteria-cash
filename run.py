"""Punto de arranque de Cafetería Cash.

Solo localhost: la aplicación escucha en 127.0.0.1 y nunca en 0.0.0.0.
No exponer a Internet ni a la red local.
"""

from app import create_app

HOST = "127.0.0.1"
PORT = 5000

app = create_app()

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)
