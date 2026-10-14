#!/usr/bin/env python3
"""Revisa que una pantalla HTML respete la estructura de ld-design (sin navegador).

Uso:
    python scripts/revisar_diseno.py pantalla.html [otra.html ...] [--modo ld|externo]

Errores (código de salida 1): sin LD.css, sin `main.ld-pagina`, sin `section.ld-tarjeta`, contenido suelto en <body>
(Marco, Fila, div de texto fuera de la estructura), `style="..."` en línea y colores sueltos en <style>.
Avisos: más de un botón primario por tarjeta, `Marco` usado como tarjeta nueva, `Mensaje` con color en línea.
Modo: por defecto lo toma de `.ld/diseno.json` (se busca hacia arriba desde la pantalla); sin ese archivo es `ld`. En modo
`externo` (otro skill de diseño, p. ej. con Tailwind) NO se exige LD.css, ld-pagina ni ld-tarjeta ni se vigila lo suelto en <body>;
se siguen revisando `style="..."` en línea y los colores sueltos en <style>.
Corre este script ANTES de capturar la pantalla; la captura (capturar_pantalla.py) confirma el resultado visual.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

PERMITIDOS_EN_BODY = {"script", "style", "link", "template", "noscript", "main", "header", "nav", "footer", "br"}
CLASES_ENCABEZADO = {"Titulo", "Subtitulo", "ld-encabezado", "ld-shell", "PopupContainer", "ld-ancho-total"}
CLASES_POPUP = {"PopupWindow", "PopupImagen", "PopupContainer"}
COLOR_SUELTO = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")


class Revisor(HTMLParser):
    def __init__(self, modo="ld"):
        super().__init__(convert_charrefs=True)
        self.modo = modo
        self.pila = []           # (etiqueta, clases)
        self.errores = []
        self.avisos = []
        self.usa_ld_css = False
        self.usa_dacp = False
        self.tiene_pagina = False
        self.tarjetas = 0
        self.en_style = False
        self.primarios = []      # contador de botones primarios por tarjeta abierta

    def _clases(self, attrs):
        return set((dict(attrs).get("class") or "").split())

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        clases = self._clases(attrs)
        linea = self.getpos()[0]
        if tag == "link" and "LD.css" in (a.get("href") or ""):
            self.usa_ld_css = True
        if tag == "link" and "DACP.css" in (a.get("href") or ""):
            self.usa_dacp = True
        if tag == "style":
            self.en_style = True
        if "ld-pagina" in clases:
            self.tiene_pagina = True
        if "style" in a and not (clases & CLASES_POPUP):
            self.errores.append(f"línea {linea}: <{tag}> con style=\"...\" en línea; usa clases y tokens de LD.css")
        enbody = any(t == "body" for t, _ in self.pila)
        padre = self.pila[-1] if self.pila else None
        if self.modo == "ld" and enbody and padre and padre[0] == "body" and tag not in PERMITIDOS_EN_BODY and not (clases & CLASES_ENCABEZADO) \
                and not (tag == "input" and a.get("type") == "hidden"):
            self.errores.append(f"línea {linea}: <{tag}{' class=' + ' '.join(sorted(clases)) if clases else ''}> suelto en <body>; "
                                "va dentro de main.ld-pagina > section.ld-tarjeta")
        if "Marco" in clases and any("ld-pagina" in c for _, c in self.pila):
            self.avisos.append(f"línea {linea}: usa section.ld-tarjeta en lugar de Marco para una tarjeta nueva")
        if "ld-tarjeta" in clases:
            self.tarjetas += 1
            self.primarios.append(0)
        if tag in ("input", "button", "a") and "Boton" in clases and not (clases & {"Secundario", "Peligro", "BotonSmall", "BotonGrid"}):
            if self.primarios:
                self.primarios[-1] += 1
        if "Mensaje" in clases and "style" in a:
            self.avisos.append(f"línea {linea}: Mensaje con color en línea; usa ld-alerta (error, ok, aviso) o ld-ayuda")
        if tag not in ("br", "img", "input", "link", "meta", "hr"):
            self.pila.append((tag, clases))

    def handle_endtag(self, tag):
        if tag == "style":
            self.en_style = False
        for i in range(len(self.pila) - 1, -1, -1):
            if self.pila[i][0] == tag:
                if "ld-tarjeta" in self.pila[i][1] and self.primarios:
                    n = self.primarios.pop()
                    if n > 1:
                        self.avisos.append(f"línea {self.getpos()[0]}: la tarjeta tiene {n} botones primarios; deja uno y el resto como Boton Secundario")
                del self.pila[i:]
                break

    def handle_data(self, data):
        if self.en_style and COLOR_SUELTO.search(data):
            self.errores.append(f"línea {self.getpos()[0]}: color suelto en <style>; usa las variables --ld-*")


def modo_del_proyecto(ruta):
    """Lee `.ld/diseno.json` hacia arriba desde la pantalla; sin archivo válido, «ld»."""
    for carpeta in [ruta.resolve().parent, *ruta.resolve().parents]:
        f = carpeta / ".ld" / "diseno.json"
        if f.is_file():
            try:
                return "externo" if json.loads(f.read_text(encoding="utf-8")).get("modo") == "externo" else "ld"
            except (OSError, ValueError):
                return "ld"
    return "ld"


def revisar(texto, modo="ld"):
    r = Revisor(modo)
    r.feed(texto)
    errores = list(r.errores)
    if modo == "externo":
        return errores, r.avisos
    if not r.usa_ld_css:
        errores.insert(0, "no enlaza LD.css" + (" (usa DACP.css: cámbialo)" if r.usa_dacp else ""))
    if not r.tiene_pagina:
        errores.append("falta <main class=\"ld-pagina\"> que contenga las tarjetas")
    if r.tarjetas == 0:
        errores.append("falta al menos una <section class=\"ld-tarjeta\">")
    return errores, r.avisos


def main(argv=None):
    rutas = list(argv if argv is not None else sys.argv[1:])
    modo = None
    if "--modo" in rutas:
        i = rutas.index("--modo")
        modo = rutas[i + 1] if i + 1 < len(rutas) else ""
        del rutas[i:i + 2]
        if modo not in ("ld", "externo"):
            print("ERROR: --modo debe ser ld o externo", file=sys.stderr)
            return 2
    if not rutas:
        print(__doc__)
        return 2
    codigo = 0
    for ruta in rutas:
        p = Path(ruta)
        if not p.is_file():
            print(f"ERROR: no existe {p}", file=sys.stderr)
            return 2
        errores, avisos = revisar(p.read_text(encoding="utf-8"), modo or modo_del_proyecto(p))
        for e in errores:
            print(f"{p}: ERROR {e}")
        for a in avisos:
            print(f"{p}: aviso {a}")
        if errores:
            codigo = 1
        else:
            print(f"{p}: estructura correcta" + (f" ({len(avisos)} avisos)" if avisos else ""))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
