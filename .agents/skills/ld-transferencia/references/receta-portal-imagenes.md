# Receta: portal para arrastrar muchas imágenes, ver su vista previa y guardarlas en una carpeta

Caso de uso: "una web donde se arrastran varias imágenes de distintos tamaños para guardarlas en el sistema de archivos
dentro de una carpeta con nombre". Se resuelve **sin base de datos y sin JSON**, con las técnicas 1, 2, 3, 4 y 8 del
[catálogo](./tecnicas.md).

## Piezas (todas en [examples/](../examples/))

| Pieza | Archivo | Origen |
|---|---|---|
| Pantalla | `CargaArchivos.html` | appDemo13 (arrastrar y soltar, `progreso`, `spnValida`) |
| Cliente de carga | `CargaArchivos.js` | appDemo13 (bloques `I`/`P`) + lotes por tamaño |
| Cliente de consulta | `GaleriaLotes.js` | appDemo10_2 (lotes de descarga) + bloques simétricos a la subida (extensión) |
| Paquetes (cliente) | `Paquetes.js` → `Static/scripts/Paquetes.js` | appDemo06–10, 14 |
| Paquetes y archivos (servidor) | `modPaquetes.py` → `Modulos/modPaquetes.py` | idem + `NombreSeguro`, `EsImagen` |
| Vistas | `views_transferencia.py`, `urls_transferencia.py` | appDemo13 y appDemo10 |

## Contrato (cadenas y bytes)

| Operación | Ruta | Entrada | Respuesta |
|---|---|---|---|
| Crear carpeta | `CrearCarpeta` (POST) | `Carpeta` | `OK` o `Error - La carpeta ya existe` / `Error - Nombre de carpeta no válido` |
| Bloque de un archivo grande | `GrabarBloque` (POST) | `Carpeta`, `Nombre`, `Flag` (`I`/`P`), `Blob` | `OK` o `Error - ...` |
| Lote de archivos pequeños | `GrabarLote` (POST) | `Carpeta`, `Blob` = paquete | `OK` o `Error - ...` |
| Listar carpetas | `ListarCarpetas` (GET) | — | `Carpeta\|Imagenes\|Fecha;300\|100\|150;str\|int\|str;nombre\|n\|fecha;...` (más recientes primero) |
| Listar archivos | `ListarArchivos` (GET) | `Carpeta` | `Nombre del Archivo\|Size;600\|100;str\|int;a.jpg\|3;...` |
| Tamaños para agrupar | `ListarCodigosSize` (GET) | `Carpeta` | `a.jpg\|3;b.jpg\|5` |
| Lote de descarga | `ObtenerPaquete` (POST) | `Carpeta`, `Nombres` = `a\|b\|c` | paquete de bytes (`octet-stream`); `Error - ...` (texto) si los datos superan `LD_SIZE_LOTE` o un archivo no cabe en un lote |
| Bloque de descarga | `ObtenerBloque` (GET) | `Carpeta`, `Nombre`, `Indice` | bytes del bloque (`octet-stream`) o `Error - ...` (texto) |
| Un archivo a disco | `ObtenerArchivo` (GET) | `Carpeta`, `Nombre` | bytes (`FileResponse` con `as_attachment`) |

## Flujo en el navegador

1. **Agregar** (`agregarArchivos`): arrastrar y soltar o selector; se rechazan los que no son imagen o superan el tamaño
   máximo, con mensaje que nombra el archivo; los nombres repetidos reciben un sufijo `(2)`, `(3)`…
2. **Vista previa** (`dibujarMiniaturas`): `URL.createObjectURL`, botón *Quitar* por imagen, nombre con `textContent`.
   Nada se guarda hasta pulsar *Grabar*.
3. **Grabar** (`grabarCarpeta`): valida el nombre de carpeta, llama a `CrearCarpeta` y arma la cola de viajes
   (`prepararCola` → `Paquete.PlanificarViajes`): un solo recorrido en orden; los de `LD_SIZE_LOTE` o menos se acumulan en un lote mientras la suma no lo supere, el que no cabe abre el siguiente lote y un archivo mayor cierra el lote abierto, se parte en bloques y, al terminar su último bloque, el flujo continúa con los demás.
4. **Enviar** (`procesarCola`): un viaje por llamada, con `progreso` y "Viaje x/n"; se detiene ante un error y deja
   reintentar sin volver a crear la carpeta; *Cancelar* corta la cola.
5. **Consultar** (`consultarCarpeta` de `GaleriaLotes.js`): plan de viajes con `Paquete.PlanificarViajes` y los
   límites de `settings` (campos ocultos `hdfSizeLote`, `hdfSizeBloque` y `hdfMaxArchivosLote` de `PantallaConsulta`): las imágenes que
   caben en un lote viajan en paquetes y las mayores por bloques que el cliente une con `new Blob(partes)`;
   progreso por viaje y reintento del viaje fallido (la descarga es idempotente).

