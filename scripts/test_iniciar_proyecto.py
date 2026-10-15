"""Pruebas de iniciar_proyecto.py. Ejecuta: python scripts/test_iniciar_proyecto.py"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import iniciar_proyecto as ip  # noqa: E402

try:
    import yaml
    HAY_YAML = True
except ImportError:
    HAY_YAML = False

BLOQUE = (ip.REFS / "agents-block.md").read_text(encoding="utf-8")
PLANTILLA_VACIA = "# [PROJECT_NAME] Constitution\n\n### [PRINCIPLE_1_NAME]\n[PRINCIPLE_1_DESCRIPTION]\n"


def correr(args):
    salida = io.StringIO()
    with redirect_stdout(salida):
        rc = ip.main(args)
    return rc, salida.getvalue()


def correr_error(args):
    import contextlib
    err = io.StringIO()
    with contextlib.redirect_stderr(err), redirect_stdout(io.StringIO()):
        rc = ip.main(args)
    return rc, err.getvalue()


class PruebasPuras(unittest.TestCase):
    def test_stack_lines_tiene_dos_variantes(self):
        con, sin = ip.leer_lineas_stack((ip.REFS / "stack-lines.md").read_text(encoding="utf-8"))
        self.assertIn("pyodbc y SQL Server", con)
        self.assertIn("sin base de datos", sin)

    def test_render_constitucion_sin_marcadores_sobrantes(self):
        t = ip.render_constitucion((ip.REFS / "constitution.template.md").read_text(encoding="utf-8"),
                                   "mi_app", "2026-10-10", "- Stack: X", "prueba")
        self.assertNotIn("{{", t)
        self.assertIn("# mi_app Constitution", t)
        self.assertIn("- Stack: X", t)
        self.assertIn("**Ratified**: 2026-10-10", t)
        self.assertTrue(ip.es_constitucion_ld(t))
        self.assertFalse(ip.es_constitucion_vacia(t))

    def test_render_falla_si_la_plantilla_trae_marcador_desconocido(self):
        with self.assertRaises(ValueError):
            ip.render_constitucion("{{OTRO}}", "a", "b", "c", "d")

    def test_constitucion_vacia_de_speckit(self):
        self.assertTrue(ip.es_constitucion_vacia(PLANTILLA_VACIA))

    def test_constitucion_rellenada_que_cita_marcadores_en_su_reporte_no_es_vacia(self):
        # Caso real (shifu_calc): el Sync Impact Report menciona los marcadores originales
        rellenada = ("<!--\nSync Impact Report\nModified principles:\n  - [PRINCIPLE_1_NAME] → I. Estilo base primero\n"
                     "  - [PROJECT_NAME] → shifu_calc\n-->\n# shifu_calc Constitution\n\n### I. Estilo base primero\nMUST...\n")
        self.assertFalse(ip.es_constitucion_vacia(rellenada))

    def test_agents_nuevo_idempotente_y_conserva_contenido(self):
        t1, antiguo = ip.fusionar_agents("", BLOQUE)
        self.assertFalse(antiguo)
        self.assertIn(ip.MARCA_INI, t1)
        t2, _ = ip.fusionar_agents(t1, BLOQUE)
        self.assertEqual(t1, t2)  # idempotente
        base = "# Reglas del proyecto\n\n- usar tabs\n"
        t3, _ = ip.fusionar_agents(base, BLOQUE)
        self.assertTrue(t3.startswith(base.rstrip("\n")))
        self.assertIn("usar tabs", t3)
        t4, _ = ip.fusionar_agents(t3.replace("carga primero", "CAMBIADO"), BLOQUE)
        self.assertNotIn("CAMBIADO", t4)  # actualiza solo dentro de las marcas
        self.assertIn("usar tabs", t4)

    def test_agents_con_bloque_antiguo_sin_marcas(self):
        antiguo = "# Mi proyecto\n\n" + BLOQUE.replace("carga primero", "VIEJO") + "\n## Otra sección\n\ntexto\n"
        t, era = ip.fusionar_agents(antiguo, BLOQUE)
        self.assertTrue(era)
        self.assertNotIn("VIEJO", t)
        self.assertIn("## Otra sección", t)
        self.assertEqual(t.count(ip.TITULO_BLOQUE), 1)

    def test_opencode_json(self):
        self.assertEqual(json.loads(ip.fusionar_opencode_json(""))["instructions"], [ip.RUTA_CONSTITUCION])
        t = ip.fusionar_opencode_json('{"model": "x", "instructions": ["A.md"]}')
        d = json.loads(t)
        self.assertEqual(d["model"], "x")
        self.assertEqual(d["instructions"], ["A.md", ip.RUTA_CONSTITUCION])
        self.assertEqual(ip.fusionar_opencode_json(t), t)  # idempotente
        self.assertEqual(json.loads(ip.fusionar_opencode_json('{"instructions": "A.md"}'))["instructions"], ["A.md", ip.RUTA_CONSTITUCION])
        with self.assertRaises(ValueError):
            ip.fusionar_opencode_json("[1]")


class PruebasExtremoAExtremo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proy = Path(self.tmp.name) / "mi_app"
        self.addCleanup(self.tmp.cleanup)

    def preparar_speckit(self, constitucion):
        d = self.proy / ".specify" / "memory"
        d.mkdir(parents=True)
        (d / "constitution.md").write_text(constitucion, encoding="utf-8")

    def test_dry_run_no_escribe(self):
        rc, salida = correr([str(self.proy), "--sin-speckit", "--si", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertFalse(self.proy.exists())
        self.assertIn("[simulación]", salida)

    def test_arranque_completo_con_speckit_ya_iniciado(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        rc, salida = correr([str(self.proy), "--si", "--sin-sql"])
        self.assertEqual(rc, 0)
        skills = sorted(p.name for p in (self.proy / ".agents" / "skills").iterdir())
        self.assertIn("ld-speckit", skills)
        self.assertEqual(len(skills), len([p for p in ip.SKILLS_ORIGEN.iterdir() if p.is_dir() and p.name.startswith("ld-")]))
        self.assertIn("ld-transferencia", skills)
        self.assertFalse(list((self.proy / ".agents").rglob("__pycache__")))
        const = (self.proy / ip.RUTA_CONSTITUCION).read_text(encoding="utf-8")
        self.assertIn("# mi_app Constitution", const)
        self.assertIn("sin base de datos", const)
        for d, _ in ip.archivos_kit():          # kit base: módulos, estilos e iconos reales de los proyectos LD
            self.assertTrue((self.proy / d).is_file(), d)
        self.assertTrue((self.proy / "Static/styles/LD.css").is_file())
        self.assertTrue((self.proy / "Static/Images/Icons/Editar.png").is_file())
        self.assertEqual((self.proy / "Modulos" / "modAccesoDatos.py").read_bytes(),
                         (ip.SKILLS_ORIGEN / "ld-data/examples/base/modAccesoDatos.py").read_bytes())
        self.assertTrue(ip.MARCA_INI in (self.proy / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((self.proy / "opencode.json").read_text())["instructions"], [ip.RUTA_CONSTITUCION])
        self.assertIn("Siguiente paso", salida)

    def test_segunda_ejecucion_no_cambia_nada(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        correr([str(self.proy), "--si"])
        antes = {p: p.read_bytes() for p in self.proy.rglob("*") if p.is_file()}
        rc, salida = correr([str(self.proy), "--si"])
        despues = {p: p.read_bytes() for p in self.proy.rglob("*") if p.is_file()}
        self.assertEqual(antes, despues)
        self.assertIn("ya existe (LD)", salida)

    def test_constitucion_rellenada_con_reporte_que_cita_marcadores_no_se_sobrescribe(self):
        rellenada = ("<!--\nSync Impact Report\n  - [PRINCIPLE_1_NAME] → I. Estilo base primero\n-->\n"
                     "# mi_app Constitution\n\n### I. Estilo base primero\nMUST algo propio.\n")
        self.preparar_speckit(rellenada)
        correr([str(self.proy), "--si"])
        self.assertEqual((self.proy / ip.RUTA_CONSTITUCION).read_text(encoding="utf-8"), rellenada)

    def test_constitucion_existente_no_se_toca(self):
        propia = "# Mi constitución\n\n### I. Algo propio\nMUST algo.\n"
        self.preparar_speckit(propia)
        correr([str(self.proy), "--si"])
        self.assertEqual((self.proy / ip.RUTA_CONSTITUCION).read_text(encoding="utf-8"), propia)
        self.assertIn("instructions", (self.proy / "opencode.json").read_text())  # igualmente se enlaza

    def test_skills_modificados_requieren_update(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        correr([str(self.proy), "--si"])
        archivo = self.proy / ".agents" / "skills" / "ld-data" / "SKILL.md"
        archivo.write_text("modificado a mano", encoding="utf-8")
        _, salida = correr([str(self.proy), "--si"])
        self.assertEqual(archivo.read_text(), "modificado a mano")
        self.assertIn("ld-data", salida)
        self.assertIn("--update", salida)
        correr([str(self.proy), "--si", "--update"])
        self.assertNotEqual(archivo.read_text(), "modificado a mano")
        self.assertEqual((archivo.parent / "SKILL-old.md").read_text(), "modificado a mano")

    def test_kit_no_sobrescribe_archivos_existentes(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        css = self.proy / "Static" / "styles" / "DACP.css"
        css.parent.mkdir(parents=True)
        css.write_text("/* mío */", encoding="utf-8")
        correr([str(self.proy), "--si"])
        self.assertEqual(css.read_text(encoding="utf-8"), "/* mío */")
        self.assertTrue((self.proy / "Static" / "scripts" / "General.js").exists())

    def test_sin_base_no_instala_el_kit(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        correr([str(self.proy), "--si", "--sin-base"])
        self.assertFalse((self.proy / "Modulos").exists())
        self.assertFalse((self.proy / "Static").exists())

    # ---- stack y modo de desarrollo (.ld/config.json)
    def test_si_usa_ld_y_sdd_por_defecto(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        rc, salida = correr([str(self.proy), "--si", "--sin-sql"])
        self.assertEqual(rc, 0)
        cfg = json.loads((self.proy / ip.RUTA_CONFIG).read_text(encoding="utf-8"))
        self.assertEqual(cfg["stack"], "ld")
        self.assertEqual(cfg["modo"], "sdd")
        self.assertIn("Siguiente paso", salida)

    def test_stack_actual_no_instala_kit_ni_diseno(self):
        rc, salida = correr([str(self.proy), "--si", "--sin-speckit", "--stack", "actual"])
        self.assertEqual(rc, 0)
        self.assertFalse((self.proy / "Modulos").exists())
        self.assertFalse((self.proy / "Static").exists())
        self.assertFalse((self.proy / ip.RUTA_DISENO).exists())
        cfg = json.loads((self.proy / ip.RUTA_CONFIG).read_text(encoding="utf-8"))
        self.assertEqual(cfg["stack"], "actual")
        self.assertEqual(cfg["sql"], False)          # con stack no-LD no se impone SQL Server
        self.assertIn("no se instala el kit base", salida)

    def test_modo_vibe_guarda_config_y_sugiere_prompts(self):
        rc, salida = correr([str(self.proy), "--si", "--sin-speckit", "--modo", "vibe"])
        self.assertEqual(rc, 0)
        cfg = json.loads((self.proy / ip.RUTA_CONFIG).read_text(encoding="utf-8"))
        self.assertEqual(cfg["modo"], "vibe")
        self.assertIn("vibe coding", salida)
        self.assertIn("Agrega un gráfico", salida)

    def test_config_se_conserva_y_no_se_reescribe_en_update(self):
        correr([str(self.proy), "--si", "--sin-speckit", "--stack", "actual", "--modo", "vibe"])
        cfg_ruta = self.proy / ip.RUTA_CONFIG
        antes = cfg_ruta.read_bytes()
        rc, salida = correr([str(self.proy), "--si", "--sin-speckit", "--update"])
        self.assertEqual(rc, 0)
        self.assertEqual(cfg_ruta.read_bytes(), antes)        # la elección sobrevive a --update
        self.assertFalse((self.proy / "Modulos").exists())    # sigue sin kit: el stack es el mismo
        self.assertNotIn("guardar", salida)

    def test_stack_definir_requiere_detalle(self):
        rc, err = correr_error([str(self.proy), "--si", "--sin-speckit", "--stack", "definir"])
        self.assertEqual(rc, 2)
        self.assertIn("stack-detalle", err)
        self.assertFalse((self.proy / ip.RUTA_CONFIG).exists())
        rc, _ = correr([str(self.proy), "--si", "--sin-speckit", "--stack", "definir", "--stack-detalle", "FastAPI + React"])
        self.assertEqual(rc, 0)
        cfg = json.loads((self.proy / ip.RUTA_CONFIG).read_text(encoding="utf-8"))
        self.assertEqual(cfg["stack"], "definir")
        self.assertEqual(cfg["stack_detalle"], "FastAPI + React")

    def test_comando_shifu_iniciar_se_instala(self):
        correr([str(self.proy), "--si", "--sin-speckit"])
        cmd = self.proy / ip.RUTA_COMANDO_INICIAR
        self.assertTrue(cmd.is_file())
        texto = cmd.read_text(encoding="utf-8")
        self.assertIn("iniciar_proyecto.py", texto)
        self.assertIn(str(ip.RAIZ), texto)                    # ruta del paquete resuelta
        self.assertNotIn("{{RUTA_PAQUETE}}", texto)

    def test_version_informa_modo_y_stack(self):
        correr([str(self.proy), "--si", "--sin-speckit", "--stack", "definir",
                "--stack-detalle", "FastAPI + React", "--modo", "vibe"])
        rc, salida = correr([str(self.proy), "--version"])
        self.assertEqual(rc, 0)
        self.assertIn("modo de desarrollo: vibe", salida)
        self.assertIn("FastAPI + React", salida)

    def test_preguntar_opcion_acepta_numero_clave_o_defecto(self):
        import unittest.mock as mock
        opciones = [("a", "A"), ("b", "B")]
        with mock.patch("builtins.input", return_value="2"):
            self.assertEqual(ip.preguntar_opcion("X", opciones, "a", True), "b")
        with mock.patch("builtins.input", return_value="B"):
            self.assertEqual(ip.preguntar_opcion("X", opciones, "a", True), "b")
        with mock.patch("builtins.input", return_value=""):
            self.assertEqual(ip.preguntar_opcion("X", opciones, "a", True), "a")
        self.assertEqual(ip.preguntar_opcion("X", opciones, "a", False), "a")

    def test_skill_obsoleto_se_avisa_y_se_aparta_con_update(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        viejo = self.proy / ".agents" / "skills" / "ld-crud-legacy"
        viejo.mkdir(parents=True)
        (viejo / "SKILL.md").write_text("viejo", encoding="utf-8")
        _, salida = correr([str(self.proy), "--si"])
        self.assertTrue(viejo.exists())
        self.assertIn("obsoleto", salida)
        correr([str(self.proy), "--si", "--update"])
        self.assertFalse(viejo.exists())
        self.assertTrue((viejo.parent / "ld-crud-legacy-old" / "SKILL-old.md").exists())
        self.assertTrue((self.proy / ".agents" / "skills" / "ld-crud").is_dir())

    def test_sin_specify_no_genera_constitucion_ni_json(self):
        correr([str(self.proy), "--si", "--sin-speckit"])
        self.assertTrue((self.proy / "AGENTS.md").exists())
        self.assertFalse((self.proy / ip.RUTA_CONSTITUCION).exists())
        self.assertFalse((self.proy / "opencode.json").exists())

    def test_invoca_specify_init_cuando_falta_spec_kit(self):
        llamadas = []

        def falso(cmd, **kw):
            llamadas.append(cmd)
            if cmd[0] == "specify":  # simula lo que crea `specify init`
                (kw["cwd"] / ".specify" / "memory").mkdir(parents=True)
                (kw["cwd"] / ".specify" / "memory" / "constitution.md").write_text(PLANTILLA_VACIA, encoding="utf-8")

        original = ip.shutil.which
        ip.shutil.which = lambda n: "/usr/bin/specify" if n == "specify" else original(n)
        try:
            self.proy.mkdir()
            with redirect_stdout(io.StringIO()):
                ip.main([str(self.proy), "--si", "--skills", "omitir"], ejecutar_comando=falso)
        finally:
            ip.shutil.which = original
        self.assertEqual(llamadas[0][:3], ["specify", "init", "--here"])
        self.assertIn("--non-interactive", llamadas[0])
        self.assertIn("opencode", llamadas[0])
        self.assertIn("# mi_app Constitution", (self.proy / ip.RUTA_CONSTITUCION).read_text(encoding="utf-8"))

    # ---- estilo visual (.ld/diseno.json)
    def test_diseno_por_defecto_es_ld_y_no_se_vuelve_a_preguntar(self):
        rc, salida = correr([str(self.proy), "--si", "--sin-speckit"])
        self.assertEqual(rc, 0)
        self.assertEqual(ip.leer_diseno(self.proy), {"modo": "ld"})
        self.assertIn("«ld» por defecto", salida)
        rc, salida = correr([str(self.proy), "--si", "--sin-speckit", "--update"])
        self.assertEqual(ip.leer_diseno(self.proy), {"modo": "ld"})
        self.assertNotIn("por defecto", salida)

    def test_diseno_externo_se_guarda_y_sobrevive_a_update(self):
        rc, salida = correr([str(self.proy), "--si", "--sin-speckit", "--diseno", "externo", "--skill-diseno", "tailwind-design"])
        self.assertEqual(rc, 0)
        self.assertEqual(ip.leer_diseno(self.proy), {"modo": "externo", "skill": "tailwind-design"})
        self.assertIn("AVISO: no encuentro el skill", salida)
        correr([str(self.proy), "--si", "--sin-speckit", "--update"])
        self.assertEqual(ip.leer_diseno(self.proy), {"modo": "externo", "skill": "tailwind-design"})

    def test_cambiar_de_externo_a_ld_con_la_bandera(self):
        correr([str(self.proy), "--si", "--sin-speckit", "--skill-diseno", "otro-skill"])
        self.assertEqual(ip.leer_diseno(self.proy)["modo"], "externo")
        correr([str(self.proy), "--si", "--sin-speckit", "--diseno", "ld"])
        self.assertEqual(ip.leer_diseno(self.proy), {"modo": "ld"})

    def test_diseno_externo_sin_nombre_de_skill_falla_sin_escribir(self):
        rc, _ = correr_error([str(self.proy), "--si", "--sin-speckit", "--diseno", "externo"])
        self.assertEqual(rc, 2)
        self.assertIsNone(ip.leer_diseno(self.proy))

    def test_diseno_valida_nombres(self):
        self.assertIsNotNone(ip.validar_diseno("externo", "../x")[1])
        self.assertIsNotNone(ip.validar_diseno("externo", "a b")[1])
        self.assertIsNone(ip.validar_diseno("externo", "owner/tailwind-design")[1])
        self.assertIsNotNone(ip.validar_diseno("otro", None)[1])

    def test_diseno_en_simulacion_no_escribe(self):
        correr([str(self.proy), "--si", "--sin-speckit", "--dry-run", "--diseno", "ld"])
        self.assertFalse((self.proy / ip.RUTA_DISENO).exists())

    # ---- limpieza de versiones *-old (--clean)
    def preparar_old(self):
        """Deja *-old como los dejaría un --update: skills, kit base y raíz."""
        skills = self.proy / ".agents" / "skills"
        (skills / "ld-speckit" / "SKILL-old.md").write_text("viejo", encoding="utf-8")
        (skills / "ld-crud-legacy-old").mkdir()
        (skills / "ld-crud-legacy-old" / "SKILL-old.md").write_text("viejo", encoding="utf-8")
        (self.proy / "Static" / "scripts" / "General-old.js").write_text("// viejo", encoding="utf-8")
        (self.proy / "AGENTS-old.md").write_text("viejo", encoding="utf-8")
        return skills

    def test_clean_simula_luego_borra_solo_los_old(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        correr([str(self.proy), "--si", "--sin-sql"])
        skills = self.preparar_old()

        rc, salida = correr([str(self.proy), "--clean", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("por borrar", salida)
        self.assertTrue((skills / "ld-speckit" / "SKILL-old.md").exists())

        rc, salida = correr([str(self.proy), "--clean"])
        self.assertEqual(rc, 0)
        self.assertIn("borrados", salida)
        self.assertFalse((skills / "ld-speckit" / "SKILL-old.md").exists())
        self.assertFalse((skills / "ld-crud-legacy-old").exists())
        self.assertFalse((self.proy / "Static" / "scripts" / "General-old.js").exists())
        self.assertFalse((self.proy / "AGENTS-old.md").exists())
        self.assertTrue((skills / "ld-speckit" / "SKILL.md").exists())          # lo real queda
        self.assertTrue((self.proy / "Static" / "scripts" / "General.js").exists())

    def test_clean_sin_old_lo_dice_y_no_toca_nada(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        correr([str(self.proy), "--si", "--sin-sql"])
        rc, salida = correr([str(self.proy), "--clean"])
        self.assertEqual(rc, 0)
        self.assertIn("nada que limpiar", salida)

    def test_entradas_old_no_repite_los_hijos_de_una_carpeta_old(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        correr([str(self.proy), "--si", "--sin-sql"])
        skills = self.preparar_old()
        entradas = [str(p.relative_to(self.proy)) for p in ip.entradas_old(self.proy)]
        self.assertIn(".agents/skills/ld-crud-legacy-old", entradas)
        self.assertNotIn(".agents/skills/ld-crud-legacy-old/SKILL-old.md", entradas)
        self.assertTrue((skills / "ld-crud-legacy-old").exists())               # solo lista, no borra

    def test_version_menciona_clean(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        correr([str(self.proy), "--si", "--sin-sql"])
        self.preparar_old()
        rc, salida = correr([str(self.proy), "--version"])
        self.assertEqual(rc, 0)
        self.assertIn("--clean las borra", salida)

    # ---- ganchos de tiempos (.specify/extensions.yml) y comando /ld.tiempo
    def test_instala_ganchos_y_comando_renderizados(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        rc, salida = correr([str(self.proy), "--si", "--sin-sql"])
        self.assertEqual(rc, 0)
        ext = (self.proy / ip.RUTA_EXTENSIONES).read_text(encoding="utf-8")
        for fase in ("before_constitution", "after_specify", "before_clarify", "after_plan",
                     "before_tasks", "after_checklist", "before_analyze", "after_implement",
                     "before_converge", "after_converge"):
            self.assertIn(f"  {fase}:", ext)
        self.assertEqual(ext.count("- extension: ld-tiempos"), 18)
        self.assertEqual(ext.count(ip.MARCA_TIEMPOS_INI), 18)
        self.assertNotIn("condition:", ext)                 # un gancho con condition se salta
        self.assertIn("optional: false", ext)
        self.assertIn(f"{ip.RAIZ}/scripts/tiempos.py . inicio plan", ext)   # ruta del paquete resuelta
        cmd = (self.proy / ip.RUTA_COMANDO_TIEMPOS).read_text(encoding="utf-8")
        self.assertIn("tiempos.py . $ARGUMENTS", cmd)
        self.assertIn(str(ip.RAIZ), cmd)
        self.assertIn("ganchos de tiempos", salida)

    def test_ganchos_conservan_los_del_usuario_y_no_duplican(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        correr([str(self.proy), "--si", "--sin-sql"])
        ext = self.proy / ip.RUTA_EXTENSIONES
        texto = ext.read_text(encoding="utf-8").replace(
            "  before_plan:\n",
            "  before_plan:\n    - extension: mio\n      command: mio.comando\n"
            "      prompt: \"haz algo\"\n      optional: true\n", 1)
        ext.write_text(texto, encoding="utf-8")
        correr([str(self.proy), "--si", "--sin-sql", "--update"])
        nuevo = ext.read_text(encoding="utf-8")
        self.assertIn("mio.comando", nuevo)                        # se conserva lo del usuario
        self.assertEqual(nuevo.count("- extension: ld-tiempos"), 18)   # sin duplicar
        self.assertTrue((ext.parent / "extensions-old.yml").exists())  # respaldo del anterior
        plantilla = ip.render_tiempos(ip.PLANTILLA_EXTENSIONES.read_text(encoding="utf-8"))
        self.assertEqual(ip.fusionar_extensiones(nuevo, plantilla), nuevo)   # idempotente

    def test_ganchos_sobre_archivo_del_usuario_sin_comentarios(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        (self.proy / ip.RUTA_EXTENSIONES).write_text("otra_clave: 1\n", encoding="utf-8")
        correr([str(self.proy), "--si", "--sin-sql", "--update"])
        nuevo = (self.proy / ip.RUTA_EXTENSIONES).read_text(encoding="utf-8")
        self.assertIn("otra_clave: 1", nuevo)
        self.assertIn("hooks:", nuevo)
        self.assertEqual(nuevo.count("- extension: ld-tiempos"), 18)

    def test_ganchos_limpian_restos_sin_marcas(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        correr([str(self.proy), "--si", "--sin-sql"])
        ext = self.proy / ip.RUTA_EXTENSIONES
        sin_marcas = "\n".join(l for l in ext.read_text(encoding="utf-8").splitlines()
                               if l.strip() not in (ip.MARCA_TIEMPOS_INI, ip.MARCA_TIEMPOS_FIN)) + "\n"
        ext.write_text(sin_marcas, encoding="utf-8")
        correr([str(self.proy), "--si", "--sin-sql", "--update"])
        nuevo = ext.read_text(encoding="utf-8")
        self.assertEqual(nuevo.count("- extension: ld-tiempos"), 18)   # no se duplican los restos

    def test_version_informa_el_estado_de_los_ganchos(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        rc, salida = correr([str(self.proy), "--version"])
        self.assertIn("ganchos de tiempos: no instalados", salida)
        correr([str(self.proy), "--si", "--sin-sql"])
        rc, salida = correr([str(self.proy), "--version"])
        self.assertIn("ganchos de tiempos: al día", salida)
        self.assertIn("comando /ld.tiempo: al día", salida)
        (self.proy / ip.RUTA_EXTENSIONES).write_text("hooks:\n  before_plan:\n", encoding="utf-8")
        rc, salida = correr([str(self.proy), "--version"])
        self.assertIn("desactualizados", salida)

    @unittest.skipUnless(HAY_YAML, "PyYAML no está instalado: se omite el parseo del YAML")
    def test_ganchos_yaml_valido(self):
        self.preparar_speckit(PLANTILLA_VACIA)
        correr([str(self.proy), "--si", "--sin-sql"])
        datos = yaml.safe_load((self.proy / ip.RUTA_EXTENSIONES).read_text(encoding="utf-8"))
        hooks = datos["hooks"]
        self.assertEqual(len(hooks), 18)
        for fase, entradas in hooks.items():
            self.assertEqual(len(entradas), 1, fase)
            self.assertEqual(entradas[0]["extension"], "ld-tiempos")
            self.assertIs(entradas[0]["optional"], False)
            self.assertNotIn("condition", entradas[0])
            self.assertIn("tiempos.py . ", entradas[0]["prompt"])


if __name__ == "__main__":
    unittest.main()
