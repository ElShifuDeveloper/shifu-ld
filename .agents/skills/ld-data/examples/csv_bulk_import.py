"""Interpreta registros CSV y envía lotes acotados a un cursor DB-API."""

import csv
import itertools
import io


def validate_rows(rows, expected_columns):
    """Valida la estructura como ejemplo; añade validaciones de dominio y tipo en la aplicación."""
    for row_number, row in enumerate(rows, start=1):
        if len(row) != len(expected_columns):
            raise ValueError(f"La fila {row_number} tiene una cantidad de columnas inesperada")


def insert_csv(binary_file, cursor, insert_sql, expected_header, batch_size=1000):
    text_file = io.TextIOWrapper(binary_file, encoding="utf-8-sig", newline="")
    reader = csv.reader(text_file, delimiter=",")
    header = next(reader, None)
    if header != expected_header:
        raise ValueError("La cabecera del CSV no es la esperada")

    count = 0
    while rows := list(itertools.islice(reader, batch_size)):
        validate_rows(rows, expected_header)  # Add domain-specific validation.
        cursor.executemany(insert_sql, rows)
        count += len(rows)
    return count
