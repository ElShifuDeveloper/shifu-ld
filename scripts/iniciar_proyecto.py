#!/usr/bin/env python3
"""Inicia y mantiene un proyecto LD: skills, kit base, Spec Kit, AGENTS.md, constitución y opencode.json.

Uso:
    python scripts/iniciar_proyecto.py <proyecto>              # instala lo que falte (no pisa nada)
    python scripts/iniciar_proyecto.py <proyecto> --version    # versión instalada y disponible, diferencias y cambios (solo lectura)
    python scripts/iniciar_proyecto.py <proyecto> --update     # lleva todo a la versión del paquete; lo anterior queda como *-old
    python scripts/iniciar_proyecto.py <proyecto> --clean      # borra las versiones *-old que quedaron de las actualizaciones

`--update` reemplaza TODO archivo que difiera del paquete. La versión anterior no se pierde: queda al lado con el sufijo -old
(General.js -> General-old.js; si ya existe, General-old-2.js, etc.). Cada instalación se registra en <proyecto>/.ld/manifest.json
(versión y huella de cada archivo). Es idempotente. No avanza las etapas de Spec Kit (specify, clarify, plan, tasks, analyze,
implement): esas requieren revisión humana.
La salida va con color cuando es una terminal (se apaga sola con NO_COLOR o si se redirige).
Detalle y opciones: .agents/skills/ld-speckit/references/instalacion.md
"""
import argparse
import collections
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True   # el paquete se distribuye sin __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import consola                      # colores de consola del paquete (se apagan solos sin terminal)
except ImportError:                     # script copiado fuera del paquete: se sigue sin color
    consola = None

RAIZ = Path(__file__).resolve().parent.parent
SKILLS_ORIGEN = RAIZ / ".agents" / "skills"
REFS = SKILLS_ORIGEN / "ld-speckit" / "references"
MARCA_INI = "<!-- LD:BEGIN -->"
MARCA_FIN = "<!-- LD:END -->"
TITULO_BLOQUE = "## Desarrollo web (skills LD)"
RUTA_CONSTITUCION = ".specify/memory/constitution.md"
RUTA_DISENO = ".ld/diseno.json"   # {"modo": "ld"} o {"modo": "externo", "skill": "<nombre>"}; --update no lo toca
IGNORAR = {"__pycache__", ".DS_Store"}
# Kit base del estilo LD: archivo en el proyecto -> fuente dentro de los skills (cada skill es dueño de los suyos)
KIT = {
    "Modulos/modAccesoDatos.py": "ld-data/examples/base/modAccesoDatos.py",
    "Modulos/modUtilidades.py": "ld-data/examples/base/modUtilidades.py",
    "Modulos/modSeguridadWeb.py": "ld-security-session/examples/modSeguridadWeb.py",
    "Modulos/modGraficos.py": "ld-security-session/examples/modGraficos.py",
    "Modulos/modPaquetes.py": "ld-transferencia/examples/modPaquetes.py",
    "Static/scripts/General.js": "ld-frontend/examples/base/General.js",
    "Static/scripts/Paquetes.js": "ld-transferencia/examples/Paquetes.js",
    "Static/scripts/sha256.js": "ld-security-session/examples/sha256.js",
    "Static/styles/LD.css": "ld-design/examples/LD.css",          # tema moderno (el que usan las pantallas nuevas)
    "Static/styles/DACP.css": "ld-design/examples/DACP.css",      # estilo original, para pantallas de los demos
    "Static/Images/Icons": "ld-design/examples/Images/Icons",     # iconos PNG que usa Gui.Grilla (carpeta completa)
}
OBSOLETOS = {"ld-crud-legacy": "ld-crud"}   # skill retirado -> reemplazo
MANIFIESTO = ".ld/manifest.json"
RUTA_CONFIG = ".ld/config.json"   # {"stack": ..., "stack_detalle": ..., "modo": "sdd|vibe", "sql": bool}; --update no lo toca
STACKS = ("ld", "actual", "definir")   # ld: kit base y estilo LD; actual/definir: solo skills, el agente se adapta
MODOS = ("sdd", "vibe")
RUTA_COMANDO_INICIAR = ".opencode/commands/shifu.iniciar.md"
PLANTILLA_COMANDO_INICIAR = SKILLS_ORIGEN / "ld-speckit" / "examples" / "shifu.iniciar.md"
PREFIJOS_SKILLS = (".agents/skills/",)
PREFIJOS_KIT = ("Modulos/", "Static/")
PATRON_OLD = re.compile(r"-old(-\d+)?(\.[^./]+)?$")   # General-old.js, SKILL-old.md, ld-crud-legacy-old, …
# Ganchos de tiempos del SDD (SPEC Kit lee .specify/extensions.yml antes y después de cada comando)
RUTA_EXTENSIONES = ".specify/extensions.yml"
RUTA_COMANDO_TIEMPOS = ".opencode/commands/ld.tiempo.md"
PLANTILLA_EXTENSIONES = REFS / "extensions.template.yml"
PLANTILLA_COMANDO_TIEMPOS = SKILLS_ORIGEN / "ld-speckit" / "examples" / "ld.tiempo.md"
MARCA_TIEMPOS_INI = "# LD:tiempos:ini"
MARCA_TIEMPOS_FIN = "# LD:tiempos:fin"


# ---------------------------------------------------------------- funciones puras
def archivos_kit():
    """Lista de (ruta_en_proyecto, ruta_fuente) del kit base; las carpetas se expanden archivo por archivo."""
    pares = []
    for destino, fuente in KIT.items():
        origen = SKILLS_ORIGEN / fuente
        if origen.is_dir():
            pares += [(f"{destino}/{p.name}", p) for p in sorted(origen.iterdir()) if p.is_file() and p.name not in IGNORAR]
        else:
            pares.append((destino, origen))
    return pares


def leer_lineas_stack(texto):
    """Devuelve (con_sql, sin_sql): el contenido de los bloques de código de stack-lines.md."""
    bloques = re.findall(r"^## (Con SQL Server|Sin SQL Server)\s*\n\s*```\n(.*?)\n```", texto, re.S | re.M)
    d = {titulo: cuerpo for titulo, cuerpo in bloques}
    if set(d) != {"Con SQL Server", "Sin SQL Server"}:
        raise ValueError("stack-lines.md no tiene los dos bloques esperados")
    return d["Con SQL Server"], d["Sin SQL Server"]


def render_constitucion(plantilla, nombre, fecha, linea_stack, origen):
    texto = (plantilla.replace("{{PROJECT_NAME}}", nombre).replace("{{DATE}}", fecha)
             .replace("{{STACK_LINE}}", linea_stack).replace("{{ORIGEN}}", origen))
    sobrantes = re.findall(r"\{\{[A-Z_]+\}\}", texto)
    if sobrantes:
        raise ValueError(f"marcadores sin reemplazar en la plantilla: {sobrantes}")
    return texto


