#!/usr/bin/env python3
"""Captura una pantalla HTML en un navegador real (claro, oscuro y móvil) para revisar el diseño.

Uso:
    python scripts/capturar_pantalla.py pagina.html [--salida capturas/pantalla] [--ancho 1200] [--alto 1600]
                                         [--sin-oscuro] [--sin-movil]

Genera <salida>-claro.png, <salida>-oscuro.png y <salida>-movil.png (390 px de ancho). Después, mira las imágenes y
corrige lo que se vea mal (desbordes, contraste, espaciado) antes de dar la pantalla por terminada.

- Necesita Chrome, Chromium, Edge o Brave (o la variable LD_NAVEGADOR con la ruta del ejecutable). No instala nada.
- Funciona con HTML estático (por ejemplo, el catálogo de ld-design). Una página de Django con {% static %} se guarda
  antes ya renderizada (`curl http://127.0.0.1:8000/ruta > pagina.html`) y sus rutas deben resolverse desde su carpeta.
- El modo oscuro se fuerza con <html data-tema="oscuro"> (lo respeta LD.css); el móvil se mide dentro de un iframe de
  390 px, porque Chrome headless impone un ancho mínimo de ventana.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATOS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
NOMBRES_PATH = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome")


def buscar_navegador():
    ruta = os.environ.get("LD_NAVEGADOR")
    if ruta and Path(ruta).exists():
        return ruta
    for c in CANDIDATOS:
        if Path(c).exists():
            return c
    for n in NOMBRES_PATH:
        encontrado = shutil.which(n)
        if encontrado:
            return encontrado
    return None


def html_con_tema(texto, carpeta_base, tema):
    """Inserta <base> (para que se resuelvan las rutas relativas) y el atributo data-tema antes de cualquier script."""
    inyeccion = f'<base href="{Path(carpeta_base).resolve().as_uri()}/"><script>document.documentElement.dataset.tema="{tema}"</script>'
    minuscula = texto.lower()
    i = minuscula.find("<head")
    if i >= 0:
        j = texto.find(">", i) + 1
        return texto[:j] + inyeccion + texto[j:]
    return inyeccion + texto


def html_movil(url_pagina, ancho=390, alto=2400):
    return (f'<!DOCTYPE html><html><body style="margin:0;background:#8a8f98"><iframe src="{url_pagina}" width="{ancho}" '
            f'height="{alto}" style="border:0;display:block;margin:0 auto;background:#fff"></iframe></body></html>')


def capturar(navegador, url, destino, ancho, alto):
    cmd = [navegador, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-color-profile=srgb",
           f"--window-size={ancho},{alto}", "--virtual-time-budget=3000", f"--screenshot={destino}", url]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
    return Path(destino).exists()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pagina", help="archivo HTML a capturar")
    ap.add_argument("--salida", help="prefijo de las imágenes (por defecto, junto a la página)")
    ap.add_argument("--ancho", type=int, default=1200)
    ap.add_argument("--alto", type=int, default=1600)
    ap.add_argument("--sin-oscuro", action="store_true")
    ap.add_argument("--sin-movil", action="store_true")
    a = ap.parse_args(argv)

    pagina = Path(a.pagina).resolve()
    if not pagina.is_file():
        print(f"ERROR: no existe {pagina}", file=sys.stderr)
        return 2
    navegador = buscar_navegador()
    if navegador is None:
        print("ERROR: no se encontró Chrome, Chromium, Edge ni Brave. Define LD_NAVEGADOR con la ruta del ejecutable.", file=sys.stderr)
        return 2
    salida = Path(a.salida) if a.salida else pagina.with_suffix("")
    salida.parent.mkdir(parents=True, exist_ok=True)
    texto = pagina.read_text(encoding="utf-8")
    generadas = []
    with tempfile.TemporaryDirectory() as tmp:
        temas = ["claro"] + ([] if a.sin_oscuro else ["oscuro"])
        paginas_tema = {}
        for tema in temas:
            temporal = Path(tmp) / f"{tema}.html"
            temporal.write_text(html_con_tema(texto, pagina.parent, tema), encoding="utf-8")
            paginas_tema[tema] = temporal
            destino = f"{salida}-{tema}.png"
            if capturar(navegador, temporal.as_uri(), destino, a.ancho, a.alto):
                generadas.append(destino)
        if not a.sin_movil:
            envoltorio = Path(tmp) / "movil.html"
            envoltorio.write_text(html_movil(paginas_tema["claro"].as_uri(), alto=a.alto + 800), encoding="utf-8")
            destino = f"{salida}-movil.png"
            if capturar(navegador, envoltorio.as_uri(), destino, 600, a.alto + 800):
                generadas.append(destino)
    for g in generadas:
        print(g)
    return 0 if generadas else 1


if __name__ == "__main__":
    sys.exit(main())
