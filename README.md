# Seguimiento Ofertas OT – Oficina Técnica

Aplicación local en Flask para consultar, crear, editar, eliminar, analizar y exportar registros de la lista de SharePoint **Seguimiento-Ofertas-OT-Final** del sitio **BD Control de Ofertas**.

La aplicación trabaja con una sesión corporativa abierta en Chrome mediante Playwright. No usa Power Apps ni registro de aplicación en Entra ID.

---

## 1. Cómo ejecutar

1. Instalar Python 3.11 o superior.
2. Abrir una terminal en esta carpeta.
3. Instalar dependencias:

```bash
pip install -r requirements.txt
playwright install chromium
```

4. Ejecutar:

```bash
python app.py
```
o entrar a app.py y en las opciones de arriba dar click a run y seguido a este run without debugging 

5. Se abrirá Chrome en la URL local:

```text
http://127.0.0.1:5001
```

6. Si SharePoint solicita inicio de sesión, iniciar sesión en la ventana de Chrome y no cerrarla mientras se usa la app.

---

## 2. Estructura de carpetas

```text
OT_OPTIMIZADO/
├── app.py                         # Rutas Flask principales y arranque de la app
├── config.py                      # Configuración SharePoint, lista y alias de campos
├── reports.py                     # Agregaciones de la pestaña Reporte Power BI
├── stats.py                       # Cálculos de estadísticas, fechas y tiempos hábiles
├── sharepoint_client.py           # Cliente SharePoint usando sesión Playwright/Chrome
├── requirements.txt               # Dependencias Python
├── routes/
│   └── export_routes.py           # Exportaciones Excel, PDF general y PDF de tiempos
├── templates/
│   ├── base.html                  # Layout base, imports CSS/JS y navbar
│   ├── index.html                 # Pestañas principales
│   ├── listado.html               # Vista Buscar/Listar
│   ├── formulario.html            # Formulario Nuevo/Editar/Recotizar
│   ├── stats.html                 # Pestaña Estadísticas y Tiempos
│   └── reportes.html              # Nueva pestaña Reporte Power BI con 11 subpestañas
└── static/
    ├── styles.css                 # Estilos generales, listado, stats y reporte
    ├── js/
    │   ├── core.js                # Helpers globales API, alertas y bootstrap
    │   ├── multiselect.js         # Componente de filtros multiselección
    │   ├── listado.js             # Búsqueda, filtros, tabla y modal Ver
    │   ├── formulario.js          # Cargar opciones, editar, guardar, eliminar, recotizar
    │   ├── estadisticas.js        # Estadísticas, filtros, tarjetas y detalle de tiempos
    │   └── reportes.js            # Render visual de la pestaña Reporte Power BI
    └── imagenes/logo/             # Logo ENEL y favicon
```

---

## 3. Dónde modificar cada cosa

### Cambiar sitio, lista o URL de SharePoint
Archivo: `config.py`

Campos principales:

```python
SITE_URL = "https://..."
LIST_TITLE = "Seguimiento-Ofertas-OT-Final"
URL_LISTA = "https://.../AllItems.aspx"
```

### Cambiar nombres de columnas o alias de SharePoint
Archivo: `config.py`

Modificar `FIELD_ALIASES`. Cada clave es el nombre que usa la aplicación y cada lista contiene posibles nombres reales de SharePoint.

Ejemplo:

```python
"Tipo de proyecto": [
    "Tipo de proyecto",
    "TipoPry",
    "Tipo Pry",
    "Tipo Proyecto"
]
```

Si una columna en SharePoint se llama diferente, agregar ese nombre en el alias correspondiente.

### Agregar campos al formulario
Archivos:

1. `templates/formulario.html`: agregar el input/select con `data-title="Nombre de columna"`.
2. `config.py`: agregar alias en `FIELD_ALIASES`.
3. `sharepoint_client.py`: si el campo debe verse en listado/reportes, agregarlo en `to_public_item`.

### Cambiar columnas del listado
Archivo: `static/js/listado.js`

Funciones principales:

- `pintarTabla(items)`: dibuja la tabla principal.
- `verRegistro(id)`: define el orden de campos del modal Ver.
- `aplicarFiltrosTabla()`: filtra la información localmente.

### Cambiar estadísticas y tiempos
Archivos:

