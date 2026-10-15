# PostgreSQL (psycopg 3) en el estilo LD

Segunda fuente de datos soportada, además de SQL Server. **El formato LD no cambia**: las cadenas
delimitadas (`¬`, `|`, `;`, `_`) que arma la función y que el cliente separa con `split`, los
archivos como bytes y el contrato del cliente (`None` = falló, `""` = sin datos o `NULL`). Cambia el
motor y, con él, el driver y algunas construcciones SQL.

Requisitos: **PostgreSQL 14 o superior** y `psycopg[binary] >= 3.2`. El despliegue toma la conexión
de una variable de entorno (`LD_RECORDS_PG_DSN`); nunca credenciales en código ni en el repositorio.

## El cliente gemelo

`examples/postgres/modAccesoDatos.py` es el **gemelo** de `examples/base/modAccesoDatos.py`: la misma
clase `clienteSQL` y los mismos métodos, para que las vistas no cambien
(`con.EjecutarComandoCadena("uspX", "Param", valor)`). `iniciar_proyecto.py --bd postgres` lo copia a
`Modulos/modAccesoDatos.py`.

| Método | Para | Devuelve |
|---|---|---|
| `EjecutarComandoCadena(func, param, valor, trx=False)` | función que devuelve un escalar (listas `...Csv`) | el escalar; `""` si no hay fila o es `NULL`; `None` si falló |
| `EjecutarComandoFila(func, param, valor)` | función que devuelve una fila | la fila; `""` si no hay fila; `None` si falló |
| `EjecutarComandoUnaLista(sql)` / `EjecutarComandoLista(sql)` | una sentencia SQL (no una función) | textos con cabecera y filas unidas por `,` / `fetchall()` |
| `EjecutarInsertMasivoCsv(tabla, csv, sepReg, sepCampo)` | cargar un bloque (`executemany`) | `"OK"` o `"Error: ..."` |
| `EjecutarInsertMasivoLista(tabla, campos, lista)` | cargar filas ya separadas | `"Datos Copiados Correctamente"` o `"Error: ..."` |
| `ValidarTablaCampos(tabla, campos)` | comprobar columnas antes de cargar | `""` si coinciden; `"Error - ..."` si no |

### No implementados en PostgreSQL

`EjecutarComandoListas` y `EjecutarComandoVariosDF` dependen de `cursor.nextset()` (varios conjuntos de
resultados en una sola llamada), que **PostgreSQL no devuelve**. El gemelo **no los define**: si una
vista los usa, falla con `AttributeError` en vez de devolver `None` (que se confundiría con un fallo de
consulta). Alternativas: una llamada por conjunto, o una función que devuelva una sola cadena con las
secciones unidas por `_` (patrón LD, como `uspOrdenConsultarPorRangoPyCsv`).

## Configuración

Mismo archivo `clave=valor` que en SQL Server. Se arma un DSN de psycopg:

| Clave | Uso |
|---|---|
| `servidor` | `host` |
| `puerto` | `port` (por defecto `5432` si falta) |
| `basedatos` | `dbname` |
| `usuario`, `clave` | `user`, `password` |
| `sslmode` | opcional (`require`, `verify-full`, …) |
| `driver` | se ignora (lo usa el cliente de SQL Server) |

## De T-SQL a PL/pgSQL

| Necesidad | SQL Server | PostgreSQL |
|---|---|---|
| Marcador de parámetro | `?` | `%s` |
| Llamar a la rutina | `EXEC uspX @P=?` | `SELECT uspX(%s)` (función) · `CALL uspX(%s)` (procedimiento) |
| Leer un escalar | `cursor.fetchval()` | `cursor.fetchone()[0]` |
| Varios conjuntos | `cursor.nextset()` | no existe → una llamada por conjunto |
| Límite de filas | `SELECT TOP (@n) …` | `… LIMIT n` |
| Paginación | `ORDER BY … OFFSET … FETCH NEXT` | `ORDER BY … LIMIT n OFFSET m` (o keyset `WHERE id > %s`) |
| Identidad tras INSERT | `SCOPE_IDENTITY()` / `OUTPUT INSERTED` | `INSERT … RETURNING id` |
| Agregar texto | `FOR XML PATH('')` (escapa `&`→`&amp;`) | `string_agg(col, ';')` (**sin escape**) |
| Concatenar con NULL | `'a' + NULL = NULL` | `'a' \|\| NULL = NULL` (usa `COALESCE`/`concat()`) |
| Partir una lista | `fnSplitString`, `PARSENAME` | `string_to_array`, `unnest`, `split_part` |
| Error controlado | `THROW 50001, '…', 1` | `RAISE EXCEPTION '…' USING ERRCODE='…'` |
| Bloque con errores | `BEGIN TRY … END CATCH`, `SET XACT_ABORT ON` | `BEGIN … EXCEPTION WHEN OTHERS THEN … RAISE` |
| Esquema por defecto | `dbo.` | `public.` (o `search_path`) |

