#!/usr/bin/env python3
"""Inicia y mantiene un proyecto LD: skills, kit base, Spec Kit, AGENTS.md, constitución y opencode.json.

Uso:
    python scripts/iniciar_proyecto.py <proyecto>              # instala lo que falte (no pisa nada)
    python scripts/iniciar_proyecto.py <proyecto> --version    # versión instalada y disponible, diferencias y cambios (solo lectura)
    python scripts/iniciar_proyecto.py <proyecto> --update     # lleva todo a la versión del paquete; lo anterior queda como *-old

`--update` reemplaza TODO archivo que difiera del paquete. La versión anterior no se pierde: queda al lado con el sufijo -old
(General.js -> General-old.js; si ya existe, General-old-2.js, etc.). Cada instalación se registra en <proyecto>/.ld/manifest.json
(versión y huella de cada archivo). Es idempotente. No avanza las etapas de Spec Kit (specify, clarify, plan, tasks, analyze,
implement): esas requieren revisión humana.
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
PREFIJOS_SKILLS = (".agents/skills/",)
PREFIJOS_KIT = ("Modulos/", "Static/")


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
    patron = re.compile(r"-old(-\d+)?(\.[^./]+)?$")
    total = 0
    for base in (proy / ".agents" / "skills", proy / "Modulos", proy / "Static"):
        if base.exists():
            total += sum(1 for f in base.rglob("*") if f.is_file() and patron.search(f.name))
    return total


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
        lineas.append(f"{viejas} versiones anteriores (*-old) en el proyecto; puedes borrarlas cuando ya no las necesites")
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
    ap.add_argument("--sin-speckit", action="store_true", help="no ejecutes `specify init`")
    ap.add_argument("--sin-base", action="store_true", help="no instales el kit base (Modulos/ y Static/)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--con-sql", dest="sql", action="store_true", default=None)
    g.add_argument("--sin-sql", dest="sql", action="store_false")
    ap.add_argument("--diseno", choices=["ld", "externo"], help="estilo visual: «ld» (Soft Glass del paquete, sin librerías) o «externo» (otro skill de diseño); se guarda en .ld/diseno.json")
    ap.add_argument("--skill-diseno", help="nombre del skill de diseño externo (con --diseno externo)")
    ap.add_argument("--git", action="store_true", help="`git init` si el proyecto no es la raíz de su repositorio")
    ap.add_argument("--si", action="store_true", help="no preguntes nada; usa valores por defecto")
    ap.add_argument("--dry-run", action="store_true", help="muestra lo que haría sin escribir")
    a = ap.parse_args(argv)

    proy = Path(a.ruta).expanduser().resolve()
    if a.version:
        if not proy.exists():
            print(f"ERROR: no existe {proy}", file=sys.stderr)
            return 2
        print("\n".join(l if l.startswith(("    ", "  [")) else f"- {l}" for l in informe_version(proy)))
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
    usa_sql = a.sql if a.sql is not None else preguntar_si_no("¿Usará SQL Server con procedimientos almacenados?", True, interactivo)

    manifiesto = leer_manifiesto(proy) or {}
    registro = dict(manifiesto.get("archivos", {}))
    escribe_manifiesto = False

    # 1) skills en la carpeta del proyecto + kit base, archivo por archivo, con manifiesto
    en_proyecto = a.skills == "proyecto"
    incluir_kit = not a.sin_base
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
    if a.diseno or a.skill_diseno or diseno_actual is None:
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

    # manifiesto: versión instalada y huella de cada archivo que LD instaló
    if escribe_manifiesto and not seco:
        manifiesto["version"] = version_paquete()
        manifiesto["archivos"] = registro
        escribir_manifiesto(proy, manifiesto)
        if contar_old(proy) or (proy / "AGENTS-old.md").exists():
            log.append(f"hay versiones anteriores *-old: revísalas y bórralas cuando ya no las necesites; el manifiesto {MANIFIESTO} sí conviene versionarlo")

    print("\n".join(l if l.startswith("    ") else f"- {l}" for l in log))
    if modo == "instalar":
        print("\nSiguiente paso: reinicia OpenCode en el proyecto y ejecuta /speckit.specify <qué debe poder hacer cada usuario>."
              "\nSi dudas de la etapa, pregunta «¿qué sigue?». Para ver si hay una versión nueva del paquete: --version.")
    else:
        print("\nRevisa el diff (git diff), prueba el proyecto y reinicia OpenCode para que cargue los skills nuevos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
