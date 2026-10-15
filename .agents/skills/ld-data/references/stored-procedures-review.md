# Análisis de los procedimientos almacenados suministrados

Este análisis se basa en las 26 definiciones de procedimientos de la carpeta `SPs`
del proyecto de origen (no incluida en el paquete) y se contrastó línea a línea con
el texto SQL. Describe los contratos y riesgos visibles en esas definiciones; no
modifica ni ejecuta los procedimientos en la base de datos. Los archivos no tienen
extensión, dos nombres no coinciden con el procedimiento declarado en su contenido
y todos son scripts `ALTER` con `USE [BD_DACP_2025]`: solo se pueden aplicar sobre
un objeto existente de esa base. Para versionar o desplegar en otro entorno usa
`CREATE OR ALTER`, sin `USE` fijo (ejemplo en
[sql/uspCubsoListarPaginaTipada.sql](../examples/sql/uspCubsoListarPaginaTipada.sql)).

Todos los objetos analizados aquí son **T-SQL de SQL Server** (`dbo.`, `FOR XML PATH`, `ISNULL`,
`@@IDENTITY`, `fnSplitString`, `TOP`). Para **PostgreSQL**, el mapeo T-SQL ↔ PL/pgSQL y el estilo
equivalente están en [postgres.md](./postgres.md); la versión PL/pgSQL del ejemplo tipado está en
[sql/pg/uspCubsoListarPaginaTipada.sql](../examples/sql/pg/uspCubsoListarPaginaTipada.sql).

**Cobertura.** Los demos de `webpython` llaman a 23 procedimientos distintos y los
23 tienen definición en `SPs`. Las otras 3 definiciones no las llama ningún demo:
`uspCubsoListarPaginaTipada` (usada por el proveedor del paquete),
`uspProductoListarPorCodigosCsv` y `uspUbigeoListarCsv`. Los demos llaman a
`uspAlumnosListarPorCodigosCsv` (alumnos), que es distinto de
`uspProductoListarPorCodigosCsv` (productos). Ningún procedimiento usa `TRY/CATCH`;
solo `uspOrdenGrabarPyCsv` abre una transacción explícita.

## Contratos observados

