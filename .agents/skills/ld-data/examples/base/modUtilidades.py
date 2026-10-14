from datetime import datetime
import hashlib, random, re

class beLog:
    def __init__(self, modulo, clase):
        self.FechaHora = str(datetime.now())
        self.Modulo = modulo
        self.Clase = clase
    
    def setLog(self, metodo, error):
        self.Metodo = metodo
        self.Error = error
    
    def printLog(self):
        print("Fecha y Hora:", self.FechaHora)
        print("Modulo:", self.Modulo)
        print("Clase:", self.Clase)
        print("Metodo:", self.Metodo)
        print("Error:", self.Error)
        
class Log:
    def saveLog(obeLog, archivo):
        with open(archivo, "a") as file:
            file.write("Fecha y Hora: " + obeLog.FechaHora + "\n")
            file.write("Modulo: " + obeLog.Modulo + "\n")
            file.write("Clase: " + obeLog.Clase + "\n")
            file.write("Metodo: " + obeLog.Metodo + "\n")
            file.write("Error: " + obeLog.Error + "\n")
            file.write("_" * 50 + "\n")

class Seguridad():
    def CifrarSha256Hex(dataSinCifrar):
        bytesSinCifrar = bytes(dataSinCifrar,"UTF-8")
        objCifrado = hashlib.sha256()
        objCifrado.update(bytesSinCifrar)
        cadenaCifradaHex = objCifrado.hexdigest()
        return cadenaCifradaHex

class Generador():
    def Codigo(n):
        S = ""
        for i in range(n):
            x = random.randint(1, 2)
            if(x==1):            
                S+= chr(random.randint(65, 90))
            else:
                S+= chr(random.randint(48, 57))
        return S

class JSON():
    def SerializarCsv(csv, sepCampo='|', sepReg=';'):
        rpta = ""
        lista = csv.split(sepReg)
        nRegistros = len(lista)
        cabeceras = lista[0].split(sepCampo)
        nCampos = len(cabeceras)
        if(nRegistros>0):
            rpta = "["
            for i in range(1, nRegistros):
                campos = lista[i].split(sepCampo)
                rpta += "{"
                for j in range(nCampos):
                    rpta += "\""
                    rpta += cabeceras[j]
                    rpta += "\":"
                    patronDecimal = r"^-?\d+\.\d+$"
                    esNumero = (campos[j].isnumeric() or re.match(patronDecimal, campos[j]))
                    if(not esNumero):
                        rpta += "\""
                        rpta += campos[j]
                        rpta += "\""
                    else:
                        rpta += campos[j]
                    if(j<nCampos-1):
                        rpta += ","
                rpta += "}"
                if(i<nRegistros-1):
                    rpta += ","
            rpta += "]"
        return rpta

class XML():
    def SerializarCsv(csv, sepCampo='|', sepReg=';', raiz='tabla', elemento='registro'):
        rpta = ""
        lista = csv.split(sepReg)
        nRegistros = len(lista)
        cabeceras = lista[0].split(sepCampo)
        nCampos = len(cabeceras)
        if(nRegistros>0):
            rpta = "<?xml version='1.0' encoding='utf-8'?>"
            rpta += "<" + raiz + ">";
            for i in range(1, nRegistros):
                campos = lista[i].split(sepCampo)
                rpta += "<" + elemento + ">"
                for j in range(nCampos):
                    rpta += "<"
                    rpta += cabeceras[j]
                    rpta += ">"
                    rpta += campos[j]
                    rpta += "</"
                    rpta += cabeceras[j]
                    rpta += ">"
                rpta += "</" + elemento + ">"
            rpta += "</" + raiz + ">"
        return rpta