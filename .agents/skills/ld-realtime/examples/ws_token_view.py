"""Vista Django que entrega el token del WebSocket a un usuario con sesión.

settings.py:  LD_WS_SECRET = os.environ["LD_WS_SECRET"].encode()   # el mismo valor que usa ws_server.py
La autenticación de sesión es la de ld-security-session (``Usuario`` en request.session).
"""
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from Modulos.modSeguridadWeb import autenticacion

from .ws_auth import emitir_token


@autenticacion("Usuario", "appDemo14/Login.html", codigoEstado=401)
@require_POST
def ObtenerTokenWs(request):
    usuario = request.session["Usuario"]
    respuesta = JsonResponse({"token": emitir_token(settings.LD_WS_SECRET, usuario, vigencia=60)})
    respuesta["Cache-Control"] = "no-store"
    return respuesta
