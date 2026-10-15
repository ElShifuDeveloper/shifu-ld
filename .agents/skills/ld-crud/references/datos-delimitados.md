# Datos delimitados y SP del ejemplo

Fuente única del formato de las listas de los SP y del contrato de los SP del ejemplo de mantenimiento. Lo enlazan [ld-crud](../SKILL.md), [ld-charts](../../ld-charts/SKILL.md) y [ld-realtime](../../ld-realtime/SKILL.md).

## Contrato de datos delimitado

Los SP `...Csv` devuelven una sola cadena (con `EjecutarComandoCadena`):

| Separador | Significado |
|---|---|
| `¬` | entre registros |
| `\|` | entre campos |
| `_` | entre conjuntos de resultados (listas) |

Ejemplo de `ObtenerListas`: `grillaProductos_proveedores_categorias`, donde cada parte usa `¬` y `|`. En JS: `rpta.split("_")`, luego `split("¬")` para cada parte.

**Formato de la lista de `Gui.Grilla`** (verificado en `General.js` y en `uspOrdenConsultarPorRangoPyCsv`): las tres primeras filas son metadatos y desde la cuarta van los datos.

| Fila | Contenido | Ejemplo |
|---|---|---|
| 1 | nombres de columna | `Id Orden\|Fecha Orden\|Cliente` |
| 2 | anchos en píxeles; el prefijo `C` marca una columna con combo de filtro | `120\|100\|C300` |
| 3 | tipos de columna | `int\|str\|str` |
| 4 y siguientes | datos | `10248\|04/07/1996\|VINET` |

El separador de registros lo indica el parámetro `sepRegistro` (`"¬"` en el CRUD de ejemplo; `;` en los SP `...PyCsv`). Si la lista llega vacía o con menos de 4 filas, la grilla no se arma.

No todos los SP usan las 3 filas de metadatos:

| Formato | SP de ejemplo |
|---|---|
| nombres, anchos y tipos + datos (`¬`) | `uspProductoListarCsv`, `uspProductoListasCboCsv`, `uspDACPListas2Csv` |
| nombres, anchos y tipos + datos (`;`) | `uspOrdenConsultarPorRangoPyCsv`, `uspCategoriaProductosStockPyCsv` |
| solo nombres + datos (para convertir a JSON con `JSON.SerializarCsv`) | `uspProductoListar3Csv`, `uspProductoObtenerPorId3` |
| sin metadatos (lista para un combo `id\|nombre`) | proveedores y categorías de `uspProductoListasCboCsv` |

Reglas:

- Una respuesta vacía `""` significa error del servidor o del SP; el JS debe mostrar un mensaje y no seguir.
- Un texto que empieza con `Error` (el login lo usa) es un error de dominio; muéstralo tal cual.
- Estos separadores no se escapan: ningún dato de usuario puede contenerlos. Valida en el servidor antes de grabar y rechaza `¬`, `|` y `_` en campos de texto libre, o usa JSON si eso es un requisito.
- No uses este formato para volúmenes grandes ni cuando la consulta pueda devolver texto libre. Para eso, ver `ld-data`.

## Procedimientos del ejemplo (contrato verificado)

Verificado contra las definiciones de `SPs` (ver [el análisis](../../ld-data/references/stored-procedures-review.md)):

| SP | Entrada | Respuesta |
|---|---|---|
| `uspProductoListasCboCsv` | ninguna | 3 secciones unidas por `_`: grilla de productos (3 filas de metadatos + datos), proveedores `id\|nombre` y categorías `id\|nombre`, con registros separados por `¬` |
| `uspProductoObtenerPorId2` | `@ProductID` | un escalar `id\|nombre\|proveedor\|categoria\|precio\|stock`; sin producto, vacío |
| `uspProductoGrabar3Csv` | `@Data` = los mismos 6 campos; `id` vacío inserta, con valor actualiza | `grilla_id` |
| `uspProductoEliminar3Csv` | `@ProductID` | `grilla_id`; borra físicamente y responde igual aunque el id no exista |

Detalles que condicionan el código:

- El orden de los controles con clase `M` del formulario debe ser exactamente el orden de los 6 campos.
- Grabar y Eliminar necesitan `trx=True`: el SP no abre transacción y el wrapper solo hace commit con ese indicador.
- Riesgos de los SP que afectan a la pantalla (texto escapado `&amp;` por `FOR XML PATH` —solo SQL Server; en PostgreSQL `string_agg` no escapa—, filas con `NULL` que desaparecen de la grilla, uniones internas que ocultan productos, `Eliminar3` que falla por clave foránea o responde igual si el id no existe): ver la sección 7 del [análisis](../../ld-data/references/stored-procedures-review.md) y muéstralos al usuario cuando apliquen.
- Las vistas devuelven 500 cuando `clienteSQL` devuelve `None` (fallo del SP); el JS lo detecta con `rptaHttp.ok`.
