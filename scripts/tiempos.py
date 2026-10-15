#!/usr/bin/env python3
"""Registra los tiempos de cada etapa del SDD y los rinde en `specs/METRICS.md`.

El archivo de tiempos es la memoria del proyecto: cuánto tardó cada etapa, en minutos,
por cada especificación, con el desglose de la implementación (desarrollo, QA, seguridad,
diseño, integración y otros). El estado vive en `<proyecto>/.ld/tiempos.json` y
`specs/METRICS.md` se RENDERIZA desde ahí: no se edita a mano (se sobrescribe).

Uso (desde el proyecto; `<paquete>` es la carpeta Skill_LD):

    python <paquete>/scripts/tiempos.py <proyecto> inicio <etapa> [--nota "…"]
    python <paquete>/scripts/tiempos.py <proyecto> fin <etapa> [--nota "…"]
    python <paquete>/scripts/tiempos.py <proyecto> informe [--spec <spec>]
    python <paquete>/scripts/tiempos.py etapas

Etapas: constitucion, especificar, clarificar, plan, tareas, analizar, implementar, converger.
Desglose de implementar: implementar:desarrollo, implementar:qa, implementar:seguridad,
implementar:diseño, implementar:integracion, implementar:otros.
Se aceptan los nombres de los comandos en inglés (`specify`, `tasks`, `implement:qa`…).

Sin `--spec`, la especificación activa se toma de `.specify/feature.json`.
`--ahora <ISO>` fija la hora (para pruebas o para anotar algo hecho antes).
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True   # el paquete se distribuye sin __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import consola
except ImportError:          # copiado fuera del paquete: se sigue sin color
    consola = None

ESTADO = ".ld/tiempos.json"
METRICS = "specs/METRICS.md"
FEATURE = ".specify/feature.json"

ETAPAS = [
    ("constitucion", "Constitución"),
    ("especificar", "Especificar"),
    ("clarificar", "Clarificar"),
    ("plan", "Plan"),
    ("tareas", "Tareas"),
    ("checklist", "Checklist"),
    ("analizar", "Analizar"),
    ("implementar", "Implementar"),
    ("converger", "Converger"),
]
SUBETAPAS = [
    ("implementar:desarrollo", "Desarrollo"),
    ("implementar:qa", "QA / pruebas"),
    ("implementar:seguridad", "Seguridad"),
    ("implementar:diseño", "Diseño"),
    ("implementar:integracion", "Integración"),
    ("implementar:otros", "Otros"),
]
ETIQUETAS = dict(ETAPAS + SUBETAPAS)


def _alias():
    """Nombres aceptados → clave canónica (incluye los comandos en inglés y variantes sin tilde)."""
    a = {}
    for clave, _ in ETAPAS + SUBETAPAS:
        a[clave] = clave
        a[clave.replace("implementar:", "implement:")] = clave
        a[clave.replace("diseño", "diseno")] = clave
        a[clave.replace("integracion", "integración").replace("implementar:", "implement:")] = clave
    extra = {
        "constitution": "constitucion", "constitución": "constitucion",
        "specify": "especificar", "especificacion": "especificar", "especificación": "especificar",
        "spec": "especificar", "clarify": "clarificar", "planificar": "plan",
        "planificacion": "plan", "planificación": "plan", "tasks": "tareas",
        "analyze": "analizar", "analisis": "analizar", "análisis": "analizar",
        "implement": "implementar", "implementacion": "implementar", "implementación": "implementar",
        "converge": "converger", "convergencia": "converger",
        "implement:development": "implementar:desarrollo", "implement:dev": "implementar:desarrollo",
        "implement:qa": "implementar:qa", "implement:calidad": "implementar:qa",
        "implementar:pruebas": "implementar:qa", "implement:seguridad": "implementar:seguridad",
        "implement:security": "implementar:seguridad", "implement:diseno": "implementar:diseño",
        "implement:design": "implementar:diseño", "implement:integration": "implementar:integracion",
        "implement:integracion": "implementar:integracion", "implement:otros": "implementar:otros",
        "implement:other": "implementar:otros",
    }
    a.update(extra)
    return a


ALIAS = _alias()


# ----------------------------------------------------------------- funciones puras
def normalizar(nombre):
    """Clave canónica de una etapa, o None si no se reconoce."""
    if not nombre:
        return None
    limpio = str(nombre).strip().lower().replace(" ", "")
    return ALIAS.get(limpio)


def ahora(iso=None):
    """Momento de la marca: el real o el que se pasa para pruebas/reconstrucciones."""
    if iso:
        try:
            return datetime.datetime.fromisoformat(iso.replace(" ", "T"))
        except ValueError:
            raise ValueError(f"--ahora no es una fecha ISO válida: {iso}")
    return datetime.datetime.now().replace(microsecond=0)


def minutos(inicio, fin):
    """Minutos entre dos ISO (0 si falta alguno); redondeado a 1 decimal."""
    if not inicio or not fin:
        return None
    a = datetime.datetime.fromisoformat(inicio)
    b = datetime.datetime.fromisoformat(fin)
    return round((b - a).total_seconds() / 60, 1)


def formato_min(valor):
    if valor is None:
        return "—"
    return str(int(valor)) if float(valor).is_integer() else f"{valor:.1f}"


def formato_hora(iso):
    if not iso:
        return "—"
    return iso.replace("T", " ")[:16]


def cargar(proy):
    f = proy / ESTADO
    try:
        datos = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    except ValueError:
        return {"specs": {}}
    return datos if isinstance(datos, dict) and isinstance(datos.get("specs"), dict) else {"specs": {}}


def guardar(proy, datos):
    f = proy / ESTADO
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(datos, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def marcar(datos, spec, etapa, cuando, cerrar=False, nota=None, reiniciar=False):
    """Aplica una marca sobre los datos. Devuelve (datos, error).

    `inicio` abre la etapa (o la reinicia con `reiniciar`); `fin` la cierra y deja la nota.
    """
    reg = datos["specs"].setdefault(spec, {"etapas": {}}).setdefault("etapas", {})
    actual = reg.get(etapa) or {}
    iso = cuando.isoformat(timespec="seconds")
    if cerrar:
        if not actual.get("inicio"):
            return datos, f"«{etapa}» no tiene inicio marcado en {spec}: márcalo antes con inicio"
        if actual.get("fin") and not reiniciar:
            return datos, f"«{etapa}» ya estaba cerrada en {spec} ({formato_hora(actual['fin'])}); usa --reiniciar para volver a cerrarla"
        if iso < actual["inicio"]:
            return datos, (f"«{etapa}» no puede cerrarse antes de su inicio ({formato_hora(actual['inicio'])}): "
                           f"revisa la hora o usa --reiniciar para empezar un ciclo nuevo")
        actual["fin"] = iso
        if nota:
            actual["nota"] = nota
        minutos(actual["inicio"], actual["fin"])          # valida el par
    else:
        if actual.get("inicio") and not reiniciar:
            extra = " (en curso)" if not actual.get("fin") else ""
            return datos, (f"«{etapa}» ya tenía inicio {formato_hora(actual['inicio'])}{extra} en {spec}; "
                           f"usa --reiniciar si quieres volver a empezar")
        actual = {"inicio": iso}
        if nota:
            actual["nota"] = nota
    reg[etapa] = actual
    return datos, None


def resolver_spec(proy, dado=None):
    """Ruta relativa de la especificación activa. Devuelve (spec, error)."""
    esps = esps_del_proyecto(proy)

    def _buscar(texto):
        t = str(texto).strip().strip("/").replace("\\", "/")
        if (proy / t).is_dir() and t.startswith("specs/"):
            return t
        if re.fullmatch(r"\d{1,4}", t):
            for e in esps:
                if e.split("/")[-1].startswith(f"{int(t):03d}-"):
                    return e
        for e in esps:
            if e.split("/")[-1] == t or e == f"specs/{t}":
                return e
        return None

    if dado:
        encontrada = _buscar(dado)
        if not encontrada:
            return None, f"no encuentro la especificación «{dado}»; candidatas: {', '.join(esps) or 'ninguna'}"
        return encontrada, None
    f = proy / FEATURE
    try:
        activa = json.loads(f.read_text(encoding="utf-8")).get("feature_directory") if f.exists() else None
    except ValueError:
        activa = None
    if activa:
        encontrada = _buscar(activa)
        if encontrada:
            return encontrada, None
    if len(esps) == 1:
        return esps[0], None
    if not esps:
        return None, ("no hay especificaciones en specs/: crea la primera con /speckit.specify "
                      "o indica --spec")
    return None, ("hay varias especificaciones y ninguna activa en .specify/feature.json; "
                  f"indica --spec: {', '.join(esps)}")


def esps_del_proyecto(proy):
    """Carpetas `specs/NNN-*` del proyecto, ordenadas."""
    base = proy / "specs"
    if not base.is_dir():
        return []
    return sorted(f"specs/{p.name}" for p in base.iterdir() if p.is_dir())


def total_etapas(etapas, ahora_dt=None):
    """Minutos sumados de las etapas de nivel superior (las sub-etapas no cuentan dos veces)."""
    total = 0.0
    for clave, _ in ETAPAS:
        reg = etapas.get(clave) or {}
        m = minutos(reg.get("inicio"), reg.get("fin"))
        if m is None and reg.get("inicio") and ahora_dt:
            m = round((ahora_dt - datetime.datetime.fromisoformat(reg["inicio"])).total_seconds() / 60, 1)
        if m:
            total += m
    return round(total, 1)


def total_subetapas(etapas, ahora_dt=None):
    total = 0.0
    for clave, _ in SUBETAPAS:
        reg = etapas.get(clave) or {}
        m = minutos(reg.get("inicio"), reg.get("fin"))
        if m is None and reg.get("inicio") and ahora_dt:
            m = round((ahora_dt - datetime.datetime.fromisoformat(reg["inicio"])).total_seconds() / 60, 1)
        if m:
            total += m
    return round(total, 1)


def _celda(reg, ahora_dt=None):
    """(inicio, fin, minutos) formateados de una marca; «en curso» si falta el fin."""
    reg = reg or {}
    inicio, fin = reg.get("inicio"), reg.get("fin")
    m = minutos(inicio, fin)
    if m is None and inicio and ahora_dt:
        m = round((ahora_dt - datetime.datetime.fromisoformat(inicio)).total_seconds() / 60, 1)
        return formato_hora(inicio), "en curso", formato_min(m)
    return formato_hora(inicio), formato_hora(fin), formato_min(m)


def _nota(reg):
    texto = (reg or {}).get("nota") or "—"
    return texto.replace("|", "/").replace("\n", " ")


def render(datos, esps, ahora_dt):
    """Texto completo de specs/METRICS.md a partir del estado."""
    lineas = [
        "# METRICS — tiempos por etapa del SDD",
        "",
        "Cuánto tardó cada etapa, en minutos, por especificación. Lo genera el script "
        "`scripts/tiempos.py` del paquete LD a partir de `.ld/tiempos.json`: **no se edita a mano** "
        "(cada marca lo reescribe).",
        "",
        "Marca el inicio y el fin de cada etapa mientras avanzas: "
        "`python <paquete>/scripts/tiempos.py . inicio <etapa>` y `... fin <etapa>`.",
        "",
        "- **Etapas:** " + ", ".join(clave for clave, _ in ETAPAS) + ".",
        "- **Desglose de `implementar`:** " + ", ".join(clave.split(":")[1] for clave, _ in SUBETAPAS) + ".",
        "",
        "Actualizado: " + ahora_dt.strftime("%Y-%m-%d %H:%M"),
        "",
    ]
    # Resumen: una fila por especificación
    lineas.append("## Resumen (minutos por etapa)")
    lineas.append("")
    cabecera = ["Especificación"] + [etq for _, etq in ETAPAS] + ["Total"]
    lineas.append("| " + " | ".join(cabecera) + " |")
    lineas.append("|" + "---|" * len(cabecera))
    for spec in esps:
        etapas = (datos["specs"].get(spec) or {}).get("etapas", {})
        celdas = []
        for clave, _ in ETAPAS:
            reg = etapas.get(clave) or {}
            m = minutos(reg.get("inicio"), reg.get("fin"))
            if m is None and reg.get("inicio"):
                celdas.append("en curso")
            else:
                celdas.append(formato_min(m))
        total = total_etapas(etapas, ahora_dt)
        lineas.append("| " + " | ".join([spec.split("/")[-1]] + celdas + [formato_min(total)]) + " |")
    if not esps:
        lineas.append("| (sin especificaciones todavía) |" + " — |" * (len(cabecera) - 1))
    lineas.append("")
    # Detalle por especificación
    for spec in esps:
        etapas = (datos["specs"].get(spec) or {}).get("etapas", {})
        lineas.append(f"## {spec}")
        lineas.append("")
        lineas.append("| Etapa | Inicio | Fin | Minutos | Notas |")
        lineas.append("|---|---|---|---|---|")
        for clave, etiqueta in ETAPAS:
            reg = etapas.get(clave) or {}
            inicio, fin, mins = _celda(reg, ahora_dt)
            lineas.append(f"| {etiqueta} | {inicio} | {fin} | {mins} | {_nota(reg)} |")
        total = total_etapas(etapas, ahora_dt)
        lineas.append(f"| **Total etapas** | | | **{formato_min(total)}** | |")
        lineas.append("")
        lineas.append("**Desglose de la implementación**")
        lineas.append("")
        lineas.append("| Sub-etapa | Inicio | Fin | Minutos | Notas |")
        lineas.append("|---|---|---|---|---|")
        for clave, etiqueta in SUBETAPAS:
            reg = etapas.get(clave) or {}
            inicio, fin, mins = _celda(reg, ahora_dt)
            lineas.append(f"| {etiqueta} | {inicio} | {fin} | {mins} | {_nota(reg)} |")
        subtotal = total_subetapas(etapas, ahora_dt)
        lineas.append(f"| **Total desglose** | | | **{formato_min(subtotal)}** | |")
        lineas.append("")
    return "\n".join(lineas).rstrip() + "\n"


def escribir_metrics(proy, datos, esps, ahora_dt):
    ruta = proy / METRICS
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(render(datos, esps, ahora_dt), encoding="utf-8")
    return ruta


def resumen_consola(datos, esps, ahora_dt):
    """Líneas coloreadas con la tabla de minutos (misma información que METRICS.md)."""
    color = (lambda f, t: f(t)) if consola is None else (
        lambda f, t: {"ok": consola.ok, "aviso": consola.aviso, "error": consola.error,
                      "titulo": consola.titulo, "tenue": consola.tenue,
                      "dato": consola.cian}[f](t))
    cabecera = ["Especificación"] + [etq for _, etq in ETAPAS] + ["Total"]
    filas = []
    for spec in esps:
        etapas = (datos["specs"].get(spec) or {}).get("etapas", {})
        celdas = []
        for clave, _ in ETAPAS:
            reg = etapas.get(clave) or {}
            m = minutos(reg.get("inicio"), reg.get("fin"))
            celdas.append("…" if (m is None and reg.get("inicio")) else formato_min(m))
        filas.append([spec.split("/")[-1]] + celdas + [formato_min(total_etapas(etapas, ahora_dt))])
    anchos = [max(len(str(f[i])) for f in [cabecera] + filas) for i in range(len(cabecera))]
    lineas = [color("titulo", "Minutos por etapa (specs/METRICS.md)")]
    lineas.append("  " + "  ".join(str(c).ljust(anchos[i]) for i, c in enumerate(cabecera)))
    for f in filas:
        lineas.append("  " + "  ".join(str(c).ljust(anchos[i]) for i, c in enumerate(f)))
    return lineas


# ----------------------------------------------------------------- estimación
# Artefacto que deja cada etapa (para `estimar` cuando no se marcó a tiempo). Las etapas que no
# dejan archivo propio (clarificar, analizar, converger) no se estiman: quedarían inventadas.
ARTEFACTOS = {
    "constitucion": ".specify/memory/constitution.md",
    "especificar": "spec.md",
    "plan": "plan.md",
    "tareas": "tasks.md",
    "checklist": "checklists/requirements.md",
    "implementar": "*",        # el archivo más reciente de la carpeta de la especificación
}


def etapas_abiertas(datos, esps):
    """[(spec, clave, inicio_iso)] de etapas con inicio y sin fin: la red de seguridad."""
    abiertas = []
    for spec in esps:
        etapas = (datos["specs"].get(spec) or {}).get("etapas", {})
        for clave, _ in ETAPAS + SUBETAPAS:
            reg = etapas.get(clave) or {}
            if reg.get("inicio") and not reg.get("fin"):
                abiertas.append((spec, clave, reg["inicio"]))
    return abiertas


def _mtime(proy, ruta):
    p = proy / ruta
    if not p.is_file():
        return None
    return datetime.datetime.fromtimestamp(p.stat().st_mtime).replace(microsecond=0)


def _mas_reciente(proy, spec):
    """Momento del archivo más reciente de la especificación (el registro de quickstart suele ser el último)."""
    base = proy / spec
    if not base.is_dir():
        return None
    fechas = [datetime.datetime.fromtimestamp(p.stat().st_mtime).replace(microsecond=0)
              for p in base.rglob("*") if p.is_file()]
    return max(fechas) if fechas else None


def _iso(valor):
    """ISO de un datetime, o el propio ISO ya guardado; None si no hay valor."""
    if valor is None:
        return None
    return valor.isoformat(timespec="seconds") if hasattr(valor, "isoformat") else str(valor)[:19]


def _fin_estimado(proy, spec, clave, referencia=None):
    """Fecha del artefacto que deja la etapa, o None si la etapa no deja archivo propio.

    Para `implementar` no basta con que exista la carpeta: el archivo más reciente debe ser
    POSTERIOR a las etapas previas; si no, es que la implementación todavía no ocurrió.
    """
    rel = ARTEFACTOS.get(clave)
    if not rel:
        return None
    if rel == "*":
        ultimo = _mas_reciente(proy, spec)
        if ultimo is None or referencia is None or not ultimo > _fecha(referencia):
            return None
        return ultimo
    if rel.startswith(".specify/"):
        return _mtime(proy, rel)
    return _mtime(proy, f"{spec}/{rel}")


def _fecha(valor):
    """datetime de un ISO string o de un datetime (para comparar marcas con fechas de archivo)."""
    if isinstance(valor, datetime.datetime):
        return valor
    return datetime.datetime.fromisoformat(str(valor))


def estimar(datos, proy, esps):
    """Rellena las etapas SIN marca con el fin deducido de sus artefactos.

    El inicio de cada etapa estimada es el fin de la etapa anterior (así los minutos son el
    hueco entre archivos, no el trabajo real). Nunca toca una fila que tenga alguna marca.
    Devuelve (datos, cambios) con cambios = [(spec, clave, inicio|None, fin)].
    """
    cambios = []
    for spec in esps:
        etapas = datos["specs"].setdefault(spec, {"etapas": {}}).setdefault("etapas", {})
        previo = None
        for clave, _ in ETAPAS:
            reg = etapas.get(clave) or {}
            if reg.get("inicio") or reg.get("fin"):
                previo = reg.get("fin") or reg.get("inicio") or previo
                continue
            fin = _fin_estimado(proy, spec, clave, referencia=previo)
            if fin is None:
                continue
            fila = {"fin": fin.isoformat(timespec="seconds")}
            # el inicio solo si la etapa previa es ANTERIOR a este artefacto: en desorden, se omite
            if previo and _fecha(previo) < fin:
                fila["inicio"] = _iso(previo)
                fila["nota"] = "estimado por fechas de archivo"
            else:
                fila["nota"] = ("estimado por fechas de archivo (sin inicio conocido: "
                                "la marca anterior es posterior)" if previo else
                                "estimado por fechas de archivo (sin inicio conocido)")
            etapas[clave] = fila
            cambios.append((spec, clave, fila.get("inicio"), fin))
            previo = fin
    return datos, cambios


# ------------------------------------------------------------------------- CLI
def _transcurrido(iso, ahora_dt):
    """Minutos desde `iso` hasta `ahora_dt` (para etapas en curso)."""
    if not iso:
        return None
    return round((ahora_dt - datetime.datetime.fromisoformat(iso)).total_seconds() / 60, 1)


def _etapas_texto():
    lineas = ["Etapas de nivel superior:"]
    lineas += [f"  {clave:<26} {etq}" for clave, etq in ETAPAS]
    lineas.append("Desglose de implementar:")
    lineas += [f"  {clave:<26} {etq}" for clave, etq in SUBETAPAS]
    lineas.append("También se aceptan los comandos en inglés: constitution, specify, clarify, plan, tasks, analyze, implement, converge.")
    return lineas


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Registra los tiempos de cada etapa del SDD y los rinde en specs/METRICS.md.")
    ap.add_argument("proyecto", nargs="?", default=".", help="carpeta del proyecto (por defecto, la actual)")
    ap.add_argument("accion", nargs="?", choices=["inicio", "fin", "informe", "etapas", "abiertas", "estimar"],
                    help="inicio|fin de una etapa; informe (crea y rinde METRICS.md); abiertas (etapas sin cerrar); "
                         "estimar (rellena huecos desde las fechas de los archivos); etapas (válidas)")
    ap.add_argument("etapa", nargs="?", help="etapa a marcar (con inicio/fin)")
    ap.add_argument("--spec", help="especificación (por defecto, la activa de .specify/feature.json)")
    ap.add_argument("--nota", help="nota corta que acompaña la marca (queda en METRICS.md)")
    ap.add_argument("--ahora", help="hora ISO a usar en la marca (por defecto, la del sistema)")
    ap.add_argument("--reiniciar", action="store_true", help="vuelve a marcar aunque ya exista la marca")
    ap.add_argument("--escribir", action="store_true", help="con `estimar`: aplica la estimación (sin esto, solo la muestra)")
    a = ap.parse_args(argv)

    proy = Path(a.proyecto).expanduser().resolve()
    if not proy.is_dir():
        print(f"ERROR: no existe la carpeta {proy}", file=sys.stderr)
        return 2
    if a.accion is None or a.accion == "etapas":
        print("\n".join(_etapas_texto()))
        return 0
    try:
        cuando = ahora(a.ahora)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    datos = cargar(proy)
    esps = esps_del_proyecto(proy)

    if a.accion == "informe":
        if a.spec:
            encontrada, err = resolver_spec(proy, a.spec)
            if err:
                print(f"ERROR: {err}", file=sys.stderr)
                return 2
            if encontrada not in esps:
                esps.append(encontrada); esps.sort()
        ruta = escribir_metrics(proy, datos, esps, cuando)
        for linea in resumen_consola(datos, esps, cuando):
            print(linea)
        print(("Archivo actualizado: " if consola is None else consola.ok("Archivo actualizado: ")) + str(ruta.relative_to(proy)))
        abiertas = etapas_abiertas(datos, esps)
        if abiertas:
            for spec, clave, inicio in abiertas:
                texto = (f"{spec} · {ETIQUETAS[clave]}: en curso desde {formato_hora(inicio)} "
                         f"({formato_min(_transcurrido(inicio, cuando))} min)")
                print(texto if consola is None else consola.aviso(texto))
            print("ciérralas con «tiempos.py . fin <etapa>», o estímalas con «tiempos.py . estimar»")
        return 0

    if a.accion == "abiertas":
        abiertas = etapas_abiertas(datos, esps)
        if not abiertas:
            print("no hay etapas abiertas: todas las marcadas están cerradas")
            return 0
        for spec, clave, inicio in abiertas:
            texto = (f"{spec} · {ETIQUETAS[clave]}: en curso desde {formato_hora(inicio)} "
                     f"({formato_min(_transcurrido(inicio, cuando))} min)")
            print(texto if consola is None else consola.aviso(texto))
        print(f"{len(abiertas)} etapa(s) abierta(s). Ciérralas con «fin <etapa>» o, si ya pasaron, "
              f"estímalas con «estimar --escribir»")
        return 0

    if a.accion == "estimar":
        datos, cambios = estimar(datos, proy, esps)
        if not cambios:
            print("nada que estimar: no hay etapas sin marca con artefacto en disco")
            return 0
        encabezado = ("[simulación] " if not a.escribir else "") + \
                     f"{len(cambios)} etapa(s) con fin deducido de sus artefactos:"
        print(encabezado if consola is None else consola.titulo(encabezado))
        for spec, clave, ini, fin in cambios:
            detalle = f"    - {spec.split('/')[-1]} · {ETIQUETAS[clave]}: " + \
                      (f"{formato_hora(_iso(ini))} → " if ini else "") + \
                      formato_hora(fin.isoformat(timespec="seconds"))
            print(detalle)
        if a.escribir:
            guardar(proy, datos)
            escribir_metrics(proy, datos, esps, cuando)
            print("METRICS.md actualizado: las filas estimadas llevan la nota «estimado por fechas de archivo»"
                  if consola is None else consola.ok("METRICS.md actualizado: las filas estimadas llevan la nota «estimado por fechas de archivo»"))
        else:
            print("para aplicarlo: añade --escribir" if consola is None else consola.aviso("para aplicarlo: añade --escribir"))
        return 0

    spec, err = resolver_spec(proy, a.spec)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    if spec not in esps:
        esps.append(spec)
        esps.sort()
    datos["specs"].setdefault(spec, {"etapas": {}})

    etapa = normalizar(a.etapa)
    if etapa is None:
        print(f"ERROR: etapa desconocida «{a.etapa or ''}»; usa «etapas» para ver las válidas", file=sys.stderr)
        return 2
    cerrar = a.accion == "fin"
    datos, err = marcar(datos, spec, etapa, cuando, cerrar=cerrar, nota=a.nota, reiniciar=a.reiniciar)
    if err:
        print(("ERROR: " if consola is None else consola.error("ERROR: ")) + err, file=sys.stderr)
        return 1
    guardar(proy, datos)
    ruta = escribir_metrics(proy, datos, esps, cuando)
    reg = datos["specs"][spec]["etapas"][etapa]
    etiqueta = ETIQUETAS[etapa]
    if cerrar:
        texto = f"{etiqueta} ({spec}): {formato_min(minutos(reg['inicio'], reg['fin']))} min"
        print(texto if consola is None else consola.ok(texto))
    else:
        texto = f"{etiqueta} ({spec}): en curso desde {formato_hora(reg['inicio'])}"
        print(texto if consola is None else consola.aviso(texto))
    print("Registro: " + str(ruta.relative_to(proy)) + f"  ·  estado: {ESTADO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())