"""Vistas de mantenimiento en el estilo base LD (adaptadas de appDemo11).

Cada operación ejecuta un procedimiento almacenado con ``clienteSQL`` y devuelve
la cadena delimitada del SP. Requiere en settings:

    LD_DB_CONFIG_PATH = BASE_DIR / "config" / "Config_BD.txt"
    LD_DB_LOG_PATH = BASE_DIR / "logs" / "database.log"

Los nombres y contratos de los SP están verificados contra sus definiciones (ver
ld-data/references/stored-procedures-review.md): ListasCbo devuelve 3 secciones unidas
por "_"; ObtenerPorId2 devuelve "id|nombre|proveedor|categoria|precio|stock"; Grabar3 recibe
esos mismos 6 campos; Grabar3 y Eliminar3 devuelven "grilla_id".
"""
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from Modulos.modAccesoDatos import clienteSQL

VERSION = "1.0001"  # súbela al cambiar el JS o el CSS
SEPARADORES_RESERVADOS = ("¬", "|", "_")


def _cliente():
    return clienteSQL(str(settings.LD_DB_CONFIG_PATH), str(settings.LD_DB_LOG_PATH))


def _responder(data):
    # clienteSQL.EjecutarComandoCadena devuelve None cuando el SP falla y "" cuando el
    # resultado es NULL/ausente. HttpResponse(None) no produce una respuesta vacía, así
    # que un fallo se convierte aquí en un 500 explícito que el JS detecta con rptaHttp.ok.
    if data is None:
        return HttpResponse("", status=500)
    return HttpResponse(data)


@require_GET
def Mantenimiento(request):
    return render(request, "appDemo11/Mantenimiento.html", {"Ver": VERSION})


@require_GET
def ObtenerListas(request):
    # grilla_proveedores_categorias, cada parte con ¬ y |
    return _responder(_cliente().EjecutarComandoCadena("uspProductoListasCboCsv"))


@require_GET
def ObtenerProductoPorId(request):
    id = request.GET.get("id", "")
    if not id.isdigit():
        return HttpResponse("Error - id invalido", status=400)
    return _responder(_cliente().EjecutarComandoCadena("uspProductoObtenerPorId2", "ProductID", id))


@require_POST
def GrabarProducto(request):
    data = request.POST.get("Data", "")
    campos = data.split("|")
    # El SP espera exactamente 6 campos; los separadores no se escapan, así que ni "¬" ni "_"
    # pueden aparecer dentro de un valor, y "|" solo puede ser el separador de campos.
    if len(campos) != 6 or any(c in campo for campo in campos for c in ("¬", "_")):
        return HttpResponse("Error - datos invalidos", status=400)
    # Sin trx=True el wrapper no hace commit y los cambios se pierden al cerrar la conexión.
    data = _cliente().EjecutarComandoCadena("uspProductoGrabar3Csv", "Data", data, trx=True)
    return _responder(data)  # "grilla_id" = éxito; 500 = el SP falló


@require_POST
def EliminarProductoPorId(request):
    id = request.POST.get("id", "")
    if not id.isdigit():
        return HttpResponse("Error - id invalido", status=400)
    return _responder(_cliente().EjecutarComandoCadena("uspProductoEliminar3Csv", "ProductID", id, trx=True))
