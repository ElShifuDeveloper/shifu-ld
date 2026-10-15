---
name: ld-crud
description: "Crea o mantiene pantallas de consulta y mantenimiento (CRUD con popup) en el estilo base de los proyectos LD: app Django con views/urls, HTML + JavaScript nativo, General.js (Gui, Popup, Validacion), LD.css y procedimientos almacenados con clienteSQL y datos delimitados ¬ | _. Úsalo cuando el proyecto ya sigue ese patrón (appDemo03–appDemo14) o se pide una pantalla 'como las demás'."
---

# LD_crud

> Metodología **LD** (cadenas delimitadas, bytes, bloques, lotes y empaquetado) creada por **Luis Dueñas Huaroto**; documentada aquí para agentes.

Convención base de las aplicaciones LD para una pantalla de consulta o de mantenimiento: **es el estilo de los proyectos LD**, no un estilo antiguo que haya que modernizar. Es el patrón de `appDemo03`–`appDemo14` de `webpython`: se aplica también en proyectos nuevos, y la consistencia con las demás pantallas pesa más que cualquier alternativa. Entrada del paquete: [ld-project-coordinator](../ld-project-coordinator/SKILL.md).

## Cuándo aplicarlo

| Situación | Decisión |
|---|---|
| Pantalla de consulta o mantenimiento en cualquier proyecto LD, nuevo o existente | Sigue este skill: `Consulta`/`Mantenimiento` con `Gui.*`, SP `...Csv` y cadenas delimitadas. |
| Volumen grande, archivos, imágenes, cargas masivas | Mantén el estilo (cadenas y bytes) y mueve los datos por viajes: [ld-transferencia](../ld-transferencia/SKILL.md). |
| Un tercero consume los datos (JSON o XML) | Un servicio aparte ([ld-realtime](../ld-realtime/SKILL.md)); la pantalla sigue con cadenas. |
| Sesión, login y auditoría | [ld-security-session](../ld-security-session/SKILL.md). |

## Kit base del proyecto

El estilo necesita estos archivos en el proyecto; `scripts/iniciar_proyecto.py` los instala si faltan (no sobrescribe), o cópialos a mano desde los skills:

| En el proyecto | Fuente en los skills |
|---|---|
| `Modulos/modAccesoDatos.py`, `Modulos/modUtilidades.py` | `ld-data/examples/base/` |
| `Modulos/modSeguridadWeb.py`, `Modulos/modGraficos.py`, `Static/scripts/sha256.js` | `ld-security-session/examples/` |
| `Modulos/modPaquetes.py`, `Static/scripts/Paquetes.js` | `ld-transferencia/examples/` |
| `Static/scripts/General.js` | `ld-frontend/examples/base/` |
| `Static/styles/LD.css` (tema moderno), `Static/styles/DACP.css` (original) y `Static/Images/Icons/` | `ld-design/examples/` |

Configuración de Django que suponen las pantallas: `TEMPLATES[0]["DIRS"] = [BASE_DIR]` (las plantillas se llaman `appX/Pantalla.html`) y `STATICFILES_DIRS = [BASE_DIR]` (se referencian como `{% static 'static/scripts/General.js' %}`). La carpeta se llama `Static`: en Windows y macOS la ruta `static/...` la resuelve igual, en Linux no (renómbrala `static` al desplegar). `General.js` también espera un `<input type="hidden" id="hdfRaiz" value="/static/static/"/>` en cada pantalla que use `Gui.Grilla`.

## Datos delimitados y SP del ejemplo

Los SP `...Csv` devuelven un escalar: registros separados por `¬` (o `;` en los `...PyCsv`), campos por `|` y listas por `_`; `Gui.Grilla` espera tres filas de metadatos (nombres, anchos, tipos) y luego los datos. Una respuesta vacía significa error o sin datos, y los separadores no se escapan, así que ningún dato de usuario puede contenerlos. El formato completo, los formatos por SP y el contrato verificado de los cuatro SP del ejemplo (`uspProductoListasCboCsv`, `...ObtenerPorId2`, `...Grabar3Csv`, `...Eliminar3Csv`) están en [datos-delimitados.md](./references/datos-delimitados.md).

Lo que condiciona el código: el orden de los controles `M` del formulario es el orden de los 6 campos del SP; Grabar y Eliminar necesitan `trx=True`; las vistas devuelven 500 cuando `clienteSQL` devuelve `None` y el JS lo detecta con `rptaHttp.ok`; los riesgos de los SP (texto escapado, filas con `NULL` que desaparecen, clave foránea) están en la sección 7 del [análisis](../ld-data/references/stored-procedures-review.md).

## Estructura de una app

```
appDemoNN/
  urls.py             # una ruta por operación, name = nombre de la vista
  views.py            # una vista por operación + la vista que renderiza el HTML
  Mantenimiento.html  # o Consulta.html
  Mantenimiento.js    # window.onload + nuevo/editar/eliminar
  models.py           # vacío: los datos viven en procedimientos almacenados
```

Nombres: vistas y rutas en PascalCase sin barra inicial (`ObtenerListas`, `GrabarProducto`, `EliminarProductoPorId`). Las rutas relativas (`fetch("ObtenerListas")`) dependen de que el HTML se sirva desde la misma raíz de la app. Registra la app en `INSTALLED_APPS` y su `urls.py` en el del proyecto.

Los estáticos se cargan con `{% load static %}`: `static 'static/styles/LD.css'`, `static 'static/scripts/General.js'` y `static 'appDemoNN/Mantenimiento.js'`, cada uno con `?v={{Ver}}` para forzar la actualización de caché. La vista que renderiza pasa `{"Ver": "1.0001"}`; súbelo cuando cambies el JS o el CSS.

