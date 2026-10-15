---
description: Cronometra las etapas del SDD (specs/METRICS.md) con el script de tiempos del paquete LD.
---

## Entrada

```text
$ARGUMENTS
```

## Qué hacer

Ejecuta el script de tiempos del paquete LD con la acción que llega en la entrada:

```sh
python {{RUTA_PAQUETE}}/scripts/tiempos.py . $ARGUMENTS
```

Acciones (`$ARGUMENTS`): `inicio <etapa>`, `fin <etapa>`, `informe`, `abiertas`,
`estimar [--escribir]`, `etapas`. Si la entrada viene vacía, usa `informe`.

Etapas: `constitucion`, `especificar`, `clarificar`, `plan`, `tareas`, `checklist`, `analizar`,
`implementar`, `converger`; desglose de implementar: `implementar:desarrollo`, `implementar:qa`,
`implementar:seguridad`, `implementar:diseño`, `implementar:integracion`, `implementar:otros`.

## Reglas

- Pasa la entrada tal cual (etapas y banderas): el script calcula los minutos y reescribe
  `specs/METRICS.md`; no lo edites a mano ni toques `.ld/tiempos.json`.
- No inventes marcas ni tiempos: si una etapa ya estaba cerrada y se repite, el script lo avisa
  (usa `--reiniciar` solo cuando de verdad empieces un ciclo nuevo).
- Reproduce la salida del script tal cual (ya trae color y símbolos) y continúa con la tarea que
  estabas haciendo; si fue un `inicio`, la etapa queda "en curso" hasta el `fin`.