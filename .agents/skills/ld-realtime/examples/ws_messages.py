"""Validación de mensajes WebSocket y límite de frecuencia. Sin dependencias: se prueba con unittest.

Los demos (wsDemo02/03) intercambian texto ``a|b|c`` y lo difunden tal cual. Aquí el servidor exige
JSON con un tipo conocido, valida cada campo y *añade* el usuario autenticado, en lugar de confiar
en el que envía el cliente.
"""
import json
import re
import time

MAX_BYTES_MENSAJE = 2048
MAX_TEXTO = 500
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


class MensajeInvalido(ValueError):
    """El mensaje no cumple el contrato; el texto es un código estable para el cliente."""


def validar_mensaje(crudo, usuario, ahora=None, lienzo=(1000, 600)):
    """Devuelve el diccionario a difundir. Acepta solo texto (``str``); rechaza bytes."""
    if not isinstance(crudo, str):
        raise MensajeInvalido("solo_texto")
    if len(crudo.encode("utf-8")) > MAX_BYTES_MENSAJE:
        raise MensajeInvalido("mensaje_demasiado_grande")
    try:
        datos = json.loads(crudo)
    except json.JSONDecodeError:
        raise MensajeInvalido("json_invalido") from None
    if not isinstance(datos, dict):
        raise MensajeInvalido("json_invalido")

    tipo = datos.get("type")
    base = {"type": tipo, "user": usuario, "sent_at": time.time() if ahora is None else ahora}
    if tipo == "chat.message":
        texto = datos.get("text")
        if not isinstance(texto, str) or not texto.strip() or len(texto) > MAX_TEXTO:
            raise MensajeInvalido("texto_invalido")
        return {**base, "text": texto.strip()}
    if tipo == "paint.point":
        x, y, color = datos.get("x"), datos.get("y"), datos.get("color")
        enteros = all(isinstance(v, int) and not isinstance(v, bool) for v in (x, y))
        if not enteros or not (0 <= x <= lienzo[0] and 0 <= y <= lienzo[1]):
            raise MensajeInvalido("punto_invalido")
        if not isinstance(color, str) or not COLOR.match(color):
            raise MensajeInvalido("color_invalido")
        return {**base, "x": x, "y": y, "color": color}
    raise MensajeInvalido("tipo_desconocido")


class LimiteTasa:
    """Cubo de fichas: ``por_segundo`` mensajes sostenidos y una ráfaga máxima de ``rafaga``."""

    def __init__(self, por_segundo=10, rafaga=20, reloj=time.monotonic):
        self.por_segundo, self.rafaga, self.reloj = por_segundo, rafaga, reloj
        self.fichas, self.ultimo = float(rafaga), reloj()

    def permitir(self):
        ahora = self.reloj()
        self.fichas = min(self.rafaga, self.fichas + (ahora - self.ultimo) * self.por_segundo)
        self.ultimo = ahora
        if self.fichas >= 1:
            self.fichas -= 1
            return True
        return False
