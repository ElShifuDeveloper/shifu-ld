"""Pruebas de settings_transferencia.py. Ejecuta: python test_settings_transferencia.py"""
import unittest

import settings_transferencia as st


class Pruebas(unittest.TestCase):
    def test_defaults_realistas_para_fotos(self):
        self.assertEqual(st.LD_SIZE_LOTE, 512 * 1024)
        self.assertEqual(st.LD_SIZE_BLOQUE, 256 * 1024)
        self.assertEqual(st.LD_MAX_ARCHIVOS_LOTE, 200)

    def test_variable_de_entorno_sobrescribe(self):
        self.assertEqual(st.LeerEntero("X", 5000, entorno={"X": " 1048576 "}), 1048576)

    def test_sin_variable_o_vacia_usa_el_defecto(self):
        self.assertEqual(st.LeerEntero("X", 5000, entorno={}), 5000)
        self.assertEqual(st.LeerEntero("X", 5000, entorno={"X": "  "}), 5000)

    def test_valores_invalidos_fallan_con_mensaje_claro(self):
        for malo in ("abc", "1.5", "0", "-5", "100", str(10 ** 12)):
            with self.assertRaises(ValueError, msg=malo) as ctx:
                st.LeerEntero("LD_SIZE_LOTE", 5000, entorno={"LD_SIZE_LOTE": malo})
            self.assertIn("LD_SIZE_LOTE", str(ctx.exception))

    def test_limite_de_archivos_por_lote_es_configurable_y_acotado(self):
        self.assertEqual(
            st.LeerEntero("LD_MAX_ARCHIVOS_LOTE", 200, minimo=1, maximo=10_000, entorno={"LD_MAX_ARCHIVOS_LOTE": "350"}),
            350,
        )
        for malo in ("abc", "0", "-1", "10001"):
            with self.subTest(malo=malo), self.assertRaises(ValueError):
                st.LeerEntero("LD_MAX_ARCHIVOS_LOTE", 200, minimo=1, maximo=10_000, entorno={"LD_MAX_ARCHIVOS_LOTE": malo})


if __name__ == "__main__":
    unittest.main()
