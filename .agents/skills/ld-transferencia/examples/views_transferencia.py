"""Vistas de transferencia de archivos del estilo LD: carpetas, bloques I/P, lotes y paquetes de bytes.

Basadas en appDemo13 (GrabarBloque, ListarArchivos, ObtenerArchivo) y appDemo10 (ListarCodigosSizeImg,
paquete de bytes). Respuestas como en los demos: texto "OK" / "Error - motivo" o listas delimitadas por
`;` y `|` con las tres filas de metadatos de Gui.Grilla; los archivos viajan como bytes.

La descarga es SIMÉTRICA a la subida (misma regla de decisión, mismos tamaños de settings): los archivos de
LD_SIZE_LOTE o menos viajan agrupados en un paquete de bytes (ObtenerPaquete) y los mayores por bloques de
LD_SIZE_BLOQUE (ObtenerBloque, el inverso de GrabarBloque: usa Archivos.LeerBloque) que el cliente une con
new Blob(partes). ObtenerPaquete nunca omite archivos en silencio: lo que no cabe se rechaza con "Error - ...".

Requiere en settings (bloque completo en settings_transferencia.py):
    LD_REPOSITORIO_ROOT = BASE_DIR / "repositorio"      # carpeta raíz; nunca una ruta del cliente
    LD_SIZE_LOTE = 512 * 1024                           # datos máximos de un lote (archivos pequeños agrupados)
    LD_SIZE_BLOQUE = 256 * 1024                         # tamaño de cada bloque I/P de un archivo grande
    LD_MAX_ARCHIVOS_LOTE = 200                          # máximo de archivos por lote (subida y descarga)
Copia Modulos/modPaquetes.py (de ld-transferencia/examples) al proyecto.

Ajustes de seguridad sobre los demos: los nombres de carpeta y archivo pasan por Archivos.NombreSeguro /
RutaSegura (los demos usan la ruta que envía el cliente: `..\\..` escribiría fuera del repositorio), el contenido de
las imágenes se valida por firma, los límites técnicos del protocolo son MAX_BLOQUE y MAX_LOTE (el tamaño por archivo
y por tanda es ilimitado salvo que la especificación pida un tope) y las escrituras son POST con CSRF (middleware).
"""
import datetime
import os
import re

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from Modulos.modPaquetes import Archivos, Paquete

# Límites del protocolo: UNA sola fuente, settings.py (ver settings_transferencia.py). El servidor es la autoridad; las pantallas
# entregan los mismos límites al navegador para que el planificador de subida y descarga coincida.
MAX_BLOQUE = getattr(settings, "LD_SIZE_BLOQUE", 256 * 1024)
MAX_LOTE = getattr(settings, "LD_SIZE_LOTE", 512 * 1024)       # bytes de DATOS de un lote (sin la cabecera ni el texto del paquete)
MAX_ARCHIVOS_LOTE = settings.LD_MAX_ARCHIVOS_LOTE
MAX_TEXTO_PAQUETE = 65535                                       # la cabecera de 2 bytes admite hasta 65 535 bytes de texto
# Límite por archivo: ninguno por defecto. Solo si la especificación lo pide: settings.LD_MAX_ARCHIVO = <bytes>.
MAX_ARCHIVO = getattr(settings, "LD_MAX_ARCHIVO", None)
RE_CARPETA = re.compile(r"^[A-Za-z0-9_-]{1,60}$")


def _raiz():
    return str(settings.LD_REPOSITORIO_ROOT)


def _carpeta(nombre):
    """Ruta de una carpeta existente del repositorio, o None."""
    if not isinstance(nombre, str) or RE_CARPETA.match(nombre) is None:
        return None
    ruta = Archivos.RutaSegura(_raiz(), nombre)
    return ruta if ruta is not None and os.path.isdir(ruta) else None


@require_GET
def PantallaCarga(request):
    """Entrega al navegador los límites de lote y bloque configurados."""
    return render(request, "CargaArchivos.html", {
        "SizeLote": MAX_LOTE,
        "SizeBloque": MAX_BLOQUE,
        "MaxArchivosLote": MAX_ARCHIVOS_LOTE,
    })


@require_GET
def PantallaConsulta(request):
    """Entrega a la galería los límites de settings en campos ocultos, igual que PantallaCarga."""
    return render(request, "GaleriaCarpetas.html", {
        "SizeLote": MAX_LOTE,
        "SizeBloque": MAX_BLOQUE,
        "MaxArchivosLote": MAX_ARCHIVOS_LOTE,
    })


@require_POST
def CrearCarpeta(request):
    nombre = request.POST.get("Carpeta", "")
    if RE_CARPETA.match(nombre) is None:
        return HttpResponse("Error - Nombre de carpeta no válido")
    ruta = Archivos.RutaSegura(_raiz(), nombre)
    if ruta is None:
        return HttpResponse("Error - Nombre de carpeta no válido")
    os.makedirs(_raiz(), exist_ok=True)
    try:
        os.mkdir(ruta)                      # atómico: si dos personas eligen el mismo nombre, solo una lo crea
    except FileExistsError:
        return HttpResponse("Error - La carpeta ya existe")
    return HttpResponse("OK")