| Nombre del archivo | Objeto SQL declarado | Parámetro y resultado observado |
|---|---|---|
| `ListarCodigosCsv` | `dbo.uspAlumnoListarCodigosCsv` | Sin parámetros; devuelve un escalar con los valores `Alumno.IdAlumno` separados por `|`. No define `ORDER BY`; la agregación puede devolver `NULL` si no hay filas. |
| `ListarPorCodigosCsv` | `dbo.uspProductoListarPorCodigosCsv` | Recibe `@Codigos varchar(max)` con identificadores separados por `|`; devuelve un escalar con campos de producto separados por `|` y registros por `;`. Recorre los identificadores con un cursor y depende de `fnSplitString`. Un identificador sin producto hace que la subconsulta devuelva `NULL` y toda la cadena acumulada quede `NULL` (con `CONCAT_NULL_YIELDS_NULL` activo); un identificador no numérico falla en la comparación con `ProductID`. No usa `FOR XML`. |
| `uspCubsoContar` | `dbo.uspCubsoContar` | Sin parámetros; devuelve un escalar con el conteo convertido a `varchar`. |
| `uspCubsoListarPaginaTipada` | `dbo.uspCubsoListarPaginaTipada` | Recibe `@AfterCubsoId int` (`NULL` = primera página) y `@PageSize int` (1 a 501, si no `THROW 50001`); devuelve **un conjunto de filas tipado** `CubsoId, Codigo, Descripcion, Precio` ordenado por `CubsoId`, con `TOP (@PageSize)`. Es el contrato que consume `cubso_records_provider.py`. |
| `uspCubsoPaginarCsvPy` | `dbo.uspCubsoPaginarCsvPy` | Recibe `@data varchar(max)` con `página|tamaño`; devuelve un escalar con registros de `Cubso` codificados mediante `;` y `|`. Ordena por `CubsoId` y usa `OFFSET/FETCH`; antepone `;` a cada fila. **Trunca `Descripcion` a 45 caracteres** y convierte un `Precio` `NULL` en `0` (`isnull(Precio,'')`), por lo que pierde datos respecto a la tabla. Con un solo número en `@data` el desplazamiento queda `NULL` y falla. |
| `uspOrdenConsultarPorRangoPyCsv` | `dbo.uspOrdenConsultarPorRangoPyCsv` | Recibe `@IdOrdenes varchar(20)` con dos identificadores separados por `|`. Devuelve **un único escalar** (el único `SELECT` que produce filas es el último; el primero solo asigna variables): sección de órdenes, `_` y sección de detalle, con filas separadas por `;`. Cada sección empieza con tres filas de metadatos: nombres de columna, anchos y tipos (`int`, `str`, `float`), que es el formato de entrada de `Gui.Grilla`. |
| `uspOrdenGrabarPyCsv` | `dbo.uspOrdenGrabarPyCsv` | Recibe `@Data varchar(max)` con `cliente|empleado_` seguido de detalles `producto|precio|cantidad` separados por `;`; devuelve un escalar `idOrden|fecha` (`dd/mm/aaaa`) cuando tiene éxito. Abre y confirma su propia transacción, inserta orden/detalles y actualiza existencias. **Toma el precio unitario del cliente** en lugar de leerlo de `Producto`. |
| `uspProductoListarCodigosPorCategoriaCsv` | `dbo.uspProductoListarCodigosPorCategoriaCsv` | Recibe `@CategoryID int`; devuelve un escalar con identificadores de producto separados por `|`. Normaliza la ausencia de resultados como `''`. |
| `uspProductoObtenerStockPorId` | `dbo.uspProductoObtenerStockPorId` | Recibe `@ProductID int`; devuelve una fila con las existencias como número, convirtiendo SQL `NULL` a `0`, o ninguna fila si el producto no existe. |
| `uspUsuarioValidarLoginCsv` | `dbo.uspUsuarioValidarLoginCsv` | Recibe `@Login varchar(100)` con `usuario|clave`; devuelve un escalar `IdCliente|Empresa|Dirección|Correo` si coincide, o ninguna fila. Compara `Clave` directamente: como el login envía `SHA-256` en hexadecimal (64 caracteres), 20 + 1 + 64 cabe en 100, y la columna contendría ese hash sin sal (verifica los datos). Si `Address` o `Correo` es `NULL`, la concatenación es `NULL` y un login correcto se rechaza. Si la entrada no contiene el separador, `SUBSTRING` falla. |
| `uspAlumnoObtenerPorIdCsv` | `dbo.uspAlumnoObtenerPorIdCsv` | `@IdAlumno int`; escalar `Apellidos\|Nombres\|Correo`, o ninguna fila. Si `Correo` es `NULL`, la concatenación es `NULL`. |
| `uspAlumnoObtenerPorIdConFoto2` | `dbo.uspAlumnoObtenerPorIdConFoto2` | `@IdAlumno int`; **una fila de dos columnas**: texto `Apellidos\|Nombres\|Correo` y `Foto` (binario). Es el único SP de muestra con bytes; se lee con `EjecutarComandoFila`. El demo que lo consume antepone un único byte con la longitud en caracteres del texto, así que falla con más de 255 caracteres o texto no ASCII. |
| `uspAlumnosListarPorCodigosCsv` | `dbo.uspAlumnosListarPorCodigosCsv` | Igual que la versión de productos: `@Codigos` con ids separados por `\|`, cursor sobre `fnSplitString`, registros `id\|apellidos\|nombres\|correo` separados por `;`. Un id inexistente o un `Correo` `NULL` deja la cadena en `NULL`. |
| `uspCategoriaProductosStockPyCsv` | `dbo.uspCategoriaProductosStockPyCsv` | Sin parámetros; escalar con tres filas de metadatos (nombres, anchos, tipos) y luego `Categoria\|Total Stock`, todo separado por `;`. Si no hay productos, la parte de datos es `NULL` y el escalar completo también. |
| `uspCategoriaProductosStock2PyCsv` | `dbo.uspCategoriaProductosStock2PyCsv` | Igual, con una columna `Id` adicional (`Id\|Categoria\|Total Stock`). |
| `uspProductoListarStockPorCategoriaPyCsv` | `dbo.uspProductoListarStockPorCategoriaPyCsv` | `@CategoryID int`; metadatos y filas `Producto\|Stock` separadas por `;`. Sin productos en la categoría el escalar es `NULL`. |
| `uspDACPListas2Csv` | `dbo.uspDACPListas2Csv` | Sin parámetros; cuatro secciones unidas por `_`: los nombres de pestaña `Alumnos\|Cursos\|Profesores` y tres grillas (metadatos con `¬` + datos). **La grilla de profesores tiene la cabecera desalineada**: declara `IdProfesor\|Apellidos\|Nombres\|FechaNac` pero los datos son `id\|Apellidos Nombres\|FechaNac\|DocIdentidad`. |
| `uspProductoListarCsv` | `dbo.uspProductoListarCsv` | Sin parámetros; escalar con 3 filas de metadatos y filas `id\|nombre\|idProv\|idCat\|precio\|stock` separadas por `¬`. |
| `uspProductoListar3Csv` | `dbo.uspProductoListar3Csv` | Igual, pero **solo con la fila de nombres** (sin anchos ni tipos): está pensado para convertirse a JSON con `JSON.SerializarCsv`, no para `Gui.Grilla`. |
| `uspProductoListasCboCsv` | `dbo.uspProductoListasCboCsv` | Sin parámetros; tres secciones unidas por `_`: grilla de productos (3 filas de metadatos, con proveedor y categoría por nombre), proveedores `id\|nombre` y categorías `id\|nombre`, con `¬` entre registros. Usa `ISNULL` por sección. |
| `uspProductoObtenerPorId2` | `dbo.uspProductoObtenerPorId2` | `@ProductID int`; escalar `id\|nombre\|idProv\|idCat\|precio\|stock`, o ninguna fila. |
| `uspProductoObtenerPorId3` | `dbo.uspProductoObtenerPorId3` | Igual, con la fila de nombres delante (`...Stock¬` + datos), para convertir a JSON. |
| `uspProductoGrabar3Csv` | `dbo.uspProductoGrabar3Csv` | `@Data` con 6 campos `id\|nombre\|idProv\|idCat\|precio\|stock`; `id` vacío inserta y con valor actualiza. Devuelve `grilla_id` (grilla con 3 filas de metadatos, `_`, id). No abre transacción: depende de `trx=True` en el wrapper. |
| `uspProductoEliminar3Csv` | `dbo.uspProductoEliminar3Csv` | `@ProductID int`; **borra físicamente** el producto y devuelve `grilla_id`, exista o no el id. Falla por clave foránea si el producto tiene detalle de órdenes. |
| `uspUbigeoListar` | `dbo.uspUbigeoListar` | Sin parámetros; **conjunto de filas tipado** `IdDpto, IdProv, IdDist, Nombre`, sin `ORDER BY`. Lo consume `EjecutarComandoLista` para una copia masiva. |
| `uspUbigeoListarCsv` | `dbo.uspUbigeoListarCsv` | Sin parámetros; registros separados por `¬` con `IdDpto + IdProv + IdDist + Nombre` **concatenados sin separador de campos**: solo se puede interpretar si los códigos tienen ancho fijo. Ningún demo lo usa. |

