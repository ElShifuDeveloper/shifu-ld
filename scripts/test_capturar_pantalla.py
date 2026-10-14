"""Pruebas de las partes puras de capturar_pantalla.py. Ejecuta: python scripts/test_capturar_pantalla.py"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capturar_pantalla as cp  # noqa: E402


class Pruebas(unittest.TestCase):
    def test_tema_se_inyecta_antes_de_cualquier_script_y_con_base(self):
        html = "<!DOCTYPE html><html><head><title>x</title><link href='LD.css'></head><body></body></html>"
        r = cp.html_con_tema(html, "/tmp", "oscuro")
        self.assertIn('dataset.tema="oscuro"', r)
        self.assertIn("<base href=\"file:///", r)
        self.assertLess(r.index("dataset.tema"), r.index("<title>"))

    def test_html_sin_head_tambien_recibe_el_tema(self):
        self.assertTrue(cp.html_con_tema("<p>hola</p>", "/tmp", "claro").startswith("<base"))

    def test_envoltorio_movil_usa_iframe_del_ancho_pedido(self):
        r = cp.html_movil("file:///tmp/x.html", ancho=390, alto=2000)
        self.assertIn('width="390"', r)
        self.assertIn('src="file:///tmp/x.html"', r)

    def test_navegador_por_variable_de_entorno(self):
        with tempfile.NamedTemporaryFile() as f:
            anterior = os.environ.get("LD_NAVEGADOR")
            os.environ["LD_NAVEGADOR"] = f.name
            try:
                self.assertEqual(cp.buscar_navegador(), f.name)
            finally:
                if anterior is None:
                    del os.environ["LD_NAVEGADOR"]
                else:
                    os.environ["LD_NAVEGADOR"] = anterior

    def test_sin_pagina_devuelve_error(self):
        self.assertEqual(cp.main(["/ruta/que/no/existe.html"]), 2)


if __name__ == "__main__":
    unittest.main()