def es_constitucion_vacia(texto):
    """La plantilla sin rellenar de Spec Kit conserva sus marcadores en el cuerpo.

    Se ignoran los comentarios HTML: el reporte de impacto de una constitución ya rellenada cita
    "[PRINCIPLE_1_NAME] → ..." y no debe confundirse con una plantilla vacía (sobrescribirla
    destruiría el trabajo de la persona).
    """
    cuerpo = re.sub(r"<!--.*?-->", "", texto, flags=re.S)
    return "[PROJECT_NAME]" in cuerpo or "[PRINCIPLE_1_NAME]" in cuerpo


def es_constitucion_ld(texto):
    return "VIII. Skills LD" in texto


def bloque_agents(texto_bloque):
    return f"{MARCA_INI}\n{texto_bloque.strip()}\n{MARCA_FIN}\n"


def fusionar_agents(existente, bloque):
    """Inserta o actualiza el bloque LD sin tocar el resto. Devuelve (texto, hubo_bloque_antiguo)."""
    nuevo = bloque_agents(bloque)
    if MARCA_INI in existente and MARCA_FIN in existente:
        i, j = existente.index(MARCA_INI), existente.index(MARCA_FIN) + len(MARCA_FIN)
        return existente[:i] + nuevo.rstrip("\n") + existente[j:], False
    if TITULO_BLOQUE in existente:  # bloque pegado a mano en una versión anterior, sin marcas
        i = existente.index(TITULO_BLOQUE)
        m = re.search(r"^## (?!Desarrollo web)", existente[i + len(TITULO_BLOQUE):], re.M)
        j = i + len(TITULO_BLOQUE) + m.start() if m else len(existente)
        return existente[:i] + nuevo + ("\n" + existente[j:] if j < len(existente) else ""), True
    base = existente.rstrip("\n")
    return (base + "\n\n" if base else "") + nuevo, False


def fusionar_opencode_json(existente, ruta_instruccion=RUTA_CONSTITUCION):
    datos = json.loads(existente) if existente.strip() else {}
    if not isinstance(datos, dict):
        raise ValueError("opencode.json no es un objeto JSON")
    instr = datos.get("instructions", [])
    if isinstance(instr, str):
        instr = [instr]
    if ruta_instruccion not in instr:
        instr.append(ruta_instruccion)
    datos["instructions"] = instr
    return json.dumps(datos, indent=2, ensure_ascii=False) + "\n"


