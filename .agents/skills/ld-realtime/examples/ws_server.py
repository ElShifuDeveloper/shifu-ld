"""Servidor WebSocket endurecido (reemplaza ServidorWebSocket.py de los demos).

Diferencias con el demo: exige un token emitido por Django (ws_auth), restringe el ``Origin``,
limita el tamaño y la frecuencia de mensajes, valida cada mensaje como JSON (ws_messages), añade el
usuario autenticado, quita las conexiones al cerrarse (``finally``) y no escucha en todas las
interfaces por defecto.

Requiere ``websockets`` >= 14 (API ``websockets.asyncio.server``). Variables de entorno:
    LD_WS_SECRET     secreto compartido con Django (obligatorio)
    LD_WS_ORIGINS    orígenes permitidos separados por coma, p. ej. https://app.ejemplo.com
    LD_WS_HOST       por defecto 127.0.0.1 (detrás de un proxy con TLS); 0.0.0.0 solo si lo necesitas
    LD_WS_PORT       por defecto 9002

Producción: publícalo con ``wss://`` mediante un proxy inverso que termine TLS y reenvíe la
actualización a WebSocket; un servidor ``ws://`` no funciona desde una página ``https://`` (contenido mixto).
Un solo proceso: con varios procesos o servidores hace falta un bus (por ejemplo Redis) para difundir.
"""
import asyncio
import json
import logging
import os
from http import HTTPStatus
from urllib.parse import parse_qs, urlsplit

from websockets.asyncio.server import broadcast, serve
from websockets.exceptions import ConnectionClosed

from ws_auth import verificar_token
from ws_messages import LimiteTasa, MensajeInvalido, validar_mensaje

logger = logging.getLogger("ld.ws")
SECRETO = os.environ["LD_WS_SECRET"].encode("utf-8")
ORIGENES = [o.strip() for o in os.environ.get("LD_WS_ORIGINS", "").split(",") if o.strip()]
CONEXIONES = set()
MAX_CONEXIONES = 200


def autenticar(connection, request):
    """Se ejecuta antes del apretón de manos: devuelve una respuesta HTTP de error o ``None`` para aceptar."""
    token = parse_qs(urlsplit(request.path).query).get("token", [""])[0]
    usuario = verificar_token(SECRETO, token)
    if usuario is None:
        return connection.respond(HTTPStatus.UNAUTHORIZED, "token invalido o caducado\n")
    if len(CONEXIONES) >= MAX_CONEXIONES:
        return connection.respond(HTTPStatus.SERVICE_UNAVAILABLE, "servidor lleno\n")
    connection.usuario = usuario  # el controlador lo lee; el cliente no puede falsearlo
    return None


async def controlador(connection):
    usuario = connection.usuario
    limite = LimiteTasa(por_segundo=10, rafaga=20)
    CONEXIONES.add(connection)
    logger.info("conectado: %s (%d conexiones)", usuario, len(CONEXIONES))
    try:
        async for crudo in connection:
            if not limite.permitir():
                await connection.send(json.dumps({"type": "error", "code": "demasiados_mensajes"}))
                continue
            try:
                mensaje = validar_mensaje(crudo, usuario)
            except MensajeInvalido as error:
                await connection.send(json.dumps({"type": "error", "code": str(error)}))
                continue
            broadcast(CONEXIONES, json.dumps(mensaje))  # no registres el contenido: puede ser privado
    except ConnectionClosed:
        pass
    finally:
        CONEXIONES.discard(connection)
        logger.info("desconectado: %s", usuario)


async def main():
    logging.basicConfig(level=logging.INFO)
    if not ORIGENES:
        raise SystemExit("Define LD_WS_ORIGINS con los orígenes permitidos")
    host = os.environ.get("LD_WS_HOST", "127.0.0.1")
    puerto = int(os.environ.get("LD_WS_PORT", "9002"))
    async with serve(
        controlador, host, puerto,
        origins=ORIGENES,           # rechaza páginas de otros orígenes (CSWSH)
        process_request=autenticar,
        max_size=4096,              # bytes por mensaje; el valor por defecto es 1 MiB
        max_queue=16,
        ping_interval=20, ping_timeout=20,
    ) as servidor:
        logger.info("WebSocket escuchando en %s:%d", host, puerto)
        await servidor.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
