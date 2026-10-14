---
name: ld-frontend
description: "Implementa el frontend JavaScript nativo del estilo LD: pantallas con General.js (Gui, Popup, Validacion, SVG), fetch con async/await, datos como cadenas delimitadas, progreso por viajes, estados y errores. Para subir o bajar archivos, bloques, lotes y paquetes de bytes usa ld-transferencia; este skill cubre además el cliente del protocolo alternativo JSON/cursor para integraciones con terceros."
---

# LD_frontend

Implementa en el navegador el estilo de los appDemo: JavaScript nativo, variables globales y funciones `async` que usan `fetch`, texto delimitado en lugar de JSON, y los componentes de `General.js`. Primero localiza el punto de acceso HTTP y confirma el contrato real con el backend; no inventes formatos ni cambies separadores sin actualizar el servidor. [ld-design](../ld-design/SKILL.md) cubre la apariencia. Entrada del paquete: [ld-project-coordinator](../ld-project-coordinator/SKILL.md).

## Estilo base LD

- Cada pantalla es `Pantalla.html` + `Pantalla.js` con `window.onload = async function(){...}`; los controles se usan por su `id` global (`txtNombre`, `divProducto`).
- `fetch(ruta)` → `rptaHttp.ok` → `await rptaHttp.text()` → `split("_")`, `split("¬")`, `split("|")`. Respuesta vacía = error o sin datos; `Error - ...` = error de dominio que se muestra tal cual. Las escrituras son `POST` con `FormData` y el token CSRF.
- Las listas se pintan con `Gui.Grilla` (tres filas de metadatos: nombres, anchos y tipos) y los combos con `Gui.Combo`. Los formularios usan `Gui.ValidarControles`, `Gui.ObtenerValoresControles`, `Gui.MostrarValoresControles` y `Gui.LimpiarControles` con clases `M`/`R`/`L`/`E`/`D`; las ventanas, `Popup`; las validaciones en línea, `Validacion`.
- Los viajes (bloques, lotes, registros por bloques) usan funciones recursivas `async`, `<progress>` y contadores `c...`/`n...`.

## Qué leer según la tarea

| Tarea | Lee |
|---|---|
| Subir o bajar archivos o imágenes, arrastrar y soltar, vista previa, bloques `I`/`P`, lotes, paquetes de bytes, registros por viajes | [ld-transferencia](../ld-transferencia/SKILL.md) |
| Pantalla de consulta o mantenimiento (`Gui`, popup, grilla) | [ld-crud](../ld-crud/SKILL.md) |
| Gráficos y animaciones | [ld-charts](../ld-charts/SKILL.md) |
| WebSocket con sesión, reconexión y render seguro | [ld-realtime](../ld-realtime/SKILL.md) |
| Estados, accesibilidad y diseño adaptable | [ld-design](../ld-design/SKILL.md) |
| **Alternativa para integraciones con terceros:** cliente JSON/cursor | [transfers-client.md](./references/transfers-client.md) |

## Ejemplos y base

[base/General.js](./examples/base/General.js) es el `General.js` real de los proyectos LD (`Gui`, `Popup`, `Validacion`, `SVG`): se copia a `Static/scripts/General.js`. No tiene objeto `Http`: usa `fetch`. Los demás ejemplos (`pagination.js`, `transfer-workflows.js`, `upload-chunks.js`, `websocket-chat.js`) son del protocolo alternativo JSON/cursor y de WebSocket; requieren que el backend configure sus proveedores.

## Procedimiento

1. Identifica controles DOM, funciones de `General.js`, puntos de acceso HTTP y formato de datos.
2. Separa la paginación de la tabla (`Gui.Grilla`, solo sobre lo ya recibido) del tamaño de bloque o de lote de una transferencia.
3. Maneja explícitamente las respuestas HTTP no exitosas, la cadena vacía y `Error - ...`; no declares éxito antes de tiempo.
4. Cuida la memoria: procesa o muestra por viajes cuando el volumen lo pida y libera las URLs de objeto (`URL.revokeObjectURL`).
5. Valida tamaño y selección; reporta progreso por viaje; permite cancelar y reintentar si el flujo lo requiere.
6. Prueba límites y verifica el resultado completo, no solo la barra de progreso.

## Estado, errores y seguridad

- Un estado por operación: `idle`, `uploading`, `finalizing`, `completed`, `failed`, `cancelled`.
- No pases al siguiente viaje si el anterior falló, salvo que el protocolo lo permita. El progreso son los viajes **confirmados por el servidor**.
- Los mensajes y datos de usuarios (nombres de archivo, textos) entran al DOM con `textContent` o nodos DOM, nunca como HTML sin escapar. Ojo: `Gui.Grilla` arma HTML con los datos que recibe; el servidor debe entregar datos sin marcado.

## Checklist

- ¿La pantalla sigue el patrón de los demos y usa `General.js` en lugar de funciones propias equivalentes?
- ¿Se maneja error de red, HTTP, cadena vacía y `Error - ...` por separado?
- ¿Las transferencias usan viajes con progreso, y el cliente se detiene ante un error?
- ¿Se liberan las URLs de objeto y no se inserta HTML sin escapar?
