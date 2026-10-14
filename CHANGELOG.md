# Historial de cambios del paquete LD

Formato: `## [versión] - fecha`, con **Cambios** y **Migración** (acciones manuales que el script no puede hacer solo).
Versionado semántico: MAJOR si cambia la forma de trabajar o se retira algo; MINOR si se añade capacidad compatible; PATCH si solo
se corrige o se aclara. El script `scripts/iniciar_proyecto.py --version` muestra lo que cambió desde la versión instalada.

## [2.6.0] - 2026-10-13

- **`ld-transferencia`: máximo de archivos por lote configurable desde una sola fuente.** Nuevo `settings.LD_MAX_ARCHIVOS_LOTE`
  (200 por defecto, configurable por variable de entorno entre 1 y 10 000). Las vistas aplican el valor en subida y descarga y
  lo entregan a ambas pantallas como `hdfMaxArchivosLote`; `Paquete.PlanificarViajes` y `AgruparPorTamano` reciben el máximo como
  parámetro en vez de mantener un 200 duplicado en el cliente y el servidor.
- Pruebas: verifican el valor por defecto, la lectura configurable, límites inválidos y el corte de lotes con máximos distintos.

### Migración
- Copia la nueva variable `LD_MAX_ARCHIVOS_LOTE` de `examples/settings_transferencia.py` a la configuración Django. Agrega
  `hdfMaxArchivosLote` a las plantillas de carga y consulta (por ejemplo, `<input id="hdfMaxArchivosLote" type="hidden" value="{{ MaxArchivosLote }}">`);
  las vistas `PantallaCarga` y `PantallaConsulta` deben pasar `MaxArchivosLote` al contexto. Si se personalizaron los clientes,
  pasa ese límite como cuarto argumento de `Paquete.PlanificarViajes` y tercer argumento de `Paquete.AgruparPorTamano`.

## [2.5.0] - 2026-10-13

- **`ld-transferencia`: descarga simétrica a la subida (la mitad que faltaba).** La descarga usa la misma regla de decisión: archivos de
  `LD_SIZE_LOTE` o menos viajan agrupados en paquetes de bytes y los mayores por bloques de `LD_SIZE_BLOQUE` que el cliente une con
  `new Blob(partes)` y comprueba contra el tamaño anunciado. Reutiliza `Paquete.PlanificarViajes` (el plan no depende de la dirección:
  lote → `ObtenerPaquete`, bloque → `ObtenerBloque`) y `Archivos.LeerBloque` (ya existía con pruebas, pero ninguna vista lo usaba).
  Vistas nuevas: `ObtenerBloque` (GET `Carpeta`, `Nombre`, `Indice`; bytes `octet-stream` o error en texto) y `PantallaConsulta` (entrega
  `hdfSizeLote`/`hdfSizeBloque` a la galería). `GaleriaLotes.js` reescrito: plan por viajes con progreso y reintento del viaje fallido
  (la descarga es idempotente: el mismo índice devuelve los mismos bytes; no hace falta reiniciar el archivo).
- **Corrección:** `ObtenerPaquete` ya no trunca la respuesta en silencio al pasar un tope (el cliente mostraba menos imágenes de las
  pedidas, sin error): aplica `LD_SIZE_LOTE` y rechaza con `Error - ...` el lote que lo supere o que pida un archivo mayor; se retira el
  `MAX_PAQUETE` fijo de 2 MB. `ObtenerArchivo` envía `as_attachment` con el filename (guardar a disco) y sus errores viajan como texto.
  Sustituye lo dicho en 2.4.0 («la descarga por lotes de la galería conserva su propio tamaño de ~100 KB; no cambia»).
- Pruebas: `test-paquetes.js` verifica que el mismo plan sirve para la descarga (todo pequeño → un viaje; grande → viajes de bloque en orden).

### Migración
- Proyectos con la galería anterior: `--update` reemplaza los archivos del skill y del kit, pero el código COPIADO al proyecto hay que
  adaptarlo: añade la vista y la ruta `ObtenerBloque`, haz que la pantalla de consulta entregue `SizeLote`/`SizeBloque` (campos ocultos
  `hdfSizeLote`/`hdfSizeBloque`) y que su JavaScript los lea y planifique con `Paquete.PlanificarViajes` en vez de `AgruparPorTamano` a 100 KB.
- Síntoma del bug que corrige: carpetas con archivos mayores que el lote se guardaban (bloques I/P) pero su galería se detenía con
  «Lote demasiado grande»; compruébalo con una carpeta que tenga fotos mayores que `LD_SIZE_LOTE`.

## [2.4.0] - 2026-10-13

