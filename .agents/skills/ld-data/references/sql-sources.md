# Fuentes de datos y SP nuevos

Cómo conectar una consulta nueva a la fuente real del proyecto y cuándo crear un SP. Para la forma de cada SP existente, ver [stored-procedures-review.md](./stored-procedures-review.md).

## Conectar una consulta nueva a una fuente existente

Antes de crear consultas o procedimientos, identifica la fuente real siguiendo
la configuración del proyecto: ORM/repositorio, cliente de acceso a datos,
alias de base de datos, configuración externa/variables de entorno y llamadas
existentes. No imprimas ni copies credenciales a código, logs, ejemplos o
respuestas. No infieras el esquema por nombres de archivos: inspecciona el
modelo, la consulta/SP desplegado o el contrato verificable de la fuente.

Decide en este orden:

1. **Reutilizar la fuente existente** si ya devuelve las columnas necesarias y
   puede aplicar filtros, orden estable y paginación en el origen. Añade un
   adaptador que transforme sus filas a la lista delimitada que consume el cliente
   (o, para un tercero, a JSON); no dupliques datos ni consultas.
2. **Adaptar sin alterar SQL** cuando la fuente heredada sea acotada y su
   contrato pueda interpretarse sin ambigüedad. Documenta límites y
   conversiones. No descargues el conjunto completo para paginarlo en Python o
   JavaScript.
3. **Crear una nueva consulta/SP** cuando la fuente actual no pueda cumplir el
   contrato, como paginar establemente columnas tipadas o devolver el cursor
   siguiente. Si el punto de partida es un SP existente, crea una copia
   independiente con nombre nuevo y reformúlala para el contrato requerido;
   conserva intacto el objeto original y sus consumidores. En PostgreSQL la
   rutina es una **función** (`LANGUAGE plpgsql`, `RETURNS text`) que arma la
   misma cadena delimitada; el mapeo T-SQL ↔ PL/pgSQL está en
   [postgres.md](./postgres.md).
4. **Modificar el SP existente solo si el usuario lo solicita de forma
   explícita**, identificando el objeto y el cambio autorizado. No interpretes
   “conectar”, “adaptar” o “hacer compatible” como permiso para alterar el
   contrato existente.

Para la decisión, registra nombre/alias de la fuente, objeto SQL real,
parámetros y tipos, columnas/resultados, nulabilidad, permisos, orden y clave
de continuación, límites y política de valores vacíos. Verifica esa
información en el código o en la base de datos destino sin revelar secretos.
Entrega el nuevo SP como script versionable (preferiblemente con nombre
preciso y extensión `.sql`) y documenta el contrato. La creación del archivo
SQL no equivale a desplegarlo: aplica cambios a una base de datos solo con
autorización explícita para ese destino y entorno. Prueba el proveedor con
resultados vacíos, primera/última página, cursores inválidos, valores `NULL`,
Unicode y orden estable antes de conectarlo a la API.

## Paginar muchos registros: viajes de N registros (estilo LD)

El estilo de los demos (appDemo26) es: `uspCubsoContar` devuelve el total y `uspCubsoPaginarCsvPy` recibe `"indice|registros"` y
devuelve el bloque como cadena `;`/`|`; el cliente pide viaje tras viaje (10 000 registros por viaje) y pinta la grilla al
final. Código y reglas en [ld-transferencia](../../ld-transferencia/SKILL.md) (técnica 5). Endurécelo en la vista, no
reemplazando el SP: `indice >= 1` y `registros` entre 1 y un máximo (el SP falla con página cero y con datos mal
formados), y en el SP, `ORDER BY` por una clave única (`CubsoId`). Limitaciones conocidas del SP: pagina con `OFFSET`
(las páginas profundas cuestan más), trunca `Descripcion` a 45 caracteres y convierte un `Precio` `NULL` en `0`
(ver [stored-procedures-review.md](./stored-procedures-review.md)).

## Alternativa tipada por clave (para integraciones con terceros)

Cuando un tercero necesita columnas tipadas y un cursor, existe `dbo.uspCubsoListarPaginaTipada`: el script portable está en [uspCubsoListarPaginaTipada.sql](../examples/sql/uspCubsoListarPaginaTipada.sql) y el adaptador Django en [cubso_records_provider.py](../../ld-backend/examples/cubso_records_provider.py). Contrato, verificado contra la definición del SP:

- parámetros `@AfterCubsoId` (clave de continuación; `NULL` devuelve la primera página) y `@PageSize` (entre 1 y 501: el proveedor pide `limit + 1` con `limit <= 500` para calcular `has_more`; si cambias `MAX_PAGE_SIZE`, cambia también ese tope en el SP);
- un único conjunto de resultados `CubsoId`, `Codigo`, `Descripcion`, `Precio`, en ese orden, que coincide con `row[0]`..`row[3]` del proveedor;
- orden estable por la clave primaria y filtro `CubsoId > @AfterCubsoId`;
- `Codigo`, `Descripcion` y `Precio` pueden ser `NULL`: el consumidor debe tolerarlo.

Configuración del proveedor (la vista que lo expone debe exigir sesión, ver [ld-security-session](../../ld-security-session/SKILL.md)):

```python
LD_RECORD_PAGE_PROVIDER = "miapp.cubso_records_provider.page_cubso_records"
LD_RECORDS_CONNECTION_FACTORY = "miapp.cubso_records_connection.open_records_connection"
```

La fábrica de ejemplo lee `LD_RECORDS_ODBC_CONNECTION_STRING` del entorno; configúrala en el gestor de secretos del despliegue, nunca en `settings.py` versionado. Para PostgreSQL, la fábrica gemela es [pg_records_connection.py](../../ld-backend/examples/pg_records_connection.py), que lee `LD_RECORDS_PG_DSN`. No reutilices un alias Django que apunte a SQLite u otra base distinta: la conexión debe apuntar a la base del proyecto anfitrión. Revisa el script y despliégalo en cada entorno mediante su propio proceso de cambios y con autorización explícita.
