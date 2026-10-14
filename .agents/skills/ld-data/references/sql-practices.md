# Prácticas SQL: parámetros, paginación, transacciones y pruebas

## SQL parametrizado y paginación

Pasa los valores como parámetros del driver. No interpolar valores del usuario en SQL. Los nombres de tabla/columna no suelen aceptar parámetros; si son dinámicos, valídalos contra una lista permitida:

```python
cursor.execute(
    "SELECT TOP (?) Id, Codigo, Descripcion FROM dbo.Articulos WHERE Id > ? ORDER BY Id",
    (page_size, after_id),
)
rows = cursor.fetchall()
```

La sintaxis de límite puede variar según SQL Server y el controlador; confirma que el servidor real la admita y usa un procedimiento almacenado si ese es el patrón del proyecto. Usa orden estable y una clave para paginación por cursor. No consultes todas las filas para luego paginar en JavaScript.

Evita `fetchall()` o un DataFrame completo para volúmenes arbitrariamente grandes. Procesa con `fetchmany(batch_size)` o `cursor.fetchmany(...)`, devuelve páginas al punto de acceso o escribe a un flujo:

```python
while batch := cursor.fetchmany(1000):
    procesar_lote(batch)
```

Ajusta el tamaño mediante mediciones; 10 000 filas es una decisión específica de la aplicación, no un tamaño universal. El frontend debe pedir un bloque y el servidor consultar solo ese bloque.

En los SP suministrados, `uspCubsoPaginarCsvPy` implementa `OFFSET/FETCH` con orden por `CubsoId`, mientras que `uspCubsoContar` entrega el total como texto. Al envolver un patrón así, valida página/tamaño positivos, aplica un máximo, detecta overflow del offset y decide si el total debe ser consistente con las filas bajo concurrencia. Para páginas profundas, evalúa cursor/keyset; no conviertas el índice de página en un cursor opaco sin cambiar el contrato SQL. El análisis enlazado contiene los hallazgos específicos de límites, orden y prefijo `;`.

## `pyodbc` y transacciones

Usa parámetros posicionales de `pyodbc` y pasa valores como secuencia de un elemento: `(valor,)`. El módulo base construye llamadas `exec nombreSP @parametro=?`, pasa el valor como lista y valida el formato del nombre del procedimiento/parámetro; confirma igualmente que el nombre procede de código confiable o de una lista permitida, nunca de una entrada libre.

Ejemplo conceptual:

```python
cursor.execute("EXEC dbo.BuscarOrden @Id = ?", (orden_id,))
row = cursor.fetchone()
```

Define quién administra `commit`/`rollback`, cierra el cursor y la conexión con `with`/`try/finally` según lo admita el controlador, y evita confirmar solo algunos caminos. No ocultes una excepción devolviendo un resultado con forma de éxito; comunica al servidor un error de dominio o de registro seguro.

Revisa quién administra la transacción antes de activar `trx=True`: algunos SP, como `uspOrdenGrabarPyCsv`, abren y confirman su propia transacción. Evita reintentos automáticos de escrituras sin idempotencia: una pérdida de conexión después de `COMMIT` puede repetir la operación. Para transacciones en T-SQL, recomienda `SET XACT_ABORT ON` y `TRY/CATCH` con `rollback` y propagación de la excepción según la versión y el comportamiento requeridos; verifica además los identificadores con `SCOPE_IDENTITY()`/`OUTPUT INSERTED` en vez de `@@IDENTITY` cuando pueda haber desencadenadores.

## DataFrame: usarlo con intención

`EjecutarComandoDF` (solo en la [variante mejorada](../examples/mejorado/modAccesoDatos.py); el cliente de los demos no lo tiene) es conveniente cuando el consumidor necesita pandas:

```python
df = pd.read_sql_query(
    "SELECT Id, Precio FROM dbo.Articulos WHERE Id > ?",
    connection,
    params=[after_id],
)
```

Para una respuesta HTTP paginada, normalmente pide una cantidad acotada de filas y serializa las columnas requeridas; no conviertas toda la tabla a DataFrame por conveniencia. Controla los tipos SQL, `NULL` y fechas, y define explícitamente la serialización JSON. Para varios conjuntos de resultados, itera `nextset()` y devuelve una colección cuyo orden y nombres estén documentados.

## Rendimiento, calidad y pruebas

- Selecciona columnas requeridas; evita `SELECT *`.
- Usa índices adecuados a filtros/orden de paginación.
- Mide latencia, tamaño de filas, memoria y rendimiento de transferencia con datos representativos.
- No confundas filas por lote con bytes de red.
- Para inserciones, `executemany`/bulk load puede superar inserciones individuales; verifica tamaños de lote y comportamiento transaccional del driver.
- Prueba cero filas, lotes parciales, lote exacto, tipos NULL/fechas/unicode, duplicados, CSV con comillas/comas/saltos, error a mitad de lote, rollback y escala máxima esperada.
- Verifica que la respuesta conserve los tipos y la codificación, y que el conteo, el orden y los datos finales coincidan con los registros de origen.
