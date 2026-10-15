"""clienteSQL para PostgreSQL con psycopg 3: gemelo de `base/modAccesoDatos.py`.

Misma API pública que el cliente de los demos (clase `clienteSQL` y sus métodos), para que las
vistas no cambien: `con.EjecutarComandoCadena("uspX", "Param", valor)`. El formato LD (cadenas
delimitadas que arma la función) y el contrato `None` = falló / `""` = sin datos o NULL son iguales.

Diferencias de motor frente a SQL Server (detalle en references/postgres.md):
  * marcadores `%s` (no `?`) y llamada `SELECT funcion(%s)` / `CALL procedimiento(%s)`;
  * no hay `fetchval`: se usa `fetchone()[0]`;
  * no hay `nextset()`: `EjecutarComandoListas`/`EjecutarComandoVariosDF` no se implementan;
  * un error aborta la transacción: cada llamada abre su conexión y la cierra;
  * identidad con `INSERT ... RETURNING`, no `SCOPE_IDENTITY()`/`@@IDENTITY`.

Credenciales y rutas siempre desde el archivo de configuración (fuera del repositorio); nunca en código.
"""
import os
import re

import psycopg

from Modulos.modUtilidades import beLog, Log

MODULO = "modAccesoDatos"
RE_OBJETO = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")
RE_PARAMETRO = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class clienteSQL():
    def __init__(self, archivoConfig, archivoLog):
        self.CadenaConexion = ""
        self.ArchivoLog = archivoLog
        try:
            if not os.path.isfile(archivoConfig):
                print("No existe el archivo Config")
                return
            with open(archivoConfig, "r") as file:
                diccionario = {}
                for linea in file.read().splitlines():
                    linea = linea.strip()
                    if linea == "" or "=" not in linea:
                        continue
                    clave, valor = linea.split("=", 1)
                    diccionario[clave.strip()] = valor.strip()
            self.CadenaConexion = "host={0} port={1} dbname={2} user={3} password={4}".format(
                diccionario["servidor"], diccionario.get("puerto", "5432"), diccionario["basedatos"],
                diccionario["usuario"], diccionario["clave"])
            if diccionario.get("sslmode"):
                self.CadenaConexion += " sslmode=" + diccionario["sslmode"]
        except Exception as errorgeneral:
            self._registrar("__init__", errorgeneral)

    def _registrar(self, metodo, error):
        obeLog = beLog(MODULO, "clienteSQL")
        obeLog.setLog(metodo, str(error))
        try:
            Log.saveLog(obeLog, self.ArchivoLog)
        except Exception:
            pass

    def _conectar(self):
        if self.CadenaConexion == "":
            raise RuntimeError("Sin cadena de conexion: revisa el archivo de configuracion")
        return psycopg.connect(self.CadenaConexion)

    @staticmethod
    def _sql_funcion(nombreSP, nombreParametro, valorParametro):
        """Sentencia para llamar a una funcion que devuelve la cadena delimitada (patron LD)."""
        if not isinstance(nombreSP, str) or RE_OBJETO.fullmatch(nombreSP) is None:
            raise RuntimeError("Nombre de funcion invalido: " + str(nombreSP))
        if nombreParametro == "":
            return "SELECT " + nombreSP + "()", []
        if not isinstance(nombreParametro, str) or RE_PARAMETRO.fullmatch(nombreParametro) is None:
            raise RuntimeError("Nombre de parametro invalido: " + str(nombreParametro))
        return "SELECT " + nombreSP + "(%s)", [valorParametro]

    @staticmethod
    def _sql_insert(tabla, campos):
        """INSERT con marcadores `%s`. Valida tabla y columnas contra un patron (no se interpolan valores)."""
        if not isinstance(tabla, str) or RE_OBJETO.fullmatch(tabla) is None:
            raise RuntimeError("Nombre de tabla invalido: " + str(tabla))
        for campo in campos:
            if not isinstance(campo, str) or RE_OBJETO.fullmatch(campo) is None:
                raise RuntimeError("Nombre de columna invalido: " + str(campo))
        marcadores = ",".join(["%s"] * len(campos))
        return "INSERT INTO {0} ({1}) VALUES ({2})".format(tabla, ",".join(campos), marcadores)

    def crearLista(self, cursor, sep=","):
        if cursor.description is None:
            raise RuntimeError("El comando no devolvio un conjunto de filas")
        rpta = [sep.join(campo[0] for campo in cursor.description)]
        for tupla in cursor.fetchall():
            rpta.append(sep.join(str(valor) for valor in tupla))
        return rpta

    def EjecutarComandoUnaLista(self, sql):
        rpta = None
        try:
            with self._conectar() as con:
                with con.cursor() as cmd:
                    cmd.execute(sql)
                    rpta = self.crearLista(cmd)
        except Exception as errorgeneral:
            rpta = None
            self._registrar("EjecutarComandoUnaLista", errorgeneral)
        return rpta

    def EjecutarComandoCadena(self, nombreSP, nombreParametro="", valorParametro="", trx=False):
        rpta = None
        try:
            sql, parametros = clienteSQL._sql_funcion(nombreSP, nombreParametro, valorParametro)
            con = self._conectar()
            try:
                with con.cursor() as cmd:
                    cmd.execute(sql, parametros if parametros else None)
                    fila = cmd.fetchone()
                rpta = "" if fila is None or fila[0] is None else fila[0]
                if trx:
                    con.commit()
            finally:
                con.close()
        except Exception as errorgeneral:
            rpta = None
            self._registrar("EjecutarComandoCadena", errorgeneral)
        return rpta

    def EjecutarComandoFila(self, nombreSP, nombreParametro="", valorParametro=""):
        rpta = None
        try:
            sql, parametros = clienteSQL._sql_funcion(nombreSP, nombreParametro, valorParametro)
            con = self._conectar()
            try:
                with con.cursor() as cmd:
                    cmd.execute(sql, parametros if parametros else None)
                    rpta = cmd.fetchone()
            finally:
                con.close()
            if rpta is None:
                rpta = ""
        except Exception as errorgeneral:
            rpta = None
            self._registrar("EjecutarComandoFila", errorgeneral)
        return rpta

    def EjecutarComandoLista(self, sql):
        rpta = None
        try:
            with self._conectar() as con:
                with con.cursor() as cmd:
                    cmd.execute(sql)
                    rpta = cmd.fetchall()
        except Exception as errorgeneral:
            rpta = None
            self._registrar("EjecutarComandoLista", errorgeneral)
        return rpta

    def EjecutarInsertMasivoLista(self, strTabla, strCampos, lista):
        rpta = None
        try:
            sql = clienteSQL._sql_insert(strTabla, strCampos.split("|"))
            con = self._conectar()
            try:
                with con.cursor() as cmd:
                    cmd.executemany(sql, lista)
                con.commit()
                rpta = "Datos Copiados Correctamente"
            finally:
                con.close()
        except Exception as errorgeneral:
            rpta = "Error: " + str(errorgeneral)
            self._registrar("EjecutarInsertMasivoLista", errorgeneral)
        return rpta

    def EjecutarInsertMasivoCsv(self, strTabla, csv, sepReg=';', sepCampo='|'):
        rpta = None
        try:
            listaInicio = csv.split(sepReg)
            campos = listaInicio[0].split(sepCampo)
            lista = [fila.split(sepCampo) for fila in listaInicio[1:] if fila != ""]
            sql = clienteSQL._sql_insert(strTabla, campos)
            con = self._conectar()
            try:
                with con.cursor() as cmd:
                    cmd.executemany(sql, lista)
                con.commit()
                rpta = "OK"
            finally:
                con.close()
        except Exception as errorgeneral:
            rpta = "Error: " + str(errorgeneral)
            self._registrar("EjecutarInsertMasivoCsv", errorgeneral)
        return rpta

    def ValidarTablaCampos(self, tabla, camposVal):
        rpta = ""
        try:
            if not isinstance(tabla, str) or RE_OBJETO.fullmatch(tabla) is None:
                raise RuntimeError("Nombre de tabla invalido: " + str(tabla))
            with self._conectar() as con:
                with con.cursor() as cmd:
                    cmd.execute("SELECT * FROM " + tabla + " LIMIT 0")
                    campos = [campo[0] for campo in cmd.description]
            camposError = [campo for campo in camposVal if campo not in campos]
            if camposError:
                rpta = "Error - No existen los sgtes campos: " + ",".join(camposError)
        except Exception as errorgeneral:
            rpta = "Error - La Tabla " + str(tabla) + " No existe"
            self._registrar("ValidarTablaCampos", errorgeneral)
        return rpta