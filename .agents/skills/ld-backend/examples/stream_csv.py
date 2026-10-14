"""Lee CSV recibido de forma incremental; valida y guarda filas en lotes acotados."""

import csv
import itertools
import io


def validate_rows(rows, expected_columns):
    """Valida la estructura como ejemplo; añade validaciones de dominio y tipo en la aplicación."""
    for row_number, row in enumerate(rows, start=1):
        if len(row) != len(expected_columns):
            raise ValueError(f"La fila {row_number} tiene una cantidad de columnas inesperada")


def import_csv(uploaded_file, cursor, insert_sql, expected_header, batch_size=1000):
    # Elige la codificación y el separador definidos en el contrato cliente/servidor.
    text_file = io.TextIOWrapper(uploaded_file, encoding="utf-8-sig", newline="")
    reader = csv.reader(text_file, delimiter=",")
    header = next(reader, None)
    if header != expected_header:
        raise ValueError("La cabecera del CSV no coincide con las columnas esperadas")

    inserted = 0
    while batch := list(itertools.islice(reader, batch_size)):
        validate_rows(batch, expected_header)  # Aquí van las validaciones propias del proyecto.
        cursor.executemany(insert_sql, batch)
        inserted += len(batch)
    return inserted