- `stats.py`: reglas de cálculo, tramos y días hábiles.
- `static/js/estadisticas.js`: presentación visual de tarjetas, tablas y modales.
- `routes/export_routes.py`: PDF/Excel exportados.

### Cambiar el nuevo reporte tipo Power BI
Archivos:

- `reports.py`: cálculos, conteos, matrices y filtros.
- `templates/reportes.html`: estructura de la pestaña y subpestañas.
- `static/js/reportes.js`: render visual de tarjetas, tablas, barras y donas.
- `static/styles.css`: diseño visual del reporte.

---

## 4. Cambios aplicados en esta versión

### 4.1 Tiempos actualizados

Se ajustaron los tramos de tiempo en `stats.py`:

- Se eliminó el uso de **Fecha de asignación de brief**.
- El primer tramo ahora es: **Aceptación Brief → Envío brief a Aliado**.
- Se eliminó el uso de **Fecha inicio estructuración OT**.
- El tramo de construcción ahora es: **Entrega Aliado → Fin Construcción OT**.
- **Validación Staff** queda como tramo condicional: solo se mide si la fecha existe.
- **Cotización de equipos** solo se mide cuando `Requiere cotización de equipos = Sí`.
- **Visita a cliente** no aplica para productos de frontera/normalización de frontera.
- Los contadores de tiempos ahora muestran lógica tipo: `400 de 400 aplicables`, para no confundir registros no aplicables con registros faltantes.

### 4.2 Recotización

Se reemplazó visualmente **Revalidación** por **Recotización**.

La aplicación interpreta:

- Versión 1 = Cotización inicial.
- Versión 2 o superior = Recotización.

### 4.3 PDF de tiempos

El PDF de tiempos conserva tres bloques:

1. General.
2. Cotización inicial.
3. Recotización.

Cada bloque incluye promedio de días hábiles y registros calculados.

### 4.4 Botón para crear recotización sin digitar todo

Se agregó botón **Recotizar** en el listado y botón **Copiar como recotización** en el formulario.

Funcionamiento:

1. Abre el registro existente.
2. Copia la información base del cliente, OP, KAM, segmento, producto, aliado, tipo de proyecto, etc.
3. Limpia fechas, estado y valores propios del proceso anterior.
4. Incrementa la versión automáticamente.
5. Deja el formulario como registro nuevo para guardar la recotización.

### 4.5 Filtros

Se reforzó la restauración visual de filtros en estadísticas y reportes para que al actualizar datos no se pierda el check seleccionado.

### 4.6 Nueva pestaña Reporte Power BI

Se agregó la pestaña **Reporte Power BI** con 11 subpestañas:

1. General.
2. Detalle de OP.
3. Tiempos por Etapas Global.
4. Detalle Ofertas.
5. Detalle ANS O.T.
6. Pendientes KAM.
7. Pendientes Contratos.
8. PV.
9. Ofertas Vigentes y en Proceso.
10. Informe Jefatura.
11. Alerta Tiempos.

La estructura visual se construyó con base en el PDF entregado. Las visualizaciones son HTML/CSS locales, no son Power BI embebido.

---

## 5. Reglas de tiempos

Archivo: `stats.py`

La lista `TIME_DEFINITIONS` define cada tramo:

```python
{
    "id": "brief_aliado",
    "name": "Aceptación Brief → Envío brief a Aliado",
    "start": "FechaAceptacionBrief",
    "end": "FechaEnvioBriefAliado",
    "applies": "always",
}
```

Valores posibles de `applies`:

| Valor | Qué hace |
|---|---|
| `always` | Siempre aplica. |
| `no_fronteras` | No aplica si el producto contiene frontera o normalización. |
| `requiere_equipos` | Solo aplica si requiere cotización de equipos. |
| `requiere_factibilidad` | Solo aplica si requiere factibilidad o existen fechas de factibilidad. |
| `validacion_staff` | Solo aplica si existe Fecha Entrega Validación Staff. |
| `sin_validacion_staff` | Aplica cuando no hay Validación Staff y va directo a firmas. |

---

## 6. Exportaciones

Archivo: `routes/export_routes.py`

Rutas disponibles:

| Ruta | Qué exporta |
|---|---|
| `/api/export/data` | Excel con registros filtrados. |
| `/api/export/pdf` | PDF de estadísticas generales. |
| `/api/export/pdf-tiempos` | PDF de tiempos general, cotización inicial y recotización. |

