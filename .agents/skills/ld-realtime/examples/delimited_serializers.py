"""Convierte las listas delimitadas de los SP (``¬`` entre registros, ``|`` entre campos) a JSON y XML.

Reemplaza a ``JSON.SerializarCsv`` y ``XML.SerializarCsv`` de modUtilidades, que arman el texto con
concatenación y producen JSON/XML inválido con comillas, ``\\``, saltos de línea, ``&``/``<`` o
códigos con ceros a la izquierda (``"007"`` se emitía como el número ``007``). Aquí los valores se
serializan con ``json`` y ``ElementTree``, que escapan correctamente.
"""
import json
import re
from xml.etree import ElementTree as ET
from xml.sax.saxutils import unescape

_ENTIDADES = {"&quot;": '"', "&apos;": "'"}
_TIPOS_NUMERICOS = {"int": int, "float": float}


def registros_desde_delimitado(texto, sep_campo="|", sep_reg="¬", filas_meta=1):
    """Devuelve una lista de diccionarios con la primera fila como nombres de columna.

    filas_meta=1: solo nombres (uspProductoListar3Csv, uspProductoObtenerPorId3).
    filas_meta=3: nombres, anchos y tipos (uspProductoListarCsv); los tipos ``int``/``float``
    convierten el valor, el resto queda como texto. Un texto vacío devuelve ``[]``.
    Lanza ValueError si una fila no tiene tantos campos como columnas.
    """
    if not texto or not texto.strip():
        return []
    registros = texto.split(sep_reg)
    if len(registros) < filas_meta:
        raise ValueError("faltan las filas de metadatos")
    nombres = registros[0].split(sep_campo)
    tipos = registros[2].split(sep_campo) if filas_meta >= 3 else [""] * len(nombres)
    if len(tipos) != len(nombres):
        raise ValueError("los tipos no coinciden con las columnas")

    salida = []
    for numero, registro in enumerate(registros[filas_meta:], start=1):
        if registro == "":
            continue
        campos = registro.split(sep_campo)
        if len(campos) != len(nombres):
            raise ValueError(f"fila {numero}: {len(campos)} campos, se esperaban {len(nombres)}")
        fila = {}
        for nombre, tipo, valor in zip(nombres, tipos, campos):
            valor = unescape(valor, _ENTIDADES)  # SQL Server: FOR XML PATH('') entrega &amp; &lt; &gt; (PostgreSQL usa string_agg, sin escape)
            conversor = _TIPOS_NUMERICOS.get(tipo)
            if conversor is not None and valor != "":
                try:
                    valor = conversor(valor)
                except ValueError:
                    raise ValueError(f"fila {numero}: '{valor}' no es {tipo}") from None
            fila[nombre] = valor
        salida.append(fila)
    return salida


def a_json(registros):
    return json.dumps(registros, ensure_ascii=False)


def _nombre_etiqueta(nombre):
    limpio = re.sub(r"[^A-Za-z0-9_.-]", "_", nombre.strip())
    return limpio if re.match(r"[A-Za-z_]", limpio) else "_" + limpio


def a_xml(registros, raiz="registros", elemento="registro"):
    """XML en bytes UTF-8; los nombres de columna con espacios se convierten en etiquetas válidas."""
    nodo_raiz = ET.Element(_nombre_etiqueta(raiz))
    for fila in registros:
        nodo = ET.SubElement(nodo_raiz, _nombre_etiqueta(elemento))
        for nombre, valor in fila.items():
            ET.SubElement(nodo, _nombre_etiqueta(nombre)).text = str(valor)
    return ET.tostring(nodo_raiz, encoding="utf-8", xml_declaration=True)
