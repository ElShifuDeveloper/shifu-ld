import os
import re
import time
import pyodbc as db
import pandas as pd
from Modulos.modUtilidades import beLog, Log

MODULO = "modAccesoDatos"
RE_PROCEDIMIENTO = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")
RE_PARAMETRO = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Codigos SQL de 2 digitos/letras del driver que suelen resolverse solos: 08 problema
# de conexion, 28 error de logon transitorio, 40 bloqueo o cambio de datos, HY timeout.
# El resto (42 sintaxis, 2300 clave duplicada, 37 obj. inexistente) se reporta en el
# primer intento: reintentar no cambia nada y solo hace mas lenta la demo.
ERRORES_TRANSITORIOS = ("08", "28", "40", "HY")


class clienteSQL():


    def __init__(self, archivoConfig, archivoLog, lanzarErrores=False, reintentos=2):
        self.CadenaConexion = ""
        self.ArchivoLog = archivoLog
        self.ArchivoConfig = archivoConfig
        self.conexion = None
        self.LanzarErrores = lanzarErrores
        self.Reintentos = reintentos
        try:
            if(os.path.isfile(archivoConfig)):
                with open(archivoConfig, "r") as file:
                    lineas = file.read().split("\n")
                diccionario = {}
                for linea in lineas:
                    linea = linea.strip()
                    if(linea == "" or "=" not in linea):
                        continue
                    clave, valor = linea.split("=", 1)
                    diccionario[clave.strip()] = valor.strip()
                self.CadenaConexion = "driver={0};server={1};uid={2};pwd={3};database={4}".format(diccionario["driver"], diccionario["servidor"], diccionario["usuario"], diccionario["clave"], diccionario["basedatos"])
            else:
                self._registrar("__init__", RuntimeError("No existe el archivo Config: " + str(archivoConfig)))
        except Exception as errorgeneral:
            self._registrar("__init__", errorgeneral)

    def _registrar(self, metodo, error):
        obeLog = beLog(MODULO, "clienteSQL")
        obeLog.setLog(metodo, str(error))
        try:
            Log.saveLog(obeLog, self.ArchivoLog)
        except Exception:
            pass
        if(self.LanzarErrores):
            raise error

    def _abrir_conexion(self):
        if(self.CadenaConexion == ""):
            raise RuntimeError("Sin cadena de conexion: revisa " + str(self.ArchivoConfig))
        return db.connect(self.CadenaConexion)

    def _es_error_transitorio(self, error):
        # pyodbc pone el SQLSTATE en args[0] y suele repetirlo entre corchetes al
        # principio del mensaje (args[1]), asi que se mira el prefijo de ambos.
        for argumento in getattr(error, "args", ())[:2]:
            coincidencia = re.match(r"\[?([0-9A-Za-z]{5})", str(argumento))
            if(coincidencia is not None and coincidencia.group(1)[:2].upper() in ERRORES_TRANSITORIOS):
                return True
        texto = str(error).lower()
        return any(palabra in texto for palabra in ("login", "timeout", "timed out", "connection", "not open", "closed"))

    def _descartar_conexion(self):
        # La conexion en memoria ya no sirve: se cierra y se vuelve a abrir en el
        # siguiente intento, o en la proxima llamada si se agotan los reintentos.
        if(self.conexion is not None):
            self._rollback()
            try:
                self.conexion.close()
            except Exception:
                pass
            self.conexion = None

    def _ejecutar(self, sql, parametros=None):
        for intento in range(self.Reintentos + 1):
            try:
                if(self.conexion is None):
                    self.conexion = self._abrir_conexion()
                cursor = self.conexion.cursor()
                try:
                    if(parametros is None):
                        cursor.execute(sql)
                    else:
                        cursor.execute(sql, parametros)
                except Exception:
                    cursor.close()
                    raise
                return cursor
            except Exception as error:
                self._descartar_conexion()
                if(intento >= self.Reintentos or not self._es_error_transitorio(error)):
                    raise
                time.sleep(0.2 * (intento + 1))

    def cerrar_conexion(self):
        if(self.conexion is not None):
            try:
                self.conexion.close()
            finally:
                self.conexion = None

    def _rollback(self):
        if(self.conexion is not None):
            try:
                self.conexion.rollback()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, traza):
        self.cerrar_conexion()
        return False

    def _sql_procedimiento(self, nombreSP, nombreParametro, valorParametro):
        if nombreParametro == "":
            return nombreSP, []
        if not isinstance(nombreSP, str) or RE_PROCEDIMIENTO.fullmatch(nombreSP) is None:
            raise RuntimeError("Nombre de procedimiento invalido: " + str(nombreSP))
        if not isinstance(nombreParametro, str) or RE_PARAMETRO.fullmatch(nombreParametro) is None:
            raise RuntimeError("Nombre de parametro invalido: " + str(nombreParametro))
        return "exec {0} @{1}=?".format(nombreSP, nombreParametro), [valorParametro]

    def _ejecutar_procedimiento(self, nombreSP, nombreParametro, valorParametro):
        sql, parametros = self._sql_procedimiento(nombreSP, nombreParametro, valorParametro)
        return self._ejecutar(sql, parametros if parametros else None)

    def crearLista(self, cursor, sep=","):
        if(cursor.description is None):
            raise RuntimeError("El comando no devolvio un conjunto de filas")
        rpta = [sep.join([cabecera[0] for cabecera in cursor.description])]
        for tupla in cursor.fetchall():
            rpta.append(sep.join([str(campo) for campo in tupla]))
        return rpta

    def crearDataFrameDesdeCursor(self, cursor):
        if(cursor.description is None):
            raise RuntimeError("El comando no devolvio un conjunto de filas")
        cabeceras = [cabecera[0] for cabecera in cursor.description]
        return pd.DataFrame.from_records(cursor.fetchall(), columns=cabeceras)

    def EjecutarComandoUnaLista(self, sql, parametros=None, sep=","):
        rpta = None
        try:
            cursor = self._ejecutar(sql, parametros)
            try:
                rpta = self.crearLista(cursor, sep)
            finally:
                cursor.close()
        except Exception as errorgeneral:
            self._rollback()
            rpta = None
            self._registrar("EjecutarComandoUnaLista", errorgeneral)
        return rpta

    def EjecutarComandoListas(self, sql, parametros=None, sep=","):
        rpta = None
        try:
            cursor = self._ejecutar(sql, parametros)
            try:
                rpta = [self.crearLista(cursor, sep)]
                while(cursor.nextset()):
                    if(cursor.description is not None):
                        rpta.append(self.crearLista(cursor, sep))
            finally:
                cursor.close()
        except Exception as errorgeneral:
            self._rollback()
            rpta = None
            self._registrar("EjecutarComandoListas", errorgeneral)
        return rpta

    def EjecutarComandoCadena(self, nombreSP, nombreParametro="", valorParametro=None, trx=False):
        rpta = None
        try:
            cursor = self._ejecutar_procedimiento(nombreSP, nombreParametro, valorParametro)
            try:
                rpta = cursor.fetchval()
                if(trx == True):
                    self.conexion.commit()
            finally:
                cursor.close()
            if(rpta is None):
                rpta = ""
        except Exception as errorgeneral:
            self._rollback()
            rpta = None
            self._registrar("EjecutarComandoCadena", errorgeneral)
        return rpta

    def EjecutarComandoFila(self, nombreSP, nombreParametro="", valorParametro=None, trx=False):
        rpta = None
        try:
            cursor = self._ejecutar_procedimiento(nombreSP, nombreParametro, valorParametro)
            try:
                rpta = cursor.fetchone()
                if(trx == True):
                    self.conexion.commit()
            finally:
                cursor.close()
        except Exception as errorgeneral:
            self._rollback()
            rpta = None
            self._registrar("EjecutarComandoFila", errorgeneral)
        return rpta

    def EjecutarComandoDF(self, nombreSP, nombreParametro="", valorParametro=None, trx=False):
        df = None
        try:
            cursor = self._ejecutar_procedimiento(nombreSP, nombreParametro, valorParametro)
            try:
                df = self.crearDataFrameDesdeCursor(cursor)
                if(trx == True):
                    self.conexion.commit()
            finally:
                cursor.close()
        except Exception as errorgeneral:
            self._rollback()
            df = None
            self._registrar("EjecutarComandoDF", errorgeneral)
        return df

    def EjecutarComandoVariosDF(self, nombreSP, nombreParametro="", valorParametro=None, trx=False):
        rpta = None
        try:
            cursor = self._ejecutar_procedimiento(nombreSP, nombreParametro, valorParametro)
            try:
                rpta = [self.crearDataFrameDesdeCursor(cursor)]
                while(cursor.nextset()):
                    if(cursor.description is not None):
                        rpta.append(self.crearDataFrameDesdeCursor(cursor))
                if(trx == True):
                    self.conexion.commit()
            finally:
                cursor.close()
        except Exception as errorgeneral:
            self._rollback()
            rpta = None
            self._registrar("EjecutarComandoVariosDF", errorgeneral)
        return rpta
