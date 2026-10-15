## Desarrollo web (skills LD)

Para cualquier solicitud de construir, corregir o ampliar una aplicación web,
carga primero el skill `ld-project-coordinator` y sigue sus indicaciones; él
decide qué otros skills `ld-*` participan y si el trabajo va en modo rápido o con
especificación. No hace falta que la persona nombre los skills.

El **stack** y el **modo de desarrollo** elegidos al instalar están en
`.ld/config.json` (`{"stack": "ld|actual|definir", "modo": "sdd|vibe", ...}`).
Léelo antes de decidir: con `modo` «vibe», trabaja guiado por chat y **no
propongas ni ejecutes `/speckit.*`** salvo que la persona lo pida; con `modo`
«sdd», el flujo de Spec Kit es el camino normal. Con `stack` distinto de «ld»,
**no impongas** el kit base ni el estilo LD: adáptate al stack real del proyecto.

Esta regla aplica también cuando la instrucción viene de un comando `/speckit.*`
(`constitution`, `specify`, `clarify`, `plan`, `tasks`, `analyze`, `implement`).
Esos comandos no mencionan skills y eso no los exime: carga además `ld-speckit`,
que define lo que LD espera en cada etapa (por ejemplo, el *Technical Context* por
defecto en `/speckit.plan` y las etiquetas `[ld-*]` en las tareas), y antes de editar
código carga el skill `ld-*` de la capa de la tarea. Si el proyecto tiene
`specs/<NNN>/`, `spec.md`, `plan.md`, `contracts/` y `tasks.md` son el contrato.

Si la persona pregunta qué sigue, en qué etapa va o dónde se quedó (o dice «continúa») en un
proyecto con `.specify/`, carga `ld-speckit`, detecta la etapa por los archivos y responde con el
siguiente comando y un texto de entrada sugerido, sin ejecutarlo.

El estilo visual lo define `.ld/diseno.json`: `ld` (Soft Glass del paquete, sin librerías) o `externo` con el skill de
diseño que la persona eligió (puede usar Tailwind u otra librería, solo para el diseño). Antes de diseñar una pantalla
lee ese archivo y sigue `ld-design`; en modo `externo`, `ld-design` cede el aspecto a ese skill y conserva la estructura,
los `id`, la accesibilidad y la verificación.

Reglas mínimas, en cualquier modo:

- Los endpoints llevan sesión cuando la aplicación tiene login; las escrituras
  van por `POST` con CSRF.
- El texto que viene de usuarios entra al DOM con `textContent`.
- No se modifica ni se despliega un procedimiento almacenado existente sin
  autorización explícita; se crea uno nuevo e independiente.
- Los datos viajan como cadenas delimitadas y bytes (no JSON, salvo servicios para terceros); los
  archivos y los volúmenes grandes por bloques, lotes y viajes con progreso (`ld-transferencia`), copiando
  el patrón de los appDemo en lugar de inventar funciones o protocolos.
- No se escriben secretos ni rutas personales en el código.
- Antes de usar un procedimiento almacenado, se lee su definición real.
- Cada etapa de `/speckit.*` se cronometra sola: los ganchos de `.specify/extensions.yml` marcan su
  inicio y su fin (minutos en `specs/METRICS.md`, con el desglose de la implementación a cargo del
  agente). Si al responder «¿qué sigue?» hay etapas abiertas, ciérralas o avísalas.
- Las respuestas van con estructura y semáforo (`✅` hecho y verificado, `⚠️` pendiente, `❌` bloqueo),
  tablas para comparar y el siguiente paso al final; los scripts del paquete emiten color cuando hay terminal.
