"""Paquetes de bytes y utilidades de archivos del estilo LD (extraídos de appDemo06-10, 13 y 14).

Los demos repiten, copiado, este formato de respuesta binaria (application/octet-stream):

    [2 bytes: longitud del texto] [texto UTF-8] [bytes del archivo 1] [bytes del archivo 2] ...

El texto lleva un registro por archivo (campos con `|`, registros con `;`) y el ÚLTIMO campo de cada
registro es el tamaño en bytes del archivo, para que el cliente corte el resto con slice().

Diferencias con los demos (a propósito):
  * La longitud del texto se cuenta en BYTES UTF-8, no en caracteres: los demos usan len(texto), que falla
    con tildes o eñes porque el cliente lee esa cantidad de bytes.
  * Los 2 bytes se leen en base 256 (n = b1*256 + b2, máximo 65535). Los demos usan base 255
    (appDemo10/14); un par cliente-servidor nuevo debe usar el mismo criterio en ambos lados.

Para leer un paquete del formato antiguo de un demo durante una migración está `Paquete.LeerLegacy`
(base 255, longitud en caracteres, texto Latin-1); no lo uses como formato de trabajo.
"""
import os
import re

SEP_CAMPO = "|"
SEP_REG = ";"
MAX_TEXTO = 65535
RE_NOMBRE = re.compile(r"^[\w][\w .()-]{0,119}$")  # letras, dígitos, _, espacio, punto, paréntesis, guion


