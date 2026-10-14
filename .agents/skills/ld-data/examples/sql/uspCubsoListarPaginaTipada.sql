-- Página de registros de dbo.Cubso con columnas tipadas y paginación por clave.
-- Versión portable del procedimiento usado por ld-backend/examples/cubso_records_provider.py:
-- misma lógica, con CREATE OR ALTER (SQL Server 2016 SP1+) y sin USE ni nombre de base fijos.
-- Selecciona la base de datos destino antes de ejecutar y despliega solo con autorización
-- explícita para ese entorno.
--
-- Contrato:
--   @AfterCubsoId : clave de continuación; NULL devuelve la primera página.
--   @PageSize     : 1 a 501 (el proveedor pide limite + 1 con limite <= 500 para calcular has_more).
--   Resultado     : un conjunto con CubsoId, Codigo, Descripcion, Precio, ordenado por CubsoId.
--   Supuestos     : CubsoId es único (clave primaria) y dbo.Cubso tiene esas cuatro columnas;
--                   Codigo, Descripcion y Precio pueden ser NULL y el consumidor debe tolerarlo.
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE dbo.uspCubsoListarPaginaTipada
    @AfterCubsoId int,
    @PageSize int
AS
BEGIN
    SET NOCOUNT ON;

    IF @PageSize IS NULL OR @PageSize < 1 OR @PageSize > 501
        THROW 50001, 'PageSize debe estar entre 1 y 501.', 1;

    IF @AfterCubsoId IS NULL
    BEGIN
        SELECT TOP (@PageSize)
            CubsoId,
            Codigo,
            Descripcion,
            Precio
        FROM dbo.Cubso
        ORDER BY CubsoId;
    END
    ELSE
    BEGIN
        SELECT TOP (@PageSize)
            CubsoId,
            Codigo,
            Descripcion,
            Precio
        FROM dbo.Cubso
        WHERE CubsoId > @AfterCubsoId
        ORDER BY CubsoId;
    END
END
GO
