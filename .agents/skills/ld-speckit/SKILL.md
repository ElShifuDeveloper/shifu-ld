---
name: ld-speckit
description: "Aplica los estándares LD cuando el trabajo va por Spec Kit (comandos /speckit.constitution, specify, clarify, plan, tasks, analyze, implement): constitución base, Technical Context por defecto, etiquetas de skills en las tareas, detección de la etapa actual y la siguiente (úsalo ante preguntas como «¿qué sigue?», «¿en qué etapa estoy?», «¿dónde me quedé?» o «continúa») y arranque automático de un proyecto LD (skills, kit base Modulos/Static, Spec Kit, AGENTS.md, constitución y opencode.json)."
---

# LD_speckit

Adaptador entre Spec Kit y los skills LD. No reemplaza ni copia plantillas de Spec Kit (que evoluciona): sus comandos siguen siendo los de Spec Kit y este skill aporta **lo que LD espera en cada etapa**. Entrada del paquete: [ld-project-coordinator](../ld-project-coordinator/SKILL.md).

## Cuándo usarlo

- Cualquier comando `/speckit.*` en un proyecto LD.
- "¿Estoy actualizado?", "actualiza LD" o "¿qué versión de LD tengo?" ([instalacion.md](./references/instalacion.md), sección de versiones).
- "Inicia un proyecto LD", "prepara el proyecto para SDD", "¿qué sigue?", "¿en qué etapa estoy?", "¿dónde me quedé?" o "continúa" (en un proyecto con `.specify/`).
- Revisar si una constitución, un plan o una lista de tareas cumplen lo que LD espera.

## Qué leer según la tarea

| Tarea | Lee |
|---|---|
| Iniciar un proyecto (skills, Spec Kit, `AGENTS.md`, constitución, `opencode.json`) | [instalacion.md](./references/instalacion.md) |
| Saber la etapa actual y qué espera LD en cada comando | [flujo.md](./references/flujo.md) |
| Crear o enmendar la constitución | [constitution.template.md](./references/constitution.template.md) y [stack-lines.md](./references/stack-lines.md) |
| Llenar el *Technical Context* en `/speckit.plan` | [technical-context.md](./references/technical-context.md) |
| Contratos y tareas por capa | [tareas.md](./references/tareas.md) |

## Reglas

1. **Etapas con revisión humana.** No ejecutes ni encadenes etapas de Spec Kit por tu cuenta; responde "¿qué sigue?" con el comando y el texto sugerido, y espera.
2. **No sustituyas plantillas de Spec Kit** (ni `.specify/templates/` ni overrides). Llena la plantilla que el comando entregue usando los valores por defecto de LD, mapeando cada uno al campo equivalente.
3. **Constitución existente:** se enmienda con versión semántica; no se reemplaza.
4. **Cada tarea de `/speckit.tasks`** lleva el skill `[ld-*]` y su ruta de archivo; en `/speckit.implement` se carga ese skill antes de editar.
5. **Actualización:** el script del paquete compara versiones y archivos (`--version`, solo lectura) y lo lleva todo a la versión del paquete (`--update`, que deja las versiones anteriores como `*-old`); el agente debe pedir la ruta del paquete Skill_LD, ejecutar primero `--version`, explicar el resultado y los pasos de **Migración** del `CHANGELOG`, y no ejecutar `--update` sin que la persona lo confirme (reemplaza también lo que modificó).
6. **Arranque automático** con `scripts/iniciar_proyecto.py` del paquete Skill_LD: instala los skills y el kit base (`Modulos/`, `Static/`), Spec Kit, `AGENTS.md`, la constitución y `opencode.json`; solo prepara el proyecto, no avanza etapas de Spec Kit.
7. **Comprobación:** en `plan` e `implement` debe verse una llamada a la herramienta `skill`; si no, detén la etapa y repítela afirmando "usa el skill ld-speckit".

## Checklist

- ¿La constitución tiene los principios I–VIII, el nombre del proyecto y la línea de stack correcta (con o sin SQL Server)?
- ¿El plan usa el *Technical Context* LD y justifica cada desviación?
- ¿Cada tarea tiene ruta de archivo, skill y, al final de cada historia, su recorrido de integración?
- ¿Los datos viajan como cadenas y bytes, y las transferencias por viajes (`ld-transferencia`), sin JSON ni una petición por archivo?
- ¿Se leyó la definición real de cada SP antes de escribir su contrato?
