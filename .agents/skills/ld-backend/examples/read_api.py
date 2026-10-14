"""API de Django con proveedores para paginar texto/metadatos y descargar archivos binarios.

El proyecto debe proporcionar las funciones para consultar registros, paginar
el catálogo y entregar contenido autorizado; los demos de referencia no
incluyen un esquema común de registros ni un catálogo de archivos.
"""

import re
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils.module_loading import import_string
from django.views.decorators.http import require_GET

from .binary_framing import encode_ldp1_page
from .transfer_api import _authenticated_json

MAX_PAGE_SIZE = 500
RANGE_HEADER = re.compile(r"^bytes=(\d*)-(\d*)$")


def _provider(setting_name):
    provider_path = getattr(settings, setting_name, "")
    if not provider_path:
        raise ImproperlyConfigured(f"Configura {setting_name} con un proveedor autorizado")
    return import_string(provider_path)


def _page_parameters(request):
    try:
        limit = int(request.GET.get("limit", "100"))
    except ValueError:
        return None, None, JsonResponse({"error": "limit debe ser un entero"}, status=400)
    if not 1 <= limit <= MAX_PAGE_SIZE:
        return None, None, JsonResponse(
            {"error": f"limit debe estar entre 1 y {MAX_PAGE_SIZE}"}, status=400
        )
    cursor = request.GET.get("cursor") or None
    return limit, cursor, None


def _page_response(page):
    if not isinstance(page, dict):
        raise TypeError("El proveedor de páginas debe devolver un diccionario")
    if not isinstance(page.get("items"), list):
        raise TypeError("El proveedor de páginas debe devolver una lista items")
    if not isinstance(page.get("has_more"), bool):
        raise TypeError("El proveedor de páginas debe devolver has_more de tipo booleano")
    next_cursor = page.get("next_cursor")
    if page["has_more"] and not isinstance(next_cursor, str):
        raise ValueError("Una página con más resultados debe incluir next_cursor de tipo texto")
    if not page["has_more"]:
        next_cursor = None
    return JsonResponse({
        "items": page["items"],
        "next_cursor": next_cursor,
        "has_more": page["has_more"],
    })


@require_GET
@_authenticated_json
def page_records(request):
    """Devuelve una página JSON UTF-8 acotada del proveedor de registros configurado."""
    limit, cursor, error = _page_parameters(request)
    if error:
        return error
    try:
        page = _provider("LD_RECORD_PAGE_PROVIDER")(request, limit, cursor)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return _page_response(page)


@require_GET
@_authenticated_json
def page_files(request):
    """Devuelve una página JSON acotada y autorizada con los metadatos de archivos."""
    limit, cursor, error = _page_parameters(request)
    if error:
        return error
    page = _provider("LD_FILE_PAGE_PROVIDER")(request, limit, cursor)
    return _page_response(page)


@require_GET
@_authenticated_json
def page_mixed_binary(request):
    """Devuelve una página LDP1 acotada del proveedor autorizado configurado."""
    limit, cursor, error = _page_parameters(request)
    if error:
        return error
    page = _provider("LD_MIXED_PAGE_PROVIDER")(request, limit, cursor)
    if not isinstance(page, dict) or not isinstance(page.get("manifest"), dict):
        raise TypeError("El proveedor de páginas mixtas debe devolver un manifiesto en un diccionario")
    manifest = page["manifest"]
    if not isinstance(manifest.get("has_more"), bool):
        raise TypeError("El manifiesto mixto debe incluir has_more de tipo booleano")
    next_cursor = manifest.get("next_cursor")
    if manifest["has_more"] and not isinstance(next_cursor, str):
        raise ValueError("Una página mixta con más resultados debe incluir next_cursor")
    if not manifest["has_more"]:
        manifest["next_cursor"] = None

    frame = encode_ldp1_page(manifest, page.get("payloads", ()))
    return HttpResponse(frame, content_type="application/vnd.ld-page-v1")


def _not_satisfiable(size):
    response = HttpResponse(status=416)
    response["Content-Range"] = f"bytes */{size}"
    response["Accept-Ranges"] = "bytes"
    return response


@require_GET
@_authenticated_json
def file_content(request, file_id):
    """Transmite un archivo autorizado y admite un rango de bytes según el formato RFC."""
    descriptor = _provider("LD_FILE_CONTENT_PROVIDER")(request, file_id)
    if descriptor is None:
        return JsonResponse({"error": "archivo no encontrado"}, status=404)
    file_object = descriptor.get("file")
    filename = descriptor.get("name")
    media_type = descriptor.get("content_type", "application/octet-stream")
    size = descriptor.get("size")
    if (
        file_object is None
        or not isinstance(filename, str)
        or type(size) is not int
        or size < 0
    ):
        raise TypeError("El proveedor debe devolver file, name y size no negativo")

    range_value = request.headers.get("Range")
    if not range_value:
        response = FileResponse(
            file_object,
            as_attachment=True,
            filename=filename,
            content_type=media_type,
        )
        response["Accept-Ranges"] = "bytes"
        return response

    match = RANGE_HEADER.fullmatch(range_value)
    if match is None or "," in range_value or size == 0:
        file_object.close()
        return _not_satisfiable(size)
    first, last = match.groups()
    if not first and not last:
        file_object.close()
        return _not_satisfiable(size)
    if first:
        start = int(first)
        end = min(int(last), size - 1) if last else size - 1
    else:
        suffix_length = int(last)
        if suffix_length <= 0:
            file_object.close()
            return _not_satisfiable(size)
        start = max(size - suffix_length, 0)
        end = size - 1
    if start >= size or end < start:
        file_object.close()
        return _not_satisfiable(size)

    file_object.seek(start)
    remaining = end - start + 1

    def stream_range():
        nonlocal remaining
        try:
            while remaining:
                block = file_object.read(min(64 * 1024, remaining))
                if not block:
                    break
                remaining -= len(block)
                yield block
        finally:
            file_object.close()

    response = StreamingHttpResponse(stream_range(), status=206, content_type=media_type)
    response["Content-Range"] = f"bytes {start}-{end}/{size}"
    response["Accept-Ranges"] = "bytes"
    response["Content-Length"] = str(end - start + 1)
    response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename, safe='')}"
    return response
