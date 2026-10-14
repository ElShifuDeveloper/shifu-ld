# Componentes de LD.css y patrones de pantalla

Cada componente usa el HTML que ya producen tus demos y `General.js`; no hace falta cambiar su JavaScript. Verlos juntos:
[catalogo.html](../examples/catalogo.html) (ábrelo en el navegador).

## Estructura de una pantalla

```html
<link href="{% static 'static/styles/LD.css' %}?v={{Ver}}" rel="stylesheet" />
<div class="Titulo">Título de la pantalla</div>
<div class="Subtitulo">Qué se puede hacer aquí</div>
<main class="ld-pagina">
  <section class="ld-tarjeta" aria-labelledby="hX"><h2 id="hX">Sección</h2> ... </section>
</main>
```

Una tarjeta por tarea o grupo de contenido; dentro, `h2` y el contenido. La página nunca depende de `style="..."` en línea. Esqueleto completo y listo para copiar: [pantalla-base.html](../examples/pantalla-base.html). `LD.css` da el mismo ancho máximo y margen lateral (`--ld-margen`) a `Titulo`, `Subtitulo` y `ld-pagina`; un elemento a todo el ancho (barra superior) lleva `ld-ancho-total`.

## Componentes

| Necesidad | Clases / HTML |
|---|---|
| Formulario | `div.Fila` > `div.Ancho20` (`<label for>`) + `div.Ancho80` (control). En móvil se apilan solos. Clases de comportamiento `M`, `R`, `L`, `E`, `D` de `General.js` se conservan. |
| Botones | `Boton` (primario), `Boton Secundario`, `Boton Peligro`, `BotonSmall`, `BotonGrid`. Una sola acción primaria por tarjeta. Barra de botones: `div.ld-barra` (`ld-barra-fin` empuja uno a la derecha). |
| Tabla / lista | `Gui.Grilla` ya produce `table > thead > tr.FilaCabecera` y `tbody > tr.FilaDatos`; paginación `Pagina`/`PaginaSel`; iconos `Icono`. En pantallas estrechas se desplaza horizontalmente dentro de la tarjeta. |
| Ventana emergente | `PopupContainer` > `PopupWindow` > `BarraTitulo` (título + botón **✕** con texto) + `Cuerpo`. `Popup.Resize` y `Popup.ConfigurarArrastre` siguen funcionando. |
| Texto de apoyo y contadores | `ld-ayuda` (pistas, formatos aceptados); `div.ld-metricas` con `<span>Etiqueta: <strong>valor</strong></span>`. |
| Tablero | `div.ld-shell` > `aside.ld-lateral` (`nav.ld-nav` con `a[aria-current="page"]`, `ld-nav-titulo`) + `main.ld-pagina`; indicadores `div.ld-kpis` > `div.ld-kpi` (`<span>` etiqueta, `<strong>` valor); fila con acción `div.ld-item`; panel blanco interior `ld-panel`. Ejemplo: [dashboard-glass.html](../examples/dashboard-glass.html). |
| Zona de arrastre | `div.ld-dropzone` (añade la clase `activo` en `ondragover`). |
| Galería de miniaturas | `div.ld-galeria` con tarjetas `MarcoImagen2` > `img.Imagen` + nombre + acción. Una columna en móvil, varias en escritorio. |
| Progreso | `<progress>` (ya estilizado) + texto "Viaje x/n" junto a él. |
| Estados | `ld-alerta info / ok / error / aviso` (un contenedor vacío se oculta solo), `ld-vacio` para "sin datos", `ld-cargando` (indicador), `ld-insignia` (contador o etiqueta). |

## Estados que toda pantalla de datos debe resolver

| Estado | Qué se ve |
|---|---|
| Cargando | Texto o indicador (`ld-cargando`) junto a la acción; los botones afectados deshabilitados |
| Vacío | `ld-vacio` con una frase útil y la acción que lo resuelve |
| Error | `ld-alerta error` cerca de la acción o el campo, con el mensaje del servidor (`Error - ...`) y sin perder lo escrito |
| Éxito | `ld-alerta ok` con el resultado concreto (cuántos, dónde), no solo "Listo" |
| Parcial | `ld-alerta aviso` con qué quedó fuera y por qué |

## Pantallas de transferencia (los seis flujos, solo lo visual)

El protocolo está en [ld-transferencia](../../ld-transferencia/SKILL.md) y en el
[contrato](../../ld-backend/references/transfer-contract.md); aquí lo que la pantalla debe mostrar:

1. **Texto paginado:** filtros, tamaño de página, navegación y estados cargando, vacío y error.
2. **Catálogo de archivos:** filas con nombre, tipo, tamaño y acciones de vista previa y descarga.
3. **Texto más archivos:** metadatos y estado de cada contenido binario, sin presentar bytes como texto.
4. **Carga de CSV o texto grande:** selección, formato aceptado, validación previa, avance por viaje, registros procesados y resumen de errores.
5. **Varios archivos:** miniatura con quitar antes de guardar, avance por viaje, cancelar y reintentar, resultado final por archivo.
6. **Texto y archivos juntos:** un resumen único, con validación y estado de cada elemento separados; no declarar éxito global mientras quede uno incompleto.

Reglas: no comuniques éxito por bytes enviados sino por viajes confirmados; antes de diseñar pausa, reanudación o cancelación,
confirma que el cliente las implementa; un nombre de archivo del usuario siempre se muestra como texto.

## Accesibilidad y adaptación

- `label` asociado a cada control; botones reales para acciones (nada de imágenes como botones: usa texto o `aria-label`).
- Orden de tabulación lógico, foco visible (lo da `LD.css`), operación por teclado en toda acción.
- No comuniques estado solo con color: acompáñalo con texto.
- Contraste de texto de al menos 4,5:1 (los tokens ya lo cumplen en claro y oscuro); objetivos táctiles de 40 px o más.
- Móvil primero: sin desbordes horizontales, formularios apilados, tablas con desplazamiento contenido.
- `prefers-reduced-motion` ya está respetado; no añadas animaciones esenciales.

## Tokens (no pongas colores ni medidas sueltas)

`--ld-primario`, `--ld-superficie`, `--ld-superficie-2`, `--ld-fondo`, `--ld-borde`, `--ld-texto`, `--ld-texto-suave`,
`--ld-ok`, `--ld-peligro`, `--ld-aviso` (y sus `-suave`), `--ld-radio`, `--ld-sombra`, escala de espacio `--ld-e1` a `--ld-e6`.
El tema oscuro sale solo del sistema; se fuerza con `<html data-tema="claro|oscuro">`. Para cambiar la marca, redefine
`--ld-primario` (y su `-hover`, `-suave`) en una hoja del proyecto cargada **después** de `LD.css`.

## Proyectos que ya usan DACP.css

`LD.css` conserva los nombres de clase de `DACP.css`: basta cambiar el `<link>` para modernizar una pantalla existente. Hazlo
pantalla por pantalla y comprueba el resultado con las capturas; las pantallas con estilos en línea (`style="width:..px"`,
colores) conservarán esos valores hasta que se limpien.
