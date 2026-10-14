"""Vistas de registros por viajes (appDemo26_2 y appDemo28), con tu cliente SQL (`clienteSQL(config, log)`).

    ContarRegistros          -> escalar con el total (uspCubsoContar)
    ObtenerBloqueRegistros   -> un bloque `;id|codigo|descripcion|precio;...` (uspCubsoPaginarCsvPy)
    ValidarTablaCampos       -> "" si la tabla y las columnas coinciden, o "Error - ..."
    GrabarBloqueRegistros    -> inserta un viaje de registros: "OK" o "Error: ..."

Requiere en settings: LD_DB_CONFIG_PATH y LD_DB_LOG_PATH. Los demos arman `Insert Into <tabla> (<campos>)`
con el nombre de tabla y de columnas que envía el cliente: sin lista permitida, eso es inyección de SQL.
TABLAS_PERMITIDAS es ese filtro.
"""
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_GET, require_POST

from Modulos.modAccesoDatos import clienteSQL

TABLAS_PERMITIDAS = {"Cubso": ("CubsoId", "Codigo", "Descripcion", "Precio")}   # tabla -> columnas aceptadas
MAX_REGISTROS_BLOQUE = 20000
MAX_REGISTROS_VIAJE = 5000


def _cliente():
    return clienteSQL(str(settings.LD_DB_CONFIG_PATH), str(settings.LD_DB_LOG_PATH))


def _entero(texto, minimo, maximo):
    return int(texto) if texto.isdigit() and minimo <= int(texto) <= maximo else None


@require_GET
def ContarRegistros(request):
    return HttpResponse(_cliente().EjecutarComandoCadena("uspCubsoContar"))


@require_GET
def ObtenerBloqueRegistros(request):
    indice = _entero(request.GET.get("indice", ""), 1, 10**9)
    registros = _entero(request.GET.get("registros", ""), 1, MAX_REGISTROS_BLOQUE)
    if indice is None or registros is None:      # uspCubsoPaginarCsvPy falla con página 0 o datos mal formados
        return HttpResponse("")
    data = _cliente().EjecutarComandoCadena("uspCubsoPaginarCsvPy", "data", "%d|%d" % (indice, registros))
    return HttpResponse(data or "")


@require_POST
def ValidarTablaCampos(request):
    tabla = request.POST.get("tabla", "")
    campos = request.POST.get("campos", "").split(",")
    if tabla not in TABLAS_PERMITIDAS or any(c not in TABLAS_PERMITIDAS[tabla] for c in campos):
        return HttpResponse("Error - Tabla o columnas no permitidas")
    return HttpResponse(_cliente().ValidarTablaCampos(tabla, campos))


@require_POST
def GrabarBloqueRegistros(request):
    tabla = request.POST.get("tabla", "")
    data = request.POST.get("data", "")
    filas = data.split(";")
    if tabla not in TABLAS_PERMITIDAS or len(filas) < 2 or len(filas) - 1 > MAX_REGISTROS_VIAJE:
        return HttpResponse("Error - Tabla no permitida o viaje vacío o demasiado grande")
    columnas = filas[0].split(",")
    if any(c not in TABLAS_PERMITIDAS[tabla] for c in columnas) or any(len(f.split(",")) != len(columnas) for f in filas[1:]):
        return HttpResponse("Error - Columnas no permitidas o registros mal formados")
    return HttpResponse(_cliente().EjecutarInsertMasivoCsv(tabla, data, ";", ","))
