---
name: ld-realtime
description: "Implementa servicios HTTP de solo lectura que publican datos de SP en CSV, JSON o XML, y comunicación en tiempo real con WebSocket (chat, dibujo compartido) en el estilo LD: servidor Python con `websockets`, cliente JavaScript nativo, autenticación por token de sesión, validación de mensajes y reconexión. Úsalo para servicios tipo servicio01–04 o para wsDemo02/03."
---

# LD_realtime

> Metodología **LD** (cadenas delimitadas, bytes, bloques, lotes y empaquetado) creada por **Luis Dueñas Huaroto**; documentada aquí para agentes.

Dos piezas que comparten un tema: exponer datos fuera de la pantalla CRUD.

1. **Servicios HTTP** (`servicio01`–`servicio04`): la misma consulta en CSV, JSON o XML.
2. **WebSocket** (`ServidorWebSocket.py`, `wsDemo02` chat, `wsDemo03` dibujo): mensajes en tiempo real entre navegadores.

Entrada del paquete: [ld-project-coordinator](../ld-project-coordinator/SKILL.md). La sesión y el login son de [ld-security-session](../ld-security-session/SKILL.md); los SP, de [ld-data](../ld-data/SKILL.md); el cliente WebSocket básico con JSON ya está en [websocket-chat.js](../ld-frontend/examples/websocket-chat.js).

## 1. Servicios HTTP en CSV, JSON y XML

Los demos devuelven el texto delimitado del SP (`servicio01`), o lo convierten con `JSON.SerializarCsv` y `XML.SerializarCsv` de `modUtilidades` (`servicio02`–`04`, con `out=csv|json|xml` en `servicio04`).

Ejemplos: [delimited_serializers.py](./examples/delimited_serializers.py), [services_views.py](./examples/services_views.py) y su prueba [test_delimited_serializers.py](./examples/test_delimited_serializers.py).

Defectos de los demos, comprobados en el código:

- **`servicio04` falla con HTTP 500** si `out` falta o si el producto no existe: la variable `mime` no se asigna en esos caminos y el `return` la usa (`UnboundLocalError`).
- **JSON inválido**: `JSON.SerializarCsv` concatena texto sin escapar. Una comilla, una barra invertida o un salto de línea en un nombre rompe el documento, y un código `"007"` se emite como el número `007`, que no es JSON. Usa `json.dumps` sobre diccionarios y convierte a número solo las columnas con tipo declarado (`int`/`float`).
- **XML frágil**: `XML.SerializarCsv` usa los nombres de columna como etiquetas (`Id Orden` no es una etiqueta válida) y no escapa los valores. Usa `ElementTree` y sanea los nombres.
- **Entidades XML del SP**: los SP con `FOR XML PATH('')` entregan `&` como `&amp;` (ver la sección 7 del [análisis](../ld-data/references/stored-procedures-review.md)); el serializador lo decodifica antes de emitir JSON.
- **Formato elegido por el cliente sin lista permitida** y el `id` sin validar: acepta solo `csv`, `json` o `xml` y un id entero.

Reglas para un servicio nuevo:

- Solo `GET` de lectura en estos ejemplos; las escrituras van con `POST`, CSRF y sesión (`ld-crud`, `ld-security-session`).
- Códigos HTTP claros: `400` entrada inválida, `404` sin datos, `502` si el SP devolvió un formato inesperado, `500` si falla la base. No uses `200` con un cuerpo vacío para todo.
- `clienteSQL` devuelve `None` si falló la consulta y `""` si no hay datos: responde `502` al primero y vacío o `404` al segundo.
- Un servicio público necesita decisión explícita sobre autenticación, límite de uso y CORS. No añadas `Access-Control-Allow-Origin: *` por comodidad.
- Documenta el contrato (campos, tipos, ejemplos) y no cambies nombres de campos de un servicio existente sin versionar la ruta.
- Estos servicios existen para terceros; las pantallas LD siguen consumiendo cadenas delimitadas (`ld-crud`).

## 2. WebSocket

### Arquitectura

`ServidorWebSocket.py` es **un proceso aparte** de Django (puerto 9002, biblioteca `websockets`); no pasa por las vistas, el middleware ni la sesión de Django. Por eso hay que resolver autenticación, origen y límites en el propio servidor. Alternativa integrada: Django Channels, que comparte la sesión; evalúala si el proyecto ya despliega ASGI.

Ejemplos: [ws_server.py](./examples/ws_server.py), [ws_messages.py](./examples/ws_messages.py), [ws_auth.py](./examples/ws_auth.py), [ws_token_view.py](./examples/ws_token_view.py), [realtime-client.js](./examples/realtime-client.js) y la prueba [test_realtime.py](./examples/test_realtime.py).

