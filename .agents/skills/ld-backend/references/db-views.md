# Vistas Django sobre procedimientos almacenados

Ejemplo: [django_views.py](../examples/django_views.py) (consulta de stock y grabado de una orden, adaptado de
appDemo14). appDemo14 no usa modelos Django (`models.py` vacío): la vista delega en `clienteSQL`. Para pantallas
CRUD completas, ver [ld-crud](../../ld-crud/SKILL.md).

## Configuración

```python
LD_DB_CONFIG_PATH = BASE_DIR / "config" / "Config_BD.txt"
LD_DB_LOG_PATH = BASE_DIR / "logs" / "database.log"
```

El archivo de configuración (driver, servidor, usuario, clave, base) queda fuera del repositorio. La vista crea
`clienteSQL(str(LD_DB_CONFIG_PATH), str(LD_DB_LOG_PATH))`: es el cliente real de los demos
(`Modulos/modAccesoDatos.py`), cuyo contrato está en [cliente-sql.md](../../ld-data/references/cliente-sql.md). Añade a
cada punto de acceso la autenticación y la auditoría de la aplicación ([ld-security-session](../../ld-security-session/SKILL.md)).

```python
from django.urls import path
from . import django_views

urlpatterns = [
    path("ObtenerStockProductoPorId", django_views.ObtenerStockProductoPorId),
    path("GrabarOrden", django_views.GrabarOrden),
]
```

## Qué responde la vista (estilo LD: texto)

- **Existencias:** el SP devuelve el stock como número (aplica `ISNULL`). Texto con el número → `200`; `""` (el producto no
  existe) → `404`; `None` (falló la consulta, ya quedó en el log) → `502`.
- **Grabar orden:** valida método, `Data` y tamaño antes de llamar al SP. Éxito: `idOrden|fecha`. Los riesgos conocidos de
  `uspOrdenGrabarPyCsv` (precio enviado por el cliente, sin control de stock, `@@IDENTITY`) están en el
  [análisis](../../ld-data/references/stored-procedures-review.md).
- **Consultas de muchos registros:** por viajes de N registros con `ContarRegistros` y `ObtenerBloqueRegistros`
  (`uspCubsoPaginarCsvPy`): ver [ld-transferencia](../../ld-transferencia/SKILL.md).
- **Texto, no JSON.** La vista devuelve la cadena que arma el SP (`...Csv`, `...PyCsv`); el cliente la separa con
  `split`. JSON solo para servicios que consumen terceros ([ld-realtime](../../ld-realtime/SKILL.md)).
