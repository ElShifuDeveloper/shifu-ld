# CSV y bytes (fuente única)

## Reglas de lectura de CSV

- No analices CSV con `split(",")` ni `split("\r\n")`: los campos entrecomillados pueden contener separadores, comillas y saltos de línea. Usa el módulo `csv` de Python con dialecto y codificación definidos (no decodifiques como UTF-8 si el cliente envía otra).
- Si lees por flujo, conserva el estado del analizador entre lecturas y define qué hacer cuando un registro cruza el límite entre bloques. Ejemplo: [stream_csv.py](../../ld-backend/examples/stream_csv.py).
- Define máximo y validación de columnas antes de cualquier escritura masiva.

## Carga masiva CSV

Un protocolo sencillo puede separar registros con `;` y columnas con `,`, y usar `executemany`; solo es válido para el formato restringido documentado. `split` no maneja CSV general con campos entrecomillados, separadores dentro del texto, comillas escapadas o saltos de línea.

Para CSV real, usa el analizador de la biblioteca estándar, no `split`. El [ejemplo incluido](../examples/csv_bulk_import.py) contiene importaciones, lectura en lotes y una validación estructural básica; `insert_sql` y el cursor se proporcionan desde la aplicación. Ajusta la codificación al contrato; no la cambies unilateralmente. Valida la cabecera, el número y tipo de columnas, el tamaño máximo por archivo y los límites por fila. Usa transacciones por archivo o por lote según el requisito de atomicidad; define si un fallo revierte todo o genera un informe de filas rechazadas.

Para el contrato actual de carga, [csv_upload_handler.py](../examples/csv_upload_handler.py) implementa una función de retorno especializada para CSV: analiza el contenido reconstruido en almacenamiento temporal, inserta por lotes dentro de una transacción y registra `upload_id` para que un reintento no duplique filas. Requiere configurar la cabecera, una instrucción SQL de inserción confiable, el alias de la base de datos y una tabla de recibos con `upload_id` único, `owner_id` y `record_count`; el skill no inventa el esquema ni la instrucción `INSERT` del negocio. Configura `LD_UPLOAD_COMPLETION_HANDLER` para que apunte a la función copiada y adaptada en el proyecto. Para otros tipos de texto, implementa una función de dominio distinta; este ejemplo rechaza elementos de texto que no sean CSV.

## Bytes e imágenes

Mantén los archivos como bytes o flujos hasta que lleguen a la biblioteca que los procesa. `BytesIO` es útil para búferes pequeños y formatos en memoria, pero el contenido completo ocupa memoria. Para archivos grandes, usa almacenamiento o flujos y evita copias duplicadas.

Para combinar texto y bytes en una misma respuesta (encuadre con longitud en bytes, LDP1), ver [read-endpoints.md](../../ld-backend/references/read-endpoints.md); no uses longitudes en caracteres, y prefiere endpoints separados o multipart.
