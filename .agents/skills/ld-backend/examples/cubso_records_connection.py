"""Fábrica de conexión ODBC desde una variable de entorno secreta."""

import os

import pyodbc
from django.core.exceptions import ImproperlyConfigured


def open_records_connection():
    """Abre una conexión ODBC configurada fuera del repositorio."""
    connection_string = os.environ.get("LD_RECORDS_ODBC_CONNECTION_STRING")
    if not connection_string:
        raise ImproperlyConfigured(
            "Configura la variable secreta LD_RECORDS_ODBC_CONNECTION_STRING"
        )
    return pyodbc.connect(connection_string)
