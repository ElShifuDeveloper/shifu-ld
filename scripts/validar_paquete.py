#!/usr/bin/env python3
"""Valida el paquete de skills LD. Uso: python scripts/validar_paquete.py [ruta_a_.agents/skills]

Comprueba las reglas de descubrimiento que documenta OpenCode (https://opencode.ai/docs/skills/):
SKILL.md con frontmatter, `name` de 1 a 64 caracteres en minúsculas y guiones que coincide con su
carpeta, y `description` de 1 a 1024 caracteres. Avisa si un SKILL.md supera el presupuesto de palabras. Además verifica enlaces relativos (los de dentro de `.agents/skills` no pueden salir de esa carpeta, para que el paquete sea portable), que no haya
archivos generados, que los .py compilen, que los .js tengan sintaxis válida (si hay `node`) y
ejecuta las pruebas del paquete. Termina con código 1 si algo falla.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILLS = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / ".agents" / "skills"
NOMBRE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PRESUPUESTO_PALABRAS = 1500  # un SKILL.md se carga entero en el contexto cada vez que se activa
errores, avisos = [], []


def frontmatter(texto):
    partes = texto.split("---")
    if not texto.startswith("---") or len(partes) < 3:
        return None
    campos = {}
    for linea in partes[1].splitlines():
        m = re.match(r'^([A-Za-z_]+):\s*(.*)$', linea)
        if m:
            valor = m.group(2).strip()
            if len(valor) >= 2 and valor[0] == valor[-1] == '"':
                valor = valor[1:-1]
            campos[m.group(1)] = valor
    return campos


def validar_skills():
    carpetas = sorted(p for p in SKILLS.iterdir() if p.is_dir())
    if not carpetas:
        errores.append(f"no hay skills en {SKILLS}")
    for carpeta in carpetas:
        archivo = carpeta / "SKILL.md"
        if not archivo.exists():
            errores.append(f"{carpeta.name}: falta SKILL.md")
            continue
        campos = frontmatter(archivo.read_text(encoding="utf-8"))
        if campos is None:
            errores.append(f"{carpeta.name}: frontmatter ausente o mal cerrado")
            continue
        nombre, desc = campos.get("name", ""), campos.get("description", "")
        if not (1 <= len(nombre) <= 64 and NOMBRE.match(nombre)):
            errores.append(f"{carpeta.name}: name inválido ({nombre!r})")
        if nombre != carpeta.name:
            errores.append(f"{carpeta.name}: name ({nombre!r}) debe coincidir con la carpeta")
        if not (1 <= len(desc) <= 1024):
            errores.append(f"{carpeta.name}: description de {len(desc)} caracteres (debe tener 1 a 1024)")
        palabras = len(archivo.read_text(encoding="utf-8").split())
        if palabras > PRESUPUESTO_PALABRAS:
            avisos.append(f"{carpeta.name}: SKILL.md tiene {palabras} palabras (> {PRESUPUESTO_PALABRAS}); mueve el detalle a references/")
    print(f"skills revisados: {len(carpetas)}")


def validar_version():
    version = (RAIZ / "VERSION").read_text(encoding="utf-8").strip() if (RAIZ / "VERSION").exists() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errores.append("falta VERSION o no tiene el formato x.y.z")
        return
    cambios = RAIZ / "CHANGELOG.md"
    if not cambios.exists() or f"## [{version}]" not in cambios.read_text(encoding="utf-8"):
        errores.append(f"CHANGELOG.md no tiene la entrada de la versión {version} (## [{version}] - fecha)")
    print(f"versión del paquete: {version}")


def validar_enlaces():
    total = 0
    for base in (RAIZ, SKILLS):
        for dirpath, _, archivos in os.walk(base):
            for f in archivos:
                if not f.endswith(".md"):
                    continue
                p = Path(dirpath) / f
                for m in re.finditer(r"\]\(([^)\s]+)\)", p.read_text(encoding="utf-8")):
                    destino = m.group(1).split("#")[0]
                    if destino and not destino.startswith(("http", "mailto")):
                        total += 1
                        if not (p.parent / destino).resolve().exists():
                            errores.append(f"enlace roto en {p.relative_to(RAIZ)}: {destino}")
                        elif p.is_relative_to(SKILLS.resolve()) and not (p.parent / destino).resolve().is_relative_to(SKILLS.resolve()):
                            # al instalar solo .agents/skills/ en otro proyecto, este enlace dejaría de existir
                            errores.append(f"enlace fuera de .agents/skills (no portable) en {p.relative_to(RAIZ)}: {destino}")
        if SKILLS.is_relative_to(RAIZ):
            break  # SKILLS ya está dentro de RAIZ: no se recorre dos veces
    print(f"enlaces relativos revisados: {total}")


def validar_archivos():
    for dirpath, dirs, archivos in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in archivos + dirs:
            if f == "__pycache__" or f.endswith(".pyc") or f == ".DS_Store":
                errores.append(f"archivo generado: {Path(dirpath, f).relative_to(RAIZ)}")
        for f in archivos:
            p = Path(dirpath) / f
            if f.endswith(".py"):
                try:
                    compile(p.read_text(encoding="utf-8"), str(p), "exec")  # no escribe .pyc
                except SyntaxError as e:
                    errores.append(f"sintaxis Python en {p.relative_to(RAIZ)}: {e}")
            elif f.endswith(".json"):
                try:
                    json.loads(p.read_text(encoding="utf-8"))
                except ValueError as e:
                    errores.append(f"JSON inválido en {p.relative_to(RAIZ)}: {e}")
            elif f.endswith(".js") and shutil.which("node"):
                texto = p.read_text(encoding="utf-8")
                if re.search(r"^\s*(?:import\b|export\b)", texto, re.MULTILINE):
                    r = subprocess.run(
                        ["node", "--check", "--input-type=module"],
                        input=texto,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                    )
                else:
                    r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
                if r.returncode:
                    errores.append(f"sintaxis JS en {p.relative_to(RAIZ)}: {r.stderr.strip()[:120]}")
    if not shutil.which("node"):
        avisos.append("node no está instalado: no se revisó la sintaxis de los .js ni sus pruebas")


def ejecutar_pruebas():
    n = 0
    for dirpath, _, archivos in os.walk(RAIZ):
        for f in sorted(archivos):
            p = Path(dirpath) / f
            if re.match(r"test_.*\.py$", f):
                cmd = [sys.executable, "-B", f]
            elif re.match(r"test-.*\.js$", f) and shutil.which("node"):
                cmd = ["node", f]
            else:
                continue
            n += 1
            r = subprocess.run(cmd, cwd=dirpath, capture_output=True, text=True)
            if r.returncode:
                errores.append(f"prueba fallida: {p.relative_to(RAIZ)}\n{(r.stdout + r.stderr)[-400:]}")
    print(f"archivos de prueba ejecutados: {n}")


if __name__ == "__main__":
    validar_skills()
    validar_version()
    validar_enlaces()
    validar_archivos()
    ejecutar_pruebas()
    for a in avisos:
        print("AVISO:", a)
    for e in errores:
        print("ERROR:", e)
    print("RESULTADO:", "FALLA" if errores else "OK")
    sys.exit(1 if errores else 0)
