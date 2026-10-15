---
name: ld-design
description: "Diseña la interfaz de los proyectos LD con un aspecto moderno «Soft Glass» (vidrio suave, solo CSS) o con un skill de diseño externo elegido al iniciar el proyecto (.ld/diseno.json): hoja de estilos LD.css (tokens, tema claro y oscuro, adaptable a móvil) compatible con General.js y las clases de los demos, estructura de pantallas con tarjetas, formularios, tablas, ventanas, zona de arrastre y galerías, estados (cargando, vacío, error, éxito), accesibilidad y verificación con un revisor de estructura y capturas. Úsalo para crear o modernizar pantallas HTML/CSS; no para arquitectura ni protocolos."
---

# LD_design

> Metodología **LD** (cadenas delimitadas, bytes, bloques, lotes y empaquetado) creada por **Luis Dueñas Huaroto**; documentada aquí para agentes.

Diseño visual y experiencia de usuario de los proyectos LD. Entrada del paquete: [ld-project-coordinator](../ld-project-coordinator/SKILL.md). Para implementar el comportamiento, [ld-frontend](../ld-frontend/SKILL.md), [ld-crud](../ld-crud/SKILL.md) y [ld-transferencia](../ld-transferencia/SKILL.md).

## Dirección visual: Soft Glass

Interfaz **moderna, sobria y de vidrio suave** (referencia: tablero «Soft Glass» con lateral, indicadores y listas de acción): fondo con degradado
claro y manchas de color suaves, **tarjetas translúcidas con desenfoque**, borde fino claro, sombras difusas, esquinas muy redondeadas, botones
en pastilla, una sola acción primaria por tarjeta, tipografía del sistema, estados completos y tema claro u oscuro automático. Solo CSS, **sin librerías**.
No inventes estilos: **todo sale de [LD.css](./examples/LD.css)** (variables `--ld-*`, componentes `ld-*` y las clases de los demos).
Sin `backdrop-filter` el CSS cae a superficies opacas (siempre legible).

## Antes de diseñar: ¿qué diseño eligió el proyecto?

Lee `.ld/diseno.json` (lo crea `iniciar_proyecto.py`; si no existe, es `ld`).

| `modo` | Qué haces |
|---|---|
| `ld` (por defecto) | Sigue esta skill: Soft Glass con `LD.css`. |
| `externo` | Carga el skill indicado en `skill` y **cede el aspecto** a él (puede usar Tailwind u otra librería, solo para el diseño); aquí conservas estructura, `id`, accesibilidad, estados y verificación. Lee [diseno-externo.md](./references/diseno-externo.md). Si el skill no está instalado, detente y avísalo. |

Three.js (fondo 3D) es un extra **solo si la persona lo pide**: [fondo-3d-opcional.md](./references/fondo-3d-opcional.md).

## Procedimiento

1. Inspecciona el proyecto: ¿carga `LD.css`, `DACP.css` o nada? En modo `ld`, usa `LD.css` en pantallas nuevas y al modernizar (el kit base lo instala en `Static/styles/LD.css`, con los iconos de `Static/Images/Icons`).
2. Define la tarea del usuario, la acción primaria y los estados: cargando, vacío, error, éxito y parcial.
3. **Parte de [pantalla-base.html](./examples/pantalla-base.html)** (o de [dashboard-glass.html](./examples/dashboard-glass.html) si es un tablero con lateral), no de una página en blanco ni de un demo antiguo: copia su esqueleto (`Titulo`, `Subtitulo`, `main.ld-pagina`, una `section.ld-tarjeta` por tarea) y cambia solo el contenido. Componentes y HTML en [componentes.md](./references/componentes.md).
4. Escribe HTML semántico con `label for`, botones reales y los `id` que ya usa el JavaScript; los datos de usuarios se muestran como texto. Los mensajes vacíos al inicio (`ld-alerta`) se ocultan solos.
5. **Verifica en dos pasos, en este orden** (los scripts son del paquete Skill_LD; corrígelos hasta que ambos pasen):
   1. `python scripts/revisar_diseno.py pantalla.html` (lee `.ld/diseno.json`; en `externo` solo vigila `style=` y colores sueltos): estructura (hoja `LD.css`, `ld-pagina`, `ld-tarjeta`, nada suelto en `<body>`, sin `style=` ni colores sueltos). Una página de Django se revisa tal cual, con sus `{% %}`.
   2. `python scripts/capturar_pantalla.py pantalla.html`: capturas clara, oscura y móvil. **Mira las imágenes** y comprueba el criterio de acabado de abajo; un script que pasa no garantiza que se vea profesional.

