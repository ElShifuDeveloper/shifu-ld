---
name: ld-data
description: "Implementa la capa de datos para consultas paginadas, catálogo de archivos, CSV/texto por flujo y cargas mixtas: SQL Server/pyodbc, procedimientos, cursores, pandas, transacciones, codificación e idempotencia."
---

# LD_data

Diseña la capa que consulta y persiste datos para `ld-frontend` y `ld-backend`. Escoge el tipo de resultado según su consumo, tamaño y necesidad de preservar tipos, y no acoples el almacenamiento a un formato de transporte accidental. Entrada del paquete: [ld-project-coordinator](../ld-project-coordinator/SKILL.md).

## Qué leer según la tarea

| Tarea | Lee |
|---|---|
| Elegir `EjecutarComandoCadena`/`Fila`/`InsertMasivo…`, errores, `NULL` | [cliente-sql.md](./references/cliente-sql.md) |
| Saber qué devuelve un SP existente o revisar su riesgo | [stored-procedures-review.md](./references/stored-procedures-review.md) (26 SP) |
| Conectar una consulta a la fuente real, crear un SP nuevo, paginar por clave | [sql-sources.md](./references/sql-sources.md) |
| Parámetros, paginación, transacciones, rendimiento y pruebas | [sql-practices.md](./references/sql-practices.md) |
| CSV grande, carga masiva, bytes e imágenes | [csv-and-bytes.md](./references/csv-and-bytes.md) |
| Contrato y flujos de transferencia (los seis casos) | [transfer-contract.md](../ld-backend/references/transfer-contract.md) |

## Ejemplos

Base: [base/modAccesoDatos.py](./examples/base/modAccesoDatos.py) y [base/modUtilidades.py](./examples/base/modUtilidades.py) son los módulos reales de los proyectos LD (`clienteSQL`, `beLog`, `Log`, `Seguridad`, `Generador`, `JSON`, `XML`); se copian a `Modulos/`. Variante opcional con reintentos y errores por excepción: [mejorado/modAccesoDatos.py](./examples/mejorado/modAccesoDatos.py). Código adaptable: [pyodbc_access.py](./examples/pyodbc_access.py), [csv_bulk_import.py](./examples/csv_bulk_import.py), [csv_upload_handler.py](./examples/csv_upload_handler.py) y [sql/uspCubsoListarPaginaTipada.sql](./examples/sql/uspCubsoListarPaginaTipada.sql). Requieren adaptar procedimientos, SQL, validación de dominio y conexión al proyecto destino.

## Procedimiento

1. **Identifica la fuente real** (ORM, `clienteSQL`, alias, configuración externa, SP desplegado) antes de crear consultas; no infieras el esquema por nombres de archivo.
2. **Lee la definición del SP** y registra parámetros y tipos, forma del resultado, nulabilidad, orden y límites. El nombre de un archivo no siempre coincide con el objeto SQL declarado, y una respuesta `...Csv` no es CSV estándar.
3. **Decide en este orden**: reutilizar la fuente si ya cumple; adaptar sin alterar SQL si el contrato es inequívoco; crear un SP **nuevo e independiente** si no cumple; modificar uno existente solo con autorización explícita para ese objeto. "Conectar", "adaptar" o "hacer compatible" no son esa autorización.
4. **Elige el método según la forma del SP**: escalar o lista delimitada (`EjecutarComandoCadena`), fila (`EjecutarComandoFila`), bloque para insertar (`EjecutarInsertMasivoCsv`) o bytes desde el disco.
5. **Consulta solo lo necesario**: pagina en el origen con orden estable y clave de continuación; nunca descargues todo para paginar en JavaScript.
6. **Escribe con cuidado**: define quién administra `commit`/`rollback` (`trx=True` frente a un SP que abre su propia transacción), no reintentes escrituras sin idempotencia y prefiere `SCOPE_IDENTITY()`/`OUTPUT` a `@@IDENTITY`.
7. **Prueba** cero filas, primera y última página, `NULL`, Unicode, orden estable, cursores inválidos, lotes parciales y rollback.

## Reglas que no cambian

- Valores siempre como parámetros del driver; nombres de objetos dinámicos solo desde una lista permitida.
- Nada de credenciales en código, logs ni ejemplos. Un script SQL versionado no es un despliegue: aplica cambios a una base real solo con autorización explícita para ese entorno.
- El formato LD son las listas delimitadas (`¬`, `|`, `;`, `_`) que arma el SP y que el cliente separa con `split`; JSON solo para servicios de terceros. Como los separadores no se escapan, valida que ningún dato de usuario los contenga y prueba la ida y vuelta con `|`, `;`, `_`, `&`, tildes y vacíos.
- Los archivos viajan como bytes o flujos, no como texto delimitado ni Base64 combinado con metadatos.
- No confundas un `None` (falló la consulta) con `""` (sin datos o `NULL`): la vista responde distinto a cada uno.

## Checklist

- ¿Se verificó la definición real del SP y su forma de retorno?
- ¿Se reutilizó la fuente existente o se creó un SP nuevo, sin tocar uno existente sin permiso?
- ¿La paginación es por clave, con orden estable y tamaño máximo?
- ¿Los `NULL`, las fechas y el Unicode se serializan de forma explícita?
- ¿Las escrituras tienen transacción clara e idempotencia?
