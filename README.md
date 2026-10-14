# Paquete de skills LD

Este paquete ayuda a crear sistemas web nuevos y mantener aplicaciones
existentes con prácticas compartidas para diseño, frontend, backend y datos.
El punto de entrada es [ld-project-coordinator](.agents/skills/ld-project-coordinator/SKILL.md);
la persona describe la necesidad en lenguaje natural y el coordinador decide
qué skills especializados participan.

## Skills incluidos

- [ld-project-coordinator](.agents/skills/ld-project-coordinator/SKILL.md):
  alcance, contratos, selección de capas y criterios de aceptación.
- [ld-design](.agents/skills/ld-design/SKILL.md): diseño moderno de la
  interfaz Soft Glass con `LD.css` (vidrio suave solo con CSS, tema claro y oscuro, adaptable a móvil; diseño externo opcional elegible al iniciar), estados,
  accesibilidad y verificación con capturas.
- [ld-frontend](.agents/skills/ld-frontend/SKILL.md): cliente web y contratos
  de interacción con las APIs.
- [ld-backend](.agents/skills/ld-backend/SKILL.md): endpoints, validación,
  autorización, errores e integración.
- [ld-data](.agents/skills/ld-data/SKILL.md): consultas, persistencia,
  transacciones, cargas y contratos de datos.
- [ld-crud](.agents/skills/ld-crud/SKILL.md): pantallas de
  consulta y mantenimiento (CRUD con popup) en el estilo base LD: Django,
  JavaScript nativo, `General.js`, `DACP.css` y procedimientos almacenados.
- [ld-transferencia](.agents/skills/ld-transferencia/SKILL.md): subida por
  bloques `I`/`P`, lotes y paquetes de bytes, descarga de varias imágenes en un
  viaje y registros por viajes, con cadenas y bytes (técnicas de los appDemo).
- [ld-security-session](.agents/skills/ld-security-session/SKILL.md): login con
  captcha, sesión, protección de endpoints, auditoría y revisión de seguridad.
- [ld-charts](.agents/skills/ld-charts/SKILL.md): gráficos de barras y columnas
  en canvas o SVG, animaciones y comandos de voz.
- [ld-realtime](.agents/skills/ld-realtime/SKILL.md): servicios HTTP en
  CSV/JSON/XML y comunicación en tiempo real con WebSocket.
- [ld-speckit](.agents/skills/ld-speckit/SKILL.md): lo que LD espera en cada
  comando de Spec Kit (constitución base, *Technical Context* por defecto,
  tareas por capa), detección de la siguiente etapa y arranque de proyectos.

## Inicio rápido

Para un proyecto nuevo (o uno que aún no tiene los skills) basta un comando:

```
python <ruta-al-paquete>/scripts/iniciar_proyecto.py <ruta-del-proyecto>
```

Instala los skills y el kit base del estilo LD (`Modulos/` y `Static/`, solo lo que falte), inicializa Spec Kit
con la integración de OpenCode si falta, crea o actualiza el bloque LD de `AGENTS.md`, genera la constitución con
el nombre del proyecto y enlaza la constitución en `opencode.json`. Es idempotente, no sobrescribe sin avisar y admite `--dry-run` para ver antes lo
que haría. Después reinicia OpenCode en el proyecto y ejecuta
`/speckit.specify <qué debe poder hacer cada usuario>`; si dudas de la etapa, pregunta «¿qué sigue?».
Detalle y opciones: [instalacion.md](.agents/skills/ld-speckit/references/instalacion.md).

## Versiones y actualización

El paquete tiene versión (`VERSION`, actualmente 2.x) e historial (`CHANGELOG.md`, con notas de **Migración**). Cada proyecto guarda lo que
instaló en `.ld/manifest.json`, y `--update` reemplaza todo lo que difiera (también lo que modificaste) y deja cada versión anterior junto al archivo con sufijo `-old` (`General.js` → `General-old.js`):

```
python <ruta-al-paquete>/scripts/iniciar_proyecto.py <proyecto> --version   # solo lectura: versión, diferencias y cambios
python <ruta-al-paquete>/scripts/iniciar_proyecto.py <proyecto> --update    # reemplaza todo por la versión del paquete; lo anterior queda como *-old
```

La constitución, las especificaciones y el código no se actualizan solos: el `CHANGELOG` dice qué enmendar y los cambios de comportamiento
siguen el flujo SDD (`/speckit.clarify`, `/speckit.plan`, `/speckit.converge`, `/speckit.implement`). Detalle en
[instalacion.md](.agents/skills/ld-speckit/references/instalacion.md).

## Estructura del paquete

Cada skill carga primero solo su `SKILL.md` (procedimiento, reglas y un mapa de qué leer) y consulta el detalle a pedido, para gastar poco contexto:

```
.agents/skills/<skill>/
  SKILL.md        procedimiento y reglas (corto)
  references/     documentos de detalle, cada tema en un único lugar
  examples/       código adaptable, sin documentos largos
VERSION, CHANGELOG.md   versión del paquete y su historial
scripts/         iniciar_proyecto.py (arranque y actualización), validar_paquete.py (validación) capturar_pantalla.py (capturas de diseño) y revisar_diseno.py (revisión de estructura)
```

Fuentes únicas: el protocolo de transferencias en `ld-backend/references/transfer-contract.md`; el contrato de `clienteSQL` y los errores en `ld-data/references/cliente-sql.md`; la forma y los riesgos de cada SP en `ld-data/references/stored-procedures-review.md`; el formato de las listas delimitadas en `ld-crud/references/datos-delimitados.md`; la constitución, el *Technical Context* y el bloque de `AGENTS.md` en `ld-speckit/references/`. Los demás documentos los enlazan en vez de repetirlos.

