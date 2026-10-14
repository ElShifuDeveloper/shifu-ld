---
name: ld-security-session
description: "Implementa y revisa login, sesión, captcha, cierre de sesión y auditoría en aplicaciones Django + JavaScript nativo del estilo LD: decoradores autenticacion/auditoria de modSeguridadWeb, validación con captcha y SHA-256, protección de endpoints, límite de intentos y configuración de cookies de sesión. Úsalo para pantallas con acceso restringido o al revisar la seguridad de una vista."
---

# LD_security_session

Seguridad de acceso del estilo base LD: sesión de Django con la clave `request.session["Usuario"]`, login con captcha y clave cifrada en el navegador, y decoradores de `Modulos/modSeguridadWeb.py`. Basado en `appDemo14` de `webpython`.

Entrada del paquete: [ld-project-coordinator](../ld-project-coordinator/SKILL.md). Para pantallas CRUD usa [ld-crud](../ld-crud/SKILL.md); para SPs y `clienteSQL`, [ld-data](../ld-data/SKILL.md).

## Piezas del proyecto

| Pieza | Función |
|---|---|
| `Modulos/modSeguridadWeb.py` | Decoradores `autenticacion(sesion, loginHtml)` y `auditoria(archivo, sesion)`. Ver [la versión corregida](./examples/modSeguridadWeb.py). |
| `Modulos/modGraficos.py` | `Captcha.Crear(n, ancho, alto, sizeFuente, colorFondo, nLineas)`: devuelve `{"Codigo", "Imagen"}` (PNG). Usa la fuente `arial.ttf`, que existe en Windows pero no en Linux/macOS: configura una ruta de fuente en esos sistemas. |
| `Static/scripts/sha256.js` | `CryptoJS.SHA256(clave)` en el navegador. |
| `Login.html` / `Login.js` | Usuario, clave, imagen de captcha y código; envía `Usuario`, `Clave` (SHA-256 hex), `Codigo` y CSRF a `ValidarLogin`. |
| SP `uspUsuarioValidarLoginCsv` | Recibe `usuario\|clave` y devuelve los datos del cliente o ninguna fila; su forma y sus riesgos (`NULL` en la concatenación, entrada sin separador) están en el [análisis](../ld-data/references/stored-procedures-review.md). |

Flujo: `Login` (HTML) → `CrearCaptcha` (imagen; guarda el código en sesión) → `ValidarLogin` (POST) → si todo es válido, `request.session["Usuario"] = usuario` y el JS redirige a la pantalla protegida.

## Reglas de implementación

Ejemplo completo: [views_login.py](./examples/views_login.py).

1. **Protege cada vista y cada endpoint**, no solo las pantallas HTML. En `appDemo14`, `Productos` y `Detalles` llevan `@autenticacion`, pero `ListarCodigos`, `ObtenerImagenes`, `ObtenerStockProductoPorId` y `GrabarOrden` no: cualquiera con la URL podía consultarlos o grabar una orden sin sesión. Pon `@autenticacion` en todo lo que no sea el login. Para los que consume `fetch` usa `codigoEstado=401`, así el JS detecta la sesión caducada.
2. **Orden de los decoradores**: `@autenticacion` primero (el más externo), luego `@auditoria`, y la validación de método (`@require_POST`) al final. Así se audita cada solicitud autenticada y no se ejecuta nada si falta sesión.
3. **Captcha de un solo uso**: léelo con `request.session.pop("Codigo", "")` y compáralo con `hmac.compare_digest` sin distinguir mayúsculas. Si falta, es un error de captcha y no una excepción (`request.session["Codigo"]` lanza `KeyError` y devuelve 500).
4. **Mensaje único** para usuario inexistente y clave incorrecta, para no revelar cuentas válidas.
5. **Rota la sesión al autenticar** (`request.session.cycle_key()`) y ofrece una vista de salida con `request.session.flush()`.
6. **Límite de intentos** por IP y usuario guardado en la caché del servidor (`django.core.cache`), no en la sesión. Si hay varios procesos, usa una caché compartida.
7. **Validación de entrada**: el SP recibe `usuario|clave`; rechaza `|` en ambos campos, longitud máxima y vacíos antes de llamar al SP.
8. **Errores de BD**: `EjecutarComandoCadena` devuelve `None` si falló la consulta y `""` si no hubo fila (login inválido). Responde `502` ante `None`: un fallo de la base no es un "login inválido" y no debe sumar intentos.
9. **Auditoría**: un archivo por aplicación, con ruta en `settings` (`LD_AUDIT_LOG_PATH`), sin rutas personales. La IP sale de `REMOTE_ADDR`; usa `confiarProxy=True` solo detrás de un proxy propio que reescriba `X-Forwarded-For`. No registres claves ni el cuerpo de las solicitudes.

