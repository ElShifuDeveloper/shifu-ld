# Uso del paquete LD con SDD y con vibe coding

El coordinador decide qué skills participan; esta guía explica **cómo se trabaja** con ellos: en modo rápido (vibe coding) o con especificación (SDD con Spec Kit). Los skills son los mismos; cambia cuánto se documenta antes de escribir código.

## 1. Elegir el modo

| Señal | Modo |
|---|---|
| Toca una capa y pocos archivos, no crea contratos nuevos, no escribe datos ni toca seguridad (texto de una pantalla, un estilo, un filtro de una grilla, un gráfico con datos existentes) | **Rápido** |
| Crea o cambia un SP, una tabla, un endpoint o un formato de intercambio | **SDD** |
| Involucra login, sesión, permisos, datos personales o escritura (grabar, eliminar) | **SDD**, aunque sea pequeño |
| Atraviesa dos o más capas (pantalla + vista + SP) | **SDD** |
| Lo construyen o lo revisan varias personas, o debe poder retomarse más tarde | **SDD** |
| Duda | Empieza en rápido y escala en cuanto aparezca una señal de SDD; no al revés |

**Cuándo escalar de rápido a SDD** (detén el código y propón la especificación): hace falta un SP o contrato nuevo; la respuesta del SP no es la que se suponía; aparece un requisito de seguridad; el cambio se extiende a una segunda capa; o el usuario pregunta "¿y si…?" sobre alcance. Di en una línea por qué escalas.

## 2. Modo rápido (vibe coding)

Pide en lenguaje natural, sin nombrar skills: "agrega un gráfico de stock por categoría en la pantalla de productos". El agente debe: localizar la pantalla modelo más parecida, seguir el estilo del proyecto, hacer el cambio mínimo y probarlo.

**Guardarraíles que no se negocian en ningún modo** (si no se pueden cumplir, escala a SDD):

1. Endpoints nuevos con sesión (`@autenticacion`) cuando la aplicación tiene login; escrituras con `POST` y CSRF.
2. Texto de usuarios al DOM con `textContent`, nunca `innerHTML`/`insertAdjacentHTML`.
3. Valores a SQL como parámetros; ningún secreto ni ruta personal en el código.
4. No modificar ni desplegar un SP existente sin autorización explícita; si hace falta, crear uno nuevo e independiente.
5. Leer la definición real del SP antes de usar su resultado (forma, separadores, `NULL`).

**Cierre del modo rápido** (tres líneas): qué cambió, qué se probó (y cómo), y qué se supuso. Si se supuso algo de seguridad o de datos, no se cierra: se confirma.

## 3. Modo SDD (Spec Kit)

Sigue el orden de Spec Kit: constitución, especificación, aclaración, plan, tareas, análisis e implementación, con revisión de una persona en cada etapa. Lo que LD espera en cada una (constitución base, *Technical Context* por defecto, contrato vertical, tareas por capa con su skill) está en el skill [ld-speckit](../../ld-speckit/SKILL.md); para iniciar un proyecto de cero, `scripts/iniciar_proyecto.py` del paquete Skill_LD lo prepara con un solo comando ([instalacion.md](../../ld-speckit/references/instalacion.md)).

## 4. Pedidos de ejemplo

**Rápido**
> En la pantalla de productos, muestra el stock por categoría en un gráfico de barras como en la de categorías.

Esperable: sigue el patrón de `ld-charts`, reutiliza `uspCategoriaProductosStockPyCsv`, deja la tabla junto al gráfico y cierra con "qué cambió / qué se probó / qué se supuso".

**SDD**
> Necesito que el personal de ventas pueda registrar pedidos y que los clientes los consulten. Quiero especificarlo antes de construir.

Esperable: no escribe código; ejecuta el flujo de especificación, propone historias priorizadas, pregunta lo que cambia el alcance (roles, permisos, volumen), y deja un `plan.md` con el *Technical Context* LD y contratos que parten de las definiciones reales de los SP.

## 5. Qué hacer cuando el agente no sigue el modo

- **Se pone a codificar una historia con escritura de datos**: pide detenerse; aplica la señal "escala a SDD".
- **Convierte un cambio pequeño en un proyecto**: recuerda que el modo rápido existe y que el coordinador no debe imponer las cuatro capas.
- **Inventa un SP o un formato**: pide leer la definición en `SPs` (o la fuente real) y no avanzar sin ella.
