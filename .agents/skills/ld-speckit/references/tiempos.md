# Tiempos por etapa (METRICS.md)

Cuánto tardó cada etapa del SDD, en minutos, por especificación. Sirve para estimar, comparar
entre especificaciones y detectar dónde se va el tiempo (por ejemplo, si la implementación se
lleva la mayor parte, o si el cuello de botella está en clarificar).

El archivo del proyecto es **`specs/METRICS.md`** (global: una tabla por especificación y un
resumen comparativo) y su estado vive en **`.ld/tiempos.json`**. El script del paquete lo rinde
desde el estado:

```
python <paquete>/scripts/tiempos.py . inicio <etapa> [--nota "…"]
python <paquete>/scripts/tiempos.py . fin <etapa>    [--nota "…"]
python <paquete>/scripts/tiempos.py . informe        # (re)escribe specs/METRICS.md y lo muestra
python <paquete>/scripts/tiempos.py . abiertas       # etapas con inicio y sin fin (red de seguridad)
python <paquete>/scripts/tiempos.py . estimar [--escribir]   # rellena huecos desde los archivos
python <paquete>/scripts/tiempos.py etapas           # etapas válidas y alias
```

**METRICS.md no se edita a mano** (cada marca lo reescribe) ni tampoco `.ld/tiempos.json`.
`informe` también crea el archivo si falta, dejando el esqueleto de todas las especificaciones.

## Automatización: ganchos de Spec Kit (instalados por LD)

`iniciar_proyecto.py` instala `.specify/extensions.yml` con **18 ganchos** (9 etapas × before/after)
que el propio comando ejecuta: al empezar la etapa marca `inicio` y al terminar marca `fin`. Por eso
normalmente no hay que ejecutar nada a mano: **`/speckit.plan` marca `plan`, `/speckit.tasks` marca
`tareas`, `/speckit.implement` marca `implementar`, y así con las nueve etapas**.

| Etapa | Comando de Spec Kit | Etapa | Comando de Spec Kit |
|---|---|---|---|
| `constitucion` | `/speckit.constitution` | `checklist` | `/speckit.checklist` |
| `especificar` | `/speckit.specify` | `analizar` | `/speckit.analyze` |
| `clarificar` | `/speckit.clarify` | `implementar` | `/speckit.implement` |
| `plan` | `/speckit.plan` | `converger` | `/speckit.converge` |
| `tareas` | `/speckit.tasks` | | |

Los ganchos llaman al comando **`/ld.tiempo`** (instalado por LD en `.opencode/commands/`), que a su
vez ejecuta el script con la etapa correspondiente. Si OpenCode no puede invocar el comando, el
propio gancho trae en su `prompt` la línea de shell exacta: ejecútala. Las etapas que no se corran
quedan en `—`.

Los ganchos cubren solo las **etapas**; el desglose de `implementar` (abajo) lo marca el agente
mientras trabaja, o se estima.

## Desglose de la implementación

`implementar` se mide entero y además por sub-etapas, que se abren y cierran mientras `implementar`
está en curso (así el total del desglose puede ser menor que el de la etapa: el resto es coordinación
y esperas):

| Sub-etapa | Qué mide |
|---|---|
| `implementar:desarrollo` | escribir el código de las tareas |
| `implementar:qa` | pruebas y recorridos (unitarias, de servidor, de navegador) |
| `implementar:seguridad` | revisión de permisos, CSRF, sesión, `textContent` (principio III) |
| `implementar:diseño` | pantallas, `revisar_diseno.py`, capturas (principio I; `ld-design`) |
| `implementar:integracion` | recorrido de integración por historia y cierre de checkpoints |
| `implementar:otros` | lo que no encaja arriba (reuniones, bloqueos, esperas) |

## Red de seguridad: etapas abiertas y estimación

- **`abiertas`**: lista las etapas con inicio y sin fin (con los minutos transcurridos). Al responder
  «¿qué sigue?», el agente las revisa y las cierra o las avisa: una etapa abierta suele significar
  que la sesión se cortó a mitad.
- **`estimar`**: cuando no se marcó a tiempo, deduce el **fin** de cada etapa por la fecha de su
  artefacto (`constitution.md`, `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md` y, para
  `implementar`, el archivo más reciente de la carpeta de la especificación **posterior a las etapas
  previas**). El **inicio** es el fin de la etapa anterior, así que los minutos son el hueco entre
  archivos, no el trabajo real. Sin `--escribir` solo muestra lo que haría; con `--escribir` lo
  aplica y las filas quedan con la nota **«estimado por fechas de archivo»**. Nunca toca una fila ya
  marcada, y `clarificar`, `analizar` y `converger` no se estiman (no dejan archivo propio): quedan
  en `—` antes que inventar un tiempo.

## Ejemplos

```
python /paquete/Skill_LD/scripts/tiempos.py . inicio plan
python /paquete/Skill_LD/scripts/tiempos.py . fin plan --nota "Technical Context + contratos"
python /paquete/Skill_LD/scripts/tiempos.py . inicio implementar:qa
python /paquete/Skill_LD/scripts/tiempos.py . fin implementar:qa --nota "61/61 + node"
python /paquete/Skill_LD/scripts/tiempos.py . abiertas
python /paquete/Skill_LD/scripts/tiempos.py . informe
```

Se aceptan los nombres de los comandos en inglés (`specify`, `tasks`, `analyze`, `converge`,
`checklist`, `implement:qa`, `implement:diseno`). La especificación activa sale de
`.specify/feature.json`; si hay varias y ninguna activa, indica `--spec 003`, `--spec 003-nombre` o la
ruta completa.

## Reglas

1. **No edites `specs/METRICS.md` ni `.ld/tiempos.json`**: se rinden desde el estado; usa el script.
2. **Marca al empezar y al terminar la etapa**, no después: los minutos salen de esas dos marcas.
   Con los ganchos esto es automático; en el desglose de `implementar`, no lo dejes para el final.
3. **Una etapa cerrada no se vuelve a cerrar** sin `--reiniciar` (evita sumar tiempo de repeticiones).
4. Si el trabajo se retoma en otra sesión, el tiempo medido incluye la pausa: anótalo en `--nota`
   («incluye pausa de un día») para que la cifra sea interpretable.
5. `specs/METRICS.md` es un artefacto del proyecto: **se versiona** junto a `spec.md`, `plan.md` y `tasks.md`.
6. Solo se marca lo que de verdad se corrió: no inventes tiempos ni etapas que no se hicieron.