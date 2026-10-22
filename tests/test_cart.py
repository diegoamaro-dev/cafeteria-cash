r"""Tests del calculo de la venta actual (FASE 2).

Stdlib unittest, sin dependencias nuevas:

    .venv\Scripts\python.exe -m unittest discover -s tests -v

Comprueba lo unico que no se puede verificar a ojo: que los subtotales y el
total salen exactos, en centimos, tambien donde float fallaria.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cart import subtotal_centimos, total_centimos  # noqa: E402
from app.money import format_euros, parse_euros  # noqa: E402


def linea(precio_centimos, cantidad):
    return {"precio_centimos": precio_centimos, "cantidad": cantidad}


class TestSubtotales(unittest.TestCase):

    def test_subtotal_de_una_unidad(self):
        self.assertEqual(subtotal_centimos(140, 1), 140)

    def test_subtotal_de_varias_unidades(self):
        self.assertEqual(subtotal_centimos(140, 2), 280)
        self.assertEqual(subtotal_centimos(140, 3), 420)
        self.assertEqual(subtotal_centimos(165, 1), 165)

    def test_subtotal_de_cero_unidades(self):
        self.assertEqual(subtotal_centimos(140, 0), 0)


class TestTotales(unittest.TestCase):

    def test_caso_de_la_fase_2_dos_cafes_y_un_cafe_con_leche(self):
        venta = [linea(140, 2), linea(165, 1)]
        self.assertEqual(total_centimos(venta), 445)
        self.assertEqual(format_euros(total_centimos(venta)), "4,45 €")

    def test_tras_pulsar_mas_en_el_cafe(self):
        venta = [linea(140, 3), linea(165, 1)]
        self.assertEqual(format_euros(subtotal_centimos(140, 3)), "4,20 €")
        self.assertEqual(format_euros(total_centimos(venta)), "5,85 €")

    def test_venta_vacia(self):
        self.assertEqual(total_centimos([]), 0)
        self.assertEqual(format_euros(total_centimos([])), "0,00 €")


class TestPrecisionMonetaria(unittest.TestCase):
    """Casos donde float daria un resultado incorrecto."""

    def test_suma_que_float_no_representa(self):
        self.assertEqual(total_centimos([linea(10, 1), linea(20, 1)]), 30)
        self.assertNotEqual(0.10 + 0.20, 0.30)

    def test_producto_que_float_no_representa(self):
        self.assertEqual(subtotal_centimos(7, 3), 21)
        self.assertNotEqual(0.07 * 3, 0.21)

        self.assertEqual(subtotal_centimos(110, 3), 330)
        self.assertNotEqual(1.10 * 3, 3.30)

    def test_caso_mixto_de_la_fase_2(self):
        # 6 cafés a 1,40 + 4 cafés con leche a 1,65 = 15,00 € exactos.
        venta = [linea(140, 6), linea(165, 4)]
        self.assertEqual(total_centimos(venta), 1500)
        self.assertEqual(format_euros(total_centimos(venta)), "15,00 €")
        self.assertNotEqual(6 * 1.40 + 4 * 1.65, 15.0)


class TestIdaYVuelta(unittest.TestCase):

    def test_texto_a_centimos_y_vuelta(self):
        for texto in ["1,40", "1,65", "0,90", "12,05"]:
            with self.subTest(texto=texto):
                self.assertEqual(format_euros(parse_euros(texto)), texto + " €")


if __name__ == "__main__":
    unittest.main(verbosity=2)