El archivo `ListarCodigosCsv` declara un procedimiento para *Alumno*, no para
productos. `ListarPorCodigosCsv` declara `uspProductoListarPorCodigosCsv`.
Desde la aplicación, usa el nombre del objeto SQL declarado. En un proyecto
de base de datos mantenido en control de versiones, conviene usar nombres de
archivo precisos y la extensión `.sql`.

## Hallazgos y mejoras sugeridas

### 1. Las cadenas delimitadas: el formato LD y su disciplina

Varios procedimientos serializan filas con `;` y `|`, pero no definen reglas
de escape. Los nombres o textos que contengan esos separadores no se pueden
interpretar de forma confiable. También requieren reglas explícitas los
valores `NULL`, fechas, precisión/formato decimal, páginas vacías y Unicode.
Esto no es CSV estándar: sus reglas de comillas no se aplican a estos
separadores personalizados. El procedimiento de consulta de órdenes agrega
metadatos de esquema como texto y construye el detalle con `FOR XML PATH('')`
sin `TYPE`/`.value()`: un `ProductName` con `&`, `<` o `>` saldrá escapado
(`&amp;`). `uspCubsoPaginarCsvPy` sí usa `TYPE` y `.value()` y no tiene ese
problema; `uspAlumnoListarCodigosCsv` y `uspProductoListarCodigosPorCategoriaCsv`
solo concatenan identificadores numéricos.

Los parámetros y algunas expresiones de texto usan `varchar`, no `nvarchar`.
Define la codificación admitida o usa tipos SQL Unicode cuando sea necesario
preservar texto no ASCII. El campo `Data` de `uspOrdenGrabarPyCsv` representa
una gramática personalizada de órdenes; no es un archivo CSV ni es compatible
directamente con el manejador genérico `csv_upload_handler.py`.

