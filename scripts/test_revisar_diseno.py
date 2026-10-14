"""Pruebas de revisar_diseno.py. Ejecuta: python scripts/test_revisar_diseno.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revisar_diseno as rd  # noqa: E402

BUENA = """<html><head><link href="LD.css" rel="stylesheet"></head><body>
<div class="Titulo">T</div><div class="Subtitulo">S</div>
<main class="ld-pagina"><section class="ld-tarjeta"><h2>x</h2><input type="button" class="Boton" value="Ok">
<input type="button" class="Boton Secundario" value="No"></section></main><script src="a.js"></script></body></html>"""

MALA = """<html><head><link href="LD.css" rel="stylesheet"></head><body>
<div class="Titulo">T</div>
<div id="z" class="Marco" style="border:2px dashed gray">arrastra</div>
<div class="Fila"><input type="button" class="Boton" value="Grabar"></div>
<div class="Mensaje" style="color:#a33"></div></body></html>"""


class Pruebas(unittest.TestCase):
    def test_pantalla_correcta_sin_errores(self):
        errores, avisos = rd.revisar(BUENA)
        self.assertEqual((errores, avisos), ([], []))

    def test_pantalla_generada_mal_se_rechaza_por_cada_causa(self):
        errores, _ = rd.revisar(MALA)
        texto = "\n".join(errores)
        for esperado in ("style=", "suelto en <body>", "ld-pagina", "ld-tarjeta"):
            self.assertIn(esperado, texto)

    def test_sin_hoja_ld_o_con_dacp(self):
        errores, _ = rd.revisar('<html><head><link href="DACP.css"></head><body></body></html>')
        self.assertIn("DACP.css", errores[0])

    def test_dos_botones_primarios_en_una_tarjeta_avisan(self):
        html = BUENA.replace('class="Boton Secundario"', 'class="Boton"')
        _, avisos = rd.revisar(html)
        self.assertTrue(any("botones primarios" in a for a in avisos))

    def test_color_suelto_en_style_y_popup_con_style_permitido(self):
        html = BUENA.replace("</head>", "<style>.x{color:#fff}</style></head>").replace(
            "</body>", '<div class="PopupContainer"><div class="PopupWindow" style="left:1%"></div></div></body>')
        errores, _ = rd.revisar(html)
        self.assertEqual(len(errores), 1)
        self.assertIn("color suelto", errores[0])

    def test_modo_externo_no_exige_estructura_ld_pero_si_vigila_style_en_linea(self):
        html = '<html><head><link href="tailwind.css"></head><body><div class="p-4"><p class="text-lg">Hola</p></div></body></html>'
        self.assertEqual(rd.revisar(html, "externo"), ([], []))
        errores, _ = rd.revisar(html.replace('class="p-4"', 'class="p-4" style="color:red"'), "externo")
        self.assertEqual(len(errores), 1)
        self.assertIn("style=", errores[0])
        self.assertTrue(rd.revisar(html, "ld")[0])   # en modo ld sí falla

    def test_modo_se_lee_de_ld_diseno_json_y_se_puede_forzar(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            (raiz / ".ld").mkdir()
            (raiz / "app").mkdir()
            pantalla = raiz / "app" / "p.html"
            pantalla.write_text("<html><body><p>x</p></body></html>", encoding="utf-8")
            self.assertEqual(rd.modo_del_proyecto(pantalla), "ld")
            (raiz / ".ld" / "diseno.json").write_text(json.dumps({"modo": "externo", "skill": "t"}), encoding="utf-8")
            self.assertEqual(rd.modo_del_proyecto(pantalla), "externo")
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rd.main([str(pantalla)]), 0)
                self.assertEqual(rd.main([str(pantalla), "--modo", "ld"]), 1)

    def test_catalogo_y_plantilla_del_skill_pasan(self):
        base = Path(__file__).resolve().parent.parent / ".agents/skills/ld-design/examples"
        for nombre in ("pantalla-base.html", "dashboard-glass.html", "catalogo.html"):
            errores, _ = rd.revisar((base / nombre).read_text(encoding="utf-8"))
            self.assertEqual(errores, [], nombre)


if __name__ == "__main__":
    unittest.main()
