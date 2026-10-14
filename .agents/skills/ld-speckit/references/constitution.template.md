<!--
Sync Impact Report
==================
Version change: (none) → 1.0.0
Bump rationale: Ratificación inicial a partir de la plantilla del skill ld-speckit
  ({{ORIGEN}}).

Modified principles: ninguno (alta inicial de los principios I–VIII).

Added sections: Core Principles I–VIII, Restricciones adicionales, Flujo de desarrollo,
  Governance.

Removed sections: none

Follow-up TODOs: none
-->
# {{PROJECT_NAME}} Constitution

## Core Principles

### I. Estilo base primero
Las pantallas, vistas y servicios nuevos MUST seguir el patrón del proyecto: apps
Django con `views.py`/`urls.py`, HTML y JavaScript nativo, `General.js`, `LD.css` (tema moderno compatible con las clases de los demos) y
procedimientos almacenados accedidos con `clienteSQL`. No se mezclan dos formatos de
datos en una misma pantalla. No se introduce un framework de frontend salvo mediante
una enmienda a esta constitución; las librerías de **solo diseño** (CSS, iconos, fuentes, Three.js) de un skill de diseño externo elegido en `.ld/diseno.json` no cuentan como framework siempre que no toquen datos, rutas ni lógica. Los datos viajan como cadenas delimitadas (`¬`, `|`,
`;`, `_`) y como bytes; el JSON se reserva para servicios que consumen terceros. Los
archivos y los volúmenes grandes se mueven por viajes con progreso (bloques `I`/`P`,
lotes por tamaño, paquetes de bytes y registros por bloques), según el skill
`ld-transferencia`.

**Razón**: la uniformidad con los proyectos LD existentes reduce la carga
cognitiva, permite reutilizar `General.js`/`LD.css` y hace que cualquier pantalla
nueva sea reconocible y mantenible por el mismo equipo.

### II. Contratos antes que código
Cada historia MUST tener un contrato vertical acordado antes de implementarla, que
cubra: interacción, datos, endpoint, límites, seguridad y aceptación. Ninguna capa
fija un formato que otra capa no haya acordado.

**Razón**: acordar el contrato completo por adelantado evita que frontend, backend y
datos diverjan y que el trabajo se rehaga al integrar.

### III. Seguridad por defecto (innegociable)
- Todo endpoint MUST exigir sesión cuando la aplicación tiene inicio de sesión.
- Las escrituras MUST ir por `POST` con CSRF.
- El texto que viene de usuarios MUST entrar al DOM como texto (`textContent`),
  nunca como HTML.
- Las sesiones MUST guardarse en el servidor.

**Razón**: estos cuatro puntos eliminan las clases de fallo más comunes (acceso no
autenticado, CSRF y XSS) sin depender del criterio caso por caso.

### IV. Datos con cuidado (innegociable)
- Antes de usar un procedimiento almacenado MUST leerse su definición real.
- Un procedimiento existente MUST NOT modificarse ni desplegarse sin autorización
  explícita para ese objeto y ese entorno; si no cumple el contrato, se crea uno
  nuevo e independiente.
- Los valores que llegan a SQL MUST ir como parámetros, nunca interpolados.
- Las escrituras MUST definir su transacción y ser idempotentes cuando puedan
  repetirse.

**Razón**: la base de datos es compartida y potencialmente de producción; leer antes
de usar y no tocar lo existente sin autorización protege a consumidores que no
vemos, y los parámetros e idempotencia previenen inyección y duplicaciones.

### V. Sin secretos en el repositorio
Credenciales, cadenas de conexión y rutas personales MUST salir de `settings` o del
entorno, nunca del código, los logs ni los ejemplos.

**Razón**: un secreto versionado queda expuesto para siempre en el historial; la
configuración por entorno es el único canal seguro.

### VI. Probar el recorrido
Cada historia MUST tener una prueba de extremo a extremo, y las funciones puras
MUST tener pruebas unitarias. Una tarea no se da por terminada hasta que su prueba
se ejecutó y su resultado se anotó.

**Razón**: "terminado" significa verificado, no escrito; anotar el resultado deja
evidencia revisable de que el recorrido funciona.

### VII. Compatibilidad
Los consumidores y contratos existentes MUST conservarse. Un cambio incompatible
requiere una migración acordada con quienes consumen el contrato afectado.

**Razón**: el proyecto convive con pantallas y servicios heredados; romperlos en
silencio traslada el coste a otros equipos y a producción.

### VIII. Skills LD en la implementación
Antes de editar código web, cada tarea MUST cargar `ld-project-coordinator` y el
skill `ld-*` de su capa (`ld-data`, `ld-backend`, `ld-frontend`, `ld-design`,
`ld-crud`, `ld-transferencia`, `ld-security-session`, `ld-charts`,
`ld-realtime`). Si el skill no
está disponible, la tarea MUST detenerse y avisarlo en lugar de improvisar. Los
artefactos de la especificación (`spec.md`, `plan.md`, `contracts/`, `tasks.md`) son
el contrato de trabajo: si la realidad los contradice (un procedimiento distinto, un
formato distinto), la tarea se detiene y se propone actualizar los artefactos.

**Razón**: los skills LD concentran el patrón probado del estilo base; improvisar sin
ellos reintroduce exactamente los fallos que los principios I–IV buscan evitar.

## Restricciones adicionales

{{STACK_LINE}}
- Despliegue detrás de HTTPS.
- Sin cambios a bases de datos reales sin autorización explícita.

## Flujo de desarrollo

- Se sigue el orden de Spec Kit: constitución, especificación, plan, tareas, análisis
  e implementación. La especificación describe el qué, sin tecnología.
- Modo rápido: permitido solo para cambios pequeños, de una capa, sin contratos ni
  datos nuevos, sin escritura y sin implicación de seguridad. Todo lo demás se
  implementa por especificación.

## Governance

Esta constitución prevalece sobre cualquier otra práctica del proyecto.

- **Enmiendas**: se proponen por escrito, se versionan con versión semántica y se
  revisan contra el plan y las tareas vigentes antes de aplicarse.
  - MAJOR: se elimina o redefine un principio.
  - MINOR: se añade un principio o una sección nueva.
  - PATCH: solo aclaraciones de redacción, sin cambio de significado.
- **Verificación de cumplimiento**: cada plan MUST incluir una verificación contra
  estos principios y justificar por escrito cualquier excepción. Las revisiones de
  código y de tareas comprueban el cumplimiento de los principios innegociables
  (III y IV) sin excepción.
- **Artefactos**: `spec.md`, `plan.md`, `contracts/` y `tasks.md` de cada historia son
  el contrato de trabajo; ante contradicción con la realidad se detiene la tarea y se
  actualizan los artefactos (véase el principio VIII).

**Version**: 1.0.0 | **Ratified**: {{DATE}} | **Last Amended**: {{DATE}}
