# Catálogo de técnicas de transferencia LD

Cada técnica sale de un demo de `webpython`. El estilo es el de todos ellos: cadenas delimitadas y bytes,
variables globales, `async/await` recursivo (un viaje por llamada), respuestas `OK` / `Error - ...`,
`<progress>` más contadores. **Copia el patrón, no lo reescribas**: el código de [examples/](../examples/)
conserva los nombres y la estructura de los demos (`sizeBloque`, `nBloques`, `cBloques`, `enviarBloque…`,
`diccionario`, `grupoContador`, `registrosBloque`…).

## 1. Subir un archivo grande por bloques `I` / `P` (appDemo13)

- **Cliente:** `Math.floor(file.size / sizeBloque)` (+1 si hay resto) bloques de `sizeBloque` (en subida, `settings.LD_SIZE_BLOQUE` entregado por la página; 100 KB en el demo);
  `file.slice(inicio, fin)`; `FormData` con `Id`, `Nombre`, `Flag` (`I` el primero, `P` los demás), `Blob` y el
  token CSRF; envía el siguiente bloque solo cuando el servidor responde `OK`; avance con `<progress>`
  (`progreso.max = nBloquesTotal`) y `spnValida`. Arrastrar y soltar con `ondragover`/`ondrop`
  (`event.dataTransfer.items`).
- **Servidor:** `GrabarBloque`: ruta de la carpeta del registro; si `Flag == "I"` borra el archivo anterior;
  abre en `"ab"` y anexa el bloque; responde `OK`.
- **Código:** `CargaArchivos.js` (cliente), `Archivos.GrabarBloque` de `modPaquetes.py`, `GrabarBloque` de
  `views_transferencia.py`.
- **Ajustes de seguridad sobre el demo:** el nombre y la carpeta pasan por `Archivos.NombreSeguro`/`RutaSegura`
  (el demo une la ruta con lo que manda el cliente); `P` sin `I` previo se rechaza; tamaño máximo por bloque y por
  archivo; contenido validado por firma en el bloque `I`.
- **Reintentos:** reenviar un bloque `P` que el servidor ya anexó duplicaría bytes. Ante un fallo, reintenta el
  archivo completo desde su bloque `I` (así lo hace `CargaArchivos.js`).

## 2. Descargar imágenes: lotes de pequeñas y bloques de grandes (appDemo10_2, appDemo09, appDemo14 + extensión)

La descarga sigue la MISMA regla de decisión que la subida: `size <= sizeLote` (`settings.LD_SIZE_LOTE`) viaja
agrupado en un paquete de bytes; mayor, se pide por bloques de `sizeBloque` (`settings.LD_SIZE_BLOQUE`) que el
cliente une. Los demos solo bajaban iconos y miniaturas (todo cabía en lotes de 100 KB): la parte de bloques es
extensión, el inverso exacto de appDemo13 (allí el cliente corta con `slice`; aquí recibe los trozos y los une).

- **Cliente:** pide `nombre|size;nombre|size` (`ListarCodigosSize`); arma el plan con
  `Paquete.PlanificarViajes(items, sizeLote, sizeBloque, maxArchivosLote)` —los valores salen de los campos ocultos
  `hdfSizeLote`, `hdfSizeBloque` y `hdfMaxArchivosLote` que entrega `PantallaConsulta`, nunca a mano— y recorre un viaje por llamada:
  `lote` → `POST ObtenerPaquete` (`Nombres` = `a|b|c`) → `Paquete.Leer` → una imagen por registro;
  `bloque` → `GET ObtenerBloque?Nombre=&Indice=` → acumula `partes[nombre].push(blob)` y, en el último bloque
  (`bloque == nBloques - 1`), une con `new Blob(partes)` y comprueba que el tamaño coincida con el anunciado.
  Progreso por viaje (`progreso`, "Viaje x/n · c de n imágenes"). La descarga es idempotente: un viaje fallido se
  reenvía tal cual y la cola continúa donde quedó (los demos no tenían archivos que no cupieran en un lote).
- **Servidor:** `ObtenerPaquete` responde `application/octet-stream` acotado por `LD_SIZE_LOTE` y rechaza con
  `Error - ...` (texto) el lote que lo supere, que pida más de `LD_MAX_ARCHIVOS_LOTE` nombres, que incluya
  un archivo mayor o que solicite un nombre/archivo inexistente. Nunca omite archivos en silencio: los demos
  cortaban la respuesta y el cliente mostraba menos imágenes de las pedidas; `ObtenerBloque` usa
  `Archivos.LeerBloque`, que no carga el archivo completo en memoria. El cliente distingue éxito de error por el
  `Content-Type`.
- **Código:** `GaleriaLotes.js`, `ObtenerPaquete` y `ObtenerBloque` de `views_transferencia.py`, `ListarCodigosSize`.

## 3. Paquete de bytes (appDemo06–10, 14)

Formato y reglas en [formato-paquete.md](./formato-paquete.md). Es el código que los demos repiten copiado
(`byte1`, `byte2`, `nTexto`, `bytesRpta.extend(...)`, `blob.slice(x, x + size)`); aquí está extraído a
`Paquete.Crear`/`Paquete.Leer` (JavaScript, `Paquetes.js`) y `Paquete.Crear`/`Paquete.Leer` (Python,
`modPaquetes.py`).

## 4. Subir muchos archivos pequeños en lotes (extensión de 2 y 3)

