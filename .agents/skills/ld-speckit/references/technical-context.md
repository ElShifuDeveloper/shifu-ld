# Technical Context por defecto de los proyectos LD

Valores que `/speckit.plan` debe usar al llenar el *Technical Context* de `plan.md`, sin que la
persona tenga que escribirlos. Se aplican **por significado de campo**: si una versión de Spec Kit
cambia los nombres o el orden de los campos de su plantilla, mapea cada valor al campo equivalente.
Si un campo no existe en la plantilla, no lo inventes.

| Campo | Valor por defecto LD |
|---|---|
| Lenguaje y versión | Python 3.12 con Django 5.2 en el servidor; JavaScript nativo (ES2017+) en el navegador, sin frameworks de frontend |
| Dependencias principales | Django; `psycopg[binary] >= 3.2` si hay datos en PostgreSQL (por defecto) o `pyodbc` si es SQL Server (según `.ld/config.json`); `websockets` >= 14 solo si hay tiempo real; sin librerías de frontend |
| Almacenamiento | La base elegida en `.ld/config.json` (`bd`): PostgreSQL 14+ (por defecto) mediante funciones almacenadas y `clienteSQL`, o SQL Server mediante procedimientos almacenados y `clienteSQL`, cuando haya datos relacionales. Si la feature solo necesita otro almacén (por ejemplo, archivos en disco), indícalo y justifica en el *Constitution Check* por qué la base relacional no aplica. Rutas y credenciales desde `settings` o el entorno |
| Pruebas | `python manage.py test`; `unittest` para funciones puras; `node` para utilidades JavaScript; pruebas de navegador registradas en `quickstart.md` |
| Plataforma | Navegador moderno de escritorio y móvil; servidor Windows o Linux detrás de un proxy con HTTPS |
| Tipo de proyecto | Aplicación web Django con una app por función (`views.py`, `urls.py`, HTML y JavaScript) |
| Formato de datos | Cadenas delimitadas (`¬`, `\|`, `;`, `_`) que arma el SP y bytes (`application/octet-stream`); respuestas `OK` / `Error - ...`; JSON solo para servicios que consumen terceros |
| Transferencias | «Streaming» = metodología por chunks/bloques (formato: cadena delimitada u octet-stream). Archivos y volúmenes por viajes con progreso, según `ld-transferencia`: bloques `I`/`P` de 100 KB para archivos grandes, lotes de ~100 KB en paquetes de bytes para muchos archivos pequeños, registros por bloques de N; sin una petición por archivo ni JSON |
| Rendimiento | Derívalo de los criterios de éxito de `spec.md`; si no están, `NEEDS CLARIFICATION` |
| Restricciones | Estilo base LD (`ld-crud`); sin cambios a SP existentes sin autorización; endpoints con sesión si la app tiene login y escrituras por `POST` con CSRF; los límites que fija `spec.md` |
| Escala y alcance | Derívalo de `spec.md` (volumen de datos, pantallas). Archivos y tandas **sin límite de tamaño ni de cantidad** salvo que la especificación lo pida; no lo marques `NEEDS CLARIFICATION` |
| Diseño | Lo define `.ld/diseno.json`: `ld` (Soft Glass de `LD.css`, sin librerías) o `externo` con el skill elegido (librerías solo de diseño, locales y con versión fijada). Anótalo en el plan; el funcionamiento sigue sin librerías |
| Skills | Cada tarea indica entre corchetes el skill `ld-*` que aplica; el implementador lo carga antes de editar. Usa solo los skills que la feature necesita |

## Estructura por defecto del código

Una app Django por función; sustituye los nombres por los reales de la feature:

```text
manage.py
<proyecto>/                  # settings y urls (rutas y secretos desde el entorno)
app<Funcion>/
├── urls.py                  # una ruta por operación
├── views.py                 # una vista por operación y la que renderiza la pantalla
├── <Pantalla>.html
├── <Pantalla>.js
└── tests.py
Static/                      # estáticos compartidos
```

## Desviaciones

Cambia un valor solo si la especificación lo exige o la feature no lo necesita, y déjalo
justificado en el *Constitution Check* o en *Complexity Tracking*. Si una desviación se repite en
varios proyectos, propón enmendar la constitución en lugar de justificarla cada vez.
