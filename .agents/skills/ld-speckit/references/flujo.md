# Flujo por etapas con Spec Kit y OpenCode

Los comandos `/speckit.*` son de Spec Kit; este documento solo añade lo que LD espera en cada
etapa. Cada etapa la revisa una persona antes de pasar a la siguiente: no encadenes etapas solas.

## ¿Qué sigue? (detecta la etapa por los archivos)

| Estado del proyecto | Siguiente paso |
|---|---|
| No existe `.specify/` | Iniciar el proyecto con `iniciar_proyecto.py` (ver [instalacion.md](./instalacion.md)) |
| `.specify/memory/constitution.md` no existe o conserva `[PROJECT_NAME]` | `/speckit.constitution` (o `iniciar_proyecto.py`) |
| Constitución lista y no hay `specs/` | `/speckit.specify <qué debe poder hacer cada usuario>` |
| `specs/<NNN>/spec.md` sin `plan.md` | `/speckit.clarify` si hay `NEEDS CLARIFICATION` o huecos; si no, `/speckit.plan` |
| `plan.md` sin `tasks.md` | `/speckit.tasks` |
| `tasks.md` sin revisión | `/speckit.analyze`, corregir lo crítico y luego `/speckit.implement` |
| `tasks.md` con tareas sin marcar | `/speckit.implement` (continúa donde quedó) |

Cuando la persona pregunte "¿qué sigue?", inspecciona esos archivos, responde con el comando y
sugiere el texto de entrada. No ejecutes la etapa por tu cuenta salvo que lo pida.

Cada etapa se **cronometra**: marca su inicio al empezar y su fin al terminar con
`python <paquete>/scripts/tiempos.py . inicio|fin <etapa>`; los minutos quedan en `specs/METRICS.md`
([tiempos.md](./tiempos.md)). Y responde con el estilo LD ([estilo-salida.md](./estilo-salida.md)):
estructura, semáforo y el siguiente paso al final.

## Qué espera LD en cada etapa

- **`/speckit.constitution`:** parte de [constitution.template.md](./constitution.template.md) y
  de [stack-lines.md](./stack-lines.md), con el nombre del proyecto. Si ya existe una constitución,
  enmiéndala (versión semántica) en lugar de reemplazarla.
- **`/speckit.specify`:** solo el qué, sin tecnología. Las historias deben incluir quién puede ver o
  hacer cada cosa y qué pasa ante errores. **No inventes límites** (tamaños, cantidades, tandas): si la persona no los pide, déjalos sin tope y anótalo como suposición; los bloques y lotes de `ld-transferencia` permiten archivos de cualquier tamaño. Pregunta solo por límites de negocio que cambien el alcance.
- **`/speckit.clarify`:** prioriza permisos y visibilidad, fallo a mitad de una operación (revertir
  o dejar parcial) y reglas de nombres. No preguntes por límites de tamaño o cantidad que nadie pidió. La entrada del comando solo prioriza; el comando
  hace como máximo 5 preguntas, de a una.
- **`/speckit.plan`:** completa el *Technical Context* con [technical-context.md](./technical-context.md).
  La entrada del comando solo necesita lo que distingue a la feature (por ejemplo, "sin base de
  datos: las imágenes se guardan en el sistema de archivos"). Si la feature mueve archivos o volúmenes,
  el plan usa las técnicas de `ld-transferencia` (viajes, bloques, lotes, paquetes) y respuestas en
  cadenas y bytes, no JSON ni una petición por archivo. Los contratos de `contracts/` siguen la
  plantilla de [tareas.md](./tareas.md).
- **`/speckit.tasks`:** tareas por historia y capa, con ruta de archivo y el skill `[ld-*]` (por ejemplo
  `[ld-transferencia]` para el cliente y las vistas de una carga de archivos), en el
  orden datos, servidor, navegador, integración, y la última tarea de cada historia es el
  recorrido de integración ([tareas.md](./tareas.md)).
- **`/speckit.analyze`:** comprueba además la constitución (en especial III y IV), que cada tarea
  tenga su skill y que los contratos partan de las definiciones reales.
- **`/speckit.implement`:** en cada tarea, carga `ld-project-coordinator` y el skill indicado antes
  de editar; usa `spec.md`, `plan.md`, `contracts/` y `tasks.md` como contrato y, si la realidad
  los contradice, detente y propón actualizarlos. Cada tarea termina con su prueba ejecutada y
  anotada. La etapa se mide entera y además por sub-etapas (`implementar:desarrollo`, `:qa`,
  `:seguridad`, `:diseño`, `:integracion`, `:otros`), que se abren y cierran cuando ocurren
  ([tiempos.md](./tiempos.md)); el recorrido de integración de cada historia es tarea propia.

## Tiempos y cierre del ciclo

- **`/speckit.analyze`**: además de lo anterior, revisa que `specs/METRICS.md` tenga las marcas de
  las etapas ya corridas (sin huecos ni etapas inventadas).
- **`/speckit.converge`**: cierra también la etapa `converger` en METRICS.md y deja el informe al día.
- Al terminar una feature, `specs/METRICS.md` y el registro de `quickstart.md` son la evidencia de
  lo que costó y de lo que se probó: ambos se versionan con el proyecto.

## Comprobación

En `/speckit.plan` y `/speckit.implement` debe verse una llamada a la herramienta `skill` con
`ld-speckit` o con el skill de la capa. Si no aparece, el paquete no se está aplicando: detén la
etapa y repítela afirmando "usa el skill ld-speckit".
