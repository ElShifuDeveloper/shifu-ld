"""Pruebas del cliente PostgreSQL (gemelo). Ejecuta: python test_modAccesoDatosPg.py

Sin psycopg instalado se omiten. Las pruebas contra un servidor real se activan con LD_TEST_PG_DSN.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from modAccesoDatos import clienteSQL
    HAY_PSYCOPG = True
except ImportError:
    clienteSQL = None
    HAY_PSYCOPG = False

DSN_PRUEBA = os.environ.get("LD_TEST_PG_DSN", "")


def cliente_con_config(texto):
    """clienteSQL con un archivo de config temporal (no abre conexión en __init__)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(texto)
        ruta = f.name
    try:
        return clienteSQL(ruta, os.path.join(tempfile.gettempdir(), "ld_pg.log"))
    finally:
        os.unlink(ruta)


@unittest.skipUnless(HAY_PSYCOPG, "psycopg no está instalado: se omite el cliente PostgreSQL")
class PruebasClientePg(unittest.TestCase):
    def test_dsn_con_puerto_por_defecto(self):
        c = cliente_con_config("servidor=localhost\nbasedatos=tienda\nusuario=u\nclave=se=creta\n")
        self.assertIn("host=localhost", c.CadenaConexion)
        self.assertIn("port=5432", c.CadenaConexion)
        self.assertIn("dbname=tienda", c.CadenaConexion)
        self.assertIn("password=se=creta", c.CadenaConexion)   # la clave puede contener '='

    def test_dsn_con_puerto_y_sslmode(self):
        c = cliente_con_config("servidor=db\npuerto=6543\nbasedatos=t\nusuario=u\nclave=k\nsslmode=require\n")
        self.assertIn("port=6543", c.CadenaConexion)
        self.assertIn("sslmode=require", c.CadenaConexion)

    def test_sentencia_de_funcion(self):
        self.assertEqual(clienteSQL._sql_funcion("uspX", "", ""), ("SELECT uspX()", []))
        self.assertEqual(clienteSQL._sql_funcion("public.uspX", "ProductID", "7"),
                         ("SELECT public.uspX(%s)", ["7"]))

    def test_nombres_invalidos_se_rechazan(self):
        for malo in ("uspX; drop table t", "usp X", "", None, "a..b"):
            with self.subTest(malo=malo):
                with self.assertRaises(RuntimeError):
                    clienteSQL._sql_funcion(malo, "", "")
        with self.assertRaises(RuntimeError):
            clienteSQL._sql_funcion("uspX", "p;--", "1")

    def test_sentencia_insert(self):
        self.assertEqual(clienteSQL._sql_insert("Producto", ["Id", "Nombre"]),
                         "INSERT INTO Producto (Id,Nombre) VALUES (%s,%s)")
        for malo_tabla, malos_campos in (("a b", ["Id"]), ("Producto", ["Id;--"])):
            with self.subTest(tabla=malo_tabla):
                with self.assertRaises(RuntimeError):
                    clienteSQL._sql_insert(malo_tabla, malos_campos)

    def test_no_define_metodos_sin_equivalente(self):
        # nextset() no existe en PostgreSQL: el gemelo no implementa estas variantes
        self.assertFalse(hasattr(clienteSQL, "EjecutarComandoListas"))
        self.assertFalse(hasattr(clienteSQL, "EjecutarComandoVariosDF"))


@unittest.skipUnless(HAY_PSYCOPG and DSN_PRUEBA,
                     "sin LD_TEST_PG_DSN: se omiten las pruebas contra un PostgreSQL real")
class PruebasIntegracionPg(unittest.TestCase):
    def test_ida_y_vuelta_de_una_funcion_escalar(self):
        import psycopg
        with psycopg.connect(DSN_PRUEBA) as con:
            with con.cursor() as cmd:
                cmd.execute("CREATE OR REPLACE FUNCTION ld_eco(p text) RETURNS text "
                            "LANGUAGE sql AS $$ SELECT p $$")
                cmd.execute("SELECT ld_eco(%s)", ("hola|1;2",))
                self.assertEqual(cmd.fetchone()[0], "hola|1;2")
                cmd.execute("DROP FUNCTION ld_eco(text)")


if __name__ == "__main__":
    unittest.main()