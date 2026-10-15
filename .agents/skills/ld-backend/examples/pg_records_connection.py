"""Fábrica de conexión a PostgreSQL desde una variable de entorno secreta (DSN)."""

import os

import psycopg
from django.core.exceptions import ImproperlyConfigured


def open_records_connection():
    """Abre una conexión PostgreSQL configurada fuera del repositorio."""
    dsn = os.environ.get("LD_RECORDS_PG_DSN")
    if not dsn:
        raise ImproperlyConfigured(
            "Configura la variable secreta LD_RECORDS_PG_DSN (host=... dbname=... user=... password=...)"
        )
    return psycopg.connect(dsn)