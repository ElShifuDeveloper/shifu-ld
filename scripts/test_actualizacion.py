"""Pruebas del sistema de versión, manifiesto y actualización de iniciar_proyecto.py.

Cada prueba trabaja con una COPIA temporal del paquete (para poder "publicar una versión nueva" cambiando archivos y VERSION)
y con un proyecto temporal. Ejecuta: python scripts/test_actualizacion.py
"""
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import iniciar_proyecto as ip  # noqa: E402

PLANTILLA_VACIA = "# [PROJECT_NAME] Constitution\n\n### [PRINCIPLE_1_NAME]\n[PRINCIPLE_1_DESCRIPTION]\n"
CHANGELOG = """# Historial

## [1.1.0] - 2026-11-01

### Cambios
- Se mejoró el ejemplo de carga.

### Migración
- Enmienda la constitución.

## [1.0.0] - 2026-10-01

Versión inicial.
"""
ARCHIVO = ".agents/skills/ld-data/SKILL.md"
OLD = ".agents/skills/ld-data/SKILL-old.md"
OLD2 = ".agents/skills/ld-data/SKILL-old-2.md"
KIT = "Static/scripts/Paquetes.js"


def correr(args):
    salida = io.StringIO()
    with redirect_stdout(salida):
        rc = ip.main(args)
    return rc, salida.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        raiz = Path(self.tmp.name) / "paquete"
        shutil.copytree(ip.SKILLS_ORIGEN, raiz / ".agents" / "skills", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        (raiz / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        (raiz / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
        original = (ip.RAIZ, ip.SKILLS_ORIGEN, ip.REFS)
        ip.RAIZ, ip.SKILLS_ORIGEN = raiz, raiz / ".agents" / "skills"
        ip.REFS = ip.SKILLS_ORIGEN / "ld-speckit" / "references"
        self.addCleanup(lambda: setattr(ip, "RAIZ", original[0]) or setattr(ip, "SKILLS_ORIGEN", original[1]) or setattr(ip, "REFS", original[2]))
        self.paquete = raiz
        self.proy = Path(self.tmp.name) / "proyecto"
        memoria = self.proy / ".specify" / "memory"
        memoria.mkdir(parents=True)
        (memoria / "constitution.md").write_text(PLANTILLA_VACIA, encoding="utf-8")

    def instalar(self, *extra):
        return correr([str(self.proy), "--si", "--sin-sql", *extra])

    def manifiesto(self):
        return json.loads((self.proy / ip.MANIFIESTO).read_text(encoding="utf-8"))

    def publicar(self, version, cambios):
        """Simula una versión nueva del paquete: {ruta_relativa_al_paquete: texto} (None = borrar)."""
        for rel, texto in cambios.items():
            f = self.paquete / rel
            if texto is None:
                f.unlink()
            else:
                f.write_text(texto, encoding="utf-8")
        (self.paquete / "VERSION").write_text(version + "\n", encoding="utf-8")

    def instantanea(self):
        return {p.relative_to(self.proy).as_posix(): p.read_bytes() for p in self.proy.rglob("*") if p.is_file()}


class PruebasPuras(unittest.TestCase):
    def test_versiones(self):
        self.assertGreater(ip.tupla_version("1.10.0"), ip.tupla_version("1.9.9"))
        self.assertEqual(ip.tupla_version("2"), (2, 0, 0))
        self.assertEqual(ip.tupla_version(None), (0, 0, 0))

    def test_entradas_de_changelog_posteriores_a_la_instalada(self):
        self.assertEqual([v for v, _ in ip.entradas_changelog(CHANGELOG, "1.0.0")], ["1.1.0"])
        self.assertEqual([v for v, _ in ip.entradas_changelog(CHANGELOG, None)], ["1.1.0", "1.0.0"])
        self.assertEqual(ip.entradas_changelog(CHANGELOG, "1.1.0"), [])
        self.assertIn("Enmienda la constitución", ip.entradas_changelog(CHANGELOG, "1.0.0")[0][1])

    def test_clasificar_los_seis_estados(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            src = t / "paquete.txt"
            proy = t / "proy"
            proy.mkdir()

            def estado(contenido_proyecto, contenido_paquete, registro):
                src.write_text(contenido_paquete)
                if contenido_proyecto is None:
                    (proy / "a.txt").unlink(missing_ok=True)
                else:
                    (proy / "a.txt").write_text(contenido_proyecto)
                return ip.clasificar(proy, "a.txt", src, ip.hashlib.sha256(registro.encode()).hexdigest() if registro is not None else None)

            self.assertEqual(estado(None, "v2", "v1"), "nuevo")
            self.assertEqual(estado("v2", "v2", "v1"), "al_dia")
            self.assertEqual(estado("v1", "v2", "v1"), "actualizable")        # tuyo == lo instalado; el paquete cambió
            self.assertEqual(estado("mio", "v1", "v1"), "personalizado")      # lo cambiaste tú; el paquete no
            self.assertEqual(estado("mio", "v2", "v1"), "modificado")         # lo cambiaste tú y el paquete también
            self.assertEqual(estado("mio", "v2", None), "sin_registro")       # LD nunca lo registró


class PruebasActualizacion(Base):
    def test_la_instalacion_crea_manifiesto_con_version_y_huellas(self):
        self.instalar()
        m = self.manifiesto()
        self.assertEqual(m["version"], "1.0.0")
        self.assertEqual(m["archivos"][ARCHIVO], ip.sha(self.paquete / ARCHIVO))
        self.assertEqual(m["archivos"][KIT], ip.sha(ip.SKILLS_ORIGEN / "ld-transferencia/examples/Paquetes.js"))
        self.assertIn("plantilla_sha256", m["constitucion"])

    def test_update_reemplaza_y_deja_la_version_anterior_como_old(self):
        self.instalar()
        anterior = (self.proy / ARCHIVO).read_bytes()
        self.publicar("1.1.0", {".agents/skills/ld-data/SKILL.md": "# ld-data nuevo\n"})
        _, salida = self.instalar("--update")
        self.assertEqual((self.proy / ARCHIVO).read_text(encoding="utf-8"), "# ld-data nuevo\n")
        self.assertEqual((self.proy / OLD).read_bytes(), anterior)
        self.assertEqual(self.manifiesto()["version"], "1.1.0")
        self.assertEqual(self.manifiesto()["archivos"][ARCHIVO], ip.sha(self.paquete / ARCHIVO))
        self.assertIn("1 reemplazados", salida)
        self.assertNotIn(OLD, self.manifiesto()["archivos"])

    def test_instalar_sin_update_solo_avisa(self):
        self.instalar()
        self.publicar("1.1.0", {".agents/skills/ld-data/SKILL.md": "# ld-data nuevo\n"})
        antes = self.instantanea()
        _, salida = self.instalar()
        self.assertEqual((self.proy / ARCHIVO).read_text(encoding="utf-8"), antes[ARCHIVO].decode())
        self.assertFalse((self.proy / OLD).exists())
        self.assertIn("--update", salida)

    def test_update_tambien_reemplaza_lo_que_modificaste_y_lo_conserva_como_old(self):
        self.instalar()
        (self.proy / ARCHIVO).write_text("# mi versión\n", encoding="utf-8")
        self.instalar("--update")
        self.assertEqual((self.proy / ARCHIVO).read_bytes(), (self.paquete / ARCHIVO).read_bytes())
        self.assertEqual((self.proy / OLD).read_text(encoding="utf-8"), "# mi versión\n")

    def test_update_sin_cambios_no_crea_old(self):
        self.instalar()
        _, salida = self.instalar("--update")
        self.assertFalse(list(self.proy.rglob("*-old*")))
        self.assertNotIn("quedó como *-old", salida)

    def test_old_numerado_si_ya_existe(self):
        self.instalar()
        (self.proy / ARCHIVO).write_text("# v-a\n", encoding="utf-8")
        self.instalar("--update")
        (self.proy / ARCHIVO).write_text("# v-b\n", encoding="utf-8")
        self.instalar("--update")
        self.assertEqual((self.proy / OLD).read_text(encoding="utf-8"), "# v-a\n")
        self.assertEqual((self.proy / OLD2).read_text(encoding="utf-8"), "# v-b\n")

    def test_instalacion_sin_manifiesto_informa_y_update_la_regulariza(self):
        self.instalar()
        (self.proy / ip.MANIFIESTO).unlink()                                # como un proyecto instalado con el script anterior
        (self.proy / ARCHIVO).write_text("# no sé si es mío o viejo\n", encoding="utf-8")
        _, salida = self.instalar()
        self.assertEqual((self.proy / ARCHIVO).read_text(encoding="utf-8"), "# no sé si es mío o viejo\n")
        self.assertIn("LD no los instaló", salida)
        self.instalar("--update")
        self.assertEqual((self.proy / ARCHIVO).read_bytes(), (self.paquete / ARCHIVO).read_bytes())
        self.assertEqual((self.proy / OLD).read_text(encoding="utf-8"), "# no sé si es mío o viejo\n")

    def test_archivo_retirado_del_paquete_queda_como_old(self):
        self.instalar()
        retirado = ".agents/skills/ld-data/references/sql-practices.md"
        self.publicar("1.1.0", {retirado: None})
        _, salida = self.instalar()
        self.assertTrue((self.proy / retirado).exists())                    # sin --update no se toca
        self.assertIn("ya no están en el paquete", salida)
        self.instalar("--update")
        self.assertFalse((self.proy / retirado).exists())
        self.assertTrue((self.proy / ".agents/skills/ld-data/references/sql-practices-old.md").exists())
        self.assertNotIn(retirado, self.manifiesto()["archivos"])

    def test_update_aparta_agents_y_opencode_json_si_cambian(self):
        self.instalar()
        agents = self.proy / "AGENTS.md"
        agents.write_text("# mío\n\n" + agents.read_text(encoding="utf-8"), encoding="utf-8")
        self.instalar("--update")      # el bloque LD ya está al día: fusionar conserva lo tuyo, no cambia nada
        self.assertFalse((self.proy / "AGENTS-old.md").exists())
        agents.write_text(agents.read_text(encoding="utf-8").replace(ip.TITULO_BLOQUE, ip.TITULO_BLOQUE + " x", 1), encoding="utf-8")
        self.instalar("--update")
        self.assertTrue((self.proy / "AGENTS-old.md").exists())
        (self.proy / "opencode.json").write_text('{"instructions": []}\n', encoding="utf-8")
        self.instalar("--update")
        self.assertTrue((self.proy / "opencode-old.json").exists())
        self.assertIn(ip.RUTA_CONSTITUCION, (self.proy / "opencode.json").read_text(encoding="utf-8"))

    def test_skill_obsoleto_se_aparta_como_old_e_inerte(self):
        self.instalar()
        viejo = self.proy / ".agents/skills/ld-crud-legacy"
        viejo.mkdir()
        (viejo / "SKILL.md").write_text("---\nname: ld-crud-legacy\ndescription: x\n---\n", encoding="utf-8")
        _, salida = self.instalar()
        self.assertIn("--update", salida)
        self.instalar("--update")
        self.assertFalse(viejo.exists())
        apartado = self.proy / ".agents/skills/ld-crud-legacy-old"
        self.assertTrue((apartado / "SKILL-old.md").exists())
        self.assertFalse((apartado / "SKILL.md").exists())

    def test_el_kit_tambien_se_actualiza(self):
        self.instalar()
        self.publicar("1.1.0", {".agents/skills/ld-transferencia/examples/Paquetes.js": "// nueva versión\n"})
        self.instalar("--update")
        self.assertEqual((self.proy / KIT).read_text(encoding="utf-8"), "// nueva versión\n")

    def test_sin_base_no_toca_ni_retira_el_kit_registrado(self):
        self.instalar()
        self.instalar("--update", "--sin-base")
        self.assertTrue((self.proy / KIT).exists())
        self.assertIn(KIT, self.manifiesto()["archivos"])

    def test_dry_run_no_escribe_nada(self):
        self.instalar()
        self.publicar("1.1.0", {".agents/skills/ld-data/SKILL.md": "# ld-data nuevo\n"})
        antes = self.instantanea()
        self.instalar("--update", "--dry-run")
        self.assertEqual(antes, self.instantanea())


class PruebasVersion(Base):
    def test_version_es_de_solo_lectura_y_muestra_version_y_cambios(self):
        self.instalar()
        self.publicar("1.1.0", {".agents/skills/ld-data/SKILL.md": "# ld-data nuevo\n"})
        antes = self.instantanea()
        rc, salida = correr([str(self.proy), "--version"])
        self.assertEqual(rc, 0)
        self.assertEqual(antes, self.instantanea())
        self.assertIn("versión instalada: 1.0.0 | disponible: 1.1.0", salida)
        self.assertIn("tienen una versión nueva", salida)
        self.assertIn("Se mejoró el ejemplo de carga", salida)
        self.assertIn("Enmienda la constitución", salida)
        self.assertIn("--update", salida)

    def test_version_al_dia(self):
        self.instalar()
        _, salida = correr([str(self.proy), "--version"])
        self.assertIn("resultado: al día", salida)
        self.assertIn("constitución: al día con la plantilla LD", salida)

    def test_version_cuenta_las_versiones_old(self):
        self.instalar()
        (self.proy / ARCHIVO).write_text("# mío\n", encoding="utf-8")
        self.instalar("--update")
        _, salida = correr([str(self.proy), "--version"])
        self.assertIn("1 versiones anteriores (*-old)", salida)

    def test_version_sin_manifiesto(self):
        self.instalar()
        (self.proy / ip.MANIFIESTO).unlink()
        _, salida = correr([str(self.proy), "--version"])
        self.assertIn("sin manifiesto", salida)

    def test_version_avisa_si_la_plantilla_de_constitucion_cambio(self):
        self.instalar()
        plantilla = ip.REFS / "constitution.template.md"
        plantilla.write_text(plantilla.read_text(encoding="utf-8") + "\n### IX. Nuevo principio\n", encoding="utf-8")
        _, salida = correr([str(self.proy), "--version"])
        self.assertIn("la plantilla LD cambió", salida)
        self.assertIn("/speckit.constitution", salida)

    def test_version_de_carpeta_inexistente(self):
        self.assertEqual(correr([str(Path(self.tmp.name) / "no_existe"), "--version"])[0], 2)


if __name__ == "__main__":
    unittest.main()
