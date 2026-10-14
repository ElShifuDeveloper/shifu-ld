"""Login con captcha y sesión en el estilo base LD (versión endurecida de appDemo14).

Requiere en settings:
    LD_DB_CONFIG_PATH, LD_DB_LOG_PATH      (ver ld-crud)
    LD_AUDIT_LOG_PATH = BASE_DIR / "logs" / "auditoria.txt"
    SESSION_ENGINE = "django.contrib.sessions.backends.db"   # ver SKILL.md: no signed_cookies
    SESSION_COOKIE_HTTPONLY = True; SESSION_COOKIE_SECURE = True (con HTTPS)
    CACHES con un backend compartido si hay varios procesos (para el límite de intentos)

El SP uspUsuarioValidarLoginCsv y su formato de retorno son los del demo: verifícalos
en tu entorno (ld-data). No se modifican aquí.
"""
import hmac

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from Modulos.modAccesoDatos import clienteSQL
from Modulos.modGraficos import Captcha
from Modulos.modSeguridadWeb import auditoria, autenticacion

SESION = "Usuario"
LOGIN_HTML = "appDemo14/Login.html"
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 300


def _cliente():
    return clienteSQL(str(settings.LD_DB_CONFIG_PATH), str(settings.LD_DB_LOG_PATH))


def _clave_intentos(request, usuario):
    # Por IP y usuario. El contador vive en caché del servidor, no en la sesión:
    # con cookies el cliente podría borrarla y reiniciar el conteo.
    return "login:%s:%s" % (request.META.get("REMOTE_ADDR", ""), usuario.lower())


@require_GET
@auditoria(settings.LD_AUDIT_LOG_PATH, SESION)
def Login(request):
    return render(request, LOGIN_HTML, {"Ver": "1.0001"})


@require_GET
def CrearCaptcha(request):
    rpta = Captcha.Crear(5, 220, 80, 40, "aqua", 10)
    request.session["Codigo"] = rpta["Codigo"]
    respuesta = HttpResponse(rpta["Imagen"], content_type="image/png")
    respuesta["Cache-Control"] = "no-store"
    return respuesta


@require_POST
def ValidarLogin(request):
    usuario = request.POST.get("Usuario", "").strip()
    claveCifrada = request.POST.get("Clave", "")
    codigoEnviado = request.POST.get("Codigo", "").strip().upper()
    # Un captcha sirve una sola vez: se retira de la sesión haya o no coincidencia.
    codigoGenerado = request.session.pop("Codigo", "")

    # El SP recibe "usuario|clave": un "|" en el usuario cambiaría el significado.
    if not usuario or "|" in usuario or len(usuario) > 20 or not claveCifrada or "|" in claveCifrada:
        return HttpResponse("Error - Login invalido", status=400)

    clave = _clave_intentos(request, usuario)
    if cache.get(clave, 0) >= MAX_INTENTOS:
        return HttpResponse("Error - Demasiados intentos. Espera unos minutos", status=429)

    if not codigoGenerado or not hmac.compare_digest(codigoGenerado, codigoEnviado):
        return HttpResponse("Error - Codigo de captcha incorrecto")

    # clienteSQL.EjecutarComandoCadena devuelve None si falló la consulta y "" si no hubo fila (login
    # inválido): un fallo de la base de datos no debe contarse ni mostrarse como "login invalido".
    rpta = _cliente().EjecutarComandoCadena("uspUsuarioValidarLoginCsv", "Login", usuario + "|" + claveCifrada)
    if rpta is None:
        return HttpResponse("Error - No se pudo validar el acceso", status=502)
    if rpta == "":
        # Mismo mensaje para usuario inexistente y clave errónea (no revela cuál falló).
        cache.set(clave, cache.get(clave, 0) + 1, BLOQUEO_SEGUNDOS)
        return HttpResponse("Error - Login invalido")

    cache.delete(clave)
    request.session.cycle_key()  # nuevo identificador de sesión al autenticar
    request.session[SESION] = usuario
    return HttpResponse(rpta)


@require_POST
def Salir(request):
    request.session.flush()  # borra los datos y la cookie de sesión
    return HttpResponse("OK")


@autenticacion(SESION, LOGIN_HTML)
@auditoria(settings.LD_AUDIT_LOG_PATH, SESION)
def Categorias(request):
    return render(request, "appDemo14/Categorias.html", {"Ver": "1.0001"})


# Un endpoint que consume fetch devuelve 401 para que el JS detecte sesión caducada
# y redirija al login, en vez de recibir el HTML del login con 200.
@autenticacion(SESION, LOGIN_HTML, codigoEstado=401)
@auditoria(settings.LD_AUDIT_LOG_PATH, SESION)
@require_POST
def GrabarOrden(request):
    data = request.POST.get("Data", "")
    con = _cliente()
    return HttpResponse(con.EjecutarComandoCadena("uspOrdenGrabarPyCsv", "Data", data, trx=True))
