-- Página de registros de Cubso con columnas tipadas y paginación por clave (PostgreSQL 14+).
-- Equivalente en PL/pgSQL de examples/sql/uspCubsoListarPaginaTipada.sql (T-SQL).
-- Se declara sin comillas, así que PostgreSQL la guarda en minúsculas: se llama como
--   SELECT uspCubsoListarPaginaTipada(%s, %s)
--
-- Contrato:
--   p_after_cubso_id : clave de continuación; NULL devuelve la primera página.
--   p_page_size      : 1 a 501 (el proveedor pide límite + 1 con límite <= 500 para calcular has_more).
--   Resultado        : un conjunto con CubsoId, Codigo, Descripcion, Precio, ordenado por CubsoId.
--   Supuestos        : CubsoId es único (clave primaria); Codigo, Descripcion y Precio pueden ser NULL.
-- Aplica este script a la base solo con autorización explícita para ese entorno.
CREATE OR REPLACE FUNCTION uspCubsoListarPaginaTipada(
    p_after_cubso_id integer,
    p_page_size integer
)
RETURNS TABLE (CubsoId integer, Codigo text, Descripcion text, Precio numeric)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_page_size IS NULL OR p_page_size < 1 OR p_page_size > 501 THEN
        RAISE EXCEPTION 'PageSize debe estar entre 1 y 501.' USING ERRCODE = '22023';
    END IF;

    RETURN QUERY
    SELECT c.CubsoId, c.Codigo, c.Descripcion, c.Precio
    FROM Cubso AS c
    WHERE p_after_cubso_id IS NULL OR c.CubsoId > p_after_cubso_id
    ORDER BY c.CubsoId
    LIMIT p_page_size;
END;
$$;