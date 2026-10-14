# Cliente de consultas, descargas y cargas

> **Cliente del protocolo alternativo (JSON, cursor, LDP1, sesión de carga).** No es el estilo base LD. Para archivos y
> volúmenes al estilo de los appDemo usa [ld-transferencia](../../ld-transferencia/SKILL.md).

Detalle del lado navegador. El protocolo, los códigos de error y los reintentos están en el [contrato](../../ld-backend/references/transfer-contract.md) (fuente única); aquí solo lo que el cliente debe hacer.

## Paginación de registros

- Prefiere JSON tipado y cursores para resultados grandes o cambiantes. El sobre es `items`, `next_cursor` y `has_more`: [fetchRecordPage](../examples/transfer-workflows.js), atendido por [read_api.py](../../ld-backend/examples/read_api.py). Ejemplo completo: [pagination.js](../examples/pagination.js).
- Para archivos, pagina solo el catálogo de metadatos (`fetchFilePage`) y pide el contenido por id y rango (`fetchFileRange`); el backend autoriza cada descarga y responde `206` con `Content-Range`.
- La paginación local sobre datos ya cargados usa `start = pageIndex * pageSize` y `end = Math.min(start + pageSize, items.length)`; no la llames "paginación de backend".
- Un contrato heredado con texto `;`/`|` debe documentar escape, nulos y codificación y validar su forma antes de usar `split`.

## Carga por partes

Código: [transfer-workflows.js](../examples/transfer-workflows.js) (`uploadItems`) y [upload-chunks.js](../examples/upload-chunks.js) (un solo archivo); el receptor es [transfer_api.py](../../ld-backend/examples/transfer_api.py).

- 100 KiB = `100 * 1024` = 102400 bytes de contenido (no del total de la solicitud HTTP). Cantidad de partes con `Math.ceil`; final de cada parte con `Math.min`.
- No uses `fin = inicio + (size % chunkSize)`: con tamaño múltiplo exacto da `fin == inicio`. Usa `file.slice(start, Math.min(start + chunkSize, file.size))`.
- Casos de prueba de tamaño: 0, 1, `chunkSize - 1`, `chunkSize`, `chunkSize + 1`, `2 * chunkSize` y `2 * chunkSize + 1`.
- `uploadItems` admite elementos `file` (Blob/File) y `text` (codificado con `TextEncoder` a UTF-8 antes de dividirlo); envía en orden y avanza solo cuando el servidor confirma cada índice. Los casos 4, 5 y 6 se distinguen solo por los tipos de elemento del manifiesto. Los elementos vacíos se inicializan y finalizan sin enviar partes.
- No fijes a mano el `Content-Type` de `FormData`: el navegador genera el boundary. Con cookie/CSRF de Django, añade el token al encabezado o al formulario.
- Reintentos (red, `5xx`, `chunk_in_progress`, hasta tres) y la imposibilidad de reanudar tras recargar: ver el contrato.

El protocolo de bloques `I`/`P` de appDemo13 está en [ld-transferencia](../../ld-transferencia/SKILL.md) (técnica 1).

## Archivos y respuestas binarias

```js
const response = await fetch(`/api/files/${encodeURIComponent(fileId)}/content`);
if (!response.ok) throw new Error(`Descarga fallida: HTTP ${response.status}`);
const blob = await response.blob();
const objectUrl = URL.createObjectURL(blob);
try {
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = nombreSeguro;
  link.click();
} finally {
  setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}
```

- `response.blob()` conserva el cuerpo completo en memoria: para descargas grandes usa flujo o `Range`. En estilo LD, un archivo grande que la app va a mostrar o procesar se pide por bloques y se une con `new Blob(partes)` ([ld-transferencia](../../ld-transferencia/SKILL.md), técnicas 2 y 7); `FileResponse` con `as_attachment` queda para guardarlo en disco y `blob()` solo para archivos pequeños.
- Si llegan texto y bytes en un solo cuerpo, no lo decodifiques entero como texto: usa el encuadre con longitud en bytes (`parseLdp1`) o separa metadatos y descarga. Los caracteres no equivalen a bytes UTF-8 y `String.fromCharCode` no sirve para Unicode.
- Para vistas previas con `FileReader`, valida `file.type` o el contenido y libera `URL.createObjectURL` al quitar la miniatura. El MIME declarado por el navegador no valida nada en el servidor.

## CSV grande

Usa un analizador CSV con lectura por flujo o envía los bytes para que el servidor los analice; define codificación, BOM, separador y política de errores. Reglas completas en [csv-and-bytes.md](../../ld-data/references/csv-and-bytes.md).
