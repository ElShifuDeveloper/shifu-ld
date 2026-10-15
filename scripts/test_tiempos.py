"""Pruebas de tiempos.py (METRICS.md del SDD). Ejecuta: python scripts/test_tiempos.py"""
import datetime
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True   # el paquete se distribuye sin __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiempos as t  # noqa: E402


def correr(args):
    salida, err = io.StringIO(), io.StringIO()
    with redirect_stdout(salida), redirect_stderr(err):
        rc = t.main(args)
    return rc, salida.getvalue(), err.getvalue()


class PruebasPuras(unittest.TestCase):
    def test_normalizar_acepta_espanol_ingles_y_desglose(self):
        for entrada, esperado in [
            ("plan", "plan"), ("PLAN", "plan"), ("specify", "especificar"),
            ("especificar", "especificar"), ("tasks", "tareas"), ("implement", "implementar"),
            ("analyze", "analizar"), ("converge", "converger"), ("constitution", "constitucion"),
            ("implementar:qa", "implementar:qa"), ("implement:qa", "implementar:qa"),
            ("implementar:diseño", "implementar:diseño"), ("implement:diseno", "implementar:diseño"),
            ("implement:integration", "implementar:integracion"),
        ]:
            self.assertEqual(t.normalizar(entrada), esperado, entrada)
        self.assertIsNone(t.normalizar("etapa_falsa"))
        self.assertIsNone(t.normalizar(""))

    def test_minutos_y_formato(self):
        self.assertEqual(t.minutos("2026-10-10T10:00:00", "2026-10-10T10:12:00"), 12)
        self.assertEqual(t.minutos("2026-10-10T10:00:00", "2026-10-10T10:01:30"), 1.5)
        self.assertIsNone(t.minutos(None, "2026-10-10T10:12:00"))
        self.assertEqual(t.formato_min(12.0), "12")
        self.assertEqual(t.formato_min(1.5), "1.5")
        self.assertEqual(t.formato_min(None), "—")

    def test_marcar_y_errores(self):
        datos = {"specs": {}}
        cuando = t.ahora("2026-10-10T10:00:00")
        datos, err = t.marcar(datos, "specs/001-x", "plan", cuando)
        self.assertIsNone(err)
        datos, err = t.marcar(datos, "specs/001-x", "plan", t.ahora("2026-10-10T10:05:00"))
        self.assertIn("ya tenía inicio", err)                       # no se re-marca sin --reiniciar
        datos, err = t.marcar(datos, "specs/001-x", "plan", cuando, reiniciar=True)
        self.assertIsNone(err)
        datos, err = t.marcar(datos, "specs/001-x", "plan", t.ahora("2026-10-10T10:12:00"), cerrar=True)
        self.assertIsNone(err)
        self.assertEqual(t.minutos(**{k: datos["specs"]["specs/001-x"]["etapas"]["plan"][k]
                                      for k in ("inicio", "fin")}), 12)
        datos, err = t.marcar(datos, "specs/001-x", "plan", cuando, cerrar=True)
        self.assertIn("ya estaba cerrada", err)
        datos, err = t.marcar(datos, "specs/001-x", "tareas", cuando, cerrar=True)
        self.assertIn("no tiene inicio marcado", err)
        # no se puede cerrar antes de empezar (protege contra intervalos negativos)
        otros = {"specs": {}}
        t.marcar(otros, "specs/001-x", "plan", t.ahora("2026-10-10T10:00:00"))
        otros, err = t.marcar(otros, "specs/001-x", "plan", t.ahora("2026-10-10T09:00:00"),
                              cerrar=True)
        self.assertIn("no puede cerrarse antes", err)

    def test_totales_solo_cuentan_etapas_de_nivel_superior(self):
        etapas = {
            "plan": {"inicio": "2026-10-10T10:00:00", "fin": "2026-10-10T10:10:00"},
            "implementar": {"inicio": "2026-10-10T11:00:00", "fin": "2026-10-10T12:00:00"},
            "implementar:qa": {"inicio": "2026-10-10T11:10:00", "fin": "2026-10-10T11:25:00"},
        }
        self.assertEqual(t.total_etapas(etapas), 70)      # 10 + 60; el desglose no se suma aquí
        self.assertEqual(t.total_subetapas(etapas), 15)