## Compatibilidad con agentes

Los skills siguen el formato estándar (`SKILL.md` con `name` y `description`) y no
dependen de un agente concreto. Rutas donde cada agente los descubre:

| Agente | Proyecto | Global (todos tus proyectos) | Estado |
|---|---|---|---|
| OpenCode | `.agents/skills/`, `.claude/skills/` o `.opencode/skills/` | `~/.agents/skills/`, `~/.claude/skills/` o `~/.config/opencode/skills/` | Rutas verificadas en [opencode.ai/docs/skills](https://opencode.ai/docs/skills/) (9 oct 2026) |
| GitHub Copilot (VS Code) | `.agents/skills/` | — | Según la guía anterior de este paquete; compruébalo en tu versión |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | Compruébalo en la documentación de tu versión |

Reglas de OpenCode que este paquete cumple (las comprueba `scripts/validar_paquete.py`):
`name` de 1 a 64 caracteres en minúsculas y guiones, igual al nombre de su carpeta;
`description` de 1 a 1024 caracteres. Los campos desconocidos se ignoran. OpenCode
carga cada skill a pedido con su herramienta `skill`, y busca los de proyecto desde
el directorio de trabajo hacia arriba hasta la raíz del repositorio git.

## Instalar en un proyecto (a mano)

`iniciar_proyecto.py` hace todo esto por ti; estos son los pasos manuales equivalentes.

1. Elige **una sola** ubicación del proyecto destino. OpenCode lee las tres rutas
   de proyecto a la vez, así que instalar el mismo skill en varias duplica el
   nombre (la documentación no indica cuál prevalece).
   - Solo OpenCode o Copilot: `<proyecto>/.agents/skills/`.
   - OpenCode y Claude Code en el mismo proyecto: `<proyecto>/.claude/skills/`, que
     leen ambos.
   - Para usarlos en todos tus proyectos: `~/.agents/skills/` o
     `~/.config/opencode/skills/` (`iniciar_proyecto.py --skills global`).
2. Copia las once carpetas de `Skill_LD/.agents/skills/` completas, con sus
   ejemplos: los enlaces entre skills dependen de que permanezcan juntas.
3. No reemplaces una carpeta de skills existente. Si el proyecto ya tiene
   skills, integra solo las carpetas LD que falten y compara antes cualquier
   colisión de nombres.
4. No copies `__pycache__` ni `*.pyc`. Para comprobar que el paquete está
   limpio y es válido, ejecuta `python scripts/validar_paquete.py`.
5. Añade al archivo de instrucciones del agente (`AGENTS.md`, `CLAUDE.md` o
   `.github/copilot-instructions.md`) el contenido de
   [agents-block.md](.agents/skills/ld-speckit/references/agents-block.md). Hace
   que el agente cargue `ld-project-coordinator` (y `ld-speckit` con los comandos
   de Spec Kit) sin depender solo de la autoselección por descripción.
6. Con Spec Kit: ejecuta `/speckit.constitution` con la plantilla
   [constitution.template.md](.agents/skills/ld-speckit/references/constitution.template.md)
   y copia [opencode.json](.agents/skills/ld-speckit/references/opencode.json) a la
   raíz del proyecto, para que la constitución esté en el contexto de toda sesión.
7. Abre el proyecto destino en el agente y prueba en una conversación nueva una
   solicitud natural, sin nombrar skills. Usa los casos de
   [aceptación](.agents/skills/ld-project-coordinator/references/acceptance-tests.md)
   para comprobar qué se activó y qué quedó ejecutado. En OpenCode debes ver una
   llamada a la herramienta `skill` que carga `ld-project-coordinator`.

### Si el skill no se activa (OpenCode)

- Ejecuta el agente desde dentro del proyecto o de una subcarpeta: la búsqueda de
  skills de proyecto sube hasta la raíz del repositorio git, no baja.
- Revisa que no haya una regla `permission.skill` en `opencode.json` que lo
  deniegue (`"ld-*": "deny"`) ni `tools: { skill: false }`.
- Ejecuta `python scripts/validar_paquete.py`: un `name` que no coincide con la
  carpeta o una `description` de más de 1024 caracteres impide cargarlo.
- Si usas el registro de skills de `gentle-ai`, `gentle-ai skill-registry list`
  (desde el proyecto) debe mostrar los `ld-*` con alcance `project`; si
  `.atl/skill-registry.md` está desactualizado, `gentle-ai skill-registry refresh`
  lo regenera.
- Los enlaces entre archivos son relativos a la carpeta de cada skill. Si el agente
  no los resuelve, pídele que lea el archivo desde `.agents/skills/<skill>/`.

La presencia de los archivos hace al paquete disponible; no garantiza que el
agente lo seleccione solo en cualquier configuración. Comprueba la activación en
tu versión y con tus permisos.

## Procedencia de los ejemplos

Los ejemplos se adaptaron de demos internos (`appDemoNN`, `mpDemo07`) y de
procedimientos almacenados de muestra que no se incluyen en el paquete. Esos
nombres indican el origen; no hace falta tenerlos para usar los skills. Ninguna
ruta, credencial ni base de datos real forma parte del paquete: toda
configuración se toma de `settings` o del entorno del proyecto destino.

## Alcance y seguridad

Los skills son guías de trabajo, no librerías instalables ni una aplicación
ejecutable. Sus ejemplos requieren adaptación al proyecto real. Antes de
integrar, verifica fuente de datos, contratos, autenticación, permisos,
configuración y pruebas. No incluyas secretos, registros reales ni datos
privados al compartir o probar el paquete. No despliegues en entornos reales
sin autorización explícita para el objeto y destino correspondientes.
