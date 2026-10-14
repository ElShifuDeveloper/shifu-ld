---
name: ld-transferencia
description: "Implementa transferencias de archivos y de datos al estilo LD de los appDemo: subida y descarga simétricas por bloques con indicador I/P o por índice, lotes de archivos pequeños en paquetes de bytes, galerías que descargan por viajes (las imágenes grandes en bloques que el cliente une), consultas y cargas masivas de registros por viajes con progreso. Siempre con cadenas delimitadas y bytes, no con JSON. Úsalo para subir o descargar archivos o imágenes, arrastrar y soltar, vista previa, carpetas en el sistema de archivos, carga masiva de CSV o consultas de muchos registros."
---

# LD_transferencia

Cómo mueven archivos y volúmenes de datos los proyectos LD: **cadenas delimitadas y bytes**, en **viajes** secuenciales de tamaño acotado, con progreso. Es el estilo de `appDemo13` (bloques), `appDemo10` (lotes y paquetes de bytes), `appDemo26` y `appDemo28` (registros por viajes). No uses JSON, `multipart` por archivo completo ni un protocolo nuevo para esto: copia el patrón del demo (el código está en `examples/` con sus nombres originales). Entrada del paquete: [ld-project-coordinator](../ld-project-coordinator/SKILL.md).

En navegador, `File`/`Blob` solo representan archivos que la persona seleccionó o soltó; la página no puede explorar rutas arbitrarias del disco local. El backend opera sobre su propio repositorio, configurado por el proyecto. La transferencia agrupa bytes en paquetes o bloques; no implica crear un ZIP.

## Qué técnica usar

| Necesidad | Técnica | Demo | Código |
|---|---|---|---|
| Subir un archivo grande | Bloques de `LD_SIZE_BLOQUE` con `Flag` `I`/`P` | appDemo13 | `CargaArchivos.js`, `GrabarBloque` |
| Subir muchos archivos pequeños | Lotes por tamaño en un paquete de bytes (extensión) | appDemo10 en sentido inverso | `CargaArchivos.js`, `GrabarLote` |
| Subir una mezcla de tamaños | Un recorrido en orden: pequeños en lote hasta `LD_SIZE_LOTE`, el que no cabe abre el siguiente lote, el grande va por bloques y el flujo continúa | appDemo13 + 10 | `Paquete.PlanificarViajes`, `prepararCola`, `procesarCola` |
| Mostrar o descargar muchas imágenes | Misma regla que la subida: `PlanificarViajes` con lotes de `LD_SIZE_LOTE`; las mayores viajan por bloques que el cliente une | appDemo10_2, 09, 14 + extensión | `GaleriaLotes.js`, `ObtenerPaquete`, `ObtenerBloque` |
| Descargar un archivo a disco | `FileResponse` con `as_attachment` (un viaje; el navegador lo guarda sin pasar por la memoria de la app) | appDemo13 | `ObtenerArchivo` |
| Descargar un archivo grande para usarlo en la app | Bloques por índice: `Archivos.LeerBloque` en el servidor, el cliente acumula y une con `new Blob(partes)` | Extensión (inverso de appDemo13) | `ObtenerBloque`, `GaleriaLotes.js` |
| Consultar muchos registros | `ContarRegistros` y bloques de N registros | appDemo26_2 | `ViajesRegistros.js` (A) |
| Cargar muchos registros | `ValidarTablaCampos` y bloques de N registros | appDemo28 | `ViajesRegistros.js` (B) |
| Vista previa antes de guardar | `URL.createObjectURL` (no `readAsDataURL`) | appDemo12 | `dibujarMiniaturas` |

Detalle de cada técnica: [tecnicas.md](./references/tecnicas.md). Formato exacto del paquete: [formato-paquete.md](./references/formato-paquete.md). Caso completo (portal de imágenes con carpeta nombrada): [receta-portal-imagenes.md](./references/receta-portal-imagenes.md).

## Código base (copiar al proyecto, sin renombrar)

- `examples/Paquetes.js` → `Static/scripts/Paquetes.js` (objeto `Paquete`: `Leer`, `Crear`, `PlanificarViajes` —sirve para subir y para bajar—, `AgruparPorTamano`, `CantidadBloques`, `ParametroEntero`). Su prueba es `test-paquetes.js`.
- `examples/modPaquetes.py` → `Modulos/modPaquetes.py` (clases `Paquete` y `Archivos`). Su prueba es `test_modPaquetes.py`.
- Vistas: `views_transferencia.py` (incluye `PantallaConsulta` y `ObtenerBloque` para la descarga simétrica) y `views_registros.py`; pantalla: `CargaArchivos.html` (la de la galería lleva los mismos campos ocultos `hdfSizeLote`, `hdfSizeBloque` y `hdfMaxArchivosLote`); rutas: `urls_transferencia.py`.

## Reglas

