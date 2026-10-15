"""Ejecuta: python test_modPaquetes.py"""
import os
import tempfile
import unittest

from modPaquetes import Archivos, Paquete


def paquete_legacy(texto, lista_bytes):
    """Arma un paquete con el formato ANTERIOR de los demos: cabecera base 255 y texto contado en
    caracteres (no bytes). Solo válido con texto ASCII, que es el único caso que soportan los demos."""
    bytes_texto = texto.encode("utf-8")
    n = len(texto)
    return bytes([n // 255, n % 255]) + bytes_texto + b"".join(lista_bytes)


class PruebasPaquete(unittest.TestCase):
    def test_ida_y_vuelta_con_tildes(self):
        datos = [b"\x00\x01\x02", b"", b"x" * 1000]
        texto = "ñandú.jpg|3;vacío.png|0;grande.gif|1000"
        paquete = Paquete.Crear(texto, datos)
        registros, bytes_leidos = Paquete.Leer(paquete)
        self.assertEqual(registros, [["ñandú.jpg", "3"], ["vacío.png", "0"], ["grande.gif", "1000"]])
        self.assertEqual(bytes_leidos, datos)

    def test_la_longitud_cuenta_bytes_no_caracteres(self):
        texto = "ñ|1"                      # 3 caracteres, 4 bytes en UTF-8
        paquete = Paquete.Crear(texto, [b"A"])
        self.assertEqual(paquete[0] * 256 + paquete[1], len(texto.encode("utf-8")))

    def test_cabecera_en_base_256(self):
        texto = "a|1;" * 100 + "z|1"
        n = len(texto.encode("utf-8"))
        p = Paquete.Crear(texto, [b"x"] * 101)
        self.assertEqual((p[0], p[1]), (n // 256, n % 256))
        self.assertGreater(p[0], 0)

    def test_texto_demasiado_largo(self):
        with self.assertRaises(ValueError):
            Paquete.Crear("a" * 70000, [])

    def test_paquetes_invalidos(self):
        bueno = Paquete.Crear("a|3", [b"abc"])
        for malo in (b"", b"\x00", bueno[:-1], bueno + b"x", Paquete.Crear("a|xx", [b""]), bytes([0, 200]) + b"corto"):
            with self.subTest(malo=malo):
                with self.assertRaises(ValueError):
                    Paquete.Leer(malo)

    def test_paquete_vacio(self):
        self.assertEqual(Paquete.Leer(Paquete.Crear("", [])), ([], []))

    def test_leer_legacy_ida_y_vuelta(self):
        datos = [b"\x00\x01\x02", b"", b"x" * 1000]
        texto = "foto1.jpg|3;vacio.png|0;grande.gif|1000"
        registros, bytes_leidos = Paquete.LeerLegacy(paquete_legacy(texto, datos))
        self.assertEqual(registros, [["foto1.jpg", "3"], ["vacio.png", "0"], ["grande.gif", "1000"]])
        self.assertEqual(bytes_leidos, datos)

    def test_leer_legacy_rechaza_invalidos(self):
        bueno = paquete_legacy("a|3", [b"abc"])
        for malo in (b"", b"\x00", bueno[:-1], bueno + b"x",
                     paquete_legacy("a|xx", [b""]), bytes([0, 200]) + b"corto"):
            with self.subTest(malo=malo):
                with self.assertRaises(ValueError):
                    Paquete.LeerLegacy(malo)

    def test_legacy_base_255_solo_llega_a_65279(self):
        # n = b1*255 + b2 con b1, b2 en 0..255 -> máximo 65279; 65280 exigiría un byte 256, inexistente.
        self.assertEqual(255 * 255 + 254, 65279)
        with self.assertRaises(ValueError):
            bytes([256, 1])
        texto = "a" * 65277 + "|1"                       # 65279 caracteres ASCII = 65279 bytes
        self.assertEqual(len(texto), 65279)
        registros, bytes_leidos = Paquete.LeerLegacy(paquete_legacy(texto, [b"z"]))
        self.assertEqual(registros, [["a" * 65277, "1"]])
        self.assertEqual(bytes_leidos, [b"z"])

    def test_leer_no_entiende_un_paquete_legacy(self):
        # Texto ASCII de 300 bytes: cabecera legacy base 255 = (1, 45); Leer la lee en base 256 = 301
        # y detecta el truncamiento. Comprueba que los dos formatos no son compatibles.
        legacy = bytes([300 // 255, 300 % 255]) + b"a" * 300
        with self.assertRaises(ValueError):
            Paquete.Leer(legacy)

    def test_agrupar_por_tamano(self):
        items = [("a", 40), ("b", 40), ("c", 40), ("d", 150), ("e", 10)]
        self.assertEqual(Paquete.AgruparPorTamano(items, 100, 200), [["a", "b"], ["c"], ["d"], ["e"]])
        self.assertEqual(Paquete.AgruparPorTamano([], 100, 200), [])
        self.assertEqual(Paquete.AgruparPorTamano([("x", 5)], 100, 200), [["x"]])
        self.assertEqual(
            list(map(len, Paquete.AgruparPorTamano([(i, 0) for i in range(5)], 100, 2))),
            [2, 2, 1],
        )
        self.assertEqual(
            list(map(len, Paquete.AgruparPorTamano([(i, 0) for i in range(201)], 100, 200))),
            [200, 1],
        )
        with self.assertRaises(ValueError):
            Paquete.AgruparPorTamano([], 100, 0)


class PruebasArchivos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = self.tmp.name

    def test_nombre_seguro(self):
        self.assertEqual(Archivos.NombreSeguro("foto 1.jpg"), "foto 1.jpg")
        self.assertEqual(Archivos.NombreSeguro("a/b/foto.jpg"), "foto.jpg")        # se queda con el nombre base
        self.assertEqual(Archivos.NombreSeguro("..\\..\\foto.jpg"), "foto.jpg")
        for malo in ("", ".", "..", "..\\", "a:b.jpg", "x" * 200, "con|barra.jpg", None, "punto.", "<b>.png"):
            with self.subTest(malo=malo):
                self.assertIsNone(Archivos.NombreSeguro(malo))

    def test_ruta_segura_queda_dentro(self):
        ok = Archivos.RutaSegura(self.raiz, "carpeta1", "foto.jpg")
        self.assertTrue(ok.startswith(os.path.realpath(self.raiz) + os.sep))
        self.assertIsNone(Archivos.RutaSegura(self.raiz, "..", "x.jpg"))
        self.assertIsNone(Archivos.RutaSegura(self.raiz, "carpeta", "con|barra.jpg"))

    def test_grabar_bloques_i_p(self):
        ruta = os.path.join(self.raiz, "grande.bin")
        self.assertEqual(Archivos.GrabarBloque(ruta, b"AAA", "P"), "Error - Falta el primer bloque")
        self.assertEqual(Archivos.GrabarBloque(ruta, b"AAA", "I"), "OK")
        self.assertEqual(Archivos.GrabarBloque(ruta, b"BB", "P"), "OK")
        with open(ruta, "rb") as f:
            self.assertEqual(f.read(), b"AAABB")
        self.assertEqual(Archivos.GrabarBloque(ruta, b"Z", "I"), "OK")   # I reemplaza
        with open(ruta, "rb") as f:
            self.assertEqual(f.read(), b"Z")
        self.assertTrue(Archivos.GrabarBloque(ruta, b"x", "X").startswith("Error"))
        self.assertTrue(Archivos.GrabarBloque(ruta, b"x" * 200000, "P").startswith("Error"))

    def test_es_imagen_por_firma(self):
        jpg, png = b"\xff\xd8\xff\xe0" + b"0" * 20, b"\x89PNG\r\n\x1a\n" + b"0" * 20
        gif, webp = b"GIF89a" + b"0" * 20, b"RIFF\x10\x00\x00\x00WEBPVP8 "
        self.assertTrue(all([Archivos.EsImagen("a.jpg", jpg), Archivos.EsImagen("a.PNG", png),
                             Archivos.EsImagen("a.gif", gif), Archivos.EsImagen("a.webp", webp)]))
        self.assertFalse(Archivos.EsImagen("a.jpg", b"texto plano"))  # extensión válida, contenido no
        self.assertFalse(Archivos.EsImagen("a.exe", jpg))                                           # contenido válido, extensión no
        self.assertFalse(Archivos.EsImagen(None, jpg))

    def test_listar_con_metadatos_de_grilla(self):
        os.makedirs(os.path.join(self.raiz, "c"))
        for nombre, datos in (("a.jpg", b"123"), ("b.jpg", b"12345")):
            with open(os.path.join(self.raiz, "c", nombre), "wb") as f:
                f.write(datos)
        self.assertEqual(Archivos.Listar(os.path.join(self.raiz, "c")),
                         "Nombre del Archivo|Size;600|100;str|int;a.jpg|3;b.jpg|5")
        self.assertEqual(Archivos.Listar(os.path.join(self.raiz, "no_existe")), "")


class PruebasLeerBloque(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.dir.name, "a.bin")

    def tearDown(self):
        self.dir.cleanup()

    def escribir(self, datos):
        with open(self.ruta, "wb") as f:
            f.write(datos)

    def test_ida_y_vuelta_con_grabar_bloque_en_tamanos_limite(self):
        for size in (0, 1, 99, 100, 101, 200, 201, 1000):
            datos = bytes((i * 7) % 256 for i in range(size))
            self.escribir(datos)
            n = max(1, -(-size // 100))
            leido = b"".join(Archivos.LeerBloque(self.ruta, i, 100) for i in range(n))
            self.assertEqual(leido, datos, size)
            destino = os.path.join(self.dir.name, "copia.bin")
            for i in range(n):
                self.assertEqual(Archivos.GrabarBloque(destino, Archivos.LeerBloque(self.ruta, i, 100), "I" if i == 0 else "P", 100), "OK")
            with open(destino, "rb") as f:
                self.assertEqual(f.read(), datos, size)

    def test_ultimo_bloque_parcial_y_fuera_de_rango(self):
        self.escribir(b"x" * 250)
        self.assertEqual([len(Archivos.LeerBloque(self.ruta, i, 100)) for i in range(3)], [100, 100, 50])
        self.assertIsNone(Archivos.LeerBloque(self.ruta, 3, 100))
        self.escribir(b"")
        self.assertEqual(Archivos.LeerBloque(self.ruta, 0, 100), b"")
        self.assertIsNone(Archivos.LeerBloque(self.ruta, 1, 100))

    def test_es_idempotente_y_rechaza_entradas_invalidas(self):
        self.escribir(bytes(range(256)) * 2)
        self.assertEqual(Archivos.LeerBloque(self.ruta, 1, 100), Archivos.LeerBloque(self.ruta, 1, 100))
        for malo in (-1, "1", 1.0, None, True):
            self.assertIsNone(Archivos.LeerBloque(self.ruta, malo, 100), repr(malo))
        self.assertIsNone(Archivos.LeerBloque(self.ruta, 0, 0))
        self.assertIsNone(Archivos.LeerBloque(os.path.join(self.dir.name, "no.bin"), 0, 100))
        self.assertIsNone(Archivos.LeerBloque(self.dir.name, 0, 100))


if __name__ == "__main__":
    unittest.main()
