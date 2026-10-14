import logging
from datetime import datetime
from functools import wraps

from django.shortcuts import render

logger = logging.getLogger(__name__)


def _limpiar(texto):
    # Evita inyectar líneas falsas en el archivo de auditoría.
    return str(texto).replace("\r", " ").replace("\n", " ")


def autenticacion(nombreSesionLogin, urlVistaLogin, codigoEstado=200):
    """Exige que request.session[nombreSesionLogin] exista y no esté vacío.

    Si no hay sesión válida muestra la vista de login (HTTP 200 por defecto, para
    no romper la navegación existente). Usa codigoEstado=401 en endpoints que
    consume fetch para que el JavaScript detecte la sesión caducada.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrap(request, *args, **kwargs):
            if request.session.get(nombreSesionLogin, ""):
                return view_func(request, *args, **kwargs)
            return render(request, urlVistaLogin, status=codigoEstado)
        return wrap
    return decorator


def auditoria(archivoAuditoria, nombreSesionLogin, confiarProxy=False):
    """Registra fecha, usuario, ruta, IP y método de cada solicitud.

    confiarProxy=True toma la IP de X-Forwarded-For; actívalo solo detrás de un
    proxy propio que sobrescriba ese encabezado, porque un cliente puede falsearlo.
    Un fallo al escribir la auditoría se registra con logging y no cae la vista.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrap(request, *args, **kwargs):
            usuario = request.session.get(nombreSesionLogin, "")
            ip = request.META.get("REMOTE_ADDR", "")
            if confiarProxy:
                ips = request.META.get("HTTP_X_FORWARDED_FOR")
                if ips:
                    ip = ips.split(",")[0].strip()
            registro = (
                "Fecha y Hora: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n"
                "Usuario: " + _limpiar(usuario) + "\n"
                "Ruta: " + _limpiar(request.path) + "\n"
                "IP Cliente: " + _limpiar(ip) + "\n"
                "Metodo Http: " + _limpiar(request.method) + "\n"
                "________________________________________\n"
            )
            try:
                with open(archivoAuditoria, "a", encoding="utf-8") as archivo:
                    archivo.write(registro)
            except OSError:
                logger.exception("No se pudo escribir la auditoria en %s", archivoAuditoria)
            return view_func(request, *args, **kwargs)
        return wrap
    return decorator