---

## 7. Validaciones importantes

- La app depende de los nombres reales de columnas en SharePoint. Si un campo no carga, revisar `FIELD_ALIASES` en `config.py`.
- Los cálculos de días hábiles excluyen sábados, domingos y festivos de Colombia.
- Los registros sin fecha inicio o fecha fin no se usan en el promedio, pero sí se distinguen de los registros no aplicables.
- La nueva pestaña de reporte es una réplica local del enfoque Power BI; puede requerir ajustes finos si los nombres exactos de estados o productos cambian en la lista.

---

## 8. Archivos más importantes para mantenimiento rápido

| Necesidad | Archivo |
|---|---|
| Cambiar SharePoint/lista/alias | `config.py` |
| Cambiar cálculo de tiempos | `stats.py` |
| Cambiar reporte gerencial | `reports.py`, `reportes.js`, `reportes.html` |
| Cambiar formulario | `formulario.html`, `formulario.js` |
| Cambiar listado | `listado.js`, `listado.html` |
| Cambiar PDFs | `routes/export_routes.py` |
| Cambiar colores/diseño | `static/styles.css` |

## Cambios V4 solicitados

### Reporte tipo Power BI
- Las 11 hojas del reporte se recalculan en vivo desde SharePoint mediante `/api/report`; no tienen valores quemados.
- Los gráficos se organizaron en grillas para que queden lado a lado cuando el ancho de pantalla lo permite.
- Los pie/dona muestran leyenda con dato y porcentaje. Al poner el cursor encima de barras, dona, tablas o segmentos aparece el dato en tooltip.
- Al hacer clic sobre una barra o categoría compatible, la hoja aplica el filtro correspondiente y refresca el reporte.
- Los filtros quedan por encima de los cuadros, con `z-index` alto para que el desplegable no se esconda detrás de las tarjetas.
- Se agregaron filtros por Año, Mes, Día, Estado Activa/Cerrada, Estado Oferta O.T., Tipo de proyecto, Producto, Segmento y Aliado.
- Se agregaron botones para exportar cada hoja individual o todo el reporte a PDF.
- En la hoja Vigentes / Proceso, la tabla de Ofertas Vigentes y la tabla de Ofertas en Proceso se pueden exportar a Excel.

### Reglas de fechas y cálculo
- Las fechas que llegan como `2024-01-10T05:00:00Z` se muestran como `dd/mm/aaaa` en las tablas del reporte.
- Cotización de equipos solo aplica cuando `Requiere cotización de equipos = Sí`; si está en No, no se usan esas fechas para cálculo.
- Factibilidad solo aplica cuando `Requiere Factibilidad = Sí`; si está en No, no se usan esas fechas para cálculo.
- Para visita comercial se mantienen excluidos productos de frontera / normalización de frontera en los tiempos.
- El ANS global se calcula en vivo según tipo/tamaño de proyecto y si es cotización inicial o recotización, tomando la tabla de tiempos enviada.
- El ANS O.T. de firmas usa máximo 2 días hábiles entre Inicio Circuito de Firmas y Entrega a KAM.

### Tipo de proyecto automático
En el formulario, al diligenciar el valor de la oferta y la factibilidad, el campo `Tipo de proyecto` se asigna automáticamente así:
- Menor a 100M sin factibilidad: `Pequeño <100M`.
- Menor a 100M con factibilidad: `Pequeño con Factibilidad <100M`.
- 100M a menor de 500M: `Mediano >100M<500M`.
- 500M a menor de 1000M: `Grande >500M<1000M`.
- Mayor o igual a 1000M: `Megaproyecto >1000M`.

### Recotización
- Se reforzó el botón de recotizar para que siempre conserve la OP y envíe `Número de Versión` en el payload al guardar.
- Si el formulario queda en modo recotización y la versión está vacía o menor a 2, se fuerza a `2` antes de guardar.

### Dependencia nueva

## Cambios V5

