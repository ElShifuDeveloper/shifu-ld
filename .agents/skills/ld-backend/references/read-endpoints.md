# Consultas paginadas y descargas

> **Protocolo alternativo (JSON, cursor, LDP1, sesión de carga).** No es el estilo base LD: sirve para integraciones con
> terceros o cuando la persona lo pide. Para subir y bajar archivos y mover volúmenes al estilo de los appDemo (cadenas y
> bytes, bloques `I`/`P`, lotes, paquetes, viajes) usa [ld-transferencia](../../ld-transferencia/SKILL.md).

Contrato en [transfer-contract.md](./transfer-contract.md) (casos 1–3).

El contrato de lectura común está en [transfer-contract.md](./transfer-contract.md). Conecta las vistas [read_api.py](../examples/read_api.py) en `urls.py`:

```python
from django.urls import path
from . import read_api

urlpatterns = [
    path("api/records", read_api.page_records),
    path("api/files", read_api.page_files),
    path("api/files/<str:file_id>/content", read_api.file_content),
    path("api/mixed", read_api.page_mixed_binary),
]
```

Configura `LD_RECORD_PAGE_PROVIDER`, `LD_FILE_PAGE_PROVIDER` y `LD_FILE_CONTENT_PROVIDER` con funciones de la aplicación. Las dos primeras reciben `(request, limit, cursor)` y devuelven `{"items": [...], "next_cursor": str | None, "has_more": bool}`; la última recibe `(request, file_id)` y devuelve `None` o `{"file": archivo_binario_abierto, "name": str, "content_type": str, "size": int}`. La función proveedora de archivos debe filtrar por usuario y permisos, y resolver el identificador mediante almacenamiento autorizado. Como los ejemplos no comparten un modelo ni un catálogo, implementa estas funciones usando el esquema real.

`read_api.py` transmite JSON UTF-8 para texto y un flujo binario separado para archivos. Acepta rangos simples `bytes=start-end`, `bytes=start-` y `bytes=-suffix`, devuelve `206`/`Content-Range` o `416`, y no acumula el archivo completo en memoria. Para respuestas que mezclan texto y bytes, usa el codificador limitado [binary_framing.py](../examples/binary_framing.py) solo con datos pequeños; corresponde al intérprete del frontend [parseLdp1](../../ld-frontend/examples/transfer-workflows.js). Los ejemplos no incluyen el servidor backend de appDemo107 ni un catálogo de archivos paginado.

Para el caso 3, configura, por ejemplo, `LD_MIXED_PAGE_PROVIDER = "miapp.providers.pagina_mixta"` y crea una función `(request, limit, cursor)` que devuelva `{"manifest": {"has_more": bool, "next_cursor": str | None, "payloads": [{"id": str, "size": int, ...}]}, "payloads": [bytes, ...]}`. La vista `page_mixed_binary` empaqueta una página LDP1 limitada a 16 MiB; la función proveedora debe autorizar cada dato y conservar el mismo orden entre identificadores y bytes.

## Descarga binaria y texto con bytes

Para archivos, usa `FileResponse` o un flujo `StreamingHttpResponse`; configura el tipo de contenido y un `Content-Disposition` seguro. Implementa `Range` solo si se necesita reanudación/acceso aleatorio, con validación del rango y respuestas `206`/`Content-Range` correctas.

Evita crear un protocolo con una cadena que use `|` y `;` seguida de bytes sin un encuadre formal. Si conservas un encabezado binario de longitud, codifícalo primero en UTF-8 y calcula la longitud en bytes:

```python
header = metadata_text.encode("utf-8")
prefix = len(header).to_bytes(4, byteorder="big")
response_bytes = prefix + header + image_bytes
```

El cliente debe leer el entero de 4 bytes y decodificar exactamente esa cantidad de bytes. Es preferible separar el punto de acceso JSON de metadatos del punto de acceso binario, o usar multipart.