0. **«Streaming» en LD = metodología por chunks (bloques), en las DOS direcciones.** Cuando una especificación o una persona pida *streaming*, *transmisión*, *progreso* o *archivos grandes*, significa enviar y recibir por bloques secuenciales con progreso (el estilo `I`/`P`, los lotes y los viajes de registros), no una conexión abierta ni un protocolo nuevo. La regla de decisión es la misma al subir y al bajar: `size <= LD_SIZE_LOTE` viaja agrupado con otros en lotes (pocos viajes); mayor, se parte en bloques de `LD_SIZE_BLOQUE` (muchos viajes pequeños) que el receptor une. El formato del bloque puede ser **cadena delimitada** (registros) u **octet-stream** (bytes), según el dato; ambos son válidos. `StreamingHttpResponse`/`FileResponse` solo son una forma de leer del disco por trozos en el servidor, no la definición.
1. **Cadenas y bytes.** Listas con `;`/`|`/`¬`/`_`, tres filas de metadatos para `Gui.Grilla`, bytes con `application/octet-stream`. JSON solo en servicios para terceros (`ld-realtime`).
2. **Un viaje por llamada, en orden.** `async/await` recursivo; avanza solo con `OK`; `<progress>` y contadores; un fallo detiene la cola y permite reintentar.
3. **Límites paramétricos, una sola fuente.** `settings.LD_SIZE_LOTE` (datos máximos de un lote de archivos pequeños; por defecto **512 KB**), `settings.LD_SIZE_BLOQUE` (tamaño de cada bloque `I`/`P`; por defecto **256 KB**) y `settings.LD_MAX_ARCHIVOS_LOTE` (máximo de archivos en cada lote; por defecto **200**, configurable de 1 a 10 000), con variables de entorno homónimas y validación al arrancar (`examples/settings_transferencia.py`). Aplican a subida **y descarga**. Las vistas aplican los topes y las pantallas entregan al navegador `hdfSizeLote`, `hdfSizeBloque` y `hdfMaxArchivosLote`; el cliente debe leerlos y pasarlos a `Paquete.PlanificarViajes`. No mantengas límites duplicados en las vistas ni en JavaScript. Los 100 KB de los demos eran para iconos y miniaturas: con fotos casi nada cabe en un lote y la tanda se llena de viajes (12 fotos de 1,25 MB: 16 viajes con 100 KB, 4 con 512 KB). Antes de fijar los valores estima las llamadas: subida `2 + lotes + bloques`; galería de descarga `1 + lotes + bloques` (`Paquete.PlanificarViajes(...).length` en el cliente, que sirve para las dos direcciones). Registros: 10 000 por viaje.
   **Límites reales del servidor:** los de `LD_SIZE_*` que comprueban las vistas y, en producción, el cuerpo máximo del proxy (nginx `client_max_body_size`, IIS `maxAllowedContentLength`; déjalo por encima de `max(LD_SIZE_LOTE, LD_SIZE_BLOQUE)` más la sobrecarga multipart). `DATA_UPLOAD_MAX_MEMORY_SIZE` de Django **no** limita los archivos (solo cuenta los campos de texto) ni `FILE_UPLOAD_MAX_MEMORY_SIZE` (solo decide memoria o disco): no los uses para esto.
4. **Longitud en bytes.** El texto del paquete se mide en bytes UTF-8 (los demos la miden en caracteres y fallan con tildes).
5. **Nunca confíes en el cliente:** nombres y carpetas por `NombreSeguro`/`RutaSegura`; contenido de imágenes por firma (`EsImagen`); en consultas e inserciones, lista permitida de tablas y columnas. Los ejemplos de imagen validan imágenes, no cualquier tipo de archivo. No hay límites de negocio por defecto por tamaño total o cantidad de archivos de una tanda; aplica los que pida el dominio en cliente y servidor. Además de los topes de bytes, `LD_MAX_ARCHIVOS_LOTE` limita cada lote en el servidor y `PlanificarViajes` lo respeta también en el cliente.
6. **Reintentos:** en la subida, un bloque `P` no se reenvía solo (duplicaría bytes); se reinicia el archivo desde `I`. Los lotes sí se pueden reenviar. En la descarga todos los viajes son idempotentes (`Archivos.LeerBloque` devuelve los mismos bytes para el mismo índice y un lote se vuelve a leer igual): el viaje fallido se reenvía tal cual y la cola continúa donde quedó, sin reiniciar el archivo.
7. **Escrituras por `POST` con CSRF**, rutas desde `settings`, nada de rutas personales ni secretos. CSRF no autentica ni autoriza; las vistas de referencia no agregan autenticación propia. Al integrarlas, protege lectura y escritura con `login_required`/permisos adecuados y restringe el repositorio al ámbito autorizado.

## Procedimiento

1. Elige la técnica en la tabla y copia su código (cliente y servidor) con sus nombres.
2. Define el contrato en cadenas (qué devuelve cada ruta) antes de conectar las capas.
3. Ajusta límites a la especificación y valida en el servidor lo que el cliente ya valida.
4. Prueba tamaños límite, nombres hostiles, paquete truncado y corte de red (lista en la receta).

## Checklist

- ¿Se reutilizó el patrón del demo en lugar de inventar funciones o un protocolo nuevo?
- ¿Todo viaja como cadena o bytes, y los archivos grandes por bloques?
- ¿La descarga sigue la misma regla de decisión que la subida (≤ lote en paquete, > lote por bloques que el cliente une) y los tamaños salen de settings en las dos pantallas?
- ¿El avance se muestra por viaje y el cliente se detiene ante un error?
- ¿Nombres, rutas, contenido y tamaños se validan en el servidor?
- ¿La longitud del paquete se cuenta en bytes y ambos lados usan el mismo formato?
