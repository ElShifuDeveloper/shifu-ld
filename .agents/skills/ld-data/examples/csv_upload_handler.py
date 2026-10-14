"""Manejador idempotente de Django para finalizar cargas de texto/CSV de transfer_api.py.

El proyecto debe proporcionar una tabla de recibos con columnas únicas
upload_id, owner_id y record_count, además de una cabecera y una sentencia
INSERT de confianza.
"""

import csv
import itertools
import re

from django.conf import settings
from django.db import connections, transaction

SAFE_TABLE_NAME = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$"
)


def process_completed_upload(upload_id, owner_id, assembled_items):
    """Importa una vez por carga los elementos CSV de texto; deja los binarios en el almacenamiento final."""
    text_items = [
        (item, path)
        for item, path in assembled_items
        if item["kind"] == "text"
    ]
    if not text_items:
        return

    expected_header = getattr(settings, "LD_CSV_IMPORT_EXPECTED_HEADER", None)
    insert_sql = getattr(settings, "LD_CSV_IMPORT_INSERT_SQL", "")
    receipt_table = getattr(settings, "LD_CSV_IMPORT_RECEIPT_TABLE", "")
    database_alias = getattr(settings, "LD_CSV_IMPORT_DATABASE", "default")
    batch_size = getattr(settings, "LD_CSV_IMPORT_BATCH_SIZE", 1000)

    if not isinstance(expected_header, (list, tuple)) or not expected_header:
        raise RuntimeError("Configura LD_CSV_IMPORT_EXPECTED_HEADER")
    if not isinstance(insert_sql, str) or not insert_sql.strip():
        raise RuntimeError("Configura una sentencia de confianza en LD_CSV_IMPORT_INSERT_SQL")
    if not isinstance(receipt_table, str) or not SAFE_TABLE_NAME.fullmatch(receipt_table):
        raise RuntimeError("Configura un nombre válido en LD_CSV_IMPORT_RECEIPT_TABLE")
    if type(batch_size) is not int or batch_size <= 0:
        raise RuntimeError("LD_CSV_IMPORT_BATCH_SIZE debe ser un entero positivo")

    connection = connections[database_alias]
    total_rows = 0
    with transaction.atomic(using=database_alias):
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT 1 FROM {receipt_table} WHERE upload_id = %s",
                [upload_id],
            )
            if cursor.fetchone():
                return

            for item, path in text_items:
                if not item["name"].lower().endswith(".csv"):
                    raise ValueError(f"El elemento de texto no es compatible: {item['name']}")
                with path.open("r", encoding="utf-8-sig", newline="") as source:
                    reader = csv.reader(source)
                    header = next(reader, None)
                    if header != list(expected_header):
                        raise ValueError(f"La cabecera CSV de {item['name']} no es la esperada")

                    while rows := list(itertools.islice(reader, batch_size)):
                        if any(len(row) != len(expected_header) for row in rows):
                            raise ValueError(f"Una fila de {item['name']} tiene una cantidad incorrecta de columnas")
                        cursor.executemany(insert_sql, rows)
                        total_rows += len(rows)

            cursor.execute(
                f"INSERT INTO {receipt_table} (upload_id, owner_id, record_count) "
                "VALUES (%s, %s, %s)",
                [upload_id, owner_id, total_rows],
            )
