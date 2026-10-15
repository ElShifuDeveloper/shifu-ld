"""Pruebas de consola.py (colores). Ejecuta: python scripts/test_consola.py"""
import io
import os
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True   # el paquete se distribuye sin __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
import consola  # noqa: E402


class FlujoFalso:
    """Flujo que dice ser terminal (para probar el camino con color)."""

    def __init__(self, tty=True):
        self._tty = tty

    def isatty(self):
        return self._tty


class PruebasColor(unittest.TestCase):
    def setUp(self):
        self._no_color = os.environ.pop("NO_COLOR", None)
        self._term = os.environ.pop("TERM", None)
        self.addCleanup(self._restaurar)

    def _restaurar(self):
        if self._no_color is not None:
            os.environ["NO_COLOR"] = self._no_color
        if self._term is not None:
            os.environ["TERM"] = self._term

    def test_sin_terminal_no_hay_ansi(self):
        self.assertFalse(consola.soporta_color(io.StringIO()))
        self.assertEqual(consola.ok("listo"), "✔ listo")
        self.assertEqual(consola.error("rompió"), "✖ rompió")

    def test_con_terminal_y_sin_no_color_hay_ansi(self):
        self.assertTrue(consola.soporta_color(FlujoFalso()))
        pintado = consola.ok("listo", flujo=FlujoFalso())
        self.assertIn("\033[32m", pintado)
        self.assertTrue(pintado.endswith("\033[0m"))
        self.assertIn("listo", pintado)

    def test_no_color_manda_aunque_haya_terminal(self):
        os.environ["NO_COLOR"] = "1"
        self.assertFalse(consola.soporta_color(FlujoFalso()))
        self.assertEqual(consola.titulo("x", flujo=FlujoFalso()), "x")

    def test_term_dumb_apaga_el_color(self):
        os.environ["TERM"] = "dumb"
        self.assertFalse(consola.soporta_color(FlujoFalso()))

    def test_decorar_no_cambia_el_texto_sin_terminal(self):
        lineas = ["ERROR: falta algo", "AVISO: revisa", "resultado: al día", "otra línea"]
        self.assertEqual(consola.decorar_lineas(lineas, flujo=io.StringIO()), "\n".join(lineas))

    def test_decorar_colorea_por_contenido_con_terminal(self):
        f = FlujoFalso()
        self.assertIn("\033[31m", consola.decorar("ERROR: x", flujo=f))
        self.assertIn("\033[33m", consola.decorar("AVISO: x", flujo=f))
        self.assertIn("\033[32m", consola.decorar("resultado: al día", flujo=f))


if __name__ == "__main__":
    unittest.main()