def huella_directorio(ruta):
    h = hashlib.sha256()
    for p in sorted(ruta.rglob("*")):
        if p.is_file() and not (set(p.parts) & IGNORAR) and p.suffix != ".pyc":
            h.update(str(p.relative_to(ruta)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def estado_skills(origen, destino):
    """{nombre: 'nuevo' | 'identico' | 'diferente'} para cada skill ld-* del origen."""
    estados = {}
    for carpeta in sorted(p for p in origen.iterdir() if p.is_dir() and p.name.startswith("ld-")):
        d = destino / carpeta.name
        if not d.exists():
            estados[carpeta.name] = "nuevo"
        else:
            estados[carpeta.name] = "identico" if huella_directorio(carpeta) == huella_directorio(d) else "diferente"
    return estados


def copiar_skill(origen, destino, conservar_anterior=False):
    if destino.exists():
        if conservar_anterior:
            anterior = destino.with_name(f"{destino.name}-old")
            n = 2
            while anterior.exists():
                anterior = destino.with_name(f"{destino.name}-old-{n}"); n += 1
            destino.rename(anterior)
            if (anterior / "SKILL.md").exists():
                (anterior / "SKILL.md").rename(anterior / "SKILL-old.md")
        else:
            shutil.rmtree(destino)
    shutil.copytree(origen, destino, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))



# ---------------------------------------------------------------- versión, manifiesto y sincronización
def sha(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def version_paquete():
    f = RAIZ / "VERSION"
    return f.read_text(encoding="utf-8").strip() if f.exists() else "0.0.0"


def tupla_version(v):
    n = [int(x) for x in re.findall(r"\d+", v or "")[:3]]
    return tuple(n + [0] * (3 - len(n)))


def entradas_changelog(texto, desde):
    """[(versión, cuerpo)] de las versiones posteriores a `desde` (todas si es None), la más reciente primero."""
    partes = re.split(r"^## \[(\d+\.\d+\.\d+)\][^\n]*\n", texto, flags=re.M)
    entradas = []
    for i in range(1, len(partes), 2):
        if desde is None or tupla_version(partes[i]) > tupla_version(desde):
            entradas.append((partes[i], partes[i + 1].strip()))
    return entradas


def archivos_paquete(incluir_skills=True, incluir_kit=True):
    """{ruta_en_proyecto: ruta_fuente} de todos los archivos que el paquete instala (skills y kit base)."""
    d = {}
    if incluir_skills:
        for skill in sorted(SKILLS_ORIGEN.iterdir()):
            if skill.is_dir() and skill.name.startswith("ld-"):
                for p in sorted(skill.rglob("*")):
                    rel = p.relative_to(SKILLS_ORIGEN)
                    if p.is_file() and not (set(rel.parts) & IGNORAR) and p.suffix != ".pyc":
                        d[".agents/skills/" + rel.as_posix()] = p
    if incluir_kit:
        d.update(dict(archivos_kit()))
    return d


def leer_manifiesto(proy):
    f = proy / MANIFIESTO
    try:
        datos = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    except ValueError:
        return None
    return datos if isinstance(datos, dict) else None


def escribir_manifiesto(proy, datos):
    f = proy / MANIFIESTO
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(datos, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def clasificar(proy, rel, src, h_reg, h_paq=None):
    """nuevo | al_dia | actualizable | personalizado | modificado | sin_registro (ver instalacion.md)."""
    destino = proy / rel
    if not destino.exists():
        return "nuevo"
    h_paq = h_paq or sha(src)
    h_pro = sha(destino)
    if h_pro == h_paq:
        return "al_dia"
    if h_reg is None:
        return "sin_registro"        # existe, difiere y LD nunca lo registró: no se sabe si es tuyo o de una versión vieja
    if h_pro == h_reg:
        return "actualizable"        # sin cambios tuyos y el paquete trae una versión nueva
    if h_paq == h_reg:
        return "personalizado"       # lo cambiaste tú y el paquete no cambió
    return "modificado"              # lo cambiaste tú Y el paquete trae una versión nueva: conflicto


def en_alcance(rel, incluir_skills, incluir_kit):
    return (incluir_skills and rel.startswith(PREFIJOS_SKILLS)) or (incluir_kit and rel.startswith(PREFIJOS_KIT))


def ruta_old(destino):
    """Ruta libre para la versión anterior de `destino`: nombre-old.ext, nombre-old-2.ext, ..."""
    destino = Path(destino)
    candidata = destino.with_name(f"{destino.stem}-old{destino.suffix}")
    n = 2
    while candidata.exists():
        candidata = destino.with_name(f"{destino.stem}-old-{n}{destino.suffix}")
        n += 1
    return candidata


def apartar_como_old(destino):
    """Mueve el archivo actual a su nombre -old (conserva sus bytes y su fecha)."""
    destino = Path(destino)
    if destino.exists():
        shutil.move(str(destino), str(ruta_old(destino)))


def apartar_como_old_copia(destino):
    """Guarda una copia de `destino` como nombre-old.ext y lo deja en su sitio (para archivos que se fusionan)."""
    destino = Path(destino)
    if destino.exists():
        shutil.copy2(destino, ruta_old(destino))


def copiar_archivo(src, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, destino)


def sincronizar(proy, paquete, registro, modo, seco, alcance):
    """Compara el proyecto con el paquete y, salvo `seco`, aplica según `modo`.

    modo "instalar": copia lo que falta y registra lo que ya está al día; no cambia nada más.
    modo "update":   además REEMPLAZA todo archivo que difiera; la versión anterior queda como nombre-old.ext.
    Devuelve (contadores, detalles, nuevo_registro).
    """
    nuevo = dict(registro)
    cont = collections.Counter()
    det = collections.defaultdict(list)
    for rel, src in paquete.items():
        h_paq = sha(src)
        est = clasificar(proy, rel, src, registro.get(rel), h_paq)
        destino = proy / rel
        if est == "nuevo":
            if not seco:
                copiar_archivo(src, destino)
            nuevo[rel] = h_paq; cont["instalados"] += 1
        elif est == "al_dia":
            nuevo[rel] = h_paq; cont["al_dia"] += 1
        else:
            # difiere del paquete: por una versión nueva (actualizable), por un cambio tuyo o por no tener registro
            cat = {"actualizable": "por_actualizar", "personalizado": "modificados", "modificado": "modificados", "sin_registro": "sin_registro"}[est]
            cont[cat] += 1; det[cat].append(rel)
            if modo == "update":
                if not seco:
                    apartar_como_old(destino)
                    copiar_archivo(src, destino)
                nuevo[rel] = h_paq; cont["reemplazados"] += 1
    # archivos que el paquete ya no trae: se apartan como -old (no se borran)
    for rel in sorted(k for k in registro if k not in paquete and en_alcance(k, *alcance)):
        destino = proy / rel
        if not destino.exists():
            nuevo.pop(rel, None)
        elif modo == "update":
            if not seco:
                apartar_como_old(destino)
            nuevo.pop(rel, None); cont["retirados"] += 1
        else:
            cont["retirables"] += 1; det["retirables"].append(rel)
    return cont, det, nuevo


def resumen_sincronizacion(cont, det, modo, limite=10):
    """Líneas del informe: conteos y, de lo que difiere, los archivos que importan."""
    partes = [f"{n} {t}" for t, n in (("instalados", cont["instalados"]), ("reemplazados", cont["reemplazados"]),
              ("retirados", cont["retirados"]), ("al día", cont["al_dia"])) if n]
    lineas = ["archivos (skills y kit base): " + (", ".join(partes) if partes else "sin cambios")]
    if modo == "update":
        if cont["reemplazados"] or cont["retirados"]:
            lineas.append("la versión anterior de cada archivo reemplazado o retirado quedó como *-old (bórralos cuando ya no los necesites)")
        return lineas
    descripciones = (
        ("por_actualizar", "tienen una versión nueva en el paquete (sin cambios tuyos)"),
        ("modificados", "difieren del paquete: los modificaste tú (su versión quedaría como *-old)"),
        ("sin_registro", "difieren del paquete y LD no los instaló (instalación sin manifiesto)"),
        ("retirables", "ya no están en el paquete (quedarían como *-old)"),
    )
    hay = False
    for clave, texto in descripciones:
        n = len(det.get(clave, []))
        if n:
            hay = True
            lineas.append(f"{n} {texto}")
            lineas += [f"    - {rel}" for rel in det[clave][:limite]]
            if n > limite:
                lineas.append(f"    … y {n - limite} más")
    if hay:
        lineas.append("para llevarlos todos a la versión del paquete: --update")
    return lineas


def contar_old(proy):
    """Cantidad de versiones anteriores (*-old) que hay en las carpetas que gestiona LD."""
    total = 0
    for base in (proy / ".agents" / "skills", proy / "Modulos", proy / "Static"):
        if base.exists():
            total += sum(1 for f in base.rglob("*") if f.is_file() and PATRON_OLD.search(f.name))
    return total


# ---------------------------------------------------------------- limpieza de *-old
def entradas_old(proy):
    """Archivos y carpetas *-old que LD dejó en el proyecto: skills, kit base y raíz (AGENTS-old.md…).

    Devuelve solo las entradas más superficiales: si una carpeta `x-old` está en la lista,
    sus hijos `x-old/inner-old.md` no se repiten (se borran con la carpeta).
    """
    rutas = set()
    for base in (proy / ".agents" / "skills", proy / "Modulos", proy / "Static"):
        if base.exists():
            rutas.update(p for p in base.rglob("*") if PATRON_OLD.search(p.name))
    if proy.exists():
        rutas.update(p for p in proy.iterdir() if PATRON_OLD.search(p.name))
    return sorted(p for p in rutas if not any(q != p and p.is_relative_to(q) for q in rutas))


def limpiar_old(proy, seco=False):
    """Borra las versiones *-old (con `seco`, solo las cuenta). Devuelve (archivos, carpetas, lista)."""
    entradas = entradas_old(proy)
    archivos = [p for p in entradas if p.is_file()]
    carpetas = [p for p in entradas if p.is_dir()]
    if not seco:
        for p in archivos:
            try:
                p.unlink()
            except OSError:
                pass
        for p in carpetas:
            shutil.rmtree(p, ignore_errors=True)
    return len(archivos), len(carpetas), entradas


def pintar_lineas(lineas):
    """Líneas con color por contenido (sin color si no hay terminal)."""
    return "\n".join(consola.decorar(l) if consola else l for l in lineas)


# ------------------------------------------------- ganchos de tiempos (extensions.yml)
def render_tiempos(texto):
    """Reemplaza {{RUTA_PAQUETE}} por la ruta absoluta del paquete (los ganchos llaman a scripts/tiempos.py)."""
    return texto.replace("{{RUTA_PAQUETE}}", str(RAIZ))


def sha_texto(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def bloques_tiempos(plantilla):
    """{fase: [líneas del bloque LD, marcadores incluidos]} extraído de la plantilla renderizada."""
    bloques, fase, buffer = {}, None, None
    for linea in plantilla.splitlines():
        despojada = linea.strip()
        if re.match(r"^\s{2}[A-Za-z_]+:\s*$", linea):
            fase = despojada[:-1]
            continue
        if despojada == MARCA_TIEMPOS_INI:
            buffer = [linea]
            continue
        if despojada == MARCA_TIEMPOS_FIN and buffer is not None:
            buffer.append(linea)
            bloques[fase] = buffer
            buffer = None
            continue
        if buffer is not None:
            buffer.append(linea)
    return bloques


def fusionar_extensiones(existente, plantilla):
    """YAML con los bloques de tiempos al día, conservando todo lo que esté fuera de las marcas LD.

    - Sin archivo (o vacío) → la plantilla tal cual.
    - Con archivo → quita los bloques LD anteriores (por marcas o por «- extension: ld-tiempos») y los
      vuelve a insertar tras su fase; las fases que falten se agregan al final del bloque `hooks:`.
    Es idempotente: volver a fusionar el resultado no cambia nada.
    """
    if not existente.strip():
        return plantilla
    bloques = bloques_tiempos(plantilla)
    limpias, dentro, saltar_indent = [], False, None
    for linea in existente.splitlines():
        despojada = linea.strip()
        indent = len(linea) - len(linea.lstrip())
        if saltar_indent is not None:                      # continuación de una entrada LD sin marcas
            if despojada == "" or indent > saltar_indent:
                continue
            saltar_indent = None
        if despojada == MARCA_TIEMPOS_INI:
            dentro = True
            continue
        if despojada == MARCA_TIEMPOS_FIN:
            dentro = False
            continue
        if dentro:
            continue
        if despojada.startswith("- extension: ld-tiempos"):
            saltar_indent = indent
            continue
        limpias.append(linea)
    faltantes = []
    for fase, bloque in bloques.items():
        patron = re.compile(r"^\s*" + re.escape(fase) + r":\s*$")
        pos = next((i for i, l in enumerate(limpias) if patron.match(l)), None)
        if pos is None:
            faltantes += [f"  {fase}:"] + bloque
        else:
            limpias[pos + 1:pos + 1] = bloque
    if faltantes:
        idx = next((i for i, l in enumerate(limpias) if re.match(r"^hooks:\s*$", l)), None)
        if idx is None:
            limpias += ["", "hooks:"] + faltantes
        else:
            fin = len(limpias)
            for j in range(idx + 1, len(limpias)):
                if limpias[j].strip() and not limpias[j].startswith((" ", "\t")):
                    fin = j
                    break
            limpias[fin:fin] = faltantes
    return "\n".join(limpias).rstrip() + "\n"


def estado_tiempos(proy):
    """Líneas del estado de los ganchos y del comando /ld.tiempo (para --version y para instalar)."""
    lineas = []
    if not (proy / ".specify").exists():
        return ["ganchos de tiempos: omitidos (aún no hay .specify; se instalan al inicializar Spec Kit)"]
    plantilla_ext = render_tiempos(PLANTILLA_EXTENSIONES.read_text(encoding="utf-8"))
    ruta_ext = proy / RUTA_EXTENSIONES
    actual_ext = ruta_ext.read_text(encoding="utf-8") if ruta_ext.exists() else ""
    if not actual_ext:
        lineas.append("ganchos de tiempos: no instalados; --update los instala (cronometran cada etapa en specs/METRICS.md)")
    elif fusionar_extensiones(actual_ext, plantilla_ext) != actual_ext:
        lineas.append("ganchos de tiempos: desactualizados o incompletos; --update los refresca (tus ganchos, fuera de las marcas LD, se conservan)")
    else:
        lineas.append("ganchos de tiempos: al día (9 etapas × before/after)")
    plantilla_cmd = render_tiempos(PLANTILLA_COMANDO_TIEMPOS.read_text(encoding="utf-8"))
    ruta_cmd = proy / RUTA_COMANDO_TIEMPOS
    actual_cmd = ruta_cmd.read_text(encoding="utf-8") if ruta_cmd.exists() else ""
    if not actual_cmd:
        lineas.append("comando /ld.tiempo: no instalado; --update lo instala (Spec Kit puede regenerar .opencode/commands/)")
    elif actual_cmd != plantilla_cmd:
        lineas.append("comando /ld.tiempo: desactualizado; --update lo refresca")
    else:
        lineas.append("comando /ld.tiempo: al día")
    return lineas


def informe_clean(proy, seco):
    """Informe de `--clean`: qué se borró (o se borraría con --dry-run). Devuelve líneas."""
    archivos, carpetas, entradas = limpiar_old(proy, seco)
    if not entradas:
        return ["*(sin versiones -old)* no hay versiones *-old en el proyecto: nada que limpiar"]
    lineas = [f"{'[simulación] ' if seco else ''}{archivos} archivos y {carpetas} carpetas *-old "
              + ("por borrar:" if seco else "borrados:")]
    lineas += ["    - " + str(p.relative_to(proy)) for p in entradas[:10]]
    if len(entradas) > 10:
        lineas.append(f"    … y {len(entradas) - 10} más")
    return lineas


# ---------------------------------------------------------------- diseño visual
def leer_diseno(proy):
    """Devuelve el diseño elegido ({"modo": ...}) o None si no hay archivo o está dañado."""
    ruta = proy / RUTA_DISENO
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) and datos.get("modo") in ("ld", "externo") else None


def validar_diseno(modo, skill):
    """Valida la elección. Devuelve (diseno, error)."""
    if modo == "ld":
        return {"modo": "ld"}, None
    if modo == "externo":
        skill = (skill or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}", skill):
            return None, "con diseño externo indica el skill con --skill-diseno <nombre> (letras, dígitos, . _ : / -)"
        return {"modo": "externo", "skill": skill}, None
    return None, "el diseño debe ser «ld» o «externo»"


def skill_disponible(proy, nombre):
    base = nombre.split(":")[-1].split("/")[-1]
    return any((d / base).is_dir() for d in (proy / ".agents" / "skills", Path.home() / ".agents" / "skills"))


# ---------------------------------------------------------------- stack y modo de desarrollo
def leer_config(proy):
    """Devuelve el stack y el modo elegidos ({"stack": ..., "modo": ...}) o None si no hay o está dañado."""
    ruta = proy / RUTA_CONFIG
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(datos, dict) or datos.get("stack") not in STACKS or datos.get("modo") not in MODOS:
        return None
    return datos


def validar_stack(stack, detalle):
    """Valida la elección de stack. Devuelve (config, error)."""
    if stack not in STACKS:
        return None, "el stack debe ser «ld», «actual» o «definir»"
    detalle = (detalle or "").strip()
    if stack == "definir":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .,+/():_-]{0,79}", detalle):
            return None, "con stack «definir» describe el stack con --stack-detalle <texto>"
        return {"stack": "definir", "stack_detalle": detalle}, None
    if detalle:
        return None, "el detalle del stack solo aplica con --stack definir"
    return {"stack": stack, "stack_detalle": ""}, None


def validar_modo(modo):
    """Valida el modo de desarrollo. Devuelve (config, error)."""
    if modo not in MODOS:
        return None, "el modo debe ser «sdd» o «vibe»"
    return {"modo": modo}, None


# ---------------------------------------------------------------- interacción
def preguntar(texto, defecto, interactivo):
    if not interactivo:
        return defecto
    r = input(f"{texto} [{defecto}]: ").strip()
    return r or defecto


def preguntar_si_no(texto, defecto, interactivo):
    if not interactivo:
        return defecto
    r = input(f"{texto} [{'S/n' if defecto else 's/N'}]: ").strip().lower()
    return defecto if not r else r.startswith(("s", "y"))


def preguntar_opcion(texto, opciones, defecto, interactivo):
    """Menú numerado; acepta el número o la clave. `opciones`: [(clave, etiqueta)]. Devuelve la clave."""
    if not interactivo:
        return defecto
    claves = [c for c, _ in opciones]
    for i, (_, etiqueta) in enumerate(opciones, 1):
        print(f"  {i}) {etiqueta}")
    r = input(f"{texto} [{defecto}]: ").strip().lower()
    if not r:
        return defecto
    if r.isdigit() and 1 <= int(r) <= len(opciones):
        return claves[int(r) - 1]
    return r if r in claves else defecto


# ---------------------------------------------------------------- informe de versión
def informe_version(proy):
    """Líneas del informe de --version (solo lectura): versión, diferencias, cambios del paquete y constitución."""
    man = leer_manifiesto(proy)
    disponible = version_paquete()
    instalada = man.get("version") if man else None
    lineas = [f"versión instalada: {instalada or 'sin manifiesto (instalación anterior al versionado)'} | disponible: {disponible}"]
    registro = (man or {}).get("archivos", {})
    cont, det, _ = sincronizar(proy, archivos_paquete(), registro, "instalar", True, (True, True))
    lineas += resumen_sincronizacion(cont, det, "version")
    viejas = contar_old(proy)
    if viejas:
        lineas.append(f"{viejas} versiones anteriores (*-old) en el proyecto; puedes borrarlas cuando ya no las necesites (--clean las borra)")
    cfg = leer_config(proy)
    if cfg:
        stack_txt = cfg["stack"] if cfg["stack"] != "definir" else f"definir ({cfg.get('stack_detalle')})"
        lineas.append(f"modo de desarrollo: {cfg['modo']} | stack: {stack_txt} | SQL: {'sí' if cfg.get('sql') else 'no'}")
    pendientes = (cont["por_actualizar"] + cont["modificados"] + cont["sin_registro"] + cont["retirables"] + cont["instalados"])
    ch = RAIZ / "CHANGELOG.md"
    if ch.exists():
        entradas = entradas_changelog(ch.read_text(encoding="utf-8"), instalada)
        if instalada is None:
            entradas = entradas[:1]
        if entradas and tupla_version(disponible) > tupla_version(instalada or "0.0.0"):
            lineas.append(f"cambios desde {instalada or 'la instalación sin versión'}:")
            for v, cuerpo in entradas:
                lineas.append(f"  [{v}]")
                lineas += ["    " + l for l in cuerpo.splitlines() if l.strip()]
    ruta_const = proy / RUTA_CONSTITUCION
    if ruta_const.exists() and not es_constitucion_vacia(ruta_const.read_text(encoding="utf-8")):
        plantilla = REFS / "constitution.template.md"
        reg_c = (man or {}).get("constitucion", {})
        if reg_c.get("plantilla_sha256") and plantilla.exists():
            if reg_c["plantilla_sha256"] != sha(plantilla):
                lineas.append("constitución: la plantilla LD cambió desde que se generó la tuya; revisa el CHANGELOG y, si aplica, "
                              "enmiéndala: /speckit.constitution Usa el skill ld-speckit y su plantilla de constitución")
            else:
                lineas.append("constitución: al día con la plantilla LD")
        else:
            lineas.append("constitución: no se puede comparar con la plantilla (no la generó este script); si el CHANGELOG pide "
                          "enmendarla: /speckit.constitution Usa el skill ld-speckit y su plantilla de constitución")
    ruta_agents = proy / "AGENTS.md"
    if (REFS / "agents-block.md").exists():
        bloque = (REFS / "agents-block.md").read_text(encoding="utf-8")
        actual = ruta_agents.read_text(encoding="utf-8") if ruta_agents.exists() else ""
        lineas.append("AGENTS.md: bloque LD " + ("al día" if fusionar_agents(actual, bloque)[0] == actual else "desactualizado (--update lo refresca y deja AGENTS-old.md)"))
    lineas += estado_tiempos(proy)
    lineas.append("resultado: " + ("hay cambios por aplicar: python scripts/iniciar_proyecto.py <proyecto> --update"
                                   if pendientes or not man else "al día"))
    return lineas


# ---------------------------------------------------------------- orquestación
def main(argv=None, ejecutar_comando=subprocess.run):
    ap = argparse.ArgumentParser(description="Inicia y actualiza un proyecto LD (skills, kit base, Spec Kit, AGENTS.md, constitución, opencode.json).")
    ap.add_argument("ruta", nargs="?", default=".", help="carpeta del proyecto (se crea si no existe)")
    ap.add_argument("--nombre", help="nombre del proyecto (por defecto, el de la carpeta)")
    ap.add_argument("--skills", choices=["proyecto", "global", "omitir"], default="proyecto")
    ap.add_argument("--version", action="store_true", help="solo lectura: versión instalada y disponible, diferencias con el paquete y cambios")
    ap.add_argument("--update", action="store_true", help="lleva todo a la versión del paquete; lo anterior queda como *-old")
    ap.add_argument("--clean", "--limpiar", dest="clean", action="store_true",
                    help="borra las versiones *-old del proyecto (skills, kit base y raíz) y termina; con --dry-run solo las lista")
    ap.add_argument("--sin-speckit", action="store_true", help="no ejecutes `specify init`")
    ap.add_argument("--sin-base", action="store_true", help="no instales el kit base (Modulos/ y Static/)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--con-sql", dest="sql", action="store_true", default=None)
    g.add_argument("--sin-sql", dest="sql", action="store_false")
    ap.add_argument("--diseno", choices=["ld", "externo"], help="estilo visual: «ld» (Soft Glass del paquete, sin librerías) o «externo» (otro skill de diseño); se guarda en .ld/diseno.json")
    ap.add_argument("--skill-diseno", help="nombre del skill de diseño externo (con --diseno externo)")
    ap.add_argument("--stack", choices=list(STACKS),
                    help="stack del proyecto: «ld» (Django + JS nativo + General.js + SPs, instala el kit base), «actual» (respetar el stack existente: solo copia los skills) o «definir» (con --stack-detalle); se guarda en .ld/config.json")
    ap.add_argument("--stack-detalle", help="descripción del stack cuando --stack definir")
    ap.add_argument("--modo", choices=list(MODOS),
                    help="modo de desarrollo: «sdd» (Spec Kit, recomendado) o «vibe» (código guiado por chat); se guarda en .ld/config.json")
    ap.add_argument("--git", action="store_true", help="`git init` si el proyecto no es la raíz de su repositorio")
    ap.add_argument("--si", action="store_true", help="no preguntes nada; usa valores por defecto")
    ap.add_argument("--dry-run", action="store_true", help="muestra lo que haría sin escribir")
    a = ap.parse_args(argv)

    proy = Path(a.ruta).expanduser().resolve()
    if a.version:
        if not proy.exists():
            print(f"ERROR: no existe {proy}", file=sys.stderr)
            return 2
        print(pintar_lineas([l if l.startswith(("    ", "  [")) else f"- {l}"
                             for l in informe_version(proy)]))
        return 0

    if a.clean:
        if not proy.exists():
            print(f"ERROR: no existe {proy}", file=sys.stderr)
            return 2
        print(pintar_lineas(informe_clean(proy, seco=a.dry_run)))
        return 0

    interactivo = sys.stdin.isatty() and not a.si
    seco = a.dry_run
    modo = "update" if a.update else "instalar"
    log = []

    def hacer(texto, fn=None):
        log.append(("[simulación] " if seco else "") + texto)
        if fn and not seco:
            fn()

    if not proy.exists():
        hacer(f"crear la carpeta {proy}", lambda: proy.mkdir(parents=True))
    nombre = a.nombre or preguntar("Nombre del proyecto", proy.name, interactivo)

    # 0) stack y modo de desarrollo: se preguntan una sola vez y se recuerdan en .ld/config.json
    config_actual = leer_config(proy)
    stack = a.stack or (config_actual or {}).get("stack")
    stack_detalle = a.stack_detalle or (config_actual or {}).get("stack_detalle", "")
    if stack is None:
        stack = preguntar_opcion("Stack del proyecto", [
            ("ld", "recomendado LD: Django + JS nativo + General.js + SPs"),
            ("actual", "respetar el stack actual (solo copia los skills; no impone kit base ni estilo LD)"),
            ("definir", "definirlo (descríbelo)"),
        ], "ld", interactivo)
    if stack == "definir" and not stack_detalle:
        stack_detalle = preguntar("Describe el stack (p. ej. «FastAPI + React»)", "", interactivo)
    modo_desarrollo = a.modo or (config_actual or {}).get("modo")
    if modo_desarrollo is None:
        modo_desarrollo = preguntar_opcion("Modo de desarrollo", [
            ("sdd", "SDD + Spec Kit (recomendado)"),
            ("vibe", "Vibe coding (código guiado por chat)"),
        ], "sdd", interactivo)
    cfg_stack, error_s = validar_stack(stack, stack_detalle)
    if error_s:
        print(f"ERROR: {error_s}", file=sys.stderr)
        return 2
    cfg_modo, error_m = validar_modo(modo_desarrollo)
    if error_m:
        print(f"ERROR: {error_m}", file=sys.stderr)
        return 2
    stack, stack_detalle, modo_desarrollo = cfg_stack["stack"], cfg_stack["stack_detalle"], cfg_modo["modo"]
    usa_sql = a.sql if a.sql is not None else (stack == "ld")
    nuevo_config = {"stack": stack, "stack_detalle": stack_detalle, "modo": modo_desarrollo, "sql": bool(usa_sql)}
    if not (config_actual and all(config_actual.get(k) == v for k, v in nuevo_config.items())):
        def escribir_config():
            ruta = proy / RUTA_CONFIG
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps(nuevo_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        etiqueta = "estilo LD" if stack == "ld" else (f"stack «{stack_detalle}»" if stack == "definir" else "stack actual")
        hacer(f"guardar {etiqueta} y modo {modo_desarrollo} en {RUTA_CONFIG}", escribir_config)
    if stack != "ld":
        log.append(f"stack {stack}: no se instala el kit base (Modulos/ y Static/); solo se copian los skills y el agente se adapta al proyecto")

    manifiesto = leer_manifiesto(proy) or {}
    registro = dict(manifiesto.get("archivos", {}))
    escribe_manifiesto = False

    # 1) skills en la carpeta del proyecto + kit base, archivo por archivo, con manifiesto
    en_proyecto = a.skills == "proyecto"
    incluir_kit = not a.sin_base and stack == "ld"
    if en_proyecto or incluir_kit:
        skills_dir = proy / ".agents" / "skills"
        if en_proyecto:
            for viejo, reemplazo in OBSOLETOS.items():
                if (skills_dir / viejo).exists():
                    if modo == "instalar":
                        log.append(f"AVISO: {viejo} está obsoleto (lo reemplaza {reemplazo}) y se duplicaría; usa --update para apartarlo como {viejo}-old")
                    else:
                        def retirar(v=viejo):
                            carpeta = skills_dir / v
                            destino = carpeta.with_name(f"{v}-old")
                            n = 2
                            while destino.exists():
                                destino = carpeta.with_name(f"{v}-old-{n}"); n += 1
                            carpeta.rename(destino)
                            # un SKILL.md dentro de una carpeta -old se descubriría como skill: se renombra para que quede inerte
                            if (destino / "SKILL.md").exists():
                                (destino / "SKILL.md").rename(destino / "SKILL-old.md")
                        hacer(f"apartar el skill obsoleto {viejo} (lo reemplaza {reemplazo}); queda como {viejo}-old", retirar)
                        for k in [k for k in registro if k.startswith(f".agents/skills/{viejo}/")]:
                            registro.pop(k)
        paquete = archivos_paquete(en_proyecto, incluir_kit)
        cont, det, registro = sincronizar(proy, paquete, registro, modo, seco, (en_proyecto, incluir_kit))
        for linea in resumen_sincronizacion(cont, det, modo):
            log.append(("[simulación] " if seco and not linea.startswith(("AVISO", "    ")) else "") + linea)
        escribe_manifiesto = True
        otra = proy / ".claude" / "skills"
        if en_proyecto and otra.exists() and any(p.name.startswith("ld-") for p in otra.iterdir()):
            log.append("AVISO: hay skills ld-* también en .claude/skills; OpenCode los leería duplicados. Deja una sola ubicación")
    if a.skills == "global":
        destino_skills = Path.home() / ".agents" / "skills"
        estados = estado_skills(SKILLS_ORIGEN, destino_skills)
        difieren = [n for n, e in estados.items() if e == "diferente"]
        for n, e in estados.items():
            if e == "nuevo" or (e == "diferente" and a.update):
                hacer(f"{'actualizar' if e == 'diferente' else 'instalar'} skill {n} en {destino_skills}"
                      + (f" (el anterior queda como {n}-old)" if e == "diferente" else ""),
                      lambda n=n, e=e: copiar_skill(SKILLS_ORIGEN / n, destino_skills / n, e == "diferente"))
        if difieren and not a.update:
            log.append(f"AVISO: {', '.join(difieren)} difieren del paquete y no se reemplazaron (usa --update)")
        if all(e == "identico" for e in estados.values()):
            log.append(f"skills globales: ya instalados e idénticos en {destino_skills}")

    # git
    if a.git:
        try:
            raiz = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=proy if proy.exists() else proy.parent,
                                  capture_output=True, text=True).stdout.strip()
        except OSError:
            raiz = ""
        if not proy.exists() or Path(raiz or "/nonexistent").resolve() != proy:
            hacer("inicializar un repositorio git propio (git init)", lambda: ejecutar_comando(["git", "init", "-q"], cwd=proy, check=True))
        else:
            log.append("git: el proyecto ya es la raíz de su repositorio")

    # 2) Spec Kit
    if (proy / ".specify").exists():
        log.append("Spec Kit: ya inicializado (.specify existe)")
    elif a.sin_speckit:
        log.append("Spec Kit: omitido por --sin-speckit (sin .specify no se generan constitución ni opencode.json)")
    elif shutil.which("specify") is None:
        log.append("AVISO: `specify` no está instalado; instálalo y repite el comando. Se omiten los pasos que dependen de Spec Kit")
    else:
        cmd = ["specify", "init", "--here", "--force", "--non-interactive", "--integration", "opencode", "--script", "sh"]
        hacer("inicializar Spec Kit: " + " ".join(cmd), lambda: ejecutar_comando(cmd, cwd=proy, check=True))

    # 2b) estilo visual: «ld» (por defecto) o un skill de diseño externo; se pregunta una sola vez y se recuerda en .ld/diseno.json
    diseno_actual = leer_diseno(proy)
    # el estilo LD solo se define con el stack LD (o si se pide explícitamente); con otro stack no se impone
    definir_diseno = stack == "ld" or bool(a.diseno or a.skill_diseno or diseno_actual is not None)
    if not definir_diseno:
        log.append("diseño: no se define (stack distinto de LD); usa --diseno ld|externo si quieres fijarlo")
    if definir_diseno and (a.diseno or a.skill_diseno or diseno_actual is None):
        modo_d = a.diseno or ("externo" if a.skill_diseno else None)
        skill_d = a.skill_diseno
        if modo_d is None:
            if interactivo:
                modo_d = preguntar("Estilo visual: «ld» (Soft Glass, sin librerías) o «externo» (otro skill de diseño, p. ej. con Tailwind)", "ld", True).lower()
                if modo_d == "externo":
                    skill_d = preguntar("Nombre del skill de diseño externo", "", True)
            else:
                modo_d = "ld"
                log.append("diseño: «ld» por defecto (sin terminal interactiva). Para un skill externo: --diseno externo --skill-diseno <nombre>")
        nuevo_diseno, error_d = validar_diseno(modo_d, skill_d)
        if error_d:
            print(f"ERROR: {error_d}", file=sys.stderr)
            return 2
        if nuevo_diseno != diseno_actual:
            def escribir_diseno():
                (proy / RUTA_DISENO).parent.mkdir(parents=True, exist_ok=True)
                (proy / RUTA_DISENO).write_text(json.dumps(nuevo_diseno, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            etiqueta = "diseño LD (Soft Glass)" if nuevo_diseno["modo"] == "ld" else f"diseño externo con el skill «{nuevo_diseno['skill']}»"
            hacer(f"guardar {etiqueta} en {RUTA_DISENO}", escribir_diseno)
            if nuevo_diseno["modo"] == "externo" and not skill_disponible(proy, nuevo_diseno["skill"]):
                log.append(f"AVISO: no encuentro el skill «{nuevo_diseno['skill']}» en .agents/skills ni en ~/.agents/skills; instálalo antes de diseñar pantallas")
            diseno_actual = nuevo_diseno
    if diseno_actual and not a.diseno and not a.skill_diseno:
        log.append("diseño: " + ("LD (Soft Glass)" if diseno_actual["modo"] == "ld" else f"externo ({diseno_actual.get('skill')})") + f" — definido en {RUTA_DISENO}")

    # 3) AGENTS.md
    ruta_agents = proy / "AGENTS.md"
    bloque = (REFS / "agents-block.md").read_text(encoding="utf-8")
    actual = ruta_agents.read_text(encoding="utf-8") if ruta_agents.exists() else ""
    nuevo_agents, era_antiguo = fusionar_agents(actual, bloque)
    if nuevo_agents != actual:
        def escribir_agents():
            if actual and (era_antiguo or modo == "update"):
                apartar_como_old_copia(ruta_agents)
            ruta_agents.write_text(nuevo_agents, encoding="utf-8")
        hacer(("actualizar" if actual else "crear") + " AGENTS.md con el bloque LD" + (" (la versión previa queda como AGENTS-old.md)" if actual and (era_antiguo or modo == "update") else ""), escribir_agents)
    else:
        log.append("AGENTS.md: el bloque LD ya está al día")

    # 4) constitución
    ruta_const = proy / RUTA_CONSTITUCION
    hay_speckit = (proy / ".specify").exists() or (seco and not a.sin_speckit and shutil.which("specify") is not None)
    const_lista = False
    if hay_speckit:
        texto_const = ruta_const.read_text(encoding="utf-8") if ruta_const.exists() else ""
        if texto_const and not es_constitucion_vacia(texto_const):
            const_lista = True
            log.append("constitución: ya existe" + (" (LD)" if es_constitucion_ld(texto_const) else " y no es la de LD") +
                       "; no se toca. Para enmendarla: /speckit.constitution Usa el skill ld-speckit y su plantilla de constitución")
        else:
            con, sin = leer_lineas_stack((REFS / "stack-lines.md").read_text(encoding="utf-8"))
            plantilla = (REFS / "constitution.template.md").read_text(encoding="utf-8")
            nuevo = render_constitucion(plantilla, nombre, datetime.date.today().isoformat(), con if usa_sql else sin, "generada por iniciar_proyecto.py")

            def escribir_const():
                ruta_const.parent.mkdir(parents=True, exist_ok=True)
                ruta_const.write_text(nuevo, encoding="utf-8")
                manifiesto["constitucion"] = {"plantilla_sha256": sha(REFS / "constitution.template.md")}
            hacer(f"generar la constitución de «{nombre}» ({'con' if usa_sql else 'sin'} SQL Server) en {RUTA_CONSTITUCION}", escribir_const)
            const_lista = True

    # 5) opencode.json
    ruta_json = proy / "opencode.json"
    if (proy / "opencode.jsonc").exists() and not ruta_json.exists():
        log.append("AVISO: existe opencode.jsonc; añade a mano \"instructions\": [\"" + RUTA_CONSTITUCION + "\"]")
    elif const_lista:
        actual_json = ruta_json.read_text(encoding="utf-8") if ruta_json.exists() else ""
        try:
            nuevo_json = fusionar_opencode_json(actual_json)
        except ValueError as e:
            log.append(f"AVISO: opencode.json no se pudo fusionar ({e}); revísalo a mano")
        else:
            if nuevo_json != actual_json:
                def escribir_json():
                    if actual_json and modo == "update":
                        apartar_como_old_copia(ruta_json)
                    ruta_json.write_text(nuevo_json, encoding="utf-8")
                hacer(("actualizar" if actual_json else "crear") + " opencode.json con la constitución en instructions"
                      + (" (la versión previa queda como opencode-old.json)" if actual_json and modo == "update" else ""), escribir_json)
            else:
                log.append("opencode.json: ya incluye la constitución")
    else:
        log.append("opencode.json: omitido (aún no hay constitución)")

    # 6) ganchos de tiempos: .specify/extensions.yml (cronometra cada etapa) + comando /ld.tiempo
    if (proy / ".specify").exists():
        plantilla_ext = render_tiempos(PLANTILLA_EXTENSIONES.read_text(encoding="utf-8"))
        ruta_ext = proy / RUTA_EXTENSIONES
        actual_ext = ruta_ext.read_text(encoding="utf-8") if ruta_ext.exists() else ""
        nuevo_ext = fusionar_extensiones(actual_ext, plantilla_ext)
        if nuevo_ext != actual_ext:
            def escribir_ext():
                ruta_ext.parent.mkdir(parents=True, exist_ok=True)
                if actual_ext and modo == "update":
                    apartar_como_old_copia(ruta_ext)
                ruta_ext.write_text(nuevo_ext, encoding="utf-8")
                manifiesto["extensiones"] = {"sha256": sha_texto(nuevo_ext)}
            hacer(("actualizar" if actual_ext else "crear") + f" {RUTA_EXTENSIONES} con los ganchos de tiempos"
                  + (f" (la versión previa queda como extensions-old.yml)" if actual_ext and modo == "update" else ""),
                  escribir_ext)
        else:
            log.append("ganchos de tiempos: al día (9 etapas × before/after)")
        plantilla_cmd = render_tiempos(PLANTILLA_COMANDO_TIEMPOS.read_text(encoding="utf-8"))
        ruta_cmd = proy / RUTA_COMANDO_TIEMPOS
        actual_cmd = ruta_cmd.read_text(encoding="utf-8") if ruta_cmd.exists() else ""
        if plantilla_cmd != actual_cmd:
            def escribir_cmd():
                ruta_cmd.parent.mkdir(parents=True, exist_ok=True)
                if actual_cmd and modo == "update":
                    apartar_como_old_copia(ruta_cmd)
                ruta_cmd.write_text(plantilla_cmd, encoding="utf-8")
                manifiesto["comando_tiempos"] = {"sha256": sha_texto(plantilla_cmd)}
            hacer(("actualizar" if actual_cmd else "crear") + f" {RUTA_COMANDO_TIEMPOS} (comando /ld.tiempo, destino de los ganchos)",
                  escribir_cmd)
        else:
            log.append("comando /ld.tiempo: al día")
    else:
        log.append("ganchos de tiempos: omitidos (aún no hay .specify; se instalan al inicializar Spec Kit)")

    # 7) comando /shifu.iniciar (asistente de instalación dentro de OpenCode)
    if PLANTILLA_COMANDO_INICIAR.exists():
        plantilla_ini = render_tiempos(PLANTILLA_COMANDO_INICIAR.read_text(encoding="utf-8"))
        ruta_ini = proy / RUTA_COMANDO_INICIAR
        actual_ini = ruta_ini.read_text(encoding="utf-8") if ruta_ini.exists() else ""
        if plantilla_ini != actual_ini:
            def escribir_ini():
                ruta_ini.parent.mkdir(parents=True, exist_ok=True)
                if actual_ini and modo == "update":
                    apartar_como_old_copia(ruta_ini)
                ruta_ini.write_text(plantilla_ini, encoding="utf-8")
                manifiesto["comando_iniciar"] = {"sha256": sha_texto(plantilla_ini)}
            hacer(("actualizar" if actual_ini else "crear") + f" {RUTA_COMANDO_INICIAR} (comando /shifu.iniciar)", escribir_ini)
        else:
            log.append("comando /shifu.iniciar: al día")

    # manifiesto: versión instalada y huella de cada archivo que LD instaló
    if escribe_manifiesto and not seco:
        manifiesto["version"] = version_paquete()
        manifiesto["archivos"] = registro
        escribir_manifiesto(proy, manifiesto)
        if contar_old(proy) or (proy / "AGENTS-old.md").exists():
            log.append(f"hay versiones anteriores *-old: revísalas y bórralas cuando ya no las necesites (--clean las borra); el manifiesto {MANIFIESTO} sí conviene versionarlo")

    print(pintar_lineas([l if l.startswith("    ") else f"- {l}" for l in log]))
    if modo != "instalar":
        print(pintar_lineas([
            "\nRevisa el diff (git diff), prueba el proyecto y reinicia OpenCode para que cargue los skills nuevos.",
            "Cuando ya no necesites las versiones *-old: --clean."]))
    elif modo_desarrollo == "vibe":
        print(pintar_lineas([
            "\nModo vibe coding: pide en lenguaje natural; no hace falta /speckit.*. Ejemplos:",
            "  - «Agrega un gráfico de stock por categoría en la pantalla de productos, como en la de categorías.»",
            "  - «Crea una pantalla de consulta de clientes con grilla y paginación, estilo LD.»",
            "  - «Sube imágenes de productos por lotes con barra de progreso.»",
            "Si luego quieres SDD: repite con --modo sdd y sigue con /speckit.specify."]))
    else:
        print(pintar_lineas([
            "\nSiguiente paso: reinicia OpenCode en el proyecto y ejecuta /speckit.specify <qué debe poder hacer cada usuario>.",
            "Si dudas de la etapa, pregunta «¿qué sigue?». Para ver si hay una versión nueva del paquete: --version.",
            "Para registrar los tiempos de cada etapa del SDD: scripts/tiempos.py (ver METRICS.md que se crea en specs/)."]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