## Tipos

| SQL Server | PostgreSQL |
|---|---|
| `varchar(max)`, `nvarchar(max)` | `text` (PostgreSQL es UTF-8 nativo: no hay `nvarchar`) |
| `int IDENTITY` | `integer GENERATED ALWAYS AS IDENTITY` (o `serial`) |
| `datetime2` | `timestamptz` |
| `bit` | `boolean` |
| `money`, `decimal` | `numeric` |
| `varbinary(max)` | `bytea` |

## Una función que devuelve la cadena delimitada

El patrón LD en PL/pgSQL usa `string_agg` (no `FOR XML PATH`):

```sql
CREATE OR REPLACE FUNCTION uspProductoListarCsv()
RETURNS text LANGUAGE plpgsql AS $$
DECLARE resultado text;
BEGIN
    SELECT string_agg(ProductoId || '|' || Nombre, ';' ORDER BY ProductoId)
      INTO resultado
      FROM Producto;
    RETURN COALESCE(resultado, '');   -- sin filas o NULL: cadena vacía, no NULL
END $$;
```

- `string_agg` **no** escapa `&`, `<` ni `>`: el problema de `&amp;` de SQL Server (`FOR XML PATH`)
  no existe aquí. Sigue valiendo la disciplina de separadores (ningún valor puede contener `¬`, `|`,
  `;` ni `_`) y la de `NULL` (`||` con `NULL` da `NULL` → envuelve con `COALESCE`/`concat`).

## Transacciones

psycopg 3 usa `autocommit=False`. **Un error aborta la transacción**: hay que hacer `rollback()` antes
de ejecutar otra sentencia en la misma conexión. El gemelo abre **una conexión por llamada** y la
cierra (rollback implícito); `EjecutarComandoCadena(..., trx=True)` confirma la escritura. Para una
operación con varios pasos, usa `with psycopg.connect(dsn) as con:` (confirma al salir, revierte si hay
excepción) y no repitas el patrón de «commit solo en algunos caminos».

## Errores (SQLSTATE)

Lee `e.sqlstate` (atributo de las excepciones de psycopg): transitorios de conexión `08*`, `40001`
(fallo de serialización) y `40P01` (deadlock); permanentes `23505` (único), `42*` (sintaxis/objeto
inexistente) y `57014` (consulta cancelada). Si adoptas la variante con reintentos del cliente
(`mejorado/`), clasifica por `sqlstate`, no por el texto del mensaje.

## Carga masiva

`executemany` sirve para lotes acotados. Para volúmenes grandes, `COPY` es más rápido y admite
delimitadores personalizados (`;`/`|`) coherentes con el formato LD:

```python
with cursor.copy("COPY Producto (ProductoId, Nombre) FROM STDIN WITH (FORMAT text, DELIMITER '|', NULL '')") as copy:
    for fila in filas:
        copy.write_row(fila)
```

Valida cabecera, tipos y límites como en [csv-and-bytes.md](./csv-and-bytes.md).

## Pruebas

Sin un servidor PostgreSQL disponible, prueba solo la lógica pura (armado del DSN, de la sentencia
`SELECT funcion(%s)` y del `INSERT`, y la clasificación de nombres). Las pruebas de integración se
activan con la variable de entorno `LD_TEST_PG_DSN`; nunca dejes cadenas de conexión en el código.

## Estados de la rutina SQL

Igual que en SQL Server: entrega la rutina como script versionable (extensión `.sql`) y documéntala;
aplicarla a una base real exige autorización explícita para ese entorno. El tope de página
`1..501` de `uspCubsoListarPaginaTipada` está duplicado en la función y en `MAX_PAGE_SIZE` del
proveedor: cámbialos juntos.