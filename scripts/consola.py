"""Colores de consola para los scripts del paquete LD.

Regla de oro: el color es SOLO para la vista de una persona. Si la salida no es una
terminal (pruebas, tuberías, CI, `redirect_stdout`) o si el entorno lo pide
(`NO_COLOR`, `TERM=dumb`), las funciones devuelven el texto limpio: los informes
y las pruebas siguen comparables carácter a carácter.

Uso desde otro script del paquete:

    try:
        import consola
    except ImportError:          # script copiado fuera del paquete: se sigue sin color
        consola = None

    print(consola.ok("listo") if consola else "listo")

Dos familias, para dos propósitos:

- `ok`/`aviso`/`error`/`titulo`: mensajes para una persona; añaden un símbolo
  (✔ / ⚠ / ✖) que se lee bien aunque no haya color.
- `decorar`/`decorar_lineas`: informes cuyo TEXTO no puede cambiar (pruebas y
  comparaciones carácter a carácter); solo envuelven la línea en color.
"""
import os
import sys

RESET = "\033[0m"
NEGRITA = "\033[1m"
TENUE = "\033[2m"
ROJO = "\033[31m"
VERDE = "\033[32m"
AMARILLO = "\033[33m"
AZUL = "\033[34m"
MAGENTA = "\033[35m"
CIAN = "\033[36m"

_ESTADOS = {
    "ok": VERDE, "listo": VERDE, "exito": VERDE, "al día": VERDE, "al dia": VERDE,
    "aviso": AMARILLO, "pendiente": AMARILLO, "en curso": AMARILLO,
    "error": ROJO, "falla": ROJO, "fallo": ROJO,
    "nuevo": CIAN, "info": CIAN,
}


def soporta_color(flujo=None):
    """True solo si `flujo` (stdout por defecto) es una terminal y el entorno no pide texto plano."""
    flujo = sys.stdout if flujo is None else flujo
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM", "") == "dumb":
        return False
    try:
        return bool(flujo.isatty())
    except (AttributeError, ValueError):
        return False


def pintar(texto, color, flujo=None):
    """`texto` con `color` si la salida lo admite; si no, el texto tal cual."""
    texto = str(texto)
    if not color or not soporta_color(flujo):
        return texto
    return f"{color}{texto}{RESET}"


def negrita(texto, flujo=None):
    return pintar(texto, NEGRITA, flujo)


def tenue(texto, flujo=None):
    return pintar(texto, TENUE, flujo)


def rojo(texto, flujo=None):
    return pintar(texto, ROJO, flujo)


def verde(texto, flujo=None):
    return pintar(texto, VERDE, flujo)


def amarillo(texto, flujo=None):
    return pintar(texto, AMARILLO, flujo)


def cian(texto, flujo=None):
    return pintar(texto, CIAN, flujo)


def magenta(texto, flujo=None):
    return pintar(texto, MAGENTA, flujo)


def titulo(texto, flujo=None):
    """Encabezado de sección: negrita + cian."""
    return pintar(texto, NEGRITA + CIAN, flujo)


def ok(texto, flujo=None):
    """Éxito: verde (✔ incluido para que se lea también sin color)."""
    return pintar(f"✔ {texto}", VERDE, flujo)


def aviso(texto, flujo=None):
    """Algo que conviene mirar: amarillo (⚠ incluido)."""
    return pintar(f"⚠ {texto}", AMARILLO, flujo)


def error(texto, flujo=None):
    """Fallo: rojo (✖ incluido)."""
    return pintar(f"✖ {texto}", ROJO, flujo)


def estado(nombre, texto=None, flujo=None):
    """Colorea `texto` según una palabra de estado (`ok`, `aviso`, `error`, `al día`…)."""
    color = _ESTADOS.get(str(nombre).strip().lower(), "")
    return pintar(texto if texto is not None else nombre, color, flujo)


def decorar(linea, flujo=None):
    """Colorea una línea de informe LD por su contenido, sin cambiar ni un carácter.

    Pensado para los informes de `iniciar_proyecto.py` y `validar_paquete.py`: los
    textos siguen siendo idénticos (las pruebas los comparan), solo se envuelven en
    el color que corresponde cuando hay terminal.
    """
    linea = str(linea)
    despojada = linea.strip()
    if despojada.startswith("ERROR") or despojada.startswith("✖"):
        return rojo(linea, flujo)
    if despojada.startswith("AVISO") or despojada.startswith("⚠"):
        return amarillo(linea, flujo)
    if despojada.startswith(("RESULTADO:", "resultado:")):
        return (verde if ("OK" in linea or "al día" in linea) else amarillo)(linea, flujo)
    if despojada.startswith("##") or despojada.startswith("# "):
        return titulo(linea, flujo)
    if despojada.startswith(("Siguiente paso", "Revisa el diff")):
        return negrita(verde(linea, flujo), flujo)
    if despojada.startswith("versión instalada") or despojada.startswith("version instalada"):
        return negrita(linea, flujo)
    if "al día" in linea or "identico" in linea or "idéntico" in linea or despojada.startswith("✔"):
        return verde(linea, flujo)
    if despojada.startswith("en curso"):
        return amarillo(linea, flujo)
    return linea


def decorar_lineas(lineas, flujo=None):
    return "\n".join(decorar(linea, flujo) for linea in lineas)