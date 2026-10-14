# Contrato de transferencia compartido por los skills LD

> **Protocolo alternativo (JSON, cursor, LDP1, sesión de carga).** No es el estilo base LD: sirve para integraciones con
> terceros o cuando la persona lo pide. Para subir y bajar archivos y mover volúmenes al estilo de los appDemo (cadenas y
> bytes, bloques `I`/`P`, lotes, paquetes, viajes) usa [ld-transferencia](../../ld-transferencia/SKILL.md).

Este archivo es la **fuente única** del contrato de intercambio compartido por
`ld-design`, `ld-frontend`, `ld-backend` y `ld-data`; los demás documentos lo
enlazan en vez de repetirlo. Mantén juntos los skills al mover este paquete. Los ejemplos frontend/backend implementan el contrato de
carga descrito aquí; las consultas aún requieren adaptadores para la base de
datos, el catálogo de archivos y la fuente de texto/binarios del proyecto.

## Unidades y formatos

- Una página es un resultado lógico acotado, no un fragmento de transporte.
- `limit` es la cantidad de filas/archivos. `cursor` es un testigo opaco y estable para continuar.
- `chunk_size` indica bytes de contenido, no el tamaño de la solicitud HTTP.
  `100 KiB` equivale a `100 * 1024 = 102400` bytes; los encabezados multipart
  agregan sobrecarga de red.
- El texto estructurado usa sobres JSON codificados en UTF-8. El texto heredado
  con `;`/`|` es solo para clientes existentes y debe definir escape, nulos,
  codificación y límites.
- El contenido de archivo permanece binario. No lo conviertas en texto con
  separadores ni Base64 solo para combinarlo con metadatos.

## Contratos de consulta (casos 1–3)

### 1. Registros de texto paginados

```http
GET /api/records?limit=200&cursor=<opaque>
Accept: application/json
```

```json
{
  "items": [{"id": 42, "description": "texto UTF-8"}],
  "next_cursor": "opaque-next",
  "has_more": true
}
```

El cuerpo de respuesta es texto codificado como JSON UTF-8. El backend aplica
la paginación solicitada en la consulta a la base de datos; el frontend muestra
solo los elementos recibidos y solicita el siguiente cursor. Una cadena
heredada con separadores constituye otro contrato y tipo de contenido con
versión propia, no una alternativa implícita.

### 2. Catálogo de archivos paginado y contenido binario

```http
GET /api/files?limit=100&cursor=<opaque>
```

Devuelve una página JSON de metadatos autorizados (`id`, nombre visible, tipo
de contenido, tamaño, suma de verificación opcional y cursor siguiente).
Solicita el contenido por separado:

```http
GET /api/files/{file_id}/content
Range: bytes=0-102399
```

Devuelve `206 Partial Content` y un encabezado `Content-Range` correcto si se
admiten rangos; en caso contrario, entrega un flujo acotado. No pagines un
binario grande como texto Base64. El identificador del archivo debe resolverse
mediante metadatos de autorización/almacenamiento del servidor, nunca con una
ruta proporcionada por el cliente.

### 3. Metadatos de texto junto con contenido binario

Se recomienda usar el manifiesto JSON paginado y las solicitudes binarias
separadas del caso 2. Si es realmente necesario combinarlo todo en una
respuesta binaria, solicita una página acotada:

```http
GET /api/mixed?limit=100&cursor=<opaque>
Accept: application/vnd.ld-page-v1
```

`LD_MIXED_PAGE_PROVIDER` entrega un manifiesto con `has_more`, `next_cursor` y
`payloads`, junto con los bytes sin procesar en el mismo orden. La vista de
referencia de Django `page_mixed_binary` limita la respuesta codificada a
16 MiB; la función de navegador `fetchMixedPage` la interpreta. Los archivos
grandes deben seguir usando el punto de acceso autorizado de contenido/rangos.

El formato de la trama es:

```text
4 bytes "LDP1"
4 bytes: longitud del manifiesto, entero sin signo en orden de bytes big-endian
manifest_length bytes UTF-8 JSON manifest
para cada contenido del manifiesto, en orden:
    8 bytes con la longitud del contenido, entero sin signo en orden de bytes big-endian
    payload_length bytes sin procesar
```

