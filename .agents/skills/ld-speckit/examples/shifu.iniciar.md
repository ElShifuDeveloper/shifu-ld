---
description: Asistente para iniciar o actualizar un proyecto LD (skills, kit base, Spec Kit): pregunta stack y modo y ejecuta el instalador del paquete.
---

## Entrada

```text
$ARGUMENTS
```

## Qué hacer

1. Pregunta a la persona (si no vienen ya en `$ARGUMENTS`), con dos preguntas de opción:
   - **Stack del proyecto:**
     1. Recomendado LD — Django + JS nativo + `General.js` + SPs (instala el kit base).
     2. Respetar el stack actual — solo copia los skills; no impone kit base ni estilo LD.
     3. Definirlo — pide una descripción (p. ej. «FastAPI + React»).
   - **Modo de desarrollo:**
     1. SDD + Spec Kit (recomendado).
     2. Vibe coding.
2. Ejecuta el instalador del paquete (no interactivo):

```sh
python {{RUTA_PAQUETE}}/scripts/iniciar_proyecto.py <proyecto> --stack <ld|actual|definir> [--stack-detalle "<texto>"] --modo <sdd|vibe> --si
```

3. Reproduce el resumen del instalador. Si el modo es «sdd», el siguiente paso es
   `/speckit.specify <qué debe poder hacer cada usuario>`; si es «vibe», propón uno de los
   prompts de ejemplo que el instalador imprime.

## Reglas

- `<proyecto>` es el directorio de trabajo actual salvo que la entrada indique otra ruta.
- No añadas `--update` sin confirmación de la persona: reemplaza todo archivo que difiera y deja
  la versión anterior como `*-old`.
- Pasa los valores tal cual; el instalador valida, es idempotente y guarda la elección en
  `.ld/config.json`.