@require_POST
def GrabarBloque(request):
    """Un bloque de un archivo grande. Flag I = primer bloque (reemplaza), P = siguiente (anexa)."""
    ruta_carpeta = _carpeta(request.POST.get("Carpeta", ""))
    nombre = Archivos.NombreSeguro(request.POST.get("Nombre", ""))
    flag = request.POST.get("Flag", "")
    if ruta_carpeta is None or nombre is None:
        return HttpResponse("Error - Carpeta o nombre no válido")
    if "Blob" not in request.FILES:
        return HttpResponse("Error - No existe Archivo que grabar")
    bloque = request.FILES["Blob"].read()
    if flag == "I" and not Archivos.EsImagen(nombre, bloque[:16]):
        return HttpResponse("Error - El archivo no es una imagen válida")
    ruta = os.path.join(ruta_carpeta, nombre)
    rpta = Archivos.GrabarBloque(ruta, bloque, flag, MAX_BLOQUE)
    if rpta == "OK" and MAX_ARCHIVO and os.path.getsize(ruta) > MAX_ARCHIVO:
        os.remove(ruta)
        return HttpResponse("Error - El archivo supera el tamaño máximo")
    return HttpResponse(rpta)


@require_POST
def GrabarLote(request):
    """Un paquete de bytes con varios archivos pequeños: [2 bytes][nombre|size;...][bytes...] (ver Paquete)."""
    ruta_carpeta = _carpeta(request.POST.get("Carpeta", ""))
    if ruta_carpeta is None:
        return HttpResponse("Error - Carpeta no válida")
    # El paquete trae 2 bytes de cabecera y un texto (nombre|size;...) además de los datos: se acota con ese margen.
    if "Blob" not in request.FILES or request.FILES["Blob"].size > MAX_LOTE + 2 + MAX_TEXTO_PAQUETE:
        return HttpResponse("Error - Lote ausente o demasiado grande")
    try:
        registros, listaBytes = Paquete.Leer(request.FILES["Blob"].read())
    except ValueError as error:
        return HttpResponse("Error - Paquete no válido: " + str(error))
    if not registros or len(registros) > MAX_ARCHIVOS_LOTE:
        return HttpResponse("Error - El lote debe contener entre 1 y %d archivos" % MAX_ARCHIVOS_LOTE)
    if sum(len(d) for d in listaBytes) > MAX_LOTE:
        return HttpResponse("Error - El lote supera el tamaño máximo")
    # Se valida TODO antes de escribir: un lote se graba completo o no se graba
    destinos = []
    for campos, datos in zip(registros, listaBytes):
        nombre = Archivos.NombreSeguro(campos[0])
        if nombre is None or not Archivos.EsImagen(nombre, datos[:16]) or (MAX_ARCHIVO and len(datos) > MAX_ARCHIVO):
            return HttpResponse("Error - Archivo no válido: " + campos[0])
        ruta = os.path.join(ruta_carpeta, nombre)
        if os.path.exists(ruta) or any(ruta == d[0] for d in destinos):
            return HttpResponse("Error - Ya existe: " + nombre)
        destinos.append((ruta, datos))
    escritos = []
    try:
        for ruta, datos in destinos:
            with open(ruta, "wb") as archivo:
                archivo.write(datos)
            escritos.append(ruta)
    except OSError:
        for ruta in escritos:
            os.remove(ruta)
        return HttpResponse("Error - No se pudo guardar el lote")
    return HttpResponse("OK")


@require_GET
def ListarCarpetas(request):
    """`Carpeta|Imagenes|Fecha;...` con metadatos de Gui.Grilla; las más recientes primero."""
    raiz = _raiz()
    if not os.path.isdir(raiz):
        return HttpResponse("")
    filas = []
    for nombre in os.listdir(raiz):
        ruta = os.path.join(raiz, nombre)
        if os.path.isdir(ruta) and RE_CARPETA.match(nombre):
            n = sum(1 for f in os.listdir(ruta) if os.path.isfile(os.path.join(ruta, f)))
            filas.append((os.path.getmtime(ruta), "%s|%d|%s" % (
                nombre, n, datetime.datetime.fromtimestamp(os.path.getmtime(ruta)).strftime("%d/%m/%Y %H:%M"))))
    if not filas:
        return HttpResponse("")
    filas.sort(reverse=True)
    return HttpResponse("Carpeta|Imagenes|Fecha;300|100|150;str|int|str;" + ";".join(f[1] for f in filas))


@require_GET
def ListarArchivos(request):
    ruta = _carpeta(request.GET.get("Carpeta", ""))
    return HttpResponse(Archivos.Listar(ruta) if ruta else "")


