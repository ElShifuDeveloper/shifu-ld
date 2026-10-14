---
name: ld-project-coordinator
description: "Punto de entrada automático para solicitudes de desarrollo web, creación de sistemas, nuevas funciones, corrección de errores y mantenimiento de aplicaciones existentes. Decide qué skills LD activar y coordina ld-design, ld-frontend, ld-backend, ld-data, ld-crud, ld-transferencia, ld-security-session, ld-charts, ld-realtime y ld-speckit según las capas necesarias, siguiendo el estilo LD (cadenas delimitadas y bytes, bloques, lotes y viajes) y respetando los contratos existentes. Elige entre modo rápido (vibe coding) y modo con especificación (SDD con Spec Kit) según el riesgo del cambio."
---

# Coordinador de sistemas web LD

Este skill organiza el trabajo de producto y la colaboración entre los skills
LD: las cuatro capas (`ld-design`, `ld-frontend`, `ld-backend`, `ld-data`) y las
especialidades `ld-crud`, `ld-transferencia`, `ld-security-session`,
`ld-charts`, `ld-realtime` y `ld-speckit`. No sustituye sus conocimientos ni obliga a usar todas las capas en
cada cambio: decide cuáles participan y mantiene entre ellas un alcance,
contratos y criterios de aceptación coherentes.

En el paquete LD, funciona como punto de entrada predeterminado ante una
solicitud de desarrollo web: la persona no necesita conocer ni invocar
individualmente los skills. Interpreta el pedido, distingue consulta, sistema
nuevo o mantenimiento y activa solo las especialidades pertinentes. Para una
corrección acotada, debe conservar el paso ligero y no convertirla en un
proyecto arquitectónico.

Para que el agente pueda descubrirlo en otro proyecto (OpenCode, Claude Code o
Copilot), copia el paquete completo en la carpeta de skills del proyecto; las
rutas por agente y los pasos están en el `README.md` del paquete Skill_LD.
Los enlaces de este skill son relativos a su carpeta. La autoselección depende
además de la configuración del agente; compruébala con una solicitud natural en
una conversación nueva.

## Cuándo usarlo

- Como punto de entrada para solicitudes de construir, corregir, ampliar o dar
  soporte a sistemas web, aunque el usuario no mencione los skills LD.
- Crear una aplicación o sistema web a partir de una necesidad.
- Implementar una función que involucra interfaz, API y datos.
- Incorporar una capacidad completa a una aplicación existente.
- Planificar una modernización que atraviesa varias capas.
- Preparar el trabajo para que los skills de diseño, frontend, backend y datos
  puedan ejecutarlo sin inventar contratos incompatibles.

Si el pedido es una consulta sin implementación o un cambio claramente acotado,
responde o deriva al skill especializado pertinente sin imponer coordinación de
las cuatro capas. Este coordinador no convierte una petición sencilla en un
proyecto de arquitectura.

## Reglas de coordinación

1. Aclara el problema y el resultado observable antes de elegir tecnología o
   implementar. Pregunta solo por decisiones que cambien alcance, seguridad,
   contratos o comportamiento; declara supuestos de bajo impacto.
2. Inspecciona el workspace antes de describir o modificar su arquitectura.
   Distingue un workspace nuevo de un sistema existente y confirma qué fuentes,
   contratos, herramientas de build y pruebas existen realmente.
3. Define una única descripción funcional del cambio y criterios de aceptación
   observables. Evita que cada capa derive requisitos diferentes del pedido.
4. Establece los contratos entre navegador, servidor y datos antes de conectar
   sus implementaciones. El contrato compartido de transferencias está en
   [ld-backend/references/transfer-contract.md](../ld-backend/references/transfer-contract.md);
   úsalo solo cuando el flujo corresponda, no como requisito universal.
5. Activa solo los skills y ejemplos pertinentes. En un sistema web completo,
   coordina `ld-design`, `ld-data`, `ld-backend` y `ld-frontend` (más las
   especialidades que apliquen); en una función parcial, omite las capas que no
   participan y explica brevemente esa decisión.
6. Conserva convenciones, contratos y consumidores existentes. Prefiere
   adaptadores o migraciones compatibles; no reemplaces ni alteres una
   integración heredada por inferencia.
7. Mantén separadas la preparación de cambios y su despliegue. No uses fuentes
   reales para escrituras ni despliegues sin autorización explícita para el
   objeto y el entorno de destino. Nunca copies secretos a código, pruebas,
   logs o documentación.
8. Valida el comportamiento solicitado en cada capa y en el límite entre capas.
   No declares un flujo completo porque compile una sola pieza o porque una
   prueba mock reproduzca su contrato.

## Modo de trabajo: rápido o con especificación

El paquete se usa de dos maneras y el coordinador elige la más ligera que sea
segura. Los detalles y los pedidos de ejemplo están en
[examples/sdd-y-vibe.md](./references/sdd-y-vibe.md).

- **Rápido (vibe coding):** cambio acotado en una capa, sin contratos nuevos,
  sin escritura de datos ni seguridad. Se hace el cambio mínimo, se prueba y se
  cierra con qué cambió, qué se probó y qué se supuso.
