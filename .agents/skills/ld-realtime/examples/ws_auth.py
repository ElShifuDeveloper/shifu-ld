"""Token corto para autenticar la conexión WebSocket con la sesión de Django.

El navegador no puede enviar cabeceras personalizadas al abrir un WebSocket y el servidor ``websockets``
es un proceso aparte que no lee la sesión de Django. Flujo: el cliente (con sesión) pide un token a una
vista HTTP protegida y lo envía en la URL; el servidor lo verifica con el mismo secreto.
Sin dependencias; el secreto viene del entorno (LD_WS_SECRET), nunca del código.
"""
import base64
import hashlib
import hmac
import json
import time


def _b64(datos):
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode("ascii")


def _desde_b64(texto):
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def emitir_token(secreto, usuario, vigencia=60, ahora=None):
    """``secreto`` en bytes. Caduca en ``vigencia`` segundos (usa valores cortos: va en la URL)."""
    caduca = int((time.time() if ahora is None else ahora) + vigencia)
    carga = _b64(json.dumps({"u": usuario, "e": caduca}, separators=(",", ":")).encode("utf-8"))
    firma = _b64(hmac.new(secreto, carga.encode("ascii"), hashlib.sha256).digest())
    return f"{carga}.{firma}"


def verificar_token(secreto, token, ahora=None):
    """Devuelve el usuario o ``None`` si el token es inválido, está alterado o caducó."""
    try:
        carga, firma = token.split(".")
        esperada = _b64(hmac.new(secreto, carga.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(firma, esperada):
            return None
        datos = json.loads(_desde_b64(carga))
        if datos["e"] < (time.time() if ahora is None else ahora):
            return None
        usuario = datos["u"]
        return usuario if isinstance(usuario, str) and usuario else None
    except (ValueError, KeyError, TypeError, AttributeError, UnicodeError):
        return None