@require_GET
def ListarCodigosSize(request):
    """`nombre|size;...` sin metadatos: lo consume el cliente para agrupar los viajes (appDemo10)."""
    ruta = _carpeta(request.GET.get("Carpeta", ""))
    if ruta is None:
        return HttpResponse("")
    filas = []
    for nombre in sorted(os.listdir(ruta)):
        archivo = os.path.join(ruta, nombre)
        if os.path.isfile(archivo):
            filas.append("%s|%d" % (nombre, os.path.getsize(archivo)))
    return HttpResponse(";".join(filas))


@require_POST
def ObtenerPaquete(request):
    """Devuelve UN paquete de bytes con los archivos pedidos (`Nombres` = a|b|c), como ObtenerDataConImagenes.

    Los datos del paquete están acotados por MAX_LOTE (settings.LD_SIZE_LOTE), igual que en la subida: el cliente
    planifica los viajes con ese límite, así que un lote que lo supere o que pida un archivo mayor es un pedido mal
    formado y se rechaza con "Error - ..." (texto). Nunca se omiten archivos en silencio: los demos cortaban la
    respuesta al pasar un tope y el cliente mostraba menos imágenes de las pedidas. Un archivo mayor que MAX_LOTE
    no cabe en un paquete: se pide por bloques (ObtenerBloque, técnica 2 de tecnicas.md).
    """
    ruta = _carpeta(request.POST.get("Carpeta", ""))
    pedidos = request.POST.get("Nombres", "").split("|")
    if ruta is None or not (0 < len(pedidos) <= MAX_ARCHIVOS_LOTE):
        return HttpResponse("Error - Carpeta o nombres no válidos")
    filas, listaBytes, total = [], [], 0
    for nombre in pedidos:
        seguro = Archivos.NombreSeguro(nombre)
        archivo = os.path.join(ruta, seguro) if seguro else None
        if archivo is None or not os.path.isfile(archivo):
            return HttpResponse("Error - Archivo no encontrado o nombre no válido: " + nombre)
        size = os.path.getsize(archivo)
        if size > MAX_LOTE:
            return HttpResponse("Error - %s no cabe en un lote: pídelo por bloques" % seguro)
        if total + size > MAX_LOTE:
            return HttpResponse("Error - El lote supera %d bytes: parte el pedido en más viajes" % MAX_LOTE)
        with open(archivo, "rb") as f:
            datos = f.read()
        total += len(datos)
        filas.append("%s|%d" % (seguro, len(datos)))
        listaBytes.append(datos)
    return HttpResponse(Paquete.Crear(";".join(filas), listaBytes), content_type="application/octet-stream")


@require_GET
def ObtenerBloque(request):
    """Un bloque de un archivo grande (inverso de GrabarBloque): GET con `Carpeta`, `Nombre` e `Indice` (base 0).

    Éxito: los bytes del bloque con application/octet-stream (el último puede ser menor que MAX_BLOQUE). Error:
    texto "Error - ..." (el cliente distingue por Content-Type). Archivos.LeerBloque no carga el archivo completo
    en memoria y es idempotente: reintentar el mismo índice devuelve los mismos bytes, así que un viaje fallido
    de la descarga se reenvía tal cual (a diferencia de un bloque P de la subida).
    """
    ruta = _carpeta(request.GET.get("Carpeta", ""))
    nombre = Archivos.NombreSeguro(request.GET.get("Nombre", ""))
    if ruta is None or nombre is None:
        return HttpResponse("Error - Carpeta o nombre no válido")
    try:
        indice = int(request.GET.get("Indice", ""))
    except ValueError:
        return HttpResponse("Error - Índice no válido")
    datos = Archivos.LeerBloque(os.path.join(ruta, nombre), indice, MAX_BLOQUE)
    if datos is None:
        return HttpResponse("Error - Bloque fuera de rango o archivo no encontrado")
    return HttpResponse(datos, content_type="application/octet-stream")


@require_GET
def ObtenerArchivo(request):
    """Un archivo completo para GUARDARLO EN EL DISCO del usuario: FileResponse lo lee del disco por trozos (no lo
    carga entero en memoria) y as_attachment hace que el navegador lo descargue con su nombre y muestre su propio
    progreso. Para mostrarlo o procesarlo DENTRO de la app, usa ObtenerBloque (técnica 7 de tecnicas.md)."""
    ruta = _carpeta(request.GET.get("Carpeta", ""))
    nombre = Archivos.NombreSeguro(request.GET.get("Nombre", ""))
    archivo = os.path.join(ruta, nombre) if ruta and nombre else None
    if archivo is None or not os.path.isfile(archivo):
        return HttpResponse("Error - Archivo no encontrado")
    return FileResponse(open(archivo, "rb"), as_attachment=True, filename=nombre,
                        content_type="application/octet-stream")