- **`ld-transferencia`: tamaños de lote y bloque paramétricos, con una sola fuente.** `settings.LD_SIZE_LOTE` (512 KB por defecto) y `settings.LD_SIZE_BLOQUE`
  (256 KB por defecto), con variable de entorno del mismo nombre y validación al arrancar (`examples/settings_transferencia.py`, con pruebas). Las vistas los usan
  como tope (`MAX_LOTE`, `MAX_BLOQUE`, con margen para la cabecera y el texto del paquete) y la nueva vista `PantallaCarga` los entrega al navegador en los campos
  ocultos `hdfSizeLote` y `hdfSizeBloque`; `CargaArchivos.js` los lee con `Paquete.ParametroEntero`. Antes `sizeLote = sizeBloque = 100 KB` (valor de los demos, pensados
  para miniaturas) estaba escrito a mano en cliente y servidor: 12 fotos de 1,25 MB generaban 16 viajes de datos; ahora, con los defaults, 4. Verificado de punta a
  punta con Django 5.2 (la página entrega los valores y el servidor rechaza un lote o bloque que los supere).
- **Corrección:** la skill decía que había que ajustar `DATA_UPLOAD_MAX_MEMORY_SIZE` al subir el tamaño de lote. Es incorrecto: ese ajuste solo cuenta los campos de texto y no
  limita los archivos (ni `FILE_UPLOAD_MAX_MEMORY_SIZE`, que solo decide memoria o disco). Los límites reales son los `LD_SIZE_*` que comprueban las vistas y el cuerpo máximo del
  proxy en producción. La receta añade la estimación de llamadas por tanda (`2 + lotes + bloques`).
- La descarga por lotes de la galería (`GaleriaLotes.js`, `ObtenerPaquete`) conserva su propio tamaño de ~100 KB; no cambia.

### Migración
- Proyectos con `sizeLote`/`sizeBloque` o `MAX_LOTE`/`MAX_BLOQUE` escritos a mano: pásalos a `settings.py` con `settings_transferencia.py`, haz que la vista de la página entregue `SizeLote`
  y `SizeBloque` (campos ocultos `hdfSizeLote` y `hdfSizeBloque`) y que el JavaScript los lea; quita números fijos de `views.py` y del `.js`. Hazlo como feature con
  `/speckit.specify` y `/speckit.plan`, porque `plan.md` y `research.md` pueden fijar 100 KB.
- Si pusiste `DATA_UPLOAD_MAX_MEMORY_SIZE` o `FILE_UPLOAD_MAX_MEMORY_SIZE` para limitar los archivos, no cumplen esa función: déjalos por defecto y define el tope en `LD_SIZE_*` y en el proxy.

## [2.3.0] - 2026-10-13

- **`ld-design` pasa a «Soft Glass» por defecto, solo con CSS:** fondo con degradado suave, tarjetas translúcidas con desenfoque (con respaldo
  opaco si el navegador no soporta `backdrop-filter`), bordes finos, sombras difusas, radios grandes y botones en pastilla; claro y oscuro.
  Nuevos componentes de tablero: `ld-shell`, `ld-lateral`, `ld-nav`, `ld-kpis`/`ld-kpi`, `ld-item` y `ld-panel`; ejemplo `dashboard-glass.html`.
  La primaria por defecto pasa a un índigo profundo (redefine `--ld-primario` para tu marca).
- **Three.js opcional:** `examples/FondoGlass3D.js` y `references/fondo-3d-opcional.md`. Solo si la persona lo pide; librería local con versión
  fijada, sin CDN; respeta `prefers-reduced-motion` y no hace nada sin WebGL. Probado con Three.js 0.170.0.
- **Diseño externo elegible al iniciar el proyecto:** `iniciar_proyecto.py` pregunta (o recibe `--diseno ld|externo` y `--skill-diseno <nombre>`) y guarda
  la elección en `.ld/diseno.json`; `--update` no la cambia. En modo `externo`, `ld-design` cede el aspecto al skill indicado (puede usar Tailwind u otra
  librería, solo de diseño) y conserva estructura, `id`, accesibilidad y verificación (`references/diseno-externo.md`). `revisar_diseno.py` lee el modo.
  El bloque de `AGENTS.md`, el *Technical Context* por defecto y el principio I de la plantilla de constitución lo reflejan.

### Migración
- Las pantallas que usen `LD.css` cambian de aspecto al actualizar (más redondeadas y con vidrio); revísalas con `revisar_diseno.py` y las capturas.
  Si tu marca redefine `--ld-primario`, no cambia.
- La plantilla de constitución cambió (principio I: las librerías de solo diseño de un skill externo no cuentan como framework). Si ya tienes constitución y vas a
  usar diseño externo, enmiéndala (MINOR): `/speckit.constitution Usa el skill ld-speckit y su plantilla de constitución`. Con el diseño `ld` no hace falta.
- `--update` crea `.ld/diseno.json` con `ld` si no existe (sin terminal interactiva) y lo avisa; para un skill externo repite con `--diseno externo --skill-diseno <nombre>`.

## [2.2.0] - 2026-10-13

- **`ld-transferencia`: subida mixta en un solo recorrido y en orden.** Nuevo `Paquete.PlanificarViajes` (`Paquetes.js`): los archivos pequeños se
  acumulan en un lote mientras la suma no supere `sizeLote` (100 KB); el que no cabe abre el siguiente lote; un archivo mayor cierra el lote
  abierto, se corta en bloques `I`/`P` y, al terminar su último bloque, el flujo continúa con los demás. Antes `prepararCola` enviaba primero
  todos los pequeños y después todos los grandes (reordenaba la tanda). `CargaArchivos.js` lo usa; el servidor no cambia. Con pruebas.

