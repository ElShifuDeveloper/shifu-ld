"""Proveedor de registros paginados de Cubso mediante un procedimiento tipado."""

from django.conf import settings
from django.core.signing import BadSignature, dumps, loads
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

CURSOR_SALT = "ld-backend.cubso-records.v1"
MAX_PAGE_SIZE = 500


def _decode_cursor(cursor):
    if cursor is None:
        return None
    if not isinstance(cursor, str):
        raise ValueError("cursor no válido")
    try:
        payload = loads(cursor, salt=CURSOR_SALT)
    except BadSignature as error:
        raise ValueError("cursor no válido") from error
    if (
        not isinstance(payload, dict)
        or type(payload.get("version")) is not int
        or payload["version"] != 1
        or type(payload.get("after_id")) is not int
    ):
        raise ValueError("cursor no válido")
    return payload["after_id"]


def page_cubso_records(request, limit, cursor):
    """Devuelve registros Cubso tipados y una continuación firmada para el cursor."""
    if type(limit) is not int or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError("limit debe estar entre 1 y 500")
    after_id = _decode_cursor(cursor)
    connection_factory_path = getattr(settings, "LD_RECORDS_CONNECTION_FACTORY", "")
    if not connection_factory_path:
        raise ImproperlyConfigured(
            "Configura LD_RECORDS_CONNECTION_FACTORY con una fábrica de conexión SQL Server"
        )

    connection = import_string(connection_factory_path)()
    try:
        database_cursor = connection.cursor()
        try:
            database_cursor.execute(
                "EXEC dbo.uspCubsoListarPaginaTipada "
                "@AfterCubsoId = ?, @PageSize = ?",
                (after_id, limit + 1),
            )
            rows = database_cursor.fetchmany(limit + 1)
        finally:
            database_cursor.close()
    finally:
        connection.close()

    has_more = len(rows) > limit
    page_rows = rows[:limit]
    items = [
        {
            "id": row[0],
            "code": row[1],
            "description": row[2],
            "price": row[3],
        }
        for row in page_rows
    ]
    next_cursor = (
        dumps(
            {"version": 1, "after_id": page_rows[-1][0]},
            salt=CURSOR_SALT,
        )
        if has_more
        else None
    )
    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