Los demos usan el paquete para **bajar** archivos. Para **subir** muchos archivos pequeños en pocos viajes se usa
el mismo formato en sentido inverso: el cliente agrupa por tamaño (técnica 2), arma el paquete con
`Paquete.Crear(texto, blobs)` y lo envía en un `POST` (`GrabarLote`); el servidor lo abre con `Paquete.Leer`. No
existe un demo de esto: está marcado como extensión. Regla de decisión por archivo: **`size <= sizeLote`** (`settings.LD_SIZE_LOTE`, 512 KB por defecto)
va a un lote; **mayor** va por bloques `I`/`P` (técnica 1). Cada lote contiene como máximo
`LD_MAX_ARCHIVOS_LOTE` archivos (por defecto 200, ajustable en `settings.py`) y
respeta el límite de bytes; cada lote o bloque es un viaje de la misma cola.

**Orden de la cola (`Paquete.PlanificarViajes`, un solo recorrido, sin reordenar):** el planificador no depende de la
dirección: el mismo plan sirve para subir (`GrabarLote`/`GrabarBloque`) y para descargar (`ObtenerPaquete`/`ObtenerBloque`,
técnica 2); solo cambia la ruta de cada viaje.
1. Se recorren los archivos en el orden de la tanda con un lote abierto y su suma.
2. Archivo pequeño: entra al lote abierto si la suma sigue `<= sizeLote`; si no cabe, se cierra el lote y ese archivo abre el siguiente.
3. Archivo mayor que `sizeLote`: cierra el lote abierto, se corta en bloques de `sizeBloque` (`I` el primero, `P` el resto) y, cuando termina su último bloque, el recorrido sigue con los demás en un lote nuevo.
Ejemplo (límite 100): `a40 b50 c30 G250 d60 e40 f10` → lote `[a,b]`, lote `[c]`, bloques `G0 G1 G2`, lote `[d,e]`, lote `[f]`.

## 5. Consultar muchos registros por viajes (appDemo26, 26_2)

`ContarRegistros` (escalar) → `totalBloques = ceil(total / registrosBloque)` (`registrosBloque = 10000`) →
`ObtenerBloqueRegistros?indice=i&registros=n` por viaje (el SP `uspCubsoPaginarCsvPy` recibe `"indice|registros"` y
devuelve los registros separados por `;`) → se acumulan en `listaCubso` con las tres filas de metadatos de
`Gui.Grilla` y se pinta la grilla **una vez al final**. Se muestra el tiempo total. Código: `ViajesRegistros.js`
(sección A) y `views_registros.py`. Nota: el SP antepone `;` a cada registro, así que el primer elemento del
`split(";")` es vacío y se descarta.

## 6. Cargar muchos registros por viajes (appDemo28)

El CSV se lee con `FileReader.readAsText`; `ValidarTablaCampos` comprueba que las columnas existan; después se
envían `registrosBloque` registros por viaje (`data = filas.join(";")`) a `GrabarBloqueRegistros`, que ejecuta
`EjecutarInsertMasivoCsv(tabla, data, ";", ",")` (`executemany`). Código: `ViajesRegistros.js` (sección B).
Seguridad: el demo arma el `INSERT` con el nombre de tabla y de columnas que envía el cliente; usa una lista
permitida (`TABLAS_PERMITIDAS` en `views_registros.py`). Un CSV con comas o saltos de línea dentro de un campo no
se separa bien con `split` (ver `ld-data/references/csv-and-bytes.md`).

## 7. Descargar un archivo (appDemo13: ObtenerArchivo)

Dos casos, según el destino del archivo:

- **Guardarlo en el disco del usuario:** `FileResponse` con `as_attachment=True` y `filename`: un viaje, el servidor
  lee del disco por trozos (no lo carga entero en memoria) y el navegador lo guarda con su propio progreso. En el
  cliente basta un enlace o `window.location`; no hace falta `blob()`.
- **Usarlo dentro de la app (mostrar, previsualizar, editar):** bloques por índice (`ObtenerBloque` +
  `Archivos.LeerBloque`, técnica 2): el cliente acumula las partes, las une con `new Blob(partes)` y comprueba el
  tamaño anunciado. `blob()` de una sola respuesta deja el archivo ENTERO en la memoria del navegador: solo es
  aceptable con archivos menores que `LD_SIZE_LOTE`.

## 8. Vista previa antes de guardar (appDemo12)

El demo usa `FileReader.readAsDataURL` para una imagen. Con muchas imágenes usa `URL.createObjectURL(file)` y
libera cada URL con `URL.revokeObjectURL` al redibujar (`dibujarMiniaturas` en `CargaArchivos.js`).

## Convenciones de respuesta (todas las técnicas)

- Éxito de escritura: `OK`. Error de dominio: texto que empieza con `Error - ` (el cliente lo muestra tal cual).
- Descargas por lotes y bloques: el éxito viaja como bytes (`application/octet-stream`) y el error como texto
  `Error - ...`; el cliente decide por `Content-Type` (patrón de `GaleriaLotes.js`).
- Lectura sin datos: cadena vacía. Un error HTTP no es un resultado de dominio.
- Listas para `Gui.Grilla`: nombres, anchos y tipos antes de los datos (`Nombre del Archivo|Size;600|100;str|int;...`).
- Los separadores (`;`, `|`, `¬`, `_`) no se escapan: ningún dato de usuario (nombres de archivo, carpetas) puede
  contenerlos. `NombreSeguro` los rechaza.
