"""Ejecuta: python test_delimited_serializers.py"""
import json
import unittest
from xml.etree import ElementTree as ET

from delimited_serializers import a_json, a_xml, registros_desde_delimitado


class Pruebas(unittest.TestCase):
    def test_un_registro_con_nombres(self):
        # forma de uspProductoObtenerPorId3
        r = registros_desde_delimitado("Codigo|Nombre|IdProv|IdCat|Precio|Stock¬1|Chai|1|1|18.00|39")
        self.assertEqual(r, [{"Codigo": "1", "Nombre": "Chai", "IdProv": "1", "IdCat": "1", "Precio": "18.00", "Stock": "39"}])

    def test_tipos_declarados(self):
        # forma de uspProductoListarCsv (nombres, anchos y tipos)
        t = "Codigo|Nombre|Precio¬80|300|80¬int|str|float¬1|Chai|18.5¬2|Chang|19"
        self.assertEqual(registros_desde_delimitado(t, filas_meta=3),
                         [{"Codigo": 1, "Nombre": "Chai", "Precio": 18.5}, {"Codigo": 2, "Nombre": "Chang", "Precio": 19.0}])

    def test_ceros_a_la_izquierda_no_se_convierten(self):
        # JSON.SerializarCsv emitía 007 sin comillas (JSON inválido)
        r = registros_desde_delimitado("Codigo|Nombre¬007|Bond")
        self.assertEqual(json.loads(a_json(r)), [{"Codigo": "007", "Nombre": "Bond"}])

    def test_caracteres_especiales_en_json(self):
        r = registros_desde_delimitado('Id|Nombre¬1|Queso "Azul" \\ x&amp;y')
        self.assertEqual(json.loads(a_json(r))[0]["Nombre"], 'Queso "Azul" \\ x&y')

    def test_xml_escapa_y_sanea_etiquetas(self):
        r = registros_desde_delimitado("Id Orden|Nombre¬1|A <b> & C")
        raiz = ET.fromstring(a_xml(r, "Ordenes", "Orden"))
        self.assertEqual(raiz.find("Orden/Id_Orden").text, "1")
        self.assertEqual(raiz.find("Orden/Nombre").text, "A <b> & C")

    def test_vacio_y_errores(self):
        self.assertEqual(registros_desde_delimitado(""), [])
        self.assertEqual(registros_desde_delimitado("A|B"), [])
        with self.assertRaises(ValueError):
            registros_desde_delimitado("A|B¬1")           # faltan campos
        with self.assertRaises(ValueError):
            registros_desde_delimitado("A¬x¬int¬abc", filas_meta=3)  # tipo int con valor no numérico

    def test_separador_dentro_del_valor_se_detecta(self):
        with self.assertRaises(ValueError):
            registros_desde_delimitado("Id|Nombre¬1|Pepe|Jr")  # un "|" extra no pasa inadvertido


if __name__ == "__main__":
    unittest.main()
