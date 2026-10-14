"""Servicios HTTP de solo lectura en CSV, JSON o XML (adaptados de servicio01-04).

Corrige los defectos de servicio04: con ``out`` ausente o con un producto inexistente la variable
``mime`` no se asignaba (UnboundLocalError, HTTP 500), y los formatos se armaban a mano. Aquí el
formato sale de una lista permitida, el id se valida y los errores devuelven códigos HTTP.

Requiere en settings: LD_DB_CONFIG_PATH y LD_DB_LOG_PATH (ver ld-crud). Las definiciones de
uspProductoListarCsv/uspProductoListar3Csv/uspProductoObtenerPorId3 están en SPs.
"""
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from Modulos.modAccesoDatos import clienteSQL

from .delimited_serializers import a_json, a_xml, registros_desde_delimitado

FORMATOS = {"csv": "text/plain; charset=utf-8", "json": "application/json", "xml": "application/xml"}


def _cliente():
    # clienteSQL.EjecutarComandoCadena devuelve None si falló la consulta y "" si no hay datos.
    return clienteSQL(str(settings.LD_DB_CONFIG_PATH), str(settings.LD_DB_LOG_PATH))


def _responder(texto, formato, raiz, elemento):
    if formato == "csv":
        return HttpResponse(texto, content_type=FORMATOS["csv"])
    try:
        registros = registros_desde_delimitado(texto, "|", "¬", filas_meta=1)
    except ValueError:
        return JsonResponse({"error": "respuesta_invalida"}, status=502)  # el SP devolvió un formato inesperado
    if formato == "json":
        return HttpResponse(a_json(registros), content_type=FORMATOS["json"])
    return HttpResponse(a_xml(registros, raiz, elemento), content_type=FORMATOS["xml"])


def _formato(request):
    formato = request.GET.get("out", "json")
    return formato if formato in FORMATOS else None


@require_GET
def ListarProductos(request):
    formato = _formato(request)
    if formato is None:
        return JsonResponse({"error": "out debe ser csv, json o xml"}, status=400)
    texto = _cliente().EjecutarComandoCadena("uspProductoListar3Csv")
    if texto is None:
        return JsonResponse({"error": "fallo_de_base_de_datos"}, status=502)
    if texto == "":
        return _responder("", formato, "Productos", "Producto") if formato == "csv" else JsonResponse([], safe=False)
    return _responder(texto, formato, "Productos", "Producto")


@require_GET
def ConsultarProducto(request):
    formato = _formato(request)
    id = request.GET.get("id", "")
    if formato is None or not id.isdigit():
        return JsonResponse({"error": "parametros_invalidos"}, status=400)
    texto = _cliente().EjecutarComandoCadena("uspProductoObtenerPorId3", "ProductID", id)
    if texto is None:
        return JsonResponse({"error": "fallo_de_base_de_datos"}, status=502)
    if texto == "":
        return JsonResponse({"error": "no_encontrado"}, status=404)
    return _responder(texto, formato, "Productos", "Producto")
