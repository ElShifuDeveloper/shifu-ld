"""Ejemplos de acceso acotado a SQL Server con parámetros posicionales al estilo pyodbc."""


def get_status(connection, order_id):
    """Obtiene un escalar o devuelve None; no lo uses para resultados con varias filas."""
    cursor = connection.cursor()
    try:
        cursor.execute("EXEC dbo.GetOrderStatus @OrderId = ?", (order_id,))
        row = cursor.fetchone()
        return None if row is None else row[0]
    finally:
        cursor.close()


def iterate_order_pages(connection, after_id, page_size=1000):
    """Entrega lotes acotados; el procedimiento debe mantener un orden estable y un cursor."""
    cursor = connection.cursor()
    try:
        cursor.execute(
            "EXEC dbo.GetOrdersAfter @AfterId = ?, @Limit = ?",
            (after_id, page_size),
        )
        while rows := cursor.fetchmany(page_size):
            yield rows
    finally:
        cursor.close()


def execute_bulk_insert(connection, insert_sql, rows):
    """Inserta un iterable acotado en una transacción; quien llama elige el tamaño del lote."""
    cursor = connection.cursor()
    try:
        cursor.executemany(insert_sql, rows)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
