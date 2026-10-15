# Estilo de salida (color y estructura)

Los comandos de Spec Kit no imponen formato a las respuestas del agente: sin reglas, todo sale como
un bloque blanco de texto y cuesta encontrar lo importante. Este documento fija el estilo LD para
**las respuestas del agente y los informes de los scripts del paquete**.

## En la respuesta del agente

La terminal de OpenCode colorea el markdown, así que la estructura ES el color:

1. **Encabezados cortos** (`##`) para separar bloques: resultado, pendientes, siguiente paso.
2. **Negritas** para lo que la persona debe leer primero (rutas, comandos, cifras, decisiones).
3. **Bloques de código** para comandos y salidas literales.
4. **Tablas** cuando hay que comparar (antes/después, requisito ↔ tarea, por spec).
5. **Semáforo con símbolo**, siempre con su texto al lado (nunca solo color):
   - `✅` hecho y verificado · `⚠️` atención, hay un pendiente · `❌` falló o bloquea · `ℹ️` dato/nota.
6. **Cierre accionable**: la última línea dice qué sigue (el comando exacto) o qué falta decidir.
7. **Nada de muros de texto**: si hay más de 10 líneas seguidas, conviértelo en lista o tabla.

No inventes sintaxis de color en el texto (códigos ANSI en la respuesta se leen como basura): el
color ya lo pone el tema de la terminal con el markdown.

## En los informes de los scripts del paquete

Los scripts (`iniciar_proyecto.py`, `validar_paquete.py`, `revisar_diseno.py`, `capturar_pantalla.py`,
`tiempos.py`) emiten color ANSI **solo cuando la salida es una terminal** y se apaga solo con
`NO_COLOR` o `TERM=dumb`; en tuberías, CI o pruebas la salida es texto plano (hay que poder compararla).

- `✔` verde: hecho · `⚠` amarillo: aviso · `✖` rojo: error · encabezados en negrita-cian.
- Los informes cuyo texto se compara en pruebas (`--version`, sincronización de archivos) usan
  `consola.decorar`: color por contenido **sin cambiar un carácter**.

Al pegar la salida de un comando en la conversación, respeta los símbolos y no reescribas los
mensajes: son parte del contrato de uso de los scripts.

## Qué NO cambia

- Las plantillas de Spec Kit y los comandos `/speckit.*` (son de Spec Kit: no se sustituyen).
- El contenido de los artefactos (`spec.md`, `plan.md`, `tasks.md`, `METRICS.md`): el estilo aplica a
  cómo se comunica, no a lo que se escribe en ellos.
- La regla de los datos: texto de usuario al DOM con `textContent` (principio III); esto es sobre la
  salida de la terminal, no sobre las pantallas de la aplicación.