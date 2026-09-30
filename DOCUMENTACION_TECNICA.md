# Documentación técnica — App Seguimiento Ofertas OT V12.3

## 1. Propósito de la aplicación

Esta aplicación permite administrar y analizar el seguimiento de ofertas de Oficina Técnica conectadas a una lista de SharePoint. Incluye formulario de carga/edición, listado operativo, estadísticas, reporte gerencial, cálculo de tiempos hábiles, análisis de ANS y exportaciones a Excel/PDF.

## 2. Arquitectura general

La aplicación está organizada en capas simples:

| Capa | Archivo(s) | Responsabilidad |
|---|---|---|
| Entrada Flask | `app.py` | Define rutas HTML, APIs JSON, filtros comunes y arranque local. |
| Configuración | `config.py` | Centraliza URL del sitio, lista SharePoint, alias de columnas, campos y opciones. |
| Integración | `sharepoint_client.py` | Gestiona sesión web, REST SharePoint, metadatos, caché y CRUD. |
| Estadísticas | `stats.py` | Calcula fechas, días hábiles, filtros y métricas generales. |
| Reporte gerencial | `reports.py` | Calcula KPIs, ANS, tablas, pendientes, tiempos, series y tarjetas. |
| Exportaciones | `routes/export_routes.py` | Genera Excel/PDF para estadísticas y reportes. |
| Interfaz | `templates/*.html` | Renderiza pantallas, filtros, tablas, tarjetas y llamadas fetch. |
| Estilos | `static/styles.css` | Define identidad visual, layout, tablas, tarjetas, semáforos y responsive. |

## 3. Flujo principal de datos

1. El usuario abre la app Flask.
2. `sharepoint_client.py` inicializa o reutiliza una sesión autenticada contra SharePoint.
3. La app consulta la lista `Seguimiento-Ofertas-OT-Final`.
4. Los registros crudos se convierten a nombres canónicos usados por la app.
5. `app.py` aplica filtros recibidos desde la interfaz.
6. `stats.py` y `reports.py` calculan indicadores, tiempos, ANS y tablas.
7. Las plantillas HTML muestran los resultados y permiten exportar.

## 4. Reglas funcionales importantes

### Tipo de proyecto

La clasificación depende del valor antes de IVA y de factibilidad:

| Regla | Resultado |
|---|---|
| Valor menor a $100 M y sin factibilidad | Pequeño |
| Valor menor a $100 M y con factibilidad | Pequeño con factibilidad |
| Valor desde $100 M hasta menor de $500 M | Mediano |
| Valor desde $500 M hasta menor de $1.000 M | Grande |
| Valor igual o mayor a $1.000 M | Megaproyecto |

### Estado Activa/Cerrada

La aplicación prioriza el campo explícito `EstadoGeneral` cuando existe. Si no existe, deriva el estado desde `EstadoOfertaOT` buscando estados de cierre, entrega, pérdida, cancelación, rechazo o inviabilidad.

### Días hábiles

Los tiempos se calculan con calendario laboral de Colombia, excluyendo fines de semana y festivos colombianos, incluidos festivos móviles asociados a Semana Santa.

### ANS

Los cálculos de ANS se realizan desde fechas reales del proceso. Si no hay dato suficiente para calcular un ANS, la salida debe mantenerse vacía o con guion según la vista, pero no debe marcar cumplimiento automáticamente.

## 5. Puntos críticos para mantenimiento

- No cambiar nombres canónicos de campos sin revisar `FIELD_ALIASES` en `config.py`.
- No modificar clases CSS usadas por las plantillas sin buscar sus referencias.
- No reemplazar reglas de fechas sin validar exportaciones Excel/PDF.
- No asumir que SharePoint trae siempre el mismo nombre interno: usar el mapa de campos del cliente.
- Cuando un indicador salga mal, revisar primero: campo fuente, filtro aplicado, fecha base y conversión de formato.

## 6. Archivos documentados

Se agregaron comentarios de módulo, docstrings de funciones/clases y comentarios de mantenimiento en:

- `app.py`
- `config.py`
- `reports.py`
- `stats.py`
- `sharepoint_client.py`
- `routes/export_routes.py`
- `templates/base.html`
- `templates/formulario.html`
- `templates/index.html`
- `templates/listado.html`
- `templates/reportes.html`
- `templates/stats.html`
- `static/styles.css`
- `static/app.js`
