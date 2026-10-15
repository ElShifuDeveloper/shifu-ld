# Iniciar un proyecto LD con Spec Kit

## Un solo comando

Desde cualquier lugar (ruta del paquete Skill_LD y ruta del proyecto):

```
python <paquete>/scripts/iniciar_proyecto.py <ruta-del-proyecto>
```

Si el proyecto no existe, lo crea. Pide (o toma de `--nombre`) el nombre del proyecto y si usará SQL Server.
Es idempotente: puedes repetirlo y no sobrescribe nada que ya exista sin avisar. Hace, en orden:

1. **Skills LD:** copia las carpetas `ld-*` a `<proyecto>/.agents/skills/`. Si ya existen y son idénticas, no hace
   nada; si difieren, las lista y `--update` las reemplaza dejando las anteriores como `*-old`. Con `--skills global` las instala una sola
   vez en `~/.agents/skills/` (valen para todos tus proyectos) y con `--skills omitir` no las toca. Si encuentra un skill
   obsoleto (`ld-crud-legacy`, ahora `ld-crud`) lo avisa y, con `--update`, lo aparta como `ld-crud-legacy-old` para no duplicar.
2. **Kit base del estilo LD:** instala los archivos que el estilo da por supuestos, solo si faltan (nunca sobrescribe):
   `Modulos/` (`modAccesoDatos.py`, `modUtilidades.py`, `modSeguridadWeb.py`, `modGraficos.py`, `modPaquetes.py`) y `Static/`
   (`scripts/General.js`, `scripts/Paquetes.js`, `scripts/sha256.js`, `styles/LD.css`, `styles/DACP.css`) y `Static/Images/Icons/`. La tabla de fuentes está en
   [ld-crud](../../ld-crud/SKILL.md). Con `--sin-base` no los instala.
2b. **Estilo visual:** pregunta una vez (o toma `--diseno ld|externo` y `--skill-diseno <nombre>`) si el proyecto usa el diseño LD (Soft Glass,
   sin librerías) o un skill de diseño externo (por ejemplo con Tailwind) y lo guarda en `<proyecto>/.ld/diseno.json`. Sin terminal
   interactiva (por ejemplo, si lo ejecuta un agente) usa `ld` y lo avisa en la salida: pregunta tú a la persona y repite con las banderas.
   `--update` no lo cambia; solo lo cambian las banderas. Detalle: [diseno-externo.md](../../ld-design/references/diseno-externo.md).
3. **Spec Kit:** si no hay `.specify/`, ejecuta `specify init --here --force --non-interactive --integration
   opencode --script sh` (funciona sin red). Si `specify` no está instalado, lo indica y sigue con lo demás.
4. **`AGENTS.md`:** crea o actualiza el bloque LD entre las marcas `<!-- LD:BEGIN -->` y `<!-- LD:END -->`,
   sin tocar el resto del archivo.
5. **Constitución:** si falta o es la plantilla vacía de Spec Kit, la genera desde
   [constitution.template.md](./constitution.template.md) con el nombre del proyecto y la línea de stack de
   [stack-lines.md](./stack-lines.md). Si ya existe una constitución LD, no la toca; para enmendarla usa
   `/speckit.constitution Usa el skill ld-speckit y su plantilla de constitución`.
6. **`opencode.json`:** crea o fusiona `instructions` con `.specify/memory/constitution.md`, conservando
   cualquier otra clave.
7. **Tiempos del SDD:** crea o actualiza `.specify/extensions.yml` con los ganchos que cronometran cada
   etapa (9 etapas × before/after; los minutos quedan en `specs/METRICS.md`) y el comando
   `/ld.tiempo` en `.opencode/commands/` al que apuntan los ganchos. La fusión **conserva tus
   ganchos**: solo se reemplazan los bloques entre las marcas LD de tiempos y todo lo que esté fuera
   de ellas queda intacto. Detalle: [tiempos.md](./tiempos.md).

Al terminar imprime el siguiente paso. Opciones útiles: `--dry-run` (muestra qué haría sin escribir),
`--clean` / `--limpiar` (borra las versiones `*-old` que quedaron de las actualizaciones y termina;
con `--dry-run` solo las lista), `--sin-speckit`, `--sin-sql` / `--con-sql` (no preguntar), `--git`
(ejecuta `git init` si el proyecto no es la raíz de su propio repositorio), `--si` (no preguntar nada,
con valores por defecto).