Cada longitud se mide en bytes. El manifiesto declara el cursor de la página
y el identificador, nombre visible, tipo de contenido y longitud esperada de
cada bloque de contenido. El codificador acotado de referencia está en
[binary_framing.py](../examples/binary_framing.py) y el intérprete del navegador en
[transfer-workflows.js](../../ld-frontend/examples/transfer-workflows.js);
ambos están conectados al punto de acceso de referencia `/api/mixed`.
Deben probarse juntos con datos de la aplicación. Este protocolo no usa el paquete de bytes de los demos (appDemo06–14), que está
corregido y documentado en
[formato-paquete.md](../../ld-transferencia/references/formato-paquete.md).

## Contratos de carga (casos 4–6)

Usa una sesión de carga para uno o más elementos tipados. Codifica el texto
como bytes UTF-8 antes de dividirlo, para que el límite de un fragmento no
parta un carácter Unicode. El tamaño predeterminado del fragmento es
102400 bytes; el servidor aplica su propio máximo.

```http
POST /api/uploads
Content-Type: application/json

{
  "items": [
    {"kind":"text","name":"notes.txt","size":12345,"content_type":"text/plain"},
    {"kind":"file","name":"report.csv","size":500000,"content_type":"text/csv"},
    {"kind":"file","name":"photo.png","size":240000,"content_type":"image/png"}
  ]
}
```

```json
{
  "upload_id": "server-generated-id",
  "chunk_size": 102400,
  "items": [{"item_id":"server-generated-item-id","chunk_size":102400}]
}
```

El tamaño puede ser cero para archivos vacíos o texto vacío; en ese caso no se
envían partes y el servidor materializa un archivo vacío al finalizar. La
validación del contenido (por ejemplo, que un CSV tenga encabezado) sigue
siendo responsabilidad del manejador configurado.

Envía los elementos secuencialmente (el paralelismo debe habilitarse de forma
explícita según la capacidad del servidor):

```http
POST /api/uploads/{upload_id}/items/{item_id}/chunks/{index}
Content-Type: multipart/form-data

chunk=<bytes sin procesar>
```

El servidor comprueba propietario, elemento/índice, longitud exacta del
fragmento, límites por elemento y totales, y errores de almacenamiento. Guarda
cada parte en una ubicación temporal generada por el servidor. Si el cliente
no recibe la respuesta de una parte, puede reenviar exactamente esos mismos
bytes: si la parte ya se guardó, el servidor compara sus sumas SHA-256 y
confirma el duplicado idéntico; si aún no se guardó, la almacena normalmente.
Un fragmento con el mismo índice pero bytes distintos se rechaza con HTTP 409
y `code:"chunk_conflict"`. Si otra solicitud está guardando ese índice, se
responde con HTTP 409 y `code:"chunk_in_progress"`; el cliente puede reintentar
esa misma parte después de una espera breve.

El cliente de referencia envía los fragmentos en orden y no avanza hasta
recibir confirmación del servidor. Ante errores de red, HTTP 5xx o
`chunk_in_progress`, reintenta el mismo fragmento hasta tres veces. Si sigue
sin poder confirmarlo, se detiene: iniciar de nuevo `uploadItems` crea otra
sesión y vuelve a enviar todos los elementos desde el principio. No se guarda
el estado de la sesión en el navegador ni existe una ruta de consulta para
reanudarla después de cerrar o recargar la página; los temporales de una sesión
abandonada requieren la política de limpieza de la aplicación.

Finaliza únicamente después de recibir confirmación de todas las partes:

```http
POST /api/uploads/{upload_id}/complete
```

El servidor verifica todos los índices esperados y el tamaño total, ensambla
cada elemento en un objeto final con nombre generado por el servidor y lo
publica atómicamente. Luego entrega los elementos de texto (o flujos CSV) a la
capa de datos. Solo informa éxito cuando termina el procesamiento/guardado
configurado. Define si todos los elementos deben ser atómicos en conjunto: una
transacción de base de datos no puede confirmar simultáneamente escrituras en
el sistema de archivos sin un mecanismo compensatorio o patrón outbox.

- El caso 4 contiene uno o más elementos `kind:"text"`, normalmente CSV.
  Después de reconstruir los bytes, interpreta la codificación UTF-8 u otra
  documentada mediante un analizador incremental. No confundas el tamaño del
  lote de filas de base de datos con el tamaño del fragmento de red.
