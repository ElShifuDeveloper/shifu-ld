---
name: ld-charts
description: "Crea gráficos de barras y columnas (2D/3D) en canvas o SVG, con interacción de detalle, animaciones con requestAnimationFrame y comandos de voz, consumiendo las listas delimitadas de los SP en el estilo LD (appDemo17–25). Úsalo para visualizar datos agregados, descargar el gráfico como PNG/SVG o animar texto e imágenes."
---

# LD_charts

> Metodología **LD** (cadenas delimitadas, bytes, bloques, lotes y empaquetado) creada por **Luis Dueñas Huaroto**; documentada aquí para agentes.

Gráficos y animaciones del navegador en el estilo base LD: JavaScript nativo, sin librerías, datos que llegan de un SP como texto delimitado. Basado en `appDemo17`–`appDemo25` de `webpython`.

Entrada del paquete: [ld-project-coordinator](../ld-project-coordinator/SKILL.md). El formato de la lista está en [datos-delimitados.md](../ld-crud/references/datos-delimitados.md) y la vista Django sigue [ld-crud](../ld-crud/SKILL.md); la apariencia general, [ld-design](../ld-design/SKILL.md).

## Cuándo usar cada técnica

| Necesidad | Técnica | Demo de origen |
|---|---|---|
| Barras o columnas simples, exportar a imagen | `<canvas>` 2D + `toDataURL` | appDemo19, 21 |
| Efecto 3D o animación de crecimiento | `<canvas>` con `requestAnimationFrame` | appDemo20, 22 |
| Gráfico escalable, interactivo (clic, teclado) o exportable como vector | SVG | appDemo23, 24, 25 |
| Navegar de un gráfico a su detalle | SVG + parámetro en la URL | appDemo25 |
| Texto o sprite en movimiento, comandos de voz | `requestAnimationFrame` + Web Speech | appDemo17, 18 |

Prefiere SVG cuando el usuario deba interactuar o el gráfico se imprima; canvas cuando haya muchos elementos o animación continua.

## Contrato de datos

Los demos llaman a SP `...PyCsv` que devuelven **un escalar** con filas separadas por `;` y campos por `|`; las tres primeras filas son nombres, anchos y tipos. Ejemplos verificados contra su definición:

| SP | Datos (desde la fila 4) |
|---|---|
| `uspCategoriaProductosStockPyCsv` | `Categoria\|Total Stock` |
| `uspCategoriaProductosStock2PyCsv` | `Id\|Categoria\|Total Stock` (el valor está en la columna 3) |
| `uspProductoListarStockPorCategoriaPyCsv` (`@CategoryID`) | `Producto\|Stock` |

La vista es la de siempre (`EjecutarComandoCadena` y `HttpResponse`); sigue las reglas de `ld-crud` (rutas desde `settings`, `None` → 500). El detalle por categoría recibe `idCat` por GET: valida que sea entero en el servidor.

Para volúmenes grandes trae los datos por viajes de N registros ([ld-transferencia](../ld-transferencia/SKILL.md), técnica 5); las listas delimitadas siguen siendo el formato. JSON solo si un tercero lo exige.

## Patrón de la pantalla

1. HTML: `<canvas>` (o `<svg>`) con `role="img"` y `aria-label`, y al lado un `div` con `Gui.Grilla(...)` con los mismos datos. Esa tabla es la alternativa accesible del gráfico y el demo ya la incluye; no la quites. Incluye `hdfRaiz` (lo usa la grilla).
2. `window.onload`: `fetch` de la vista, `parseLista`, `aDatosGrafico`, dibujar, y llenar la grilla con la misma lista.
3. Un botón de descarga (`toDataURL` o SVG serializado).
4. Texto de estado para error, vacío y carga; no dejes el lienzo negro sin mensaje.

Ejemplos listos (con prueba en Node, `node test-lista-delimitada.js`):

