---
name: ld-backend
description: "Diseña e implementa el servidor Django/Python del estilo LD: vistas con clienteSQL que responden cadenas delimitadas o bytes, autorización, CSRF, errores y límites. Para subir o bajar archivos y mover volúmenes de datos usa ld-transferencia; este skill cubre además el protocolo alternativo JSON/cursor para integraciones con terceros (consultas paginadas, catálogo de archivos, páginas mixtas LDP1, cargas por bloques con sesión)."
---

# LD_backend

Implementa el servidor como autoridad del contrato y de la validación. Antes de modificar puntos de acceso HTTP, inspecciona rutas, vistas, módulos de datos, configuración, almacenamiento y pruebas, y conserva el contrato de los clientes existentes o planifica una migración coordinada con el frontend. Entrada del paquete: [ld-project-coordinator](../ld-project-coordinator/SKILL.md).

## Estilo base LD

Las vistas son funciones PascalCase (`ObtenerListas`, `GrabarProducto`) que crean `clienteSQL`, ejecutan un procedimiento almacenado y devuelven `HttpResponse(texto)` con la cadena del SP (`...Csv`, `...PyCsv`: registros con `;` o `¬`, campos con `|`, listas con `_`) o bytes (`application/octet-stream`). Éxito de escritura `OK`, error de dominio `Error - ...`, sin datos cadena vacía. **No conviertas a JSON** lo que el cliente ya consume con `split`.

## Qué leer según la tarea

| Tarea | Lee |
|---|---|
| Subir o bajar archivos o imágenes, bloques, lotes, paquetes de bytes, consultas y cargas masivas por viajes | [ld-transferencia](../ld-transferencia/SKILL.md) |
| Vista que consulta o graba con un SP (`clienteSQL`) | [db-views.md](./references/db-views.md) |
| Pantalla CRUD completa | [ld-crud](../ld-crud/SKILL.md) |
| Qué devuelve cada SP, elegir método de `clienteSQL`, SP nuevo | [ld-data](../ld-data/SKILL.md) |
| Sesión, CSRF, auditoría | [ld-security-session](../ld-security-session/SKILL.md) |
| WebSocket y servicios en CSV/JSON/XML para terceros | [ld-realtime](../ld-realtime/SKILL.md) |
| **Alternativa para integraciones con terceros:** API JSON con cursor, catálogo de archivos, páginas LDP1, cargas por sesión | [transfer-contract.md](./references/transfer-contract.md), [read-endpoints.md](./references/read-endpoints.md), [uploads.md](./references/uploads.md) |

El protocolo JSON/cursor de las tres últimas referencias **no es el estilo base**: úsalo solo cuando un tercero lo exija o cuando la persona lo pida.

## Ejemplos (código adaptable, no módulos instalables)

| Archivo | Para qué |
|---|---|
| [django_views.py](./examples/django_views.py) | Consulta de stock y grabado de orden con `clienteSQL`, respuestas en texto |
| [read_api.py](./examples/read_api.py), [binary_framing.py](./examples/binary_framing.py), [cubso_records_provider.py](./examples/cubso_records_provider.py), [cubso_records_connection.py](./examples/cubso_records_connection.py) | Protocolo alternativo JSON/cursor/LDP1 |
| [transfer_api.py](./examples/transfer_api.py) | Alternativa: cargas por sesión autenticada con identificadores |
| [stream_csv.py](./examples/stream_csv.py) | Lectura incremental de un CSV en lotes |

## Procedimiento

1. Localiza rutas, vistas, repositorios de datos, almacenamiento y clientes que hacen las llamadas.
2. Define validación de método, autenticación, CSRF, permisos, campos obligatorios, máximos y formato **antes** de llamar a la capa de datos.
3. Para filas, pide al origen solo un bloque; para archivos, escribe y lee por bloques y no cargues todo en memoria sin necesidad (`FileResponse` para descargas grandes).
4. Nunca uses nombres o rutas del cliente como rutas de almacenamiento: `NombreSeguro`/`RutaSegura` de `modPaquetes.py`.
5. Responde con códigos HTTP adecuados: `4xx` para solicitudes inválidas, no autorizadas o fuera de límites; `5xx` para fallos del servidor (`clienteSQL` devuelve `None` cuando falla la consulta). El frontend debe distinguir error de red, HTTP y de dominio.
6. Registra contexto útil sin secretos ni datos privados, no devuelvas trazas ni rutas internas, y nunca informes éxito si no se guardó o verificó.
7. Prueba unidades, integración con almacenamiento, concurrencia y límites; añade pruebas de permisos y CSRF.

## Reglas que no cambian

- Valida el contenido real (firma de la imagen, no solo extensión, `content_type`, nombre o tamaño declarados) y ajusta los límites de Django, del proxy y del servidor WSGI al tamaño máximo más la sobrecarga del formulario.
- Escrituras por `POST` con CSRF (`{% csrf_token %}` y el token en cada `FormData`); no uses `csrf_exempt` para esquivarlo.
- Rutas y credenciales desde `settings` o el entorno, nunca del código.

## Checklist

- ¿La vista responde en el estilo LD (texto o bytes) y usa el cliente real de los demos?
- ¿Autenticación, CSRF y permisos se validan antes de tocar datos o archivos?
- ¿Hay límites de tamaño, de cantidad y de tiempo, y las rutas de almacenamiento las genera el servidor?
- ¿Las pruebas cubren permisos, límites y concurrencia?
