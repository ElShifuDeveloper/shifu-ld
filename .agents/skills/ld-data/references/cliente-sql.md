# `clienteSQL`: el cliente de los demos y cómo elegir el método

Fuente única del contrato de `clienteSQL`. El archivo es [base/modAccesoDatos.py](../examples/base/modAccesoDatos.py), copia fiel de
`Modulos/modAccesoDatos.py` de los proyectos LD (usa `Modulos/modUtilidades.py`: `beLog`, `Log`). Se crea con
`clienteSQL(archivoConfig, archivoLog)`; no tiene más parámetros.

## Configuración

`archivoConfig` es un archivo de texto de líneas `clave=valor` con `driver`, `servidor`, `usuario`, `clave` y `basedatos`; queda
**fuera del repositorio** (ruta desde `settings`). El analizador separa por `=` y toma solo el segundo trozo: una clave con
`=` dentro se corta. Un fallo al leerlo queda en `archivoLog`.

## Métodos y qué devuelven

| Método | Para | Devuelve |
|---|---|---|
| `EjecutarComandoCadena(sp, param, valor, trx=False)` | SP con un escalar (listas delimitadas `...Csv`/`...PyCsv`, conteos, ids) | el escalar; `""` si no hay fila o es `NULL`; **`None` si la consulta falló** (queda en el log) |
| `EjecutarComandoFila(sp, param, valor)` | SP con una fila (una entidad, o texto más binario) | la fila; `""` si no hay fila; `None` si falló |
| `EjecutarComandoUnaLista(sql)` / `EjecutarComandoListas(sql)` | una **sentencia SQL** (no un SP) | lista de textos con la cabecera y las filas unidas por `,`; `Listas` una lista por conjunto |
| `EjecutarComandoLista(sql)` | una sentencia SQL | `fetchall()` (filas); `None` si falló |
| `EjecutarInsertMasivoCsv(tabla, csv, sepReg, sepCampo)` | cargar un bloque de registros (`executemany`) | `"OK"` o `"Error: ..."`; la primera fila del texto son los nombres de columna |
| `EjecutarInsertMasivoLista(tabla, campos, lista)` | cargar filas ya separadas | `"Datos Copiados Correctamente"` o `"Error: ..."` |
| `ValidarTablaCampos(tabla, campos)` | comprobar que las columnas existan antes de cargar | `""` si coinciden; `"Error - No existen los sgtes campos: ..."` o `"Error - La Tabla ... No existe"` |

Particularidades que importan al escribir vistas:

- **Distinguir fallo de "sin datos":** en `EjecutarComandoCadena`/`Fila`, `None` es fallo y `""` es sin datos o `NULL`. La vista responde `502` ante `None` y `404` o cadena vacía ante `""`.
- **Parámetro vacío:** si `valorParametro == ""` el método ejecuta el SP **sin parámetro** (`nombreParametro != "" and valorParametro != ""`).
- **Transacciones:** solo `EjecutarComandoCadena(..., trx=True)` confirma. Un SP que no abre su propia transacción (`uspProductoGrabar3Csv`, `uspProductoEliminar3Csv`) necesita `trx=True` o el cambio se pierde; uno que sí (`uspOrdenGrabarPyCsv`) ya confirma.
- **Nombres de tabla y columnas:** `EjecutarInsertMasivo*` y `ValidarTablaCampos` los concatenan en el SQL. Nunca los tomes del cliente sin una lista permitida (`TABLAS_PERMITIDAS` en `ld-transferencia/examples/views_registros.py`). Los valores sí van como parámetros.
- Cada llamada abre su propia conexión y no hay reintentos; para volúmenes grandes divide el trabajo en viajes.

## Elegir el método según la forma del SP

| Forma del resultado | Método |
|---|---|
| Un escalar o una lista delimitada | `EjecutarComandoCadena` |
| Una fila (entidad; texto más `Foto`) | `EjecutarComandoFila` |
| Un bloque de registros para insertar | `EjecutarInsertMasivoCsv` |
| Varias secciones | un SP que las una con `_` en un solo escalar (`uspOrdenConsultarPorRangoPyCsv`) |
| Archivo binario | bytes o flujo desde el disco; nunca como texto delimitado |

## Variante opcional con reintentos y errores por excepción

[mejorado/modAccesoDatos.py](../examples/mejorado/modAccesoDatos.py) es una variante **que no es la de los demos**: añade
`lanzarErrores`, reintentos, contexto (`with`), DataFrame y validación de nombres de SP. Úsala solo si el proyecto decide
adoptarla; los ejemplos de este paquete se escriben contra el cliente de los demos y funcionan sin ella.

## NULL y reglas de dominio

Aplica la regla de dominio a `NULL` en el SP o en la vista: en existencias, `NULL` significa stock cero (el SP usa
`ISNULL(UnitsInStock, 0)`); una fila ausente es `404`; un fallo de base de datos es `5xx`. Los datos delimitados no
se escapan: ningún valor puede contener `¬`, `|`, `;` ni `_` (ver [stored-procedures-review.md](./stored-procedures-review.md)).