class PruebasProyecto(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.proy = Path(self.tmp.name) / "mi_app"
        self.spec = self.proy / "specs" / "003-parametric-transfer-limits"
        (self.proy / ".specify").mkdir(parents=True)
        self.spec.mkdir(parents=True)
        (self.spec / "spec.md").write_text("# spec", encoding="utf-8")
        (self.proy / ".specify" / "feature.json").write_text(
            json.dumps({"feature_directory": "specs/003-parametric-transfer-limits"}), encoding="utf-8")

    def leer_metrics(self):
        return (self.proy / "specs" / "METRICS.md").read_text(encoding="utf-8")

    def leer_estado(self):
        return json.loads((self.proy / ".ld" / "tiempos.json").read_text()
                          )["specs"]["specs/003-parametric-transfer-limits"]["etapas"]

    def test_ciclo_inicio_fin_escribe_metrics_sin_ansi(self):
        rc, salida, _ = correr([str(self.proy), "inicio", "plan", "--ahora", "2026-10-10T10:00:00"])
        self.assertEqual(rc, 0)
        self.assertIn("en curso", salida)
        rc, salida, _ = correr([str(self.proy), "fin", "plan", "--ahora", "2026-10-10T10:12:00",
                                "--nota", "Technical Context completo"])
        self.assertEqual(rc, 0)
        self.assertIn("12 min", salida)
        self.assertNotIn("\033[", salida)                       # sin terminal, sin color
        metrics = self.leer_metrics()
        self.assertIn("| Plan | 2026-10-10 10:00 | 2026-10-10 10:12 | 12 | Technical Context completo |", metrics)
        self.assertIn("| 003-parametric-transfer-limits |", metrics)
        self.assertIn("**Total etapas** | | | **12** |", metrics)
        self.assertTrue((self.proy / ".ld" / "tiempos.json").is_file())

    def test_desglose_de_implementar(self):
        correr([str(self.proy), "inicio", "implementar", "--ahora", "2026-10-11T09:00:00"])
        correr([str(self.proy), "inicio", "implementar:qa", "--ahora", "2026-10-11T09:30:00"])
        correr([str(self.proy), "fin", "implementar:qa", "--ahora", "2026-10-11T09:52:00"])
        rc, _, _ = correr([str(self.proy), "fin", "implementar", "--ahora", "2026-10-11T10:40:00"])
        self.assertEqual(rc, 0)
        metrics = self.leer_metrics()
        self.assertIn("| QA / pruebas | 2026-10-11 09:30 | 2026-10-11 09:52 | 22 | — |", metrics)
        self.assertIn("| **Total desglose** | | | **22** | |", metrics)
        self.assertIn("| Implementar | 2026-10-11 09:00 | 2026-10-11 10:40 | 100 |", metrics)

    def test_informe_crea_el_archivo_y_lista_todas_las_specs(self):
        otra = self.proy / "specs" / "001-primera"
        otra.mkdir()
        (otra / "spec.md").write_text("# spec", encoding="utf-8")
        rc, salida, _ = correr([str(self.proy), "informe"])
        self.assertEqual(rc, 0)
        self.assertIn("001-primera", salida)
        self.assertIn("003-parametric-transfer-limits", salida)
        metrics = self.leer_metrics()
        self.assertIn("## specs/001-primera", metrics)
        self.assertIn("| Constitución | — | — | — | — |", metrics)

    def test_spec_por_numero_y_por_nombre(self):
        casos = (("003", "tareas"), ("003-parametric-transfer-limits", "analizar"),
                 ("specs/003-parametric-transfer-limits", "converger"))
        for dado, etapa in casos:
            rc, _, _ = correr([str(self.proy), "inicio", etapa, "--spec", dado,
                               "--ahora", "2026-10-12T08:00:00"])
            self.assertEqual(rc, 0, dado)
        etapas = json.loads((self.proy / ".ld" / "tiempos.json").read_text()
                            )["specs"]["specs/003-parametric-transfer-limits"]["etapas"]
        for _, etapa in casos:
            self.assertIn(etapa, etapas)

    def test_errores_de_uso(self):
        rc, _, err = correr([str(self.proy), "fin", "plan", "--ahora", "2026-10-10T10:00:00"])
        self.assertEqual(rc, 1)
        self.assertIn("no tiene inicio marcado", err)
        rc, _, err = correr([str(self.proy), "inicio", "etapa_falsa"])
        self.assertEqual(rc, 2)
        self.assertIn("etapa desconocida", err)
        rc, _, err = correr([str(self.proy), "inicio", "plan", "--ahora", "no-es-fecha"])
        self.assertEqual(rc, 2)
        self.assertIn("ISO", err)

    def test_varias_specs_sin_activa_pide_spec(self):
        (self.proy / ".specify" / "feature.json").unlink()
        (self.proy / "specs" / "001-otra").mkdir()
        rc, _, err = correr([str(self.proy), "inicio", "plan"])
        self.assertEqual(rc, 2)
        self.assertIn("indica --spec", err)

    def test_estimar_no_crea_intervalos_negativos(self):
        ts = lambda h, m: datetime.datetime(2026, 10, 5, h, m).timestamp()
        (self.spec / "tasks.md").write_text("# t", encoding="utf-8")
        os.utime(self.spec / "tasks.md", (ts(9, 20), ts(9, 20)))
        # marca de plan posterior a las fechas de los artefactos (caso real: marcar hoy algo viejo)
        correr([str(self.proy), "inicio", "plan", "--ahora", "2026-10-13T22:00:00"])
        correr([str(self.proy), "fin", "plan", "--ahora", "2026-10-13T22:51:00"])
        rc, _, _ = correr([str(self.proy), "estimar", "--escribir"])
        self.assertEqual(rc, 0)
        etapas = self.leer_estado()
        self.assertIn("tareas", etapas)
        self.assertNotIn("inicio", etapas["tareas"])       # no se inventa un inicio posterior al fin
        self.assertIn("sin inicio conocido", etapas["tareas"]["nota"])
        for clave, reg in etapas.items():
            m = t.minutos(reg.get("inicio"), reg.get("fin"))
            self.assertTrue(m is None or m >= 0, f"{clave} con minutos negativos: {m}")

    def test_etapas_lista_las_validas(self):
        rc, salida, _ = correr([str(self.proy), "etapas"])
        self.assertEqual(rc, 0)
        for clave, _ in t.ETAPAS + t.SUBETAPAS:
            self.assertIn(clave, salida)

    def test_etapa_checklist(self):
        self.assertEqual(t.normalizar("checklist"), "checklist")
        self.assertEqual(t.normalizar("/speckit.checklist"), None)   # se pasa sin barra
        correr([str(self.proy), "inicio", "checklist", "--ahora", "2026-10-12T09:00:00"])
        rc, _, _ = correr([str(self.proy), "fin", "checklist", "--ahora", "2026-10-12T09:30:00"])
        self.assertEqual(rc, 0)
        self.assertIn("| Checklist | 2026-10-12 09:00 | 2026-10-12 09:30 | 30 | — |", self.leer_metrics())

    def test_abiertas_lista_en_curso_y_luego_vacio(self):
        correr([str(self.proy), "inicio", "plan", "--ahora", "2026-10-10T10:00:00"])
        rc, salida, _ = correr([str(self.proy), "abiertas", "--ahora", "2026-10-10T10:20:00"])
        self.assertEqual(rc, 0)
        self.assertIn("Plan", salida)
        self.assertIn("20 min", salida)
        correr([str(self.proy), "fin", "plan", "--ahora", "2026-10-10T10:25:00"])
        rc, salida, _ = correr([str(self.proy), "abiertas"])
        self.assertEqual(rc, 0)
        self.assertIn("no hay etapas abiertas", salida)

    def test_informe_avisa_de_etapas_abiertas(self):
        correr([str(self.proy), "inicio", "plan", "--ahora", "2026-10-10T10:00:00"])
        rc, salida, _ = correr([str(self.proy), "informe", "--ahora", "2026-10-10T10:05:00"])
        self.assertEqual(rc, 0)
        self.assertIn("en curso", salida)
        self.assertIn("estimar", salida)

    def test_estimar_solo_rellena_filas_vacias(self):
        ts = lambda h, m: datetime.datetime(2026, 10, 12, h, m).timestamp()
        spec = self.spec
        os.utime(spec / "spec.md", (ts(8, 0), ts(8, 0)))
        (spec / "plan.md").write_text("# plan", encoding="utf-8")
        os.utime(spec / "plan.md", (ts(9, 0), ts(9, 0)))
        (spec / "tasks.md").write_text("# tasks", encoding="utf-8")
        os.utime(spec / "tasks.md", (ts(9, 30), ts(9, 30)))
        # evidencia de implementación: un archivo posterior a tasks.md
        (spec / "quickstart.md").write_text("# quickstart", encoding="utf-8")
        os.utime(spec / "quickstart.md", (ts(11, 0), ts(11, 0)))
        # fila marcada a mano (no debe tocarse)
        correr([str(self.proy), "inicio", "plan", "--ahora", "2026-10-12T08:30:00"])
        correr([str(self.proy), "fin", "plan", "--ahora", "2026-10-12T08:40:00"])

        rc, salida, _ = correr([str(self.proy), "estimar", "--ahora", "2026-10-12T12:00:00"])
        self.assertEqual(rc, 0)
        self.assertIn("simulación", salida)
        self.assertNotIn("tareas", self.leer_estado())          # la simulación no toca el estado
        self.assertNotIn("estimado", self.leer_metrics())        # ni el informe

        rc, salida, _ = correr([str(self.proy), "estimar", "--escribir",
                                "--ahora", "2026-10-12T12:00:00"])
        self.assertEqual(rc, 0)
        etapas = self.leer_estado()
        # la fila ya marcada no se toca
        self.assertEqual(etapas["plan"]["inicio"][:16], "2026-10-12T08:30")
        self.assertEqual(etapas["plan"]["fin"][:16], "2026-10-12T08:40")
        self.assertEqual(etapas["plan"].get("nota", ""), "")
        # las vacías se estiman por fecha de archivo, con inicio = fin de la etapa previa
        self.assertIn("estimado por fechas de archivo", etapas["especificar"]["nota"])
        self.assertEqual(etapas["especificar"]["fin"][:16], "2026-10-12T08:00")
        self.assertEqual(etapas["tareas"]["inicio"][:16], "2026-10-12T08:40")
        self.assertEqual(etapas["tareas"]["fin"][:16], "2026-10-12T09:30")
        self.assertEqual(etapas["implementar"]["inicio"][:16], "2026-10-12T09:30")
        self.assertEqual(etapas["implementar"]["fin"][:16], "2026-10-12T11:00")
        self.assertIn("estimado por fechas de archivo", self.leer_metrics())
        # ya no queda nada que estimar
        rc, salida, _ = correr([str(self.proy), "estimar"])
        self.assertIn("nada que estimar", salida)

    def test_estimar_no_inventa_etapas_sin_evidencia(self):
        # Solo existe spec.md (lo crea setUp): hay evidencia de "especificar", ninguna de las demás.
        rc, salida, _ = correr([str(self.proy), "estimar", "--escribir"])
        self.assertEqual(rc, 0)
        etapas = json.loads((self.proy / ".ld" / "tiempos.json").read_text()
                            )["specs"]["specs/003-parametric-transfer-limits"]["etapas"]
        self.assertIn("especificar", etapas)
        for clave in ("clarificar", "plan", "tareas", "checklist", "analizar",
                      "implementar", "converger"):
            self.assertNotIn(clave, etapas)


if __name__ == "__main__":
    unittest.main()