# Líneas de stack para la constitución

El script `iniciar_proyecto.py` elige una de estas dos para el marcador `{{STACK_LINE}}` de
[constitution.template.md](./constitution.template.md). Si el proyecto cambia de caso, enmienda la
constitución con `/speckit.constitution` (MINOR).

## Con SQL Server

```
- Stack: Python 3.12 con Django 5.2, pyodbc y SQL Server mediante procedimientos
  almacenados; JavaScript nativo (ES2017+); `websockets` solo si hay tiempo real.
```

## Sin SQL Server

```
- Stack: Python 3.12 con Django 5.2 y JavaScript nativo (ES2017+); sin base de datos
  relacional (los datos viven en el sistema de archivos u otro almacén que la
  especificación indique); `websockets` solo si hay tiempo real. Si más adelante hay
  datos relacionales, se enmienda esta constitución para incorporar SQL Server con
  procedimientos almacenados.
```
