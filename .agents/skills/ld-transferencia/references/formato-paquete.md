# Formato del paquete de bytes LD

```
[2 bytes: n = longitud del texto en bytes] [texto UTF-8 de n bytes] [bytes del archivo 1] [bytes del archivo 2] ...
```

- **Texto:** un registro por archivo, registros separados por `;` y campos por `|`. El **último campo de cada
  registro es el tamaño en bytes** del archivo (así el receptor sabe dónde cortar). Ejemplo: `foto1.jpg|20432;foto2.png|8120`.
- **Cabecera:** `n = byte1 * 256 + byte2` (máximo 65 535 bytes de texto). `Paquete.Crear` rechaza textos
  más largos; si hay muchos archivos, usa más lotes.
- **Límite de elementos:** `settings.LD_MAX_ARCHIVOS_LOTE` define el máximo de archivos por lote (por defecto 200,
  configurable entre 1 y 10 000). `Paquete.PlanificarViajes` cierra el lote al alcanzar ese límite, incluso si todavía
  caben más bytes; el servidor valida el mismo máximo.
- **Respuesta HTTP:** `application/octet-stream`. En el cliente se lee con `blob()`.
- **Validación al leer:** los tamaños declarados deben sumar exactamente los bytes recibidos; un paquete truncado,
  con bytes sobrantes o con un tamaño no numérico se rechaza (`Paquete.Leer` en ambos lenguajes).

## Diferencias con los demos (decididas a propósito)

| Demo | Aquí | Motivo |
|---|---|---|
| `nTexto = len(texto)` (caracteres) | longitud en **bytes** UTF-8 | El cliente lee `nTexto` bytes: con una tilde o una eñe el texto se corta o se desplaza. |
| `byte1 = int(nTexto / 255)`, `byte2 = nTexto % 255` (base 255; appDemo10, 14) | base 256 | Base estándar; un par cliente-servidor nuevo debe usar el mismo criterio en ambos lados. La base 255 es autoconsistente hasta `n = 65279`; por encima `byte1` llega a 256 y `bytes([...])` falla. |
| appDemo06–08: un solo byte de cabecera (texto ≤ 255) | dos bytes | Un byte limita el texto a 255; con 2 caben ~65 000 bytes. |
| Texto decodificado con `String.fromCharCode` | `TextDecoder("utf-8")` | `fromCharCode` no decodifica UTF-8. |
| Sin validar tamaños | validación completa | Evita mostrar o guardar archivos incompletos. |

## Interoperabilidad con un appDemo (legado)

Los dos formatos **no son compatibles byte a byte**: un paquete de los demos (base 255, longitud en
caracteres, texto leído con `String.fromCharCode`) no lo lee `Paquete.Leer`, ni al revés. Al integrar
una pantalla o un endpoint heredado, la regla es:

- **Opción A (recomendada): moderniza cliente y servidor a la vez.** Si tocas algo que hoy usa el
  formato de los demos, cambia los dos extremos al formato de este kit (`Paquete.Crear`/`Leer`) en el
  mismo cambio y **no mezcles formatos en una misma pantalla**. Los demos solo son correctos con texto
  ASCII: con una tilde o una eñe ya cortan mal el texto y las imágenes, así que migrarlos al kit también
  corrige ese defecto.
- **Puente de migración (transitorio):** mientras un extremo siga en el formato de los demos, lee ese
  paquete con `Paquete.LeerLegacy` (está en `modPaquetes.py` y en `Paquetes.js`) en lugar de reescribir
  el demo. `LeerLegacy` reproduce el formato antiguo tal cual (base 255, longitud en caracteres, texto
  Latin-1) y por eso hereda sus límites: solo es fiable con texto ASCII y hasta `n = 65279`. Úsalo como
  paso de una migración hacia `Paquete.Crear`/`Paquete.Leer`, no como formato de trabajo.

## Agrupar por tamaño

El plan de una tanda **mixta** (subida o descarga) lo arma `Paquete.PlanificarViajes(items, sizeLote, sizeBloque, maxArchivosLote)` con los valores de `settings` (`LD_SIZE_LOTE`, `LD_SIZE_BLOQUE`, `LD_MAX_ARCHIVOS_LOTE`) entregados por la página: pequeños en lotes dentro de ambos límites, mayores por bloques, en un recorrido y en orden (ver `tecnicas.md`, técnicas 2 y 4).

`Paquete.AgruparPorTamano(items, limite, maxArchivosLote)` queda solo para listas **homogéneas** donde todo cabe en un lote (por ejemplo, miniaturas de tamaño fijo); pasa los límites de `settings`, no los dupliques. Los 100 KB de los demos eran para iconos. Cierra un lote cuando agregar el siguiente superaría el límite de bytes o de archivos; un elemento mayor que el límite de bytes forma su propio lote. (El demo reinicia el total en 0 al cerrar un grupo, lo que deja pasar lotes mayores que el límite.)

## Ejemplo con Python (servidor)

```python
from Modulos.modPaquetes import Paquete

texto = ";".join("%s|%d" % (nombre, len(datos)) for nombre, datos in archivos)   # nombre|size
respuesta = HttpResponse(Paquete.Crear(texto, [d for _, d in archivos]), content_type="application/octet-stream")

registros, listaBytes = Paquete.Leer(request.FILES["Blob"].read())               # ValueError si el paquete no es válido
```

## Ejemplo con JavaScript (cliente)

```js
var paquete = await Paquete.Leer(await rptaHttp.blob());       // { registros: [[nombre, size], ...], blobs: [Blob, ...] }
var envio = Paquete.Crear("a.jpg|3;b.png|5", [blobA, blobB]);  // Blob listo para FormData.append("Blob", envio)
```