## Servidor

- `settings.py`: `LD_REPOSITORIO_ROOT = BASE_DIR / "repositorio"` (nunca una ruta del cliente ni personal).
- Copia `modPaquetes.py` a `Modulos/` y `Paquetes.js` a `Static/scripts/`; incluye `urls_transferencia.py` en el `urls.py`
  de la app.
- Escrituras por `POST` con CSRF (`{% csrf_token %}` en la página y el token en cada `FormData`).
- Límites: copia el bloque de `settings_transferencia.py` (`LD_SIZE_LOTE` 512 KB, `LD_SIZE_BLOQUE` 256 KB y `LD_MAX_ARCHIVOS_LOTE` 200 por defecto, con variables de entorno
  y validación). Las vistas `PantallaCarga` y `PantallaConsulta` los entregan a sus páginas (`hdfSizeLote`, `hdfSizeBloque`, `hdfMaxArchivosLote`) y `CargaArchivos.js`
  y `GaleriaLotes.js` los leen: se cambian en un solo lugar y valen para las dos direcciones. Agrega los tres campos ocultos a la plantilla de galería del proyecto que la integra. Si cambias un tamaño, ajusta el cuerpo máximo del proxy; `DATA_UPLOAD_MAX_MEMORY_SIZE` de Django no limita archivos.
  El campo nuevo es `<input id="hdfMaxArchivosLote" type="hidden" value="{{ MaxArchivosLote }}">` en ambas plantillas; `PantallaCarga` y `PantallaConsulta` deben incluir `MaxArchivosLote` en el contexto.
- Estimación de llamadas: subida `2` (CrearCarpeta y cierre) `+ lotes + bloques`; galería de descarga `1 + lotes + bloques`. Con 12 fotos de 1,25 MB: 100 KB → 18, 256 KB → 8, 512 KB → 6, 1 MB → 4 llamadas.

## Límites que fija el código (ajústalos a la especificación)

**Sin límites de negocio por defecto:** `maxArchivo`, `maxArchivos` y `maxTotalTanda` valen 0 (sin tope) y el servidor no limita el
tamaño por archivo (`settings.LD_MAX_ARCHIVO` es opcional). Un límite se añade solo si la especificación lo pide; no lo inventes. Sin
tope no significa sin control: vigila el espacio en disco y define la cuota en el despliegue, no en el código. El máximo técnico de archivos por paquete es `LD_MAX_ARCHIVOS_LOTE` (200 por defecto, configurable de 1 a 10 000). Son límites **técnicos**
del protocolo `LD_SIZE_LOTE` y `LD_SIZE_BLOQUE` (512 KB y 256 KB por defecto, **parametrizables** en `settings.py`; el servidor los hace cumplir como `MAX_LOTE` y `MAX_BLOQUE` y el cliente los lee de la página). La descarga tiene los mismos topes: cada lote lleva como mucho `LD_SIZE_LOTE` de datos, cada bloque `LD_SIZE_BLOQUE` y los archivos mayores que un lote viajan por bloques (no hay límite de descarga por archivo).

## Qué probar

- Límites (con tus valores de `settings`): máximo de archivos por lote y uno más (configura `LD_MAX_ARCHIVOS_LOTE` a un número pequeño para la prueba), además de 0 bytes, 1 byte, `LD_SIZE_LOTE` − 1, `LD_SIZE_LOTE`, `LD_SIZE_LOTE` + 1, y múltiplos de `LD_SIZE_BLOQUE` ± 1 (bloques);
  un lote que llena justo el límite y otro que lo pasa por 1 byte (el servidor debe rechazarlo); cambia un valor por variable de entorno y confirma que cliente y servidor lo siguen.
- Nombres: con tildes y eñes (el paquete cuenta bytes), repetidos, con `..`, rutas absolutas y caracteres de control.
- Archivo que no es imagen aunque se llame `.jpg`; paquete truncado; carpeta que ya existe.
- Corte de red en medio de un archivo grande: el reintento vuelve a empezar por el bloque `I`.
- Descarga: carpeta con una foto mayor que `LD_SIZE_LOTE` → la galería la muestra completa (viaja por bloques, el cliente la une y el tamaño coincide con el anunciado); un lote que pida un archivo mayor que `LD_SIZE_LOTE` o supere el límite → el servidor lo rechaza con `Error - ...` en texto, nunca lo omite en silencio; corte de red en medio de una descarga por bloques → el reintento reenvía ese viaje y la cola continúa donde quedó.
- Que la carpeta quede dentro de `LD_REPOSITORIO_ROOT` con nombres maliciosos y con dos personas creándola a la vez.

## En un proyecto con Spec Kit

En el plan: almacenamiento = sistema de archivos, sin base de datos; transferencias con `ld-transferencia`. Las tareas
llevan `[ld-transferencia]` para el cliente y las vistas, y `[ld-design]` para estados y accesibilidad.
