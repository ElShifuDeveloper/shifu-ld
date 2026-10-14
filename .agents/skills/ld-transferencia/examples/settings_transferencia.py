"""Bloque de settings.py con los límites de transferencia: UNA fuente para servidor y cliente.

Copia esto al settings.py del proyecto (o impórtalo). Qué es cada valor:
  LD_SIZE_LOTE    bytes máximos de datos de un lote: un archivo con size <= LD_SIZE_LOTE es «pequeño» y viaja agrupado con otros
                  en un solo paquete mientras la suma no lo supere.
  LD_SIZE_BLOQUE  bytes de cada bloque I/P cuando un archivo es mayor que LD_SIZE_LOTE y se corta en trozos.
  LD_MAX_ARCHIVOS_LOTE máximo de archivos por lote, tanto al subir como al descargar.
Las vistas usan estos valores como topes y las páginas se los pasan al navegador mediante campos ocultos. Los valores por entorno
LD_SIZE_LOTE, LD_SIZE_BLOQUE y LD_MAX_ARCHIVOS_LOTE configuran ambos lados desde esta única fuente.

Valores por defecto: lote de 512 KB, bloque de 256 KB y hasta 200 archivos por lote. El número de archivos configurable admite 1 a
10 000; este techo protege frente a manifiestos excesivos. Con 12 fotos de 1,25 MB bastan 4 viajes; con 100 KB de los demos eran 16.
Para estimar las llamadas de una tanda: 2 (CrearCarpeta y cierre) + lotes + bloques; consulta `Paquete.PlanificarViajes(...).length` en el cliente.

NOTA: `DATA_UPLOAD_MAX_MEMORY_SIZE` de Django NO limita los archivos subidos (solo cuenta los campos de texto del formulario) y
`FILE_UPLOAD_MAX_MEMORY_SIZE` solo decide si el archivo se guarda en memoria o en un temporal. El tope real de un envío son estos
valores (que las vistas comprueban) y, en producción, el límite de cuerpo del proxy (nginx `client_max_body_size`, IIS `maxAllowedContentLength`):
déjalo por encima de max(LD_SIZE_LOTE, LD_SIZE_BLOQUE) más la sobrecarga multipart.
"""
import os


def LeerEntero(nombre, defecto, minimo=1024, maximo=64 * 1024 * 1024, entorno=None, unidad="bytes"):
    """Lee un entero positivo de la variable de entorno `nombre` (o `defecto`) y falla al arrancar si no es válido."""
    entorno = os.environ if entorno is None else entorno
    texto = entorno.get(nombre)
    if texto is None or str(texto).strip() == "":
        valor = defecto
    else:
        try:
            valor = int(str(texto).strip())
        except ValueError:
            raise ValueError(f"{nombre} debe ser un número entero, no «{texto}»")
    if not (minimo <= valor <= maximo):
        raise ValueError(f"{nombre} debe estar entre {minimo} y {maximo} {unidad}; vale {valor}")
    return valor


LD_SIZE_LOTE = LeerEntero("LD_SIZE_LOTE", 512 * 1024)
LD_SIZE_BLOQUE = LeerEntero("LD_SIZE_BLOQUE", 256 * 1024)
LD_MAX_ARCHIVOS_LOTE = LeerEntero("LD_MAX_ARCHIVOS_LOTE", 200, minimo=1, maximo=10_000, unidad="archivos")
# Opcional, solo si la especificación pide un tope por archivo (bytes). Sin él, los archivos no tienen límite de usuario.
# LD_MAX_ARCHIVO = 50 * 1024 * 1024
