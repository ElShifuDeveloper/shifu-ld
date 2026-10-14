"""Ejecuta: python test_realtime.py"""
import json
import unittest

from ws_auth import emitir_token, verificar_token
from ws_messages import LimiteTasa, MensajeInvalido, validar_mensaje

SECRETO = b"secreto-de-prueba"


class PruebasMensajes(unittest.TestCase):
    def test_chat_valido_anade_usuario_del_servidor(self):
        # el usuario enviado por el cliente se ignora: el servidor pone el autenticado
        r = validar_mensaje(json.dumps({"type": "chat.message", "text": " hola ", "user": "falso"}), "ana", ahora=1)
        self.assertEqual(r, {"type": "chat.message", "user": "ana", "sent_at": 1, "text": "hola"})

    def test_rechazos(self):
        casos = {
            b"bytes": "solo_texto",
            "no json": "json_invalido",
            "[1]": "json_invalido",
            json.dumps({"type": "otro"}): "tipo_desconocido",
            json.dumps({"type": "chat.message", "text": "  "}): "texto_invalido",
            json.dumps({"type": "chat.message", "text": "x" * 501}): "texto_invalido",
            json.dumps({"type": "chat.message", "text": "x" * 3000}): "mensaje_demasiado_grande",
            json.dumps({"type": "paint.point", "x": 5, "y": 5, "color": "red"}): "color_invalido",
            json.dumps({"type": "paint.point", "x": 5, "y": 5, "color": "#12345"}): "color_invalido",
            json.dumps({"type": "paint.point", "x": 5000, "y": 5, "color": "#112233"}): "punto_invalido",
            json.dumps({"type": "paint.point", "x": True, "y": 5, "color": "#112233"}): "punto_invalido",
            json.dumps({"type": "paint.point", "x": "5", "y": 5, "color": "#112233"}): "punto_invalido",
        }
        for crudo, codigo in casos.items():
            with self.subTest(crudo=crudo):
                with self.assertRaises(MensajeInvalido) as e:
                    validar_mensaje(crudo, "ana")
                self.assertEqual(str(e.exception), codigo)

    def test_punto_valido(self):
        r = validar_mensaje(json.dumps({"type": "paint.point", "x": 10, "y": 20, "color": "#a1B2c3"}), "ana", ahora=2)
        self.assertEqual((r["x"], r["y"], r["color"], r["user"]), (10, 20, "#a1B2c3", "ana"))

    def test_xss_viaja_como_texto_no_se_interpreta_en_el_servidor(self):
        r = validar_mensaje(json.dumps({"type": "chat.message", "text": "<img src=x onerror=alert(1)>"}), "ana")
        self.assertEqual(r["text"], "<img src=x onerror=alert(1)>")  # el cliente debe usar textContent

    def test_limite_de_tasa(self):
        t = [0.0]
        lim = LimiteTasa(por_segundo=2, rafaga=3, reloj=lambda: t[0])
        self.assertEqual([lim.permitir() for _ in range(4)], [True, True, True, False])
        t[0] = 1.0  # 1 s repone 2 fichas
        self.assertEqual([lim.permitir() for _ in range(3)], [True, True, False])


class PruebasToken(unittest.TestCase):
    def test_ida_y_vuelta(self):
        t = emitir_token(SECRETO, "ana", 60, ahora=1000)
        self.assertEqual(verificar_token(SECRETO, t, ahora=1030), "ana")

    def test_caducado(self):
        t = emitir_token(SECRETO, "ana", 60, ahora=1000)
        self.assertIsNone(verificar_token(SECRETO, t, ahora=1061))

    def test_alterado_o_secreto_distinto(self):
        t = emitir_token(SECRETO, "ana", 60, ahora=1000)
        carga, firma = t.split(".")
        otra = emitir_token(SECRETO, "root", 60, ahora=1000).split(".")[0]
        self.assertIsNone(verificar_token(SECRETO, otra + "." + firma, ahora=1001))
        self.assertIsNone(verificar_token(b"otro", t, ahora=1001))

    def test_basura(self):
        for t in ["", "abc", "a.b", "a.b.c", None, "....", "e30.e30"]:
            with self.subTest(t=t):
                self.assertIsNone(verificar_token(SECRETO, t, ahora=1))


if __name__ == "__main__":
    unittest.main()