## Vistas Django (patrón)

Ver [views.py](./examples/views.py) y [urls.py](./examples/urls.py).

- Una función por operación; cada una crea `clienteSQL`, ejecuta un SP y devuelve `HttpResponse(data)`.
- Consulta: `EjecutarComandoCadena("uspXxxListasCsv")` o con un parámetro: `EjecutarComandoCadena("uspXxxObtenerPorId", "ProductID", id)`.
- Escritura: `EjecutarComandoCadena("uspXxxGrabarCsv", "Data", data, trx=True)`. El SP devuelve la lista actualizada y el id, separados por `_`. Revisa `trx=True` con [ld-data](../ld-data/SKILL.md): algunos SP abren su propia transacción.
- La ruta de configuración y del log salen de `settings` (`LD_DB_CONFIG_PATH`, `LD_DB_LOG_PATH`). Los demos originales las escriben a mano con `r"C:\..."` en cada vista; no copies ese hábito en código nuevo ni dejes rutas personales.
- Las operaciones de grabar y eliminar deben ser `POST` con CSRF. Los demos originales eliminan con `GET`; en código nuevo usa `POST` y `@require_POST`.
- El SP nuevo se crea como copia independiente; no modifiques uno existente sin autorización explícita (`ld-data`).

## HTML y CSS (patrón)

Ver [Mantenimiento.html](./examples/Mantenimiento.html).

- Cabecera con `div.Titulo` y `div.Subtitulo`; la grilla se pinta en `<div id="divProducto">`.
- El popup: `PopupContainer` > `PopupWindow` > `BarraTitulo` (con el botón cerrar) + `Cuerpo`.
- Cada campo es una `div.Fila` con `div.Ancho20` (etiqueta) y `div.Ancho80` (control).
- Los controles del formulario llevan clases de comportamiento que `Gui.*` y `Validacion.*` buscan:

| Clase | Efecto |
|---|---|
| `M` | el control entra en `ObtenerValoresControles`, `MostrarValoresControles` y `LimpiarControles` |
| `R` | requerido (`Gui.ValidarControles("R", "L")`) |
| `L` | solo lectura (se omite de la validación de requeridos) |
| `E` | entero en línea (`Validacion.ValidarNumerosEnlinea("E")`) |
| `D` | decimal en línea (`Validacion.ValidarDecimalesEnlinea("D")`) |

- Un único `{% csrf_token %}` al final del `body`; el JS lee `document.getElementsByName("csrfmiddlewaretoken")[0].value`.
- Antes del script de la pantalla, carga `General.js`. Los controles se usan por su `id` global (`txtNombre`, `cboCategoria`), por eso los `id` deben ser únicos.

## JavaScript (patrón)

Ver [Mantenimiento.js](./examples/Mantenimiento.js).

1. `window.onload` es `async`. Configura el popup (`Popup.Resize`, `Popup.ConfigurarArrastre`) y la validación en línea. Luego pide `ObtenerListas`, divide la respuesta y llama a `Gui.Grilla(...)` y `Gui.Combo(...)`.
2. `Gui.Grilla(lista, div, "|", null, null, 20, 10, "¬", "", true)` pinta la grilla mantenible con 20 filas por página y 10 páginas por bloque. La grilla mantenible llama a las funciones globales `nuevoRegistro()`, `editarRegistro(fila, id, btn)`, `eliminarRegistro(id, btn)`, `cambiarPagina(indice)` y `seleccionarFila(idDiv, fila, id)`; debes definirlas aunque estén vacías.
3. Grabar: `Gui.ValidarControles("R", "L")`, luego `Gui.ObtenerValoresControles("M", "|")` y un `URLSearchParams` con `Data` y el token CSRF, enviado con `fetch(..., {method: "POST"})`.
4. Editar: pide el registro por id, lo divide con `split("|")` y llama a `Gui.MostrarValoresControles("M", campos)`.
5. Tras grabar o eliminar, vuelve a pintar la grilla con la lista que devuelve el servidor, sin pedirla otra vez.
6. Revisa siempre `rptaHttp.ok` y el caso `rpta == ""`. Si no es OK, muestra un mensaje; los demos originales lo omiten.

Los datos que llegan al DOM desde `Gui.Grilla` se insertan como HTML. Si un campo puede contener texto escrito por usuarios, escápalo en el servidor o en el SP antes de mostrarlo.

## Procedimiento de trabajo

1. Localiza la pantalla modelo más parecida (consulta simple: appDemo03–09; mantenimiento con popup: appDemo11–13) y cópiala como punto de partida.
2. Inspecciona o define los SP y su forma de retorno antes de escribir la vista (`ld-data`: conjuntos, nulos, `trx`).
3. Crea o adapta `urls.py`, `views.py`, el HTML y el JS en ese orden.
4. Pruébala en el navegador: carga inicial, nuevo, editar, grabar con campos vacíos, grabar válido, eliminar con confirmación y el caso de error del servidor.
5. Verifica CSRF, sesión (si la vista exige login) y que ningún dato lleve `¬`, `|` ni `_`.

## Checklist

- ¿La pantalla repite el patrón de las demás o introduce un estilo distinto?
- ¿Las rutas de configuración y log salen de `settings`, sin rutas personales?
- ¿Grabar y eliminar son `POST` con CSRF y la vista exige sesión cuando corresponde (`ld-security-session`)?
- ¿El JS maneja `rptaHttp.ok` y la respuesta vacía?
- ¿Se actualizó `Ver` al cambiar JS o CSS?
- ¿El SP es nuevo o está autorizado su cambio, y su forma de retorno está verificada?
