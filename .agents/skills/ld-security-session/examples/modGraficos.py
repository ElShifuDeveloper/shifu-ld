from Modulos.modUtilidades import Generador
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import random

class Captcha():
    def Crear(n,ancho,alto,sizeFuente,colorFondo,nLineas):
        rpta = {}
        buffer = None
        codigo = Generador.Codigo(n)
        img = Image.new("RGBA", (ancho,alto), (0,0,0,0))
        grafico = ImageDraw.Draw(img)
        grafico.rectangle([0, 0, ancho, alto], fill=colorFondo, outline=None, width=1)
        fuente = ImageFont.truetype("arial.ttf", sizeFuente)
        x = 20
        colores = ['red','green','blue','black','orange','brown','pink']
        for i in range(n):
            c = random.randint(0, len(colores)-1)
            y = random.randint(0, alto-30)
            grafico.text((x, y), codigo[i], font = fuente, fill = colores[c])
            x += 40
        for i in range(nLineas):
            x1 = random.randint(0, ancho)
            x2 = random.randint(0, ancho)
            y1 = random.randint(0, alto)
            y2 = random.randint(0, alto)
            c = random.randint(0, len(colores)-1)
            grafico.line([(x1, y1), (x2, y2)], fill = colores[c], width = 1) 
        bytes_arr = BytesIO()
        img.save(bytes_arr, format='PNG')
        buffer = bytes_arr.getvalue()
        rpta = {"Codigo": codigo, "Imagen": buffer}
        return rpta
        