- El caso 5 contiene uno o más elementos `kind:"file"`. Conserva los bytes y
  separa el almacenamiento temporal del almacenamiento final.
- El caso 6 combina ambos tipos de elemento en un mismo manifiesto/sesión y
  política de finalización. Cada elemento conserva su tipo e identificador
  generado por el servidor.
- El transporte admite elementos vacíos sin enviar partes; la aplicación debe
  definir si el dominio acepta texto/archivos vacíos, además de la cantidad
  máxima de elementos, bytes máximos por elemento/total, retención,
  cancelación, reintentos, inspección de tipo/contenido y autorización.

## Cobertura de los seis flujos (tabla única)

| # | Flujo | Cliente (`ld-frontend`) | Servidor (`ld-backend`) | Datos (`ld-data`) | Falta para el extremo a extremo |
|---|---|---|---|---|---|
| 1 | Texto paginado | `fetchRecordPage` | `read_api.page_records` | proveedor SQL con [SP tipado](../../ld-data/references/sql-sources.md) | conectar el proveedor y el cursor reales; appDemo16/26 usan rangos o índice heredados, no un cursor opaco |
| 2 | Archivos paginados | `fetchFilePage`, `fetchFileRange` | `read_api.page_files`, `file_content` (`Range`) | — | catálogo con ids y permisos: modelo o repositorio real (los demos no lo tienen) |
| 3 | Texto más bytes | `fetchMixedPage`, `parseLdp1` | `read_api.page_mixed_binary`, `binary_framing` | función proveedora autorizada | implementarla; preferir descargas separadas para contenido grande |
| 4 | Texto o CSV grande por partes | `uploadItems` con `kind:"text"` | `transfer_api` | [csv_upload_handler.py](../../ld-data/examples/csv_upload_handler.py): transacción y recibo idempotente | esquema, columnas, `INSERT`, tabla de recibos y política de errores del dominio |
| 5 | Varios archivos por partes | `uploadItems` con `kind:"file"` | `transfer_api`: temporales por usuario, publica al completar | — | multi-host (almacenamiento compartido), retención, inspección de contenido, cuotas y limpieza automática |
| 6 | Archivos y texto juntos | `uploadItems` mixto | `transfer_api` | el CSV `text` se procesa con el manejador; los bytes van al repositorio de archivos | texto que no sea CSV y atomicidad entre base de datos y sistema de archivos |

"Cubierto" significa que el paquete incluye piezas compatibles que forman un punto de partida, no que estén configuradas contra tu SQL Server ni listas para producción. Los casos 1–2 necesitan proveedores reales que los demos no incluyen.

## Relación con los demos de referencia

| Referencia | Qué demuestra | Qué no incluye |
|---|---|---|
| appDemo14 | Consultas/escrituras con procedimientos almacenados, bytes de imagen y metadatos de texto | No ofrece un formato binario general seguro; su encabezado heredado de dos bytes mide caracteres. El conjunto de SP suministrado se analiza en [stored-procedures-review.md](../../ld-data/references/stored-procedures-review.md). |
| appDemo16 | Consulta de un rango de identificadores de orden | No ofrece paginación por cursor ni un contrato JSON tipado |
| appDemo26 | Cuenta registros y luego solicita bloques por índice y tamaño | No garantiza una instantánea coherente; el conteo y las páginas pueden variar si cambian las filas |
| appDemo28 | Valida columnas de tabla e inserta filas CSV en lotes secuenciales | No admite el escape general de CSV en su punto de acceso con separadores ni almacenamiento de archivos/bloques |
| appDemo107 | Interfaz de grilla/consulta y utilidades compartidas del frontend | No incluye una implementación de backend en el directorio suministrado |
| mpDemo07 | Anexa imágenes secuencialmente con `I/P/C` y las procesa en el sistema de archivos | No incluye identificadores de carga, índices de partes, verificación de finalización ni aislamiento de concurrencia |

Usa estos demos como evidencia y referencia para migrar, no como prueba de que
esas aplicaciones ya implementan los contratos modernos. La copia de SP
suministrada documenta algunas definiciones, pero el esquema desplegado, el
comportamiento exacto en ejecución, el backend de appDemo107, el catálogo de
archivos y la configuración de almacenamiento/autorización de producción
siguen dependiendo de cada aplicación.