### Migración
- Los proyectos con `Paquetes.js` y `CargaArchivos.js` anteriores: `--update` los reemplaza; si el proyecto adaptó `prepararCola`, cámbialo para
  que llame a `Paquete.PlanificarViajes`. No hay cambios en las rutas ni en `modPaquetes.py`.

## [2.1.0] - 2026-10-13

- **`ld-design` más estricto y profesional:** `LD.css` aplica el mismo ancho y margen lateral (`--ld-margen`) a todo lo que cuelga de `<body>`
  (ya no queda contenido pegado al borde aunque se salte la estructura); nuevas clases `ld-ayuda`, `ld-metricas` y `ld-encabezado`; grupos de
  botones y `a.Boton` bien resueltos. Plantilla `examples/pantalla-base.html`, secciones «Acabado profesional» y «Anti-patrones» en `SKILL.md`,
  y `scripts/revisar_diseno.py` (revisor estático de estructura, con pruebas). `catalogo.html` ya no usa `style=` en línea.
- **`ld-speckit` enlaza con `ld-design`:** las tareas `[pantalla]` de `/speckit.tasks` incluyen el criterio de cierre de diseño
  (plantilla `pantalla-base.html`, `revisar_diseno.py` sin errores y capturas revisadas); regla en `references/tareas.md`.

### Migración
- Las pantallas ya construidas no cambian solas: pasa `python scripts/revisar_diseno.py` por cada una y rediséñalas con una feature nueva
  (`/speckit.specify` → `plan` → `tasks` → `implement`) si el revisor reporta errores.
- Si una `tasks.md` existente tiene tareas `[pantalla]` sin el criterio de cierre, añádelo con `/speckit.tasks` o a mano.

## [2.0.0] - 2026-10-13

Reorientación a la metodología LD: **cadenas delimitadas y bytes**, con bloques, lotes y viajes; JSON solo para terceros.

### Cambios
- **Nuevo skill `ld-transferencia`:** subida por bloques `I`/`P`, lotes y paquetes de bytes, descarga de varias imágenes en un viaje,
  registros por viajes (técnicas de `appDemo13`, `10`, `26` y `28`), con `Paquetes.js` y `modPaquetes.py`.
- **`ld-crud-legacy` pasa a llamarse `ld-crud`** (el estilo de los demos es el estilo base, no uno heredado).
- **Nuevo skill `ld-speckit`:** constitución base, *Technical Context* por defecto, tareas por capa, detección de la etapa
  («¿qué sigue?») y arranque de proyectos.
- **`ld-design` moderno:** `LD.css` (tokens, tema claro y oscuro, adaptable a móvil) compatible con `General.js` y las clases de los
  demos; catálogo de componentes; `capturar_pantalla.py` para verificar con capturas.
- **Kit base con tus archivos reales:** `modAccesoDatos.py`, `modUtilidades.py`, `General.js`, `DACP.css`, `sha256.js`,
  `modGraficos.py` y los iconos `Static/Images/Icons/`. El cliente SQL «mejorado» queda como variante opcional.
- **Sin límites de usuario por defecto** en las transferencias (archivo, cantidad y tanda); solo límites técnicos del protocolo.
- El protocolo JSON/cursor pasa a ser una alternativa para integraciones con terceros.
- **«Streaming» definido:** en LD significa la metodología por chunks (bloques con progreso); el formato puede ser cadena delimitada u `octet-stream`. El tamaño de bloque es 100 KB por defecto y parametrizable (`sizeBloque`/`sizeLote`, `settings.LD_SIZE_BLOQUE`).
- Mecanismo de actualización: versión, manifiesto `.ld/manifest.json` y `--version` (solo lectura) y `--update` del script: este reemplaza todo lo que difiera y deja las versiones anteriores como `*-old`.

### Migración
- Si tu constitución es anterior a esta versión, enmiéndala (MINOR) con
  `/speckit.constitution Usa el skill ld-speckit y su plantilla de constitución`: el principio I añade cadenas y bytes, `LD.css` y
  `ld-transferencia`, y el VIII incluye `ld-transferencia`.
- Si una especificación fijó límites de tamaño o cantidad que nadie pidió (por ejemplo `FR-006`), quítalos con `/speckit.clarify`,
  vuelve a ejecutar `/speckit.plan` y usa `/speckit.converge` para que las tareas nuevas lleguen al código.
- Las pantallas pasan a `LD.css` cambiando el `<link>` (conserva los nombres de clase de `DACP.css`); revisa con
  `python scripts/capturar_pantalla.py`.
- Los proyectos instalados con una versión anterior no tienen manifiesto: `--update` los regulariza y deja cada versión anterior
  como `*-old` (por ejemplo `General-old.js`); revísalas para integrar lo que habías personalizado y bórralas después.

## [1.0.0] - 2026-10-08

Versión inicial (sin número): coordinador, `ld-design`, `ld-frontend`, `ld-backend`, `ld-data`, `ld-crud-legacy`,
`ld-security-session`, `ld-charts` y `ld-realtime`.
