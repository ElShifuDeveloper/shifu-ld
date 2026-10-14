# Diseño externo (opcional)

Por defecto un proyecto LD usa el diseño del paquete: **Soft Glass** de [LD.css](../examples/LD.css), solo con CSS y sin librerías.
La persona puede elegir, **al iniciar el proyecto**, un skill de diseño externo (por ejemplo uno basado en Tailwind). La elección queda en
`.ld/diseno.json` y la hace `scripts/iniciar_proyecto.py`:

```json
{ "modo": "ld" }
{ "modo": "externo", "skill": "nombre-del-skill" }
```

Cambiarla después: `python scripts/iniciar_proyecto.py <proyecto> --diseno externo --skill-diseno <nombre>` o `--diseno ld`. `--update` no la toca.

## Qué se cede y qué se conserva

| Con modo `externo` el skill externo decide | `ld-design` sigue exigiendo (siempre) |
|---|---|
| Aspecto: paleta, tipografía, componentes, iconos, animaciones | Estructura clara: un título, una tarea por bloque, una acción primaria |
| Librerías **de diseño**: CSS (Tailwind, Bootstrap…), iconos, fuentes, Three.js | Los `id` y las clases de comportamiento (`M`, `R`, `L`, `E`, `D`) que usa el JavaScript |
| Su propio sistema de rejilla y tokens | Sin `style="..."` en línea ni colores sueltos en `<style>` |
| | Accesibilidad: `label for`, foco visible, contraste 4,5:1, teclado, sin desbordes en móvil |
| | Estados completos (cargando, vacío, error, éxito, parcial) y verificación con capturas |

## Reglas para las librerías externas

1. **Solo diseño.** Ninguna librería toca datos, rutas, transferencias ni lógica: el funcionamiento sigue sin librerías (`General.js`, `Paquetes.js`,
   `fetch`). Nada de React, Vue, jQuery, axios ni similares para el comportamiento.
2. **Locales y con versión fijada.** Los archivos van en `Static/vendor/` (CSS compilado, fuentes, `three.module.min.js`…); sin CDN en ejecución. Si el skill
   externo exige compilar (Tailwind), se compila a un `.css` estático que se versiona; no hay paso de compilación en el servidor.
3. **Texto de usuarios con `textContent`**, también con componentes externos.
4. **Anótalo:** el plan (*Technical Context*, fila «Diseño») nombra el skill y las librerías; la constitución, en su principio I, ya excluye las de solo diseño.
5. Si el skill externo no está instalado, **detente y avisa** (como cualquier skill LD); no lo sustituyas por LD.css en silencio.

## Los componentes que genera `General.js`

`Gui.Grilla`, `Popup` y la galería escriben HTML con clases fijas. Un diseño externo debe estilizarlas con un archivo propio del proyecto
(`Static/styles/puente-externo.css`, se escribe una vez):

| Genera | Clases que hay que estilizar |
|---|---|
| `Gui.Grilla` | `table`, `.FilaCabecera`, `.FilaDatos`, `.Pagina`, `.PaginaSel`, `.Icono`, `.Derecha`, `.Centro`, `.Orden` |
| `Popup` | `.PopupContainer` (oculta con `display:none`), `.PopupWindow`, `.BarraTitulo`, `.Cuerpo` (el script fija `left/top/width/height`) |
| Galería | `.MarcoImagen1/2/3`, `.MarcoImagen2Sel`, `.Imagen` |
| Mensajes | `.Mensaje`, `[hidden]` |

Con Tailwind se hace con `@apply` en ese archivo. Si hay dudas, [LD.css](../examples/LD.css) muestra qué propiedades necesita cada clase.

## Verificación en modo externo

- `python scripts/revisar_diseno.py pantalla.html` lee `.ld/diseno.json` y, en `externo`, **no** exige `LD.css`, `ld-pagina` ni `ld-tarjeta`; sí marca `style="..."`
  en línea y colores sueltos. (`--modo ld|externo` lo fuerza.)
- `python scripts/capturar_pantalla.py pantalla.html` sigue valiendo: revisa claro, oscuro (si el diseño lo soporta) y móvil.