class Paquete():
    @staticmethod
    def Crear(texto, listaBytes):
        """Arma el paquete: 2 bytes de longitud + texto UTF-8 + los bytes de cada archivo, en orden."""
        bytesTexto = texto.encode("utf-8")
        n = len(bytesTexto)
        if n > MAX_TEXTO:
            raise ValueError("El texto del paquete supera %d bytes" % MAX_TEXTO)
        return bytes([n // 256, n % 256]) + bytesTexto + b"".join(listaBytes)

    @staticmethod
    def Leer(datos, sepReg=SEP_REG, sepCampo=SEP_CAMPO):
        """Inverso de Crear. Devuelve (registros, listaBytes); cada registro es la lista de sus campos.

        Valida que los tamaños declarados coincidan con los bytes recibidos: un paquete truncado o
        manipulado lanza ValueError en lugar de grabar archivos incompletos.
        """
        if len(datos) < 2:
            raise ValueError("Paquete sin cabecera")
        n = datos[0] * 256 + datos[1]
        if len(datos) < 2 + n:
            raise ValueError("Paquete truncado: falta parte del texto")
        texto = datos[2:2 + n].decode("utf-8")
        registros = [r.split(sepCampo) for r in texto.split(sepReg)] if texto != "" else []
        posicion = 2 + n
        listaBytes = []
        for campos in registros:
            try:
                size = int(campos[-1])
            except ValueError:
                raise ValueError("Tamaño no numérico en el registro: %s" % sepCampo.join(campos)) from None
            if size < 0 or posicion + size > len(datos):
                raise ValueError("Paquete truncado: faltan bytes de %s" % campos[0])
            listaBytes.append(datos[posicion:posicion + size])
            posicion += size
        if posicion != len(datos):
            raise ValueError("Paquete con bytes sobrantes")
        return registros, listaBytes

    @staticmethod
    def LeerLegacy(datos, sepReg=SEP_REG, sepCampo=SEP_CAMPO):
        """Lee un paquete del formato ANTERIOR de los demos (appDemo06-10, 14); inverso de Leer.

        Existe solo como puente para leer un paquete que genera un demo existente durante una migración;
        el formato de trabajo es `Leer`. Los demos usan base 255 en la cabecera, cuentan el texto en
        caracteres (`len(texto)`, no bytes) y leen cada byte con `String.fromCharCode` (Latin-1, no UTF-8):
        son correctos solo con texto ASCII. Reproduce ese comportamiento tal cual, así que hereda sus
        límites (texto ASCII y `n <= 65279`). Devuelve (registros, listaBytes), igual que `Leer`.
        """
        if len(datos) < 2:
            raise ValueError("Paquete sin cabecera")
        n = datos[0] * 255 + datos[1]
        if len(datos) < 2 + n:
            raise ValueError("Paquete truncado: falta parte del texto")
        texto = datos[2:2 + n].decode("latin-1")
        registros = [r.split(sepCampo) for r in texto.split(sepReg)] if texto != "" else []
        posicion = 2 + n
        listaBytes = []
        for campos in registros:
            try:
                size = int(campos[-1])
            except ValueError:
                raise ValueError("Tamaño no numérico en el registro: %s" % sepCampo.join(campos)) from None
            if size < 0 or posicion + size > len(datos):
                raise ValueError("Paquete truncado: faltan bytes de %s" % campos[0])
            listaBytes.append(datos[posicion:posicion + size])
            posicion += size
        if posicion != len(datos):
            raise ValueError("Paquete con bytes sobrantes")
        return registros, listaBytes

    @staticmethod
    def AgruparPorTamano(items, limite, max_archivos_lote):
        """Agrupa [(id, size), ...] en lotes cuya suma no supera `limite` (appDemo10: grupos de ~100 KB).

        Un elemento mayor que el límite forma su propio lote (en la subida, esos van por bloques I/P).
        Cada lote también respeta `max_archivos_lote`, recibido desde la configuración central.
        """
        if isinstance(max_archivos_lote, bool) or not isinstance(max_archivos_lote, int) or max_archivos_lote <= 0:
            raise ValueError("max_archivos_lote debe ser un entero positivo")
        grupos, actual, total = [], [], 0
        for ident, size in items:
            if actual and (len(actual) >= max_archivos_lote or total + size > limite):
                grupos.append(actual)
                actual, total = [], 0
            actual.append(ident)
            total += size
        if actual:
            grupos.append(actual)
        return grupos


class Archivos():
    @staticmethod
    def NombreSeguro(nombre):
        """Devuelve el nombre sin ruta, o None si no es válido. Evita `../`, rutas absolutas y nombres raros.

        appDemo13 arma la ruta con el nombre que envía el cliente (os.path.join(ruta, nombre)): un
        nombre como `..\\..\\x` escribiría fuera del repositorio.
        """
        if not isinstance(nombre, str):
            return None
        normalizado = nombre.replace("\\", "/")
        if ":" in normalizado:
            return None
        base = os.path.basename(normalizado).strip()
        if base in ("", ".", "..") or RE_NOMBRE.match(base) is None or base.endswith((" ", ".")):
            return None
        return base

    @staticmethod
    def RutaSegura(raiz, *partes):
        """Une `raiz` con los nombres (carpeta, archivo) y garantiza que el resultado queda dentro de `raiz`."""
        base = os.path.realpath(raiz)
        nombres = []
        for p in partes:
            seguro = Archivos.NombreSeguro(p)
            if seguro is None:
                return None
            nombres.append(seguro)
        ruta = os.path.realpath(os.path.join(base, *nombres))
        return ruta if ruta == base or ruta.startswith(base + os.sep) else None

    EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".gif", ".webp")

    @staticmethod
    def EsImagen(nombre, datos):
        """True si la extensión y los primeros bytes (firma) corresponden a JPEG, PNG, GIF o WebP.

        El tipo MIME y la extensión que declara el navegador no validan nada en el servidor.
        """
        if not isinstance(nombre, str) or not nombre.lower().endswith(Archivos.EXTENSIONES_IMAGEN):
            return False
        return (datos[:3] == b"\xff\xd8\xff" or datos[:8] == b"\x89PNG\r\n\x1a\n"
                or datos[:6] in (b"GIF87a", b"GIF89a") or (datos[:4] == b"RIFF" and datos[8:12] == b"WEBP"))

    @staticmethod
    def GrabarBloque(ruta, bloque, flag, maxBloque=100 * 1024):
        """Escribe un bloque con el indicador de appDemo13: `I` = primer bloque (reemplaza el archivo), `P` = anexa.

        Devuelve "OK" o "Error - motivo", el formato de respuesta de los demos. `P` sin archivo previo
        se rechaza: el demo lo aceptaba y creaba un archivo incompleto.
        """
        if flag not in ("I", "P"):
            return "Error - Indicador no válido"
        if len(bloque) > maxBloque:
            return "Error - Bloque demasiado grande"
        if flag == "I":
            if os.path.isfile(ruta):
                os.remove(ruta)
        elif not os.path.isfile(ruta):
            return "Error - Falta el primer bloque"
        with open(ruta, "ab") as archivo:
            archivo.write(bloque)
        return "OK"

    @staticmethod
    def LeerBloque(ruta, indice, sizeBloque=100 * 1024):
        """Lee SOLO el bloque `indice` (base 0) de un archivo: es el inverso de GrabarBloque (el servidor envía por trozos).

        Devuelve los bytes (hasta `sizeBloque`; el último bloque puede ser menor) o None si `ruta` no es un archivo, el
        índice no es un entero >= 0 o está fuera de rango. Un archivo vacío tiene un único bloque 0 de 0 bytes. No carga el
        archivo completo en memoria y es idempotente: pedir el mismo índice dos veces devuelve lo mismo (reintentar es seguro).
        """
        if isinstance(indice, bool) or not isinstance(indice, int) or indice < 0 or sizeBloque <= 0 or not os.path.isfile(ruta):
            return None
        size = os.path.getsize(ruta)
        inicio = indice * sizeBloque
        if inicio >= size and not (indice == 0 and size == 0):
            return None
        with open(ruta, "rb") as archivo:
            archivo.seek(inicio)
            return archivo.read(sizeBloque)

    @staticmethod
    def Listar(rutaCarpeta, cabecera="Nombre del Archivo|Size;600|100;str|int"):
        """Lista `nombre|size;...` con las tres filas de metadatos que espera Gui.Grilla (ListarArchivos de appDemo13)."""
        if not os.path.isdir(rutaCarpeta):
            return ""
        filas = []
        for nombre in sorted(os.listdir(rutaCarpeta)):
            ruta = os.path.join(rutaCarpeta, nombre)
            if os.path.isfile(ruta):
                filas.append(nombre + SEP_CAMPO + str(os.path.getsize(ruta)))
        return cabecera + SEP_REG + SEP_REG.join(filas) if filas else ""
