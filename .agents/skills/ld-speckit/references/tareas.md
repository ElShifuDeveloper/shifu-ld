# Contrato vertical y tareas por capa

## Contrato por historia (`contracts/`)

```markdown
## Contrato: [nombre de la historia]
| Aspecto | Definición |
|---|---|
| Interacción | actor, acción, estado inicial y resultado visible |
| SP / datos | nombre real del SP, parámetros y tipos, forma del resultado (escalar, filas, separadores `¬`/`|`/`_`), `NULL`, orden |
| Endpoint | ruta, método, parámetros, respuesta, códigos de error, sesión requerida |
| Límites | volumen, tamaño de página, concurrencia, idempotencia |
| Seguridad | quién puede, qué se audita, qué no se expone |
| Aceptación | entrada concreta y resultado comprobable |
```

La fila "SP / datos" solo se llena **leyendo la definición**; si la rutina no existe o no coincide, la historia
incluye la tarea de crearlo. Si la feature no usa base de datos relacional —o usa PostgreSQL (por defecto) o SQL Server,
según `.ld/config.json`—, esa fila describe el almacén y la rutina que correspondan (por ejemplo, la estructura de
carpetas en el sistema de archivos; en PostgreSQL, la **función** `plpgsql` que arma la cadena delimitada).

## Tareas por historia y capa (`tasks.md`)

Orden dentro de una historia: datos, servidor, navegador, integración. Cada tarea lleva ruta de archivo
y, entre corchetes, el skill que aplica:

```markdown
## Fase 3: Historia 1 – Mantener productos (P1) 🎯 MVP
**Prueba independiente**: crear, editar y eliminar un producto desde la pantalla y ver la grilla actualizada.

- [ ] T010 [US1] [datos] Leer `uspProductoGrabar3Csv` y documentar entrada/salida en `specs/001-productos/contracts/productos.md` (ld-data)
- [ ] T011 [P] [US1] [seguridad] Proteger las vistas con `@autenticacion` y `POST` + CSRF en `appProductos/views.py` (ld-security-session)
- [ ] T012 [US1] [servidor] Vistas `ObtenerListas`, `GrabarProducto`, `EliminarProducto` y rutas en `appProductos/views.py`, `appProductos/urls.py` (ld-crud)
- [ ] T013 [P] [US1] [pantalla] `Mantenimiento.html` y `Mantenimiento.js` con popup y grilla; parte de `pantalla-base.html` y cierra con `revisar_diseno.py` sin errores y capturas clara, oscura y móvil revisadas (ld-crud, ld-design)
- [ ] T014 [US1] [integración] Recorrido: carga, nuevo, editar, grabar vacío, grabar válido, eliminar y error del servidor; registrar el resultado en `quickstart.md`
```

Reglas: una tarea modifica una capa; las transferencias de archivos y de volúmenes usan `[ld-transferencia]`; las marcadas `[P]` no comparten archivo; ninguna tarea cambia un SP
existente sin una tarea previa de autorización; la última tarea de cada historia es el recorrido de
integración.

**Tareas `[pantalla]`:** su descripción siempre nombra el criterio de cierre de diseño: partir de `ld-design/examples/pantalla-base.html`
(`main.ld-pagina` > `section.ld-tarjeta`, sin `style=` ni elementos sueltos en `<body>`), `python scripts/revisar_diseno.py <pantalla>.html`
sin errores y las capturas de `capturar_pantalla.py` (clara, oscura y móvil) revisadas, con márgenes y alineación consistentes. La
integración de la historia (`[integración]`) anota el resultado en `quickstart.md`. Si el paquete no está a mano, la tarea lo dice en lugar
de omitir la revisión.

**Definición de terminado:** el cambio existe, su prueba se ejecutó y su resultado se anotó (qué se corrió y
qué salió). Una tarea no se marca por haber escrito código.