## Configuración de sesión

`webpython/settings.py` usa `SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"`. Esa configuración tiene dos consecuencias:

- **El contenido de la sesión viaja en la cookie**: está firmado pero no cifrado, así que cualquiera puede decodificarlo. El código del captcha queda legible para un script, y el captcha pierde su función. Un bot puede leer la cookie de `CrearCaptcha` y obtener la respuesta.
- **El servidor no puede invalidar una sesión**: `flush()` borra la cookie del navegador, pero una cookie copiada sigue siendo válida hasta que caduca.

Para cualquier aplicación con login, usa sesiones en servidor:

```python
SESSION_ENGINE = "django.contrib.sessions.backends.db"   # o cache / cached_db
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = True       # con HTTPS
CSRF_COOKIE_SECURE = True          # con HTTPS
SESSION_COOKIE_AGE = 60 * 60 * 8   # ajusta a la política de la aplicación
```

`signed_cookies` solo es aceptable en demos sin datos sensibles. Si un proyecto existente lo usa, di en la respuesta que el captcha y la sesión quedan débiles y propón el cambio; no lo cambies sin avisar, porque invalida las sesiones activas y puede requerir `python manage.py migrate`.

## Clave cifrada en el navegador

`CryptoJS.SHA256(clave)` evita enviar la clave en texto plano, pero **no la protege**: el hash pasa a ser la clave real para quien lo capture, y es lo que se compara en el SP (`Clave = @Clave`). Es decir, la columna `Clave` contendría el SHA-256 sin sal (verifica los datos reales); un volcado de la tabla permite autenticarse sin conocer las claves. Por eso:

- Sirve la aplicación solo por HTTPS; el hash en el cliente no sustituye al canal cifrado.
- Si puedes cambiar el almacenamiento, guarda en la base un hash lento con sal (PBKDF2, bcrypt o Argon2) calculado en el servidor sobre lo que recibe. Eso exige cambiar el SP y los datos de usuarios: no lo hagas sin autorización explícita para ese objeto y entorno (`ld-data`).
- No registres `Clave` en logs ni en la auditoría.

## Código del cliente

- `sessionStorage.setItem("Usuario", ...)` en el navegador solo sirve para mostrar el nombre; **no es una prueba de autenticación**. La autoridad es la sesión del servidor.
- Antes de enviar, valida con `Validacion.ValidarDatos("R", "N", spnValida)`; trata `rpta == ""` como error del servidor y un texto que empieza con `Error` como error de dominio.
- Al recibir `401` en un `fetch`, limpia `sessionStorage` y redirige a `Login`.
- El captcha se pide con `fetch("CrearCaptcha")` y se muestra con `URL.createObjectURL(blob)`; revoca la URL anterior cuando pidas otro.

## Pruebas

Ver [test_modSeguridadWeb.py](./examples/test_modSeguridadWeb.py) (se ejecuta sin Django instalado). Casos mínimos para cada aplicación:

- Sin sesión, cada endpoint protegido devuelve el login o `401`; con sesión vacía también (no `None`/500).
- Con captcha incorrecto, repetido o ausente, el login falla sin excepción.
- Después de `MAX_INTENTOS` fallos, responde `429` aunque el captcha sea correcto.
- El mismo mensaje para usuario inexistente y clave errónea.
- Tras `Salir`, la sesión anterior ya no autentica.
- La auditoría escribe un registro por solicitud y un fallo de escritura no tumba la vista.

## Checklist

- ¿Todas las vistas y endpoints, excepto el login, llevan `@autenticacion`?
- ¿El captcha es de un solo uso y no se puede leer desde la cookie?
- ¿Hay límite de intentos del lado del servidor?
- ¿La sesión usa un backend del servidor y cookies `HttpOnly`/`Secure`?
- ¿Se rotó la sesión al autenticar y existe una salida?
- ¿La auditoría usa rutas de `settings` y no confía en `X-Forwarded-For` sin proxy?
- ¿El hash del cliente se trata como transporte y no como protección, con HTTPS?