Es el formato de los proyectos LD y funciona bien si se respeta su disciplina: documenta (en el contrato de la
historia) separadores, codificación, valores nulos, formatos de fecha y decimal, orden de campos, metadatos de esquema y
comportamiento sin resultados; valida en el servidor que ningún dato de usuario contenga `¬`, `|`, `;` ni `_`; y añade
pruebas de ida y vuelta con `|`, `;`, `_`, `&`, texto acentuado, `NULL` y conjuntos vacíos. Si una integración con
terceros necesita columnas tipadas o JSON, crea un SP o una vista aparte para ese consumidor.

### 2. Elige el método Python según la forma del resultado

La tabla de métodos y el contrato de `clienteSQL` (`None` = falló, `""` = sin datos o `NULL`) están en [cliente-sql.md](./cliente-sql.md). Para estos SP importa lo siguiente:

- `uspOrdenConsultarPorRangoPyCsv` **sí** se puede leer con `EjecutarComandoCadena`, porque devuelve un solo escalar con las dos secciones unidas por `_` (una versión anterior de este análisis lo describía por error como dos conjuntos de resultados). El cliente separa por `_`, `;` y `|`. Si el detalle no tiene filas, el escalar completo es `NULL` (`""` tras la normalización).
- Los que devuelven un escalar delimitado (`...Csv`, `...PyCsv`) se leen con `EjecutarComandoCadena`; `uspAlumnoObtenerPorIdConFoto2` (texto más `Foto`) y `uspProductoObtenerStockPorId` (una fila) con `EjecutarComandoFila`; `uspUbigeoListar` (filas tipadas) con `EjecutarComandoLista`, que recibe el nombre del SP como sentencia y devuelve las filas.
- Para distinguir "sin fila" de un fallo: `""` frente a `None`. En existencias, una fila presente con stock `NULL` se normaliza a cero porque el SP usa `ISNULL(UnitsInStock, 0)`.
- Para volúmenes grandes no cargues todo en una respuesta: usa viajes de N registros (`ld-transferencia`, técnica 5).

### 3. Valida las entradas y la coherencia de la paginación

`uspCubsoPaginarCsvPy` usa `PARSENAME` después de reemplazar `|` por `.`.
Valida que el número de página y el tamaño sean positivos, establece un máximo
de aplicación y comprueba que el cálculo del desplazamiento no desborde el
tipo numérico. El orden por `CubsoId` es determinista si esa columna es única.
Las páginas profundas con `OFFSET` pueden ser costosas; si la interfaz lo
permite, considera paginar por clave sobre `CubsoId`. `uspCubsoContar` devuelve
el conteo como texto, y solicitar el conteo por separado de la página puede
producir resultados incoherentes si los datos cambian. Usa un resultado
numérico `COUNT_BIG` solo si la interfaz necesita el total; en caso contrario,
consulta `tamaño_de_página + 1` filas para determinar `has_more`. Si el conteo
y la página deben pertenecer a la misma instantánea, define la transacción y
el nivel de aislamiento requeridos.

El procedimiento de consulta de órdenes convierte en enteros las partes de
un rango delimitado sin validar el separador ni que `inicio <= fin`. Valida
ambas condiciones en el backend y también dentro del procedimiento si existen
otros clientes que lo llaman directamente. Además, arma la primera sección con
`SELECT @variable += ... ORDER BY`: SQL Server no garantiza el orden de esa
concatenación, así que el orden de las filas no es fiable. Une `Products` en el
detalle mientras el resto de los procedimientos usa `Producto`: confirma que
existen ambos objetos (por ejemplo, una vista o sinónimo) en la base desplegada.

**`uspCubsoListarPaginaTipada` (validado).** Coincide con
`cubso_records_provider.py`: parámetros `@AfterCubsoId`/`@PageSize`, un conjunto
con `CubsoId, Codigo, Descripcion, Precio` (`row[0]`..`row[3]`), orden por la clave
y `TOP (@PageSize)`. Rechaza `@PageSize` fuera de 1..501 con `THROW`, lo que cuadra
con el `limit + 1` del proveedor (máximo 500). Puntos a vigilar: el orden es
determinista solo si `CubsoId` es único (clave primaria); un `@AfterCubsoId`
negativo es válido y devuelve desde el inicio; el tope 501 está duplicado en el
SP y en `MAX_PAGE_SIZE`, y ambos deben cambiar juntos; el `THROW` llega a
Python como excepción de `pyodbc`, que el proveedor debe traducir a un error
HTTP controlado. A diferencia del heredado `uspCubsoPaginarCsvPy`, no trunca
`Descripcion` ni convierte `Precio` `NULL` en `0`.

