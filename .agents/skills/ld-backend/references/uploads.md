# Recepción de cargas (lado servidor)

> **Protocolo alternativo (JSON, cursor, LDP1, sesión de carga).** No es el estilo base LD: sirve para integraciones con
> terceros o cuando la persona lo pide. Para subir y bajar archivos y mover volúmenes al estilo de los appDemo (cadenas y
> bytes, bloques `I`/`P`, lotes, paquetes, viajes) usa [ld-transferencia](../../ld-transferencia/SKILL.md).

El protocolo (sesión, partes, finalización, reintentos y códigos `409`) está en [transfer-contract.md](./transfer-contract.md). Aquí solo la configuración y las reglas del servidor.

El contrato actual se describe en [transfer-contract.md](./transfer-contract.md), con el cliente compartido en [transfer-workflows.js](../../ld-frontend/examples/transfer-workflows.js) y el adaptador para un solo archivo en [upload-chunks.js](../../ld-frontend/examples/upload-chunks.js). Ninguno de los ejemplos de referencia implementa el ciclo actual; `transfer_api.py` es el ejemplo portable para la recepción. No conectes su cliente a la vista heredada `GrabarImagen`.

Las rutas de referencia son:

```python
from django.urls import path
from . import transfer_api

urlpatterns = [
    path("api/uploads", transfer_api.start_upload, name="upload_start"),
    path(
        "api/uploads/<uuid:upload_id>/items/<uuid:item_id>/chunks/<int:index>",
        transfer_api.receive_chunk,
        name="upload_chunk",
    ),
    path(
        "api/uploads/<uuid:upload_id>/complete",
        transfer_api.complete_upload,
        name="upload_complete",
    ),
]
```

En `settings.py`, habilita la raíz de almacenamiento y, si cargas elementos `text`, indica la función de finalización de la aplicación:

```python
MEDIA_ROOT = BASE_DIR / "media"
LD_UPLOAD_COMPLETION_HANDLER = "miapp.transfer_handlers.process_completed_upload"
```

Adapta también los límites de Django, del proxy y del servidor web para que acepten el tamaño máximo de solicitud más la sobrecarga multipart.

El ejemplo limita cada bloque de datos a 100 KiB, cada elemento a 2 GiB, la carga total a 5 GiB y la cantidad de elementos a 100; admite elementos de cero bytes, que no generan solicitudes de fragmento. Ajusta esos valores junto con los límites del proxy y del servidor WSGI: multipart añade sobrecarga a los bytes enviados. Cada parte se escribe en un archivo temporal y se publica con un reemplazo atómico. El comportamiento ante reenvíos (`409` con `chunk_conflict` o `chunk_in_progress`, comparación SHA-256), los reintentos del cliente y la imposibilidad de reanudar tras recargar están en el [contrato](./transfer-contract.md); configura además la limpieza de temporales abandonados.

Si la carga incluye texto, configura `LD_UPLOAD_COMPLETION_HANDLER` con una función de la aplicación que tenga esta firma:

```python
def procesar_carga_completada(upload_id, owner_id, assembled_items):
    # assembled_items: lista de (metadata_item, ruta_temporal_completada)
    # Validar dominio y procesar los elementos de texto/CSV con la capa de datos.
    ...
```

El manejador [csv_upload_handler.py](../../ld-data/examples/csv_upload_handler.py) sirve específicamente para CSV; para otros tipos de texto, implementa una función de dominio que los interprete, sin asumir que todo texto es CSV. El manejador debe usar `upload_id` como clave de idempotencia: el proceso puede repetirse si falla después de guardar datos pero antes de registrar la finalización. Para garantizar atomicidad entre la base de datos y el sistema de archivos, implementa una transacción con patrón outbox o una compensación en la aplicación. Añade la caducidad y limpieza periódica de archivos temporales; el ejemplo no incluye una tarea de mantenimiento ni una ruta de cancelación.

En producción, verifica también MIME/bytes de firma, cuota por usuario, sumas de verificación si las requiere el contrato, antivirus/políticas documentales, límites de frecuencia y recuperación de bloqueos abandonados. Nunca uses nombres/rutas del cliente como rutas de almacenamiento.

## Subida pequeña por una sola solicitud

`request.FILES` entrega un archivo de Django. Para controlar el almacenamiento, usa `FileSystemStorage` o `default_storage`; para procesarlo incrementalmente, recorre sus fragmentos:

```python
for data in uploaded_file.chunks():
    destino.write(data)
```

Valida contenido real y límites; no confíes solo en extensión, `content_type`, nombre o tamaño declarados. Usa un nombre generado por servidor. Maneja excepciones con log seguro y código HTTP; no devuelvas stack trace ni ruta interna.

## Pruebas de cargas

Prueba fragmentos faltantes, tamaño superior al límite, índice duplicado o fuera de orden, solapamientos, cargas ajenas, vencimiento de espera, cancelación, temporales caducados, archivos de tamaño exacto y parcial, concurrencia y ensamblado idéntico byte por byte. Añade pruebas de permisos, CSRF y traversal de rutas.
