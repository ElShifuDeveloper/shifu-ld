"""Pruebas de modSeguridadWeb sin Django instalado (simula django.shortcuts).
Ejecuta: python test_modSeguridadWeb.py"""
import sys, tempfile, os, unittest
from unittest import mock
import types
d=types.ModuleType('django'); sh=types.ModuleType('django.shortcuts'); sh.render=None; d.shortcuts=sh
sys.modules.update({'django':d,'django.shortcuts':sh})
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modSeguridadWeb as m

class R:
    def __init__(s, ses, **meta): s.session=ses; s.META=meta; s.path="/x\nfalso"; s.method="GET"

class T(unittest.TestCase):
    def setUp(s):
        p=mock.patch.object(m,"render",lambda req,url,status=200: ("LOGIN",url,status)); p.start(); s.addCleanup(p.stop)
    def test_auth(s):
        v=m.autenticacion("Usuario","L.html")(lambda r: "OK")
        s.assertEqual(v(R({"Usuario":"ana"})),"OK")
        s.assertEqual(v(R({})),("LOGIN","L.html",200))
        s.assertEqual(v(R({"Usuario":""})),("LOGIN","L.html",200))   # antes: None
        s.assertEqual(m.autenticacion("Usuario","L.html",401)(lambda r:"OK")(R({}))[2],401)
    def test_audit(s):
        f=os.path.join(tempfile.mkdtemp(),"a.txt")
        v=m.auditoria(f,"Usuario")(lambda r:"OK")
        s.assertEqual(v(R({"Usuario":"ana"},REMOTE_ADDR="1.1.1.1",HTTP_X_FORWARDED_FOR="9.9.9.9")),"OK")
        t=open(f).read(); s.assertIn("IP Cliente: 1.1.1.1",t); s.assertNotIn("9.9.9.9",t)
        s.assertEqual(t.count("Ruta:"),1); s.assertNotIn("\nfalso",t)
        v2=m.auditoria(f,"Usuario",confiarProxy=True)(lambda r:"OK"); v2(R({},REMOTE_ADDR="1.1.1.1",HTTP_X_FORWARDED_FOR="9.9.9.9, 2.2.2.2"))
        s.assertIn("IP Cliente: 9.9.9.9",open(f).read())
        s.assertEqual(v(R({})),"OK")  # sin usuario ni IP: antes TypeError
    def test_audit_fallo_no_cae(s):
        v=m.auditoria("/no/existe/a.txt","Usuario")(lambda r:"OK")
        with s.assertLogs(m.logger,"ERROR"): s.assertEqual(v(R({})),"OK")
unittest.main()