### 4. Haz que las escrituras de órdenes sean atómicas y parseables

En el texto suministrado, `uspOrdenGrabarPyCsv` presenta estos riesgos:

- `@@IDENTITY` puede devolver una identidad creada por un desencadenador.
  Usa `SCOPE_IDENTITY()` o `OUTPUT INSERTED.OrderID`.
- El analizador de cantidad extrae exactamente un carácter; puede truncar
  cantidades de más de un dígito.
- **El precio unitario viene del cliente** (`@PrecioUnitario` se lee de la
  cadena) y no se contrasta con `Producto.UnitPrice`: quien llame al endpoint
  puede grabar una orden con precio arbitrario. Lee el precio en el servidor o
  valida que coincida con el vigente.
- `@orden` es `varchar(10)`: un `IdCliente|IdEmpleado` más largo se trunca sin
  error, y un `@Data` sin `_` o sin `|` provoca un error de `SUBSTRING`.
- La separación por delimitadores no admite delimitadores dentro de los
  valores y depende de `fnSplitString`. Valida campos vacíos/mal formados y
  todas las conversiones antes de escribir.
- La transacción explícita no tiene una ruta `TRY/CATCH` de reversión ni una
  política `XACT_ABORT`. Un error en ejecución puede dejar incierto el estado
  de la transacción para quien llama.
- La actualización de existencias debe validar, dentro de la misma
  transacción, que hay stock suficiente y que se afectaron las filas
  esperadas. De lo contrario, órdenes concurrentes podrían vender stock
  inexistente o aceptar cantidades inválidas.

Si más adelante se quiere un contrato más estricto, los parámetros tipados o con
valores de tabla reemplazan al `varchar(max)` delimitado. Conserva como una sola operación atómica los
cambios de orden, detalle y existencias. Define reintentos e idempotencia
antes de activar reintentos automáticos para esta escritura.

### 5. No uses la cadena de login como protocolo de credenciales

`uspUsuarioValidarLoginCsv` combina usuario y contraseña en un solo
`varchar(100)`, los separa por `|` y compara directamente el campo `Clave`.
El separador puede interferir con valores válidos y el límite conjunto de
caracteres reduce el dominio útil. Con el flujo actual, el navegador envía un
SHA-256 hexadecimal (64 caracteres), así que cabe en el límite y la columna
`Clave` contendría ese hash sin sal: quien lea la tabla o capture el hash puede
autenticarse con él. Verifica el contenido real de la columna. La concatenación
de retorno usa `+` sobre `Address` y `Correo`: si alguno es `NULL`, un login
correcto devuelve `NULL` y la aplicación lo trata como inválido. Usa `CONCAT` o
`ISNULL` y valida la presencia del separador. No
expongas este procedimiento sin cambios como nuevo punto de acceso de
autenticación. Prefiere el flujo de autenticación y verificación de hashes del
framework. Si la base de datos debe seguir siendo la autoridad, recibe usuario
y contraseña en parámetros separados y verifica un hash salado y no reversible
en una capa de autenticación establecida. No devuelvas campos derivados de
credenciales salvo que el punto de acceso esté autorizado para exponerlos.

### 6. Prefiere agregaciones basadas en conjuntos a cursores por identificador

`uspProductoListarPorCodigosCsv` recorre los identificadores y consulta el
producto individualmente. Un parámetro con valores de tabla (o una tabla
obtenida mediante otro análisis seguro de identificadores) y una unión por
conjuntos facilita la validación, el orden y el escalado. Define si los
identificadores inexistentes se omiten o se informan, conserva explícitamente
el orden original si es necesario y devuelve columnas tipadas.

### 7. Patrones comunes de los procedimientos de pantalla

Los SP de consulta y mantenimiento de los demos repiten estos patrones:

- **`FOR XML PATH('')` sin `TYPE`/`.value()`** escapa `&`, `<` y `>` en cualquier
  texto (`ProductName`, `CompanyName`, `CategoryName`, nombres de alumnos): el
  usuario vería `&amp;`. Usa `FOR XML PATH(''), TYPE).value('.', 'varchar(max)')`
  como hace `uspCubsoPaginarCsvPy`.
