AJUSTE APLICADO - MONTO ÚLTIMA VERSIÓN OP / ESTADO GENERAL / DIMENSIONES ÚLTIMA VERSIÓN

Versión: v3

Cambios incluidos:

1. Monto total ofertado
   - Sigue sumando todas las versiones/registros filtrados.

2. Monto última versión OP
   - Agrupa por OP.
   - Selecciona la última versión real de cada OP.
   - Si hay empate de versión, desempata por Fecha última versión / Fecha última cotización.
   - Suma solo el Valor última oferta antes de IVA de esa última versión.

3. Producto y Segmento
   - El Producto y el Segmento válidos para este indicador son los de la última versión de la OP.
   - Primero se identifica la última versión y luego se aplican los filtros de Producto y Segmento.
   - Esto corrige casos donde una OP cambió de EI a Normalización de frontera, o cambió de segmento entre versiones.

4. Revisión EI / Normalización de frontera
   - Normalización de frontera debe incluir la OP cuya última versión quedó en ese producto.
   - EI ya no debe sumar OP cuya última versión pertenece a otro producto.

5. Estado General
   - Al registrar/actualizar, si Estado Oferta O.T. corresponde a Entregada a KAM u otro cierre, Estado queda como Cerrada.

IMPORTANTE PARA INSTALAR:
- Reemplazar la carpeta/archivos del proyecto por esta versión.
- Cerrar y volver a abrir la app Flask.
- No reutilizar una ventana/proceso viejo de Python, porque puede mantener caché en memoria.
- Esta versión no incluye __pycache__ para evitar que Python cargue lógica anterior.


V4 - 2026-07-09:
- El indicador Monto última versión OP selecciona primero la última fila real por OP, usando versión y fecha de última cotización/aceptación como desempate.
- Producto y Segmento se toman de esa última fila real.
- Se corrige el caso de OP duplicada con misma versión y cambio de producto/segmento.


V5 - Validación enero-junio 2026:
- Los filtros Año/Mes usan estrictamente FechaAceptacionBrief.
- El Monto última versión OP se calcula quitando primero Producto/Segmento, seleccionando última versión por OP, y aplicando después Producto/Segmento de esa última versión.
- Si los valores no coinciden con lista(2).xlsx, la app está leyendo datos diferentes o más recientes desde SharePoint/cache.