Flujo: el usuario, con sesión, pide un token a `ObtenerTokenWs` (POST, protegida); el cliente abre `wss://.../ws?token=...`; el servidor verifica firma y caducidad (60 s) antes del apretón de manos, comprueba el `Origin` y asigna el usuario a la conexión. Cada mensaje es JSON con un `type` conocido y el servidor **añade** el usuario y la hora.

### Problemas de los demos

- **Ejecución de código en los navegadores (XSS).** `wsDemo02/Chat.js` inserta el mensaje de otro usuario con `insertAdjacentHTML`, y el servidor reenvía cualquier texto a todos. Un mensaje como `<img src=x onerror=...>` se ejecuta en cada cliente conectado. Pinta con `textContent`.
- **Sin autenticación ni control de origen.** `serve(handler, "0.0.0.0", 9002)` acepta a cualquiera de la red y desde cualquier página web, incluidas conexiones iniciadas desde el navegador de una víctima en un sitio ajeno (secuestro de WebSocket entre sitios).
- **Suplantación.** El usuario viaja dentro del mensaje (`fecha|usuario|texto`), así que cualquiera puede escribir como otro.
- **Fuga de conexiones.** `clientes.remove(...)` solo se ejecuta si hay una excepción; un cierre normal deja la conexión en la lista. Añade y quita en `try/finally`.
- **Cierre por una carga vacía.** `mensaje[0]` con bytes vacíos lanza `IndexError`, que cae en el `except` y desconecta al cliente.
- **Sin límites.** Ni de frecuencia ni de conexiones; el tamaño es el valor por defecto de la biblioteca (1 MiB). En `wsDemo03` el cliente envía un mensaje por cada `mousemove`.
- **IP y esquema fijos.** `ws://172.20.10.2:9002` y `ws://190.43.83.241:9002` (una IP pública) no funcionan en otra red, y `ws://` está bloqueado desde una página `https://`. Deriva la URL de `location` y usa `wss://` con un proxy que termine TLS.
- **Difusión también a bytes**: el demo reenvía cualquier trama binaria. Acepta solo texto JSON; para archivos usa HTTP (`ld-backend`).
- **Dibujo (`wsDemo03`)**: la lógica de "dibujar" alterna con cada clic (`esModoDibujo = !esModoDibujo`), sin soltar el botón ni soporte táctil; usa eventos de puntero (`pointerdown`/`pointermove`/`pointerup`).
- **`broadcast` no es persistente**: quien se reconecta no recibe lo anterior. Si importa el historial, guárdalo (SP o tabla) y entrégalo por HTTP al conectar.

### Reglas

1. Exige sesión: token corto firmado y verificado en el servidor. El token va en la URL, así que mantenlo de vida corta y no lo registres en logs.
2. Valida el `Origin` con una lista permitida y rechaza el resto.
3. Valida cada mensaje: tipo, tamaño, campos y rangos (ver `validar_mensaje`); responde con un código de error estable y no con una traza.
4. Limita frecuencia, tamaño y número de conexiones.
5. Decide qué ve cada usuario: un `broadcast` global es solo para salas públicas. Para chats por grupo o privados, mantén salas y autoriza la unión.
6. Cliente: reconexión con retroceso exponencial, token nuevo en cada intento, `readyState` antes de enviar, y estado visible para el usuario.
7. Despliegue: proxy inverso con TLS, un proceso (o un bus como Redis para varios), y un supervisor que lo reinicie. Define cómo se detiene sin cortar a todos a la vez.

## Pruebas

- Las funciones puras (`validar_mensaje`, `LimiteTasa`, token, serializadores) se prueban con `python test_realtime.py` y `python test_delimited_serializers.py`, sin instalar nada.
- Prueba el servidor con un cliente real: token válido, caducado y alterado; `Origin` ajeno; mensaje inválido; ráfaga que supere el límite; cierre abrupto y reconexión; dos navegadores intercambiando mensajes; un mensaje con HTML que se vea como texto.
- Para los servicios: producto inexistente, `out` ausente y no válido, nombre con comillas/`&`/`<`, código con ceros a la izquierda, respuesta del SP vacía y fallo de base de datos.

## Checklist

- ¿Un servicio con formato variable usa lista permitida y devuelve códigos HTTP distintos para cada caso?
- ¿El JSON/XML se genera con bibliotecas y no por concatenación?
- ¿La conexión WebSocket exige token, comprueba el origen y asigna el usuario en el servidor?
- ¿Cada mensaje se valida y se limita, y se pinta con `textContent`?
- ¿Las conexiones se quitan al cerrarse y hay un tope?
- ¿La URL sale de `location` y se usa `wss://` en producción?
