# Modo A (sistema nuevo) y Modo B (sistema existente)

Detalle de los dos recorridos del [coordinador](../SKILL.md).

## Modo A: sistema nuevo

### 1. Entender el producto

Determina, con preguntas breves cuando falte información:

- necesidad que resuelve y usuarios principales;
- tareas esenciales y alcance del primer entregable;
- datos que se crean, consultan o transfieren, y quién es su fuente;
- autenticación, roles, permisos y datos sensibles;
- destino de ejecución e integraciones existentes, si ya se conocen;
- criterios que permitirán aceptar el MVP.

No inventes un dominio de negocio ni agregues funciones de demostración para
llenar vacíos. Separa lo imprescindible del MVP de las ideas posteriores.

### 2. Acordar el contrato vertical

Para cada tarea prioritaria, documenta lo suficiente para coordinar las capas:

| Aspecto | Definición necesaria |
|---|---|
| Interacción | Actor, acción, estado inicial y resultado visible |
| Datos | Entidades/campos necesarios, origen, nulabilidad y reglas |
| API | Operación, parámetros, respuesta, errores y autorización |
| Límites | Volumen, tamaños, formatos, orden, concurrencia o idempotencia que apliquen |
| Aceptación | Entrada y resultado que puedan probarse |

No rellenes aspectos irrelevantes con complejidad innecesaria. Para decisiones
pendientes con impacto importante, ofrece opciones y espera confirmación.

### 3. Implementar por recorrido de usuario

1. **Diseño (`ld-design`):** define navegación, contenido, estados y accesibilidad
   de las tareas acordadas, respetando el sistema visual del proyecto.
2. **Datos (`ld-data`):** inspecciona o diseña el modelo/fuente, consultas,
   transacciones, migraciones y políticas de nulos según los contratos.
3. **Servidor (`ld-backend`):** implementa las operaciones, validación,
   autorización, errores y adaptación a la fuente de datos.
4. **Navegador (`ld-frontend`):** implementa los flujos y estados consumiendo el
   contrato real del servidor; no inventa endpoints ni formatos.
5. **Integración:** ejecuta pruebas focalizadas y un recorrido de aceptación
   que atraviese las capas; actualiza documentación directamente relacionada.

El orden no exige terminar una capa entera antes de otra. Diseño y exploración
de fuentes pueden avanzar en paralelo si no compiten por una decisión común;
la interfaz no debe fijar un contrato de API antes de acordarlo.

### 4. Entrega

Resume qué quedó funcionando, decisiones/supuestos relevantes, validaciones
ejecutadas y pendientes que impidan considerar completo el MVP. Presenta los
archivos o cambios importantes y el siguiente paso concreto. No presentes
recomendaciones o mocks como si fueran integraciones reales.

## Modo B: sistema existente

1. Localiza el punto de entrada de la función, sus consumidores, contratos,
   fuente de datos, configuración, permisos, pruebas y documentación relacionada.
2. Reproduce el comportamiento actual cuando sea necesario y distingue defectos
   confirmados de riesgos hipotéticos.
3. Define el cambio mínimo que satisface la necesidad. Anota compatibilidad
   esperada y consumidores afectados antes de cambiar interfaces compartidas.
4. Coordina los skills de las capas tocadas; agrega `ld-design` si cambia el
   flujo visual. Mantén intactas las capas no involucradas.
5. Añade o actualiza pruebas que cubran el comportamiento nuevo y, cuando haya
   contrato heredado, regresión/compatibilidad.
6. Informa cualquier dato operativo que falte (por ejemplo, secreto externo,
   configuración, permiso o aprobación de despliegue) sin sustituirlo por una
   credencial o valor ficticio.