La salida de todos los scripts del paquete va **con color** cuando es una terminal (verde lo hecho,
amarillo los avisos, rojo los errores) y se apaga sola si la salida se redirige a un archivo o si se
define `NO_COLOR`; en ese caso el texto es idéntico, sin códigos de escape.

## Después

Reinicia OpenCode en el proyecto (las instrucciones se leen al iniciar) y sigue con
`/speckit.specify`. Si dudas de la etapa, pregunta "¿qué sigue?" ([flujo.md](./flujo.md)).
A partir de ahí, marca el inicio y el fin de cada etapa con `scripts/tiempos.py`: los minutos quedan
en `specs/METRICS.md` ([tiempos.md](./tiempos.md)).

## Qué no automatiza

- Las etapas de Spec Kit (`specify`, `clarify`, `plan`, `tasks`, `analyze`, `implement`): requieren
  decisiones y revisión de una persona.
- La decisión de git: Spec Kit usa el repositorio para numerar y ramificar las features; si el proyecto vive
  dentro de otro repositorio, conviene `--git` para que tenga el suyo.

## Mantener un proyecto al día (versiones)

El paquete tiene un número de versión (`VERSION`) y un historial (`CHANGELOG.md`, con una sección **Migración** para lo que no se
puede automatizar). Cada instalación se registra en `<proyecto>/.ld/manifest.json`: la versión y la huella de cada archivo que LD
instaló.

```
python <paquete>/scripts/iniciar_proyecto.py <proyecto> --version   # solo lectura: versión instalada y disponible, qué difiere y qué cambió
python <paquete>/scripts/iniciar_proyecto.py <proyecto> --update    # lleva TODO a la versión del paquete; lo anterior queda como *-old
python <paquete>/scripts/iniciar_proyecto.py <proyecto> --clean     # borra las versiones *-old cuando ya no las necesites
```

`--update` no pregunta ni distingue: todo archivo del paquete (skills y kit base) que falte se instala y todo el que difiera se reemplaza,
**incluso si lo modificaste tú**. Nada se pierde: la versión anterior queda junto al archivo con el sufijo `-old` antes de la extensión.

| Situación | `--version` | sin flag | `--update` |
|---|---|---|---|
| Falta en el proyecto | nuevo | lo instala | lo instala |
| Igual al paquete | al día | lo registra | no hace nada |
| Difiere (versión nueva del paquete, cambio tuyo o sin manifiesto) | lo lista | no lo toca | lo reemplaza; el anterior queda como `*-old` |
| Ya no está en el paquete | lo lista | no lo toca | queda como `*-old` |

Ejemplos de nombres: `General.js` → `General-old.js`; `SKILL.md` → `SKILL-old.md`; si `General-old.js` ya existe, el nuevo apartado es
`General-old-2.js`. El skill obsoleto `ld-crud-legacy` pasa a la carpeta `ld-crud-legacy-old` con su `SKILL-old.md` (inerte: OpenCode
solo descubre `SKILL.md`). `AGENTS.md` y `opencode.json` se fusionan sin pisar lo tuyo; si cambian, la versión previa queda como
`AGENTS-old.md` y `opencode-old.json`.

- **Las versiones `-old` se acumulan:** son tu respaldo para comparar e integrar lo que habías personalizado (por ejemplo con `git diff --no-index`).
  Bórralas cuando ya no las necesites; `--version` cuenta cuántas hay y `--clean` las borra de una vez (con `--clean --dry-run` las lista antes
  de tocar nada). Limpia también las de la raíz del proyecto (`AGENTS-old.md`, `opencode-old.json`) y las carpetas de skills retirados
  (`ld-crud-legacy-old`). Si usas git, la rama y el commit previos ya son un respaldo.
- **Proyectos instalados antes del versionado:** no tienen manifiesto. Sin flag, lo que coincide con el paquete queda registrado y lo que difiere se
  informa; con `--update` se regulariza todo.
- **Constitución, especificaciones y código del proyecto no se actualizan solos.** El `CHANGELOG` dice qué enmendar; `--version` avisa si la
  plantilla de constitución cambió desde que se generó la tuya, y también si los ganchos de tiempos (`.specify/extensions.yml`) o el comando
  `/ld.tiempo` están desactualizados o faltan. Los cambios de comportamiento se llevan por SDD: `/speckit.clarify` (especificación),
  `/speckit.plan` y `/speckit.converge` (tareas nuevas para lo que falte en el código) antes de `/speckit.implement`.

Flujo recomendado: rama nueva, `--version`, `--update`, revisar `git diff` y los `*-old`, probar, `--clean` cuando ya no hagan falta y reiniciar OpenCode.