- **Con especificación (SDD):** contratos o SP nuevos, escritura de datos,
  sesión o permisos, dos o más capas, o varias personas. Antes de codificar se
  acuerda la especificación, el plan y las tareas por capa; no se escribe código
  de una historia hasta tener su contrato.
- **Con Spec Kit:** carga también [ld-speckit](../ld-speckit/SKILL.md), que define lo que LD espera en
  cada comando `/speckit.*` y cómo iniciar un proyecto. Si el proyecto tiene `.specify/` y una carpeta `specs/<NNN>/`
  con `spec.md`, `plan.md` y `tasks.md`, esos artefactos y la constitución son el
  contrato: no repitas las preguntas del sistema nuevo, ejecuta la tarea pedida con el
  skill de su capa y, si la realidad los contradice (un SP o un formato distintos),
  detente y propón actualizar los artefactos en lugar de improvisar.
- **Escalar:** si durante el modo rápido aparece una de esas señales, se detiene
  el código, se dice en una línea por qué y se propone la especificación.
- Los guardarraíles de seguridad y datos aplican en ambos modos y están en
  la sección 2 de la guía.

## Estilo base del proyecto

Si el workspace ya usa el patrón LD (apps Django con `views.py`/`urls.py`,
HTML + JavaScript nativo, `General.js`, `LD.css` y procedimientos almacenados
con datos delimitados), las pantallas de consulta y mantenimiento nuevas o
modificadas se resuelven con [ld-crud](../ld-crud/SKILL.md). **El estilo LD
son cadenas delimitadas y bytes, no JSON**: el protocolo JSON/cursor de
`ld-backend`/`ld-frontend` es solo una alternativa para integraciones con
terceros y no se usa por defecto, ni siquiera en proyectos nuevos. No mezcles
ambos formatos en una misma pantalla sin decirlo.

Para subir o bajar archivos o imágenes, arrastrar y soltar, vista previa,
archivos grandes, muchos archivos pequeños, cargas masivas y consultas de muchos
registros, participa [ld-transferencia](../ld-transferencia/SKILL.md): copia las
técnicas de los appDemo (bloques `I`/`P`, lotes y paquetes de bytes, viajes de
registros) en lugar de inventar funciones o un protocolo propio.

Cuando la función requiere acceso restringido (login, sesión, captcha,
auditoría) o se pide revisar la seguridad de una vista, participa también
[ld-security-session](../ld-security-session/SKILL.md). Toda vista o endpoint
nuevo de una aplicación con login se protege por defecto.

Para gráficos, animaciones o comandos de voz usa
[ld-charts](../ld-charts/SKILL.md); para servicios que publican datos en
CSV/JSON/XML o comunicación en tiempo real con WebSocket, usa
[ld-realtime](../ld-realtime/SKILL.md).

## Sistema nuevo o existente

- **Sistema nuevo:** entiende el producto con preguntas breves (necesidad, usuarios, tareas del MVP, datos y fuentes, seguridad, criterios de aceptación), acuerda un contrato vertical por tarea (interacción, datos, API, límites, aceptación) e implementa por recorrido de usuario: diseño, datos, servidor, navegador, integración.
- **Sistema existente:** localiza el punto de entrada, consumidores, contratos, fuente de datos y pruebas; distingue defectos confirmados de riesgos hipotéticos; haz el cambio mínimo con compatibilidad; coordina solo las capas tocadas; añade pruebas de regresión e informa lo que falte (secreto, permiso, aprobación) sin sustituirlo por valores ficticios.

Los pasos completos están en [modos-de-trabajo.md](./references/modos-de-trabajo.md).

## Prueba de aceptación

Los escenarios reproducibles (cambio de datos, cambio transversal, operación sensible, sistema nuevo, pantalla CRUD, endpoint con sesión, gráfico y tiempo real, elección de modo) y sus criterios están en [acceptance-tests.md](./references/acceptance-tests.md). Ejecútalos como tareas independientes y comprueba resultados, no solo menciones de skills. El proceso es satisfactorio si cada uno deja evidencia verificable (inspección de la fuente, contrato, cambio, prueba ejecutada y limitación reportada); registra los fallos de coordinación y corrige el skill que los origina, sin duplicar la guía en todos.

## Checklist de cierre

- ¿Se resolvió la necesidad del usuario y no una interpretación supuesta?
- ¿El alcance y criterios de aceptación son concretos y comprobables?
- ¿Las capas participantes comparten contrato, errores y permisos coherentes?
- ¿Se inspeccionaron las fuentes y consumidores reales antes de adaptar?
- ¿Se preservaron los contratos existentes o se autorizó explícitamente su cambio?
- ¿Las pruebas cubren comportamiento y límites relevantes en las capas tocadas?
- ¿Quedaron claros configuración, despliegue, seguridad y tareas pendientes?
- ¿Se eligió el modo adecuado (rápido o con especificación) y se dijo por qué?
- ¿Cada tarea terminada tiene su prueba ejecutada y anotada?