- Tipo de proyecto calculado automáticamente según el valor de la oferta y si requiere factibilidad.
- Soporte adicional para alias de campos como `Tipo py`, `Requiere visita`, `Solicita Factibilidad` y variantes de `Requiere cotización de equipos`.
- Ajustes en métricas de tiempos para usar solo registros aplicables en visita, factibilidad y equipos.
- Corrección del overlay gris del modal al cerrar "Ver".
- Botón de recotización más ancho y estable.
- Reporte Power BI local; se deja exportación a PDF desde la vista actual y exportación Excel de tablas vigentes/proceso.
- Filtros del reporte reacomodados para evitar scroll horizontal.
- Tablas del reporte muestran tanto Histórico de observaciones como Observaciones.
- ANS O.T. en 2 días calculado para el tramo `Entrega aliado -> Inicio circuito de firmas`.


## Cambios V6

- En el formulario, `Tipo de proyecto` queda junto al `Valor última oferta antes de IVA` y se calcula automáticamente.
- Se agrega `Requiere visita`; si está en No, se bloquean `Fecha programación visita` y `Fecha de visita al Cliente`.
- Las opciones de filtros de Estadísticas se calculan sobre toda la lista para que el texto seleccionado no se oculte como “Todos”.
- En el reporte, los filtros ya no recargan automáticamente por cada checkbox; se pueden seleccionar varios y luego usar Actualizar reporte.
- La hoja General muestra la conciliación tipo Power BI con signos `→`, `-` y `=`.
- Se agrega tabla completa de regla ANS de Oferta Inicial y Recotización.
- ANS O.T. usa el mismo monto total ofertado que la hoja General.
- PV, Jefatura y Alerta Tiempos quedan filtradas a los estados solicitados.
- Se agrega exportación Excel para Detalle Jefatura.
- Las observaciones e histórico ya no quedan truncadas en las tablas del reporte.

## Cambios V7

- Corrección de aplicabilidad en tiempos de visita: si `Requiere visita` está en No, no aplica; si está en Sí o viene vacío por registros antiguos, se toma como aplicable.
- Corrección de equipos: si `Requiere cotización de equipos` está en Sí se calcula; si viene vacío pero hay fechas de solicitud/recibo, también se calcula para no perder registros históricos.
- Se agregaron alias adicionales para columnas de equipos, valor de oferta, Estado O.T. y Tipo py.
- Se agregó filtro de Estado O.T. en Estadísticas y en la búsqueda/listado.
- Se corrigió el agrupamiento mensual de reportes para respetar el año filtrado y evitar meses viejos como octubre dentro de 2026.
- Se agregó exportación Excel en Alerta Tiempos.
- En Alerta Tiempos, la matriz usa Cotización Equipos ENEL y Estructuración Oferta - Oficina Técnica; la dona usa Visita Programada, Estructuración Oferta - Aliado y Sin Visita - Aliado.
- La matriz del reporte deja celdas vacías en vez de mostrar ceros.
- Se ajustó el detalle de alertas con fechas operativas y Estado Tiempo OT.

## Documentación agregada en esta versión

Esta entrega incluye comentarios técnicos en el código fuente y un archivo adicional `DOCUMENTACION_TECNICA.md` con la explicación general de arquitectura, flujo de datos, reglas funcionales y puntos críticos de mantenimiento.

La documentación agregada no cambia la lógica funcional de la aplicación; su objetivo es facilitar soporte, ajustes futuros y revisión de indicadores.


## V14 - Listas grandes + Mobility
- Lectura de SharePoint por lotes de 1.000 registros usando Id para evitar el umbral de 5.000 elementos.
- Nueva hoja Mobility en Reporte SharePoint con tarjetas, gráficas y detalle exportable.
- Alias adicionales para campos Mobility.

## V14.1 - Ajustes reporte Mobility

- `Tipo servicio Mobility` se toma como campo principal para el tipo de servicio.
- `Potencia de cargador` resume todas las columnas cuyo nombre contiene Potencia + Cargador, incluidas las numeradas (2, 3, etc.).
- Tarjeta `Ofertas ganadas` reemplazada por `Valor total` de ofertas Mobility antes de IVA.
- Eliminada la gráfica `Mobility por vendedor`.
- Eliminado el bloque duplicado de `Tipo de servicio`.
- La tabla `Detalle Mobility` usa columnas propias de Mobility y ya no hereda `Cantidad de luminarias` ni `Histórico Observaciones`.
- Se amplió la resolución del campo `Nombre cliente` y se agregó búsqueda dinámica por columnas de nombre de cliente.