- **Filas con `NULL` desaparecen sin error.** En `'a' + NULL`, la concatenación es
  `NULL` y `FOR XML PATH` omite el elemento: un producto con `UnitsInStock`
  `NULL`, o un alumno sin `Correo`, no aparece en la grilla. Envuelve las
  columnas anulables con `ISNULL`/`CONCAT`.
- **Secciones vacías producen `NULL`.** Salvo `uspProductoListasCboCsv`, la
  mayoría no usa `ISNULL` por sección; un resultado vacío devuelve `NULL` y
  `EjecutarComandoCadena` lo convierte a `""`, igual que un error en la ruta
  de éxito. El cliente no puede distinguir "sin datos" de "falló".
- **Formatos distintos** (`¬` frente a `;`, con o sin anchos y tipos): el
  cliente debe saber qué formato espera cada SP. No mezcles en una misma
  pantalla procedimientos de formatos distintos sin documentarlo.
- **Uniones internas que ocultan filas**: `uspProductoListasCboCsv`,
  `Grabar3` y `Eliminar3` unen `Proveedor` y `Categoria` con `INNER JOIN`, así
  que los productos sin proveedor o categoría no se muestran.
- **Escrituras sin transacción ni `TRY/CATCH`**: `Grabar3` y `Eliminar3` ejecutan
  DML directo; el commit depende de `trx=True` en el wrapper, y un error de
  conversión llega como excepción, no como mensaje de dominio. `Grabar3` usa
  `@@IDENTITY` y no valida los 6 campos antes de escribir.
- **Parámetros `varchar` frente a columnas `int`**: `@Codigo` (de `fnSplitString`)
  se compara con `ProductID` o `IdAlumno` por conversión implícita, y un valor
  no numérico falla la consulta completa.

## Ejemplos para elegir la llamada

Con el wrapper `clienteSQL` suministrado, los procedimientos que devuelven un
único escalar pueden llamarse con `EjecutarComandoCadena`; para una fila
tipada, es preferible `EjecutarComandoFila`. No uses `EjecutarComandoCadena`
para conjuntos de filas. `uspOrdenConsultarPorRangoPyCsv` devuelve un solo
escalar y puede leerse con él, pero el resultado se separa por `_`, `;` y `|`:

```python
stock_row = db.EjecutarComandoFila(
    "dbo.uspProductoObtenerStockPorId",
    "ProductID",
    str(product_id),
)
stock = None if stock_row is None else (0 if stock_row[0] is None else stock_row[0])

count_text = db.EjecutarComandoCadena("dbo.uspCubsoContar")

orders_text = db.EjecutarComandoCadena(
    "dbo.uspOrdenConsultarPorRangoPyCsv", "IdOrdenes", f"{first_id}|{last_id}"
)  # "cabecera;anchos;tipos;filas_ordenes_" + "cabecera;anchos;tipos;filas_detalle"

saved_order = db.EjecutarComandoCadena(
    "dbo.uspOrdenGrabarPyCsv",
    "Data",
    validated_payload,
    trx=True,
)
```

Estos ejemplos ilustran los nombres de parámetros y la cantidad de resultados;
no corrigen los contratos SQL descritos arriba. `uspOrdenGrabarPyCsv` inicia y
confirma su propia transacción, por lo que debes verificar el efecto de
`trx=True` y los reintentos del wrapper con el procedimiento realmente
desplegado antes de depender de ellos.

## Lista de verificación para procedimientos futuros

- Registra la definición exacta desplegada, tipos de parámetros SQL,
  nulabilidad/valores predeterminados, cantidad de conjuntos, nombres/tipos de
  columnas y ejemplos con resultados vacíos y no vacíos.
- Comprueba que la forma de retorno corresponda al método `clienteSQL`
  elegido; prueba por separado varios conjuntos, escalar ausente, SQL `NULL` y
  errores de base de datos.
- Valida los valores de entrada tanto en el límite HTTP como en SQL; enlaza
  parámetros en vez de interpolarlos.
- Define límites de filas/bytes y orden determinista para páginas. Prueba
  primera/última/vacía, entradas inválidas o excesivas y cambios concurrentes.
- Para escrituras, prueba errores de conversión, duplicados/reintentos,
  reversión, valores de identidad, límites de stock/cantidad y llamadas
  simultáneas.
- Trata los resultados de procedimientos como datos, no como HTML seguro ni
  como cadenas CSV que necesariamente se puedan analizar.
