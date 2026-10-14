"""Vistas Django con clienteSQL en el estilo LD, adaptadas de appDemo14 (stock y grabado de una orden).

Las respuestas son texto, como en los demos: el stock como número y la orden grabada como `idOrden|fecha`.
Requiere en settings: LD_DB_CONFIG_PATH y LD_DB_LOG_PATH (el archivo de configuración de la base queda
fuera del repositorio). Usa el clienteSQL real de los demos (Modulos/modAccesoDatos.py): clienteSQL(config, log).

Cómo distingue ese cliente los casos (EjecutarComandoCadena):
    texto del SP     -> resultado correcto
    ""               -> el SP no devolvió filas, o devolvió NULL
    None             -> falló la consulta (queda en el log); la vista responde 502
"""
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_GET, require_POST

from Modulos.modAccesoDatos import clienteSQL

MAX_BYTES_ORDEN = 1024 * 1024   # protección del ejemplo; ajústala al contrato de órdenes


def _cliente():
    return clienteSQL(str(settings.LD_DB_CONFIG_PATH), str(settings.LD_DB_LOG_PATH))


@require_GET
def ObtenerStockProductoPorId(request):
    """uspProductoObtenerStockPorId aplica ISNULL(UnitsInStock, 0): un stock NULL llega como 0."""
    id = request.GET.get("id", "")
    if not id.isdigit() or int(id) <= 0:
        return HttpResponse("Error - id no válido", status=400)
    stock = _cliente().EjecutarComandoCadena("uspProductoObtenerStockPorId", "ProductID", id)
    if stock is None:
        return HttpResponse("", status=502)        # falló la base de datos
    if stock == "":
        return HttpResponse("", status=404)        # el producto no existe
    return HttpResponse(str(stock))


@require_POST
def GrabarOrden(request):
    """uspOrdenGrabarPyCsv abre y confirma su propia transacción; devuelve `idOrden|fecha`."""
    data = request.POST.get("Data", "")
    if not data or len(data.encode("utf-8")) > MAX_BYTES_ORDEN:
        return HttpResponse("Error - Data ausente o demasiado grande", status=400)
    rpta = _cliente().EjecutarComandoCadena("uspOrdenGrabarPyCsv", "Data", data, trx=True)
    if rpta is None or rpta == "":
        return HttpResponse("", status=502)
    return HttpResponse(rpta)