- [lista-delimitada.js](./examples/lista-delimitada.js): `parseLista`, `aDatosGrafico`, `escala`, `alturaFila`.
- [grafico-barras-canvas.js](./examples/grafico-barras-canvas.js) y [grafico-barras-svg.js](./examples/grafico-barras-svg.js).
- [animacion.js](./examples/animacion.js): bucle por tiempo, `prefers-reduced-motion` y comandos de voz.

## Problemas que los demos tienen y estos ejemplos evitan

- **`&amp;` parte los registros (solo SQL Server).** Los SP que usan `FOR XML PATH('')` escapan `&`, `<` y `>`, y la entidad termina en `;`, el separador de registros: "Condimentos & Salsas" se lee como dos filas y la gráfica sale mal. `parseLista` decodifica el texto completo antes de separarlo; la solución de fondo es corregir el SP con `TYPE` y `.value()` (ver `ld-data`). En canvas, sin decodificar, se vería el texto `&amp;`.
- **División por cero.** `escalaH = ancho / maxStock` da `Infinity`/`NaN` si todos los valores son 0 o no hay filas. Usa `escala()` y muestra "Sin datos".
- **Desborde.** Los demos fijan 50 px por barra y 120 px por columna en un lienzo de 1000×600: más de ~10 categorías o ~8 columnas se salen del dibujo. Calcula el paso según la cantidad (`alturaFila`) o pagina.
- **SVG armado con cadenas.** `html += "...data-nombre='" + nombre + "'"` y `svg.innerHTML = html` rompen el SVG con una comilla en el nombre y ejecutan código si el dato contiene marcado. Usa `createElementNS`, `setAttribute` y `textContent`.
- **Etiqueta de valor equivocada.** En `appDemo25/GraficoBarras3D.js` la etiqueta del valor imprime el nombre (`campos[1]`) en lugar del stock (`campos[2]`).
- **Descarga SVG.** El demo usa `Blob` con tipo `text/plain`; usa `image/svg+xml`. Si el SVG no lleva `xmlns` en su etiqueta, el archivo no abre fuera del navegador.
- **Estado entre pantallas por `sessionStorage`** (`IdCategoria`): se pierde al abrir el detalle en otra pestaña y no se puede compartir. Pasa el id por la URL.
- **Animación.** `posX += 10` por fotograma depende de la tasa de refresco; los bucles de appDemo20/22 nunca terminan. Usa `crearAnimacion` (por tiempo, con `detener()`).
- **Voz.** `webkitSpeechRecognition` solo existe en Chromium/Safari, pide HTTPS o `localhost` y permiso del usuario. En appDemo17, `ejecutarComandoVoz` usa `this.value` (que no es el botón) y `ultimoComando` es una global implícita; `alert(event.error)` interrumpe en cada "no-speech". Ofrece siempre el botón como alternativa.

## Accesibilidad y diseño

- El gráfico no es la única vía a los datos: deja la grilla o una tabla.
- No uses solo color: etiqueta cada barra con su valor; mantén contraste (amarillo/blanco sobre negro cumple, azul sobre negro no para texto).
- Barras interactivas con `tabindex="0"`, `role="button"`, `aria-label` y activación con Enter y Espacio (ver el ejemplo SVG).
- Respeta `prefers-reduced-motion`: no animes el crecimiento si el usuario lo pidió.
- Define tamaño y relación de aspecto que funcionen en pantallas pequeñas (`viewBox` en SVG; en canvas, escala por `devicePixelRatio`).

## Checklist

- ¿Maneja respuesta vacía, error HTTP, valores 0 y filas de más?
- ¿Decodifica o evita el escape XML antes de separar por `;`?
- ¿Los textos del usuario entran por `textContent`, no por `innerHTML`?
- ¿Hay una alternativa en tabla y etiquetas de valor?
- ¿La animación va por tiempo, se puede detener y respeta "reducir movimiento"?
- ¿El detalle recibe un id validado por la URL y se valida en el servidor?
