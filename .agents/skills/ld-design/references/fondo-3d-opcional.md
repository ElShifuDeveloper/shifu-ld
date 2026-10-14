# Fondo 3D opcional con Three.js

**No es parte del diseño por defecto.** Soft Glass se ve completo con solo CSS. Este extra se añade únicamente si la persona lo pide
(por ejemplo, «fondo animado en 3D»). Three.js es una librería externa **de diseño**: sigue las reglas de [diseno-externo.md](./diseno-externo.md)
(solo diseño, archivo local con versión fijada, sin CDN).

## Cómo se agrega

1. Descarga una versión fija de Three.js (`npm pack three@<versión>` o su release) y copia `build/three.module.min.js` a
   `Static/vendor/three.module.min.js`. Registra la versión en el plan (*Technical Context*, fila «Diseño»).
2. Copia [FondoGlass3D.js](../examples/FondoGlass3D.js) a `Static/scripts/FondoGlass3D.js`.
3. Al final del `<body>`:

```html
<script type="module">
  import * as THREE from "{% static 'vendor/three.module.min.js' %}";
  import { FondoGlass3D } from "{% static 'scripts/FondoGlass3D.js' %}";
  FondoGlass3D(THREE);            // opciones: { esferas: 7, velocidad: 0.25 }
</script>
```

Dibuja esferas translúcidas detrás del contenido (`canvas.ld-fondo3d`, fijo y con `z-index:-1`); el desenfoque de las tarjetas de vidrio las difumina,
como en el tablero de referencia. Los colores salen de `--ld-primario`, así que siguen a la marca.

## Qué garantiza

- **Sin WebGL o con error:** no hace nada y queda el degradado CSS.
- **`prefers-reduced-motion`:** dibuja un solo cuadro, sin animación.
- **Pestaña oculta:** pausa la animación; densidad de píxeles limitada a 1,5; `FondoGlass3D(THREE)` devuelve una función para destruirlo.
- La pantalla **no depende** de él: ningún dato, `id` ni acción pasa por Three.js.

Probado con Three.js 0.170.0 en Chrome headless (software WebGL). Revisa en capturas que el texto siga legible sobre las esferas; si no, baja `esferas`.