## Acabado profesional (lo que se mira en la captura)

- **Márgenes:** el contenido nunca toca el borde de la ventana; título, subtítulo y tarjetas comparten el mismo borde izquierdo y derecho.
- **Agrupación:** cada tarea en su tarjeta con `h2`; nada flota fuera de una tarjeta.
- **Jerarquía:** un título, un subtítulo, títulos de tarjeta; una sola acción primaria (`Boton`) y el resto `Boton Secundario`; los enlaces de apoyo van al final de la barra (`ld-barra-fin`).
- **Texto de apoyo discreto:** formatos aceptados, límites y pistas con `ld-ayuda`; contadores con `ld-metricas`; los resultados y errores con `ld-alerta`, no con `Mensaje` coloreado.
- **Alineación:** etiquetas y controles en la rejilla `Fila` > `Ancho20` + `Ancho80`; nada centrado a medias ni con anchos distintos sin razón.
- **Densidad:** aire entre tarjetas y dentro de ellas; sin bloques vacíos grandes ni elementos apretados.

## Anti-patrones (lo que arruinó una pantalla real)

| No hagas | Haz |
|---|---|
| Elementos (`Marco`, `Fila`, `div`) sueltos en `<body>`, sin `main.ld-pagina` | `main.ld-pagina` > `section.ld-tarjeta` > `Fila` |
| `Marco` + `style="border:2px dashed ..."` como zona de arrastre | `div.ld-dropzone` |
| `style="width:250px"`, `style="color:#a33"`, `style="display:flex;gap:8px"` | `ld-barra`, `ld-galeria`, `ld-alerta error`, `ld-ayuda`; el ancho lo da `LD.css` |
| `Mensaje` para formatos aceptados o errores | `ld-ayuda` para pistas; `ld-alerta` para estados |
| Contador suelto en una `Fila` | `ld-metricas` con `<strong>` en cada valor |
| Botones de acción sin jerarquía (todos `Boton`) | Uno `Boton`, los demás `Boton Secundario` |
| Copiar la estructura de un demo antiguo de `webpython` | Copiar `pantalla-base.html` |

## Reglas

- Sin `style="..."` en línea, sin colores ni medidas sueltas, sin maquetar con tablas ni `float`: usa las clases y los tokens.
- Un botón con texto (o `aria-label`) para cada acción; no uses imágenes como botones nuevos.
- Los controles y mensajes asociados con su `label` o `role`; el error aparece cerca de la acción y conserva lo escrito.
- Móvil sin desbordes horizontales; tablas con desplazamiento contenido; contraste de texto de al menos 4,5:1; foco visible.
- Cualquier cosa fuera de `main.ld-pagina` solo recibe márgenes por una red de seguridad de `LD.css`: no es la estructura; cúmplela.
- Para cambiar la marca redefine `--ld-primario` en una hoja posterior a `LD.css`; no la edites.
- Antes de diseñar pausa, reanudación o cancelación, confirma que el cliente las implementa.

## Ejemplos

- [dashboard-glass.html](./examples/dashboard-glass.html): tablero Soft Glass (lateral `ld-shell`, indicadores `ld-kpis`, listas de acción `ld-item`).
- [FondoGlass3D.js](./examples/FondoGlass3D.js): fondo 3D opcional con Three.js.
- [pantalla-base.html](./examples/pantalla-base.html): **plantilla de partida** (portal de imágenes con zona de arrastre, contador, formulario y resultado, ya sin defectos).
- [catalogo.html](./examples/catalogo.html): todos los componentes juntos (formulario, botones, zona de arrastre, galería, progreso, tabla de `Gui.Grilla`, paginación, ventana, alertas y estados). Abre el archivo en el navegador; la tecla `T` alterna claro y oscuro.
- [LD.css](./examples/LD.css): el tema. [DACP.css](./examples/DACP.css): el estilo original, solo por compatibilidad.
- Pantallas completas con este diseño: `ld-transferencia/examples/CargaArchivos.html` y `ld-crud/examples/Mantenimiento.html`.

## Checklist

- ¿La acción primaria es obvia y única en su tarjeta?
- ¿Están resueltos cargando, vacío, error, éxito y parcial?
- ¿Pasó `revisar_diseno.py` sin errores y se revisaron las capturas clara, oscura y móvil, sin desbordes ni texto ilegible?
- ¿Hay márgenes y alineación consistentes, y cada tarea en su tarjeta?
- ¿Todo es operable con teclado, con etiquetas y foco visibles?
- ¿Se usaron solo clases y tokens de `LD.css`, sin estilos en línea ni colores sueltos, y nada suelto en `<body>`?
