# Código identificado para Valentina Becerra. Marca interna; no se muestra en la interfaz.
"""Motor de estadísticas: normaliza fechas, calcula días hábiles Colombia, conteos y tramos de tiempos."""

# ============================================================
# DOCUMENTACIÓN GENERAL DEL MÓDULO
# ============================================================
# Motor de estadísticas: utilidades de fechas, días hábiles Colombia, filtros, agrupaciones y métricas operativas generales.
#
# Criterio de mantenimiento:
# - Mantener aquí únicamente lógica propia de este módulo.
# - Evitar valores quemados cuando puedan venir de configuración o SharePoint.
# - Conservar nombres canónicos de campos para no romper filtros, reportes ni exportaciones.
# - Antes de cambiar reglas de ANS, tiempos o clasificación, validar impacto en reportes y Excel/PDF.
# ============================================================

from collections import Counter
from datetime import datetime, date, timedelta
from functools import lru_cache


# ============================================================
# FECHAS
# ============================================================

@lru_cache(maxsize=50000)
def parse_date_cached(text):
    """
        Propósito:
            Documenta la función `parse_date_cached` dentro del módulo `stats.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            text.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if not text:
        return None

    text = str(text).strip()

    if not text:
        return None

    # ISO rápido: 2026-05-30 o 2026-05-30T00:00:00Z
    try:
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except Exception:
        pass

    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text[:19], fmt).date()
        except Exception:
            pass

    # Fecha serial Excel
    try:
        number = float(text)
        if number > 20000:
            return date(1899, 12, 30) + timedelta(days=int(number))
    except Exception:
        pass

    try:
        return datetime.fromisoformat(text.replace("Z", "").split(".")[0]).date()
    except Exception:
        return None


def parse_date(value):
    """
        Propósito:
            Convierte fechas provenientes de SharePoint, Excel o texto a objetos date/datetime utilizables por la app.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    return parse_date_cached(str(value))


def easter_date(year):
    """
        Propósito:
            Documenta la función `easter_date` dentro del módulo `stats.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            year.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1

    return date(year, month, day)


def next_monday(d):
    """
        Propósito:
            Documenta la función `next_monday` dentro del módulo `stats.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            d.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if d.weekday() == 0:
        return d

    return d + timedelta(days=(7 - d.weekday()))


@lru_cache(maxsize=64)
def colombia_holidays(year):
    """
    Festivos de Colombia sin usar la librería holidays.
    Incluye festivos fijos, Ley Emiliani y festivos religiosos móviles.
    """
    easter = easter_date(year)

    fixed = {
        date(year, 1, 1),
        date(year, 5, 1),
        date(year, 7, 20),
        date(year, 8, 7),
        date(year, 12, 8),
        date(year, 12, 25),
        easter - timedelta(days=3),  # Jueves Santo
        easter - timedelta(days=2),  # Viernes Santo
    }

    moved_to_monday = {
        date(year, 1, 6),
        date(year, 3, 19),
        date(year, 6, 29),
        date(year, 8, 15),
        date(year, 10, 12),
        date(year, 11, 1),
        date(year, 11, 11),
    }

    # En Colombia estos quedan en lunes
    easter_related_monday = {
        easter + timedelta(days=43),  # Ascensión
        easter + timedelta(days=64),  # Corpus Christi
        easter + timedelta(days=71),  # Sagrado Corazón
    }

    holidays = set(fixed)

    for d in moved_to_monday:
        holidays.add(next_monday(d))

    for d in easter_related_monday:
        holidays.add(next_monday(d))

    return frozenset(holidays)


@lru_cache(maxsize=256)
def colombia_holidays_range(start_year, end_year):
    """
        Propósito:
            Documenta la función `colombia_holidays_range` dentro del módulo `stats.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            start_year, end_year.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    holidays = set()

    for year in range(start_year, end_year + 1):
        holidays.update(colombia_holidays(year))

    return frozenset(holidays)


def count_weekdays_excluding_start_including_end(start, end):
    """
    Cuenta lunes a viernes desde el día siguiente a start hasta end.
    Es mucho más rápido que recorrer día por día.
    """
    total_days = (end - start).days

    if total_days <= 0:
        return 0

    full_weeks = total_days // 7
    remaining_days = total_days % 7

    weekdays = full_weeks * 5

    for i in range(1, remaining_days + 1):
        current = start + timedelta(days=i)

        if current.weekday() < 5:
            weekdays += 1

    return weekdays


@lru_cache(maxsize=50000)
def business_days_between_cached(start_iso, end_iso):
    """
        Propósito:
            Documenta la función `business_days_between_cached` dentro del módulo `stats.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            start_iso, end_iso.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    start = parse_date_cached(start_iso)
    end = parse_date_cached(end_iso)

    if not start or not end:
        return None

    if end < start:
        return None

    if end == start:
        return 0

    weekdays = count_weekdays_excluding_start_including_end(start, end)
    holidays = colombia_holidays_range(start.year, end.year)

    holiday_count = 0

    for h in holidays:
        if start < h <= end and h.weekday() < 5:
            holiday_count += 1

    return weekdays - holiday_count


def business_days_between(start, end):
    """
        Propósito:
            Calcula días hábiles entre dos fechas usando calendario laboral de Colombia.
    
        Entradas:
            start, end.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if not start or not end:
        return None

    if end < start:
        return None

    if end == start:
        return 0

    return business_days_between_cached(start.isoformat(), end.isoformat())


def format_date(value):
    """
        Propósito:
            Formatea un valor para mostrarlo de forma consistente en tablas, tarjetas o exportaciones.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    d = parse_date(value)

    if not d:
        return ""

    return d.strftime("%d/%m/%Y")


# ============================================================
# NORMALIZACIÓN / FILTROS
# ============================================================

def clean(value):
    """
        Propósito:
            Documenta la función `clean` dentro del módulo `stats.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return str(value or "").strip()


def lower(value):
    """
        Propósito:
            Documenta la función `lower` dentro del módulo `stats.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return clean(value).lower()


def normalize_filter_values(value):
    """
    Soporta:
    - valor único: "2025"
    - lista: ["2024", "2025"]
    - tupla/set
    - string separado por coma: "2024,2025"
    """
    if value is None or value == "":
        return set()

    if isinstance(value, (list, tuple, set)):
        raw_values = value
    else:
        raw_values = str(value).split(",")

    result = set()

    for v in raw_values:
        text = str(v or "").strip()

        if text:
            result.add(text)

    return result


def matches_filter(selected_values, item_value):
    """
        Propósito:
            Documenta la función `matches_filter` dentro del módulo `stats.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            selected_values, item_value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if not selected_values:
        return True

    return str(item_value or "").strip() in selected_values


def get_fecha_ultima_version(item):
    """Fecha base de estadísticas.

    Por solicitud operativa, los filtros de Año/Mes/Día de Estadísticas se toman
    desde Fecha Aceptación Brief, no desde Fecha última cotización.
    """
    return parse_date(
        item.get("FechaAceptacionBrief")
        or item.get("Fecha Aceptación Brief")
        or item.get("Fecha Aceptacion Brief")
        or item.get("FechaUltimaVersion")
        or item.get("Fecha última versión")
        or item.get("FechaUltimaCotizacion")
        or item.get("Fecha última cotización")
        or item.get("Modified")
        or item.get("Modificado")
    )


def get_year_from_item(item):
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    dt = get_fecha_ultima_version(item)
    return str(dt.year) if dt else ""


def get_month_from_item(item):
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    dt = get_fecha_ultima_version(item)
    return str(dt.month) if dt else ""


def get_version_number(item):
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    raw = str(
        item.get("NumeroVersion")
        or item.get("Número de Versión")
        or item.get("Número de versión")
        or ""
    ).strip()

    try:
        return int(float(raw.replace(",", ".")))
    except Exception:
        return None


def get_version_type(item):
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    version = get_version_number(item)

    if version == 1:
        return "Cotización inicial"

    if version and version >= 2:
        return "Recotización"

    return "Sin versión"


def get_estado_general(item):
    """Obtiene Estado General y corrige a Cerrada si el Estado Oferta O.T. ya cerró el flujo."""
    estado_ot = lower(get_estado_oferta_ot(item))
    cerrada_por_estado_ot = any(
        x in estado_ot
        for x in [
            "entregada", "ganada", "ganado", "perdid", "cancel",
            "abandon", "rechaz", "cerrad", "inviabilidad"
        ]
    )

    if cerrada_por_estado_ot:
        return "Cerrada"

    return clean(
        item.get("EstadoGeneral")
        or item.get("Estado")
        or ""
    )


def get_estado_oferta_ot(item):
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return clean(
        item.get("EstadoOfertaOT")
        or item.get("Estado Oferta O.T.")
        or ""
    )


def filter_items_for_stats(
    items,
    year="",
    month="",
    segmento="",
    producto="",
    estado_general="",
    tipo_version="",
    estado_ot=""
):
    """
        Propósito:
            Documenta la función `filter_items_for_stats` dentro del módulo `stats.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            items, year, month, segmento, producto, estado_general, tipo_version, estado_ot.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    years = normalize_filter_values(year)
    months = normalize_filter_values(month)
    segmentos = normalize_filter_values(segmento)
    productos = normalize_filter_values(producto)
    estados_generales = normalize_filter_values(estado_general)
    tipos_version = normalize_filter_values(tipo_version)
    estados_ot = normalize_filter_values(estado_ot)

    filtered = []

    for item in items:
        item_year = get_year_from_item(item)
        item_month = get_month_from_item(item)
        item_segmento = clean(item.get("Segmento"))
        item_producto = clean(item.get("Producto"))
        item_estado_general = get_estado_general(item)
        item_estado_ot = get_estado_oferta_ot(item)
        item_tipo_version = get_version_type(item)

        if not matches_filter(years, item_year):
            continue

        if not matches_filter(months, item_month):
            continue

        if not matches_filter(segmentos, item_segmento):
            continue

        if not matches_filter(productos, item_producto):
            continue

        if not matches_filter(estados_generales, item_estado_general):
            continue

        if not matches_filter(estados_ot, item_estado_ot):
            continue

        if not matches_filter(tipos_version, item_tipo_version):
            continue

        filtered.append(item)

    return filtered


# ============================================================
# CONTEOS
# ============================================================

def count_by(items, key):
    """
        Propósito:
            Cuenta registros agrupados o filtrados según la regla indicada por el nombre de la función.
    
        Entradas:
            items, key.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    counter = Counter()

    for item in items:
        value = clean(item.get(key)) or "Sin dato"
        counter[value] += 1

    return [
        {"name": name, "value": value}
        for name, value in counter.most_common()
    ]


def count_by_estado_ot(items):
    """
        Propósito:
            Cuenta registros agrupados o filtrados según la regla indicada por el nombre de la función.
    
        Entradas:
            items.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    counter = Counter()

    for item in items:
        value = get_estado_oferta_ot(item) or "Sin dato"
        counter[value] += 1

    return [
        {"name": name, "value": value}
        for name, value in counter.most_common()
    ]


def get_filter_options(items):
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            items.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    segmentos = sorted(
        set(clean(x.get("Segmento")) for x in items if clean(x.get("Segmento")))
    )

    productos = sorted(
        set(clean(x.get("Producto")) for x in items if clean(x.get("Producto")))
    )

    estados_generales = sorted(
        set(get_estado_general(x) for x in items if get_estado_general(x))
    )

    estados_ot = sorted(
        set(get_estado_oferta_ot(x) for x in items if get_estado_oferta_ot(x))
    )

    return {
        "years": ["2024", "2025", "2026"],
        "months": [
            {"value": "1", "label": "Enero"},
            {"value": "2", "label": "Febrero"},
            {"value": "3", "label": "Marzo"},
            {"value": "4", "label": "Abril"},
            {"value": "5", "label": "Mayo"},
            {"value": "6", "label": "Junio"},
            {"value": "7", "label": "Julio"},
            {"value": "8", "label": "Agosto"},
            {"value": "9", "label": "Septiembre"},
            {"value": "10", "label": "Octubre"},
            {"value": "11", "label": "Noviembre"},
            {"value": "12", "label": "Diciembre"},
        ],
        "segmentos": segmentos,
        "productos": productos,
        "estados_generales": estados_generales,
        "estados_ot": estados_ot,
        "tipos_version": [
            "Cotización inicial",
            "Recotización",
            "Sin versión"
        ],
    }


# ============================================================
# TIEMPOS
# ============================================================

TIME_DEFINITIONS = [
    {
        "id": "brief_aliado",
        "name": "Aceptación Brief → Envío brief a Aliado",
        "start": "FechaAceptacionBrief",
        "end": "FechaEnvioBriefAliado",
        "applies": "always",
    },
    {
        "id": "contacto_programacion",
        "name": "Contacto Cliente → Programación Visita",
        "start": "FechaRealContactoCliente",
        "end": "FechaProgramacionVisita",
        "applies": "no_fronteras",
    },
    {
        "id": "programacion_visita",
        "name": "Programación Visita → Visita Cliente",
        "start": "FechaProgramacionVisita",
        "end": "FechaVisitaCliente",
        "applies": "no_fronteras",
    },
    {
        "id": "solicitud_radicacion_factibilidad",
        "name": "Solicitud Factibilidad → Radicación Factibilidad",
        "start": "FechaSolicitudFactibilidad",
        "end": "FechaRadicacionFactibilidad",
        "applies": "requiere_factibilidad",
    },
    {
        "id": "solicitud_recibo_equipos",
        "name": "Solicitud Equipos → Recibo Cotización Equipos",
        "start": "FechaSolicitudEquipos",
        "end": "FechaRecibidoCotizacionEquipos",
        "applies": "requiere_equipos",
    },
    {
        "id": "aliado_fin_estructuracion",
        "name": "Entrega Aliado → Fin Construcción OT",
        "start": "FechaEntregaOfertaAliado",
        "end": "FechaFinConstruccionOfertaOT",
        "applies": "always",
    },
    {
        "id": "fin_validacion_staff",
        "name": "Fin Construcción OT → Validación Staff",
        "start": "FechaFinConstruccionOfertaOT",
        "end": "FechaEntregaValidacionStaff",
        "applies": "validacion_staff",
    },
    {
        "id": "validacion_firmas",
        "name": "Validación Staff → Inicio Circuito Firmas",
        "start": "FechaEntregaValidacionStaff",
        "end": "FechaInicioCircuitoFirmas",
        "applies": "validacion_staff",
    },
    {
        "id": "firmas_kam",
        "name": "Inicio Circuito Firmas → Entrega a KAM",
        "start": "FechaInicioCircuitoFirmas",
        "end": "FechaEntregaKAM",
        "applies": "always",
    },
]

def get_time_definition(metric_id):
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            metric_id.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    for metric in TIME_DEFINITIONS:
        if metric["id"] == metric_id:
            return metric

    return None


def avg_from_sum(total_sum, total_count):
    """
        Propósito:
            Calcula promedios operativos a partir de fechas o indicadores ya normalizados.
    
        Entradas:
            total_sum, total_count.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if not total_count:
        return ""

    value = total_sum / total_count

    if value == int(value):
        return int(value)

    return round(value, 1)


def is_yes(value):
    """
        Propósito:
            Evalúa una condición de negocio sobre un registro y devuelve True/False.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    text = lower(value)
    return text in {"si", "sí", "s", "yes", "true", "1", "si aplica", "sí aplica", "aplica"}


def is_frontier_product(item):
    """
        Propósito:
            Evalúa una condición de negocio sobre un registro y devuelve True/False.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    text = lower(item.get("Producto"))
    return "frontera" in text or "normalizacion" in text or "normalización" in text


def metric_applies(item, metric):
    """
        Propósito:
            Documenta la función `metric_applies` dentro del módulo `stats.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            item, metric.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    applies = metric.get("applies", "always")

    if applies == "always":
        return True

    if applies == "no_fronteras":
        # Columnas reales usadas para visita:
        # - Requiere visita ?
        # - Fecha real contacto Cliente
        # - Fecha programación visita
        # - Fecha de visita al Cliente
        # Solo aplica si Requiere visita ? = Sí.
        return is_yes(item.get("RequiereVisita"))

    if applies == "requiere_equipos":
        # Columnas reales usadas para equipos:
        # - Requiere cotización equipos
        # - Fecha solicitud de equipos
        # - Fecha recibido cotización de equipos
        return is_yes(item.get("RequiereCotizacionEquipos"))

    if applies == "requiere_factibilidad":
        # Columnas reales usadas para factibilidad:
        # - Requiere Factibilidad
        # - Fecha solicitud de Factibilidad
        # - Fecha radicación Factibilidad
        return is_yes(item.get("RequiereFactibilidad"))

    if applies == "validacion_staff":
        return bool(parse_date(item.get("FechaEntregaValidacionStaff")))

    if applies == "sin_validacion_staff":
        return not bool(parse_date(item.get("FechaEntregaValidacionStaff")))

    return True


def build_time_metrics(items):
    """
    Calcula los promedios de tiempos por tramo.

    Reglas operativas aplicadas:
    - Recotización = versión 2 o superior.
    - No se usa Fecha asignación brief.
    - No se usa Fecha inicio estructuración OT.
    - Visita no aplica para productos de frontera/normalización de frontera.
    - Equipos solo aplica si "Requiere cotización de equipos" es Sí.
    - Validación Staff solo se mide cuando la fecha existe.
    - El contador se presenta como registros calculados / registros aplicables.
    """
    result = []

    for metric in TIME_DEFINITIONS:
        total_sum = total_count = applicable_count = not_applicable_count = 0
        initial_sum = initial_count = initial_applicable = 0
        recot_sum = recot_count = recot_applicable = 0

        start_key = metric["start"]
        end_key = metric["end"]

        for item in items:
            version_type = get_version_type(item)

            if not metric_applies(item, metric):
                not_applicable_count += 1
                continue

            applicable_count += 1
            if version_type == "Cotización inicial":
                initial_applicable += 1
            elif version_type == "Recotización":
                recot_applicable += 1

            start = parse_date(item.get(start_key))
            end = parse_date(item.get(end_key))
            days = business_days_between(start, end)

            if days is None:
                continue

            total_sum += days
            total_count += 1

            if version_type == "Cotización inicial":
                initial_sum += days
                initial_count += 1
            elif version_type == "Recotización":
                recot_sum += days
                recot_count += 1

        result.append({
            "id": metric["id"],
            "name": metric["name"],
            "avg_days": avg_from_sum(total_sum, total_count),
            "count": total_count,
            "applicable_count": applicable_count,
            "not_applicable_count": not_applicable_count,
            "initial_avg_days": avg_from_sum(initial_sum, initial_count),
            "initial_count": initial_count,
            "initial_applicable_count": initial_applicable,
            "recot_avg_days": avg_from_sum(recot_sum, recot_count),
            "recot_count": recot_count,
            "recot_applicable_count": recot_applicable,
        })

    return result

def build_time_detail(items, metric_id):
    """
        Propósito:
            Genera el detalle de tiempos por oportunidad y etapa para análisis operativo.
    
        Entradas:
            items, metric_id.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    metric = get_time_definition(metric_id)

    if not metric:
        return {"metric": None, "rows": [], "applicable_count": 0, "not_applicable_count": 0}

    rows = []
    applicable_count = 0
    not_applicable_count = 0
    start_key = metric["start"]
    end_key = metric["end"]

    for item in items:
        if not metric_applies(item, metric):
            not_applicable_count += 1
            continue

        applicable_count += 1
        start = parse_date(item.get(start_key))
        end = parse_date(item.get(end_key))
        days = business_days_between(start, end)

        if days is None:
            continue

        rows.append({
            "Id": item.get("Id"),
            "OP": item.get("OP", ""),
            "NumeroVersion": item.get("NumeroVersion", ""),
            "TipoVersion": get_version_type(item),
            "NombreCliente": item.get("NombreCliente", ""),
            "KAM": item.get("KAM", ""),
            "Segmento": item.get("Segmento", ""),
            "Producto": item.get("Producto", ""),
            "EstadoOfertaOT": get_estado_oferta_ot(item),
            "FechaInicio": start.strftime("%d/%m/%Y") if start else "",
            "FechaFin": end.strftime("%d/%m/%Y") if end else "",
            "DiasHabiles": days,
            "CampoAplica": metric.get("applies", "always"),
            "RequiereVisita": item.get("RequiereVisita", ""),
            "RequiereFactibilidad": item.get("RequiereFactibilidad", ""),
            "RequiereCotizacionEquipos": item.get("RequiereCotizacionEquipos", ""),
            "CampoFechaInicio": start_key,
            "CampoFechaFin": end_key,
        })

    rows = sorted(rows, key=lambda x: x["DiasHabiles"], reverse=True)

    return {
        "metric": metric,
        "rows": rows,
        "applicable_count": applicable_count,
        "not_applicable_count": not_applicable_count,
    }


# ============================================================
# BUILD PRINCIPAL
# ============================================================

def build_stats(
    items,
    year="",
    month="",
    segmento="",
    producto="",
    estado_general="",
    tipo_version="",
    estado_ot=""
):
    """
        Propósito:
            Construye el resumen estadístico principal a partir de los registros filtrados.
    
        Entradas:
            items, year, month, segmento, producto, estado_general, tipo_version, estado_ot.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    filtered_items = filter_items_for_stats(
        items,
        year=year,
        month=month,
        segmento=segmento,
        producto=producto,
        estado_general=estado_general,
        tipo_version=tipo_version
    )

    total = len(filtered_items)

    ganadas = 0
    perdidas = 0
    entregadas = 0
    activas = 0
    cerradas = 0

    for item in filtered_items:
        estado_ot = lower(get_estado_oferta_ot(item))
        estado_general_item = lower(get_estado_general(item))

        if "ganada" in estado_ot or "ganado" in estado_ot:
            ganadas += 1

        if "perdida" in estado_ot or "perdido" in estado_ot:
            perdidas += 1

        if "entregada a kam" in estado_ot or ("entregada" in estado_ot and "kam" in estado_ot):
            entregadas += 1

        if estado_general_item == "activa":
            activas += 1

        if estado_general_item == "cerrada":
            cerradas += 1

    return {
        "total": total,
        "ganadas": ganadas,
        "perdidas": perdidas,
        "entregadas": entregadas,
        "activas": activas,
        "cerradas": cerradas,
        "por_segmento": count_by(filtered_items, "Segmento"),
        "por_producto": count_by(filtered_items, "Producto"),
        "por_kam": count_by(filtered_items, "KAM"),
        "por_estado": count_by_estado_ot(filtered_items),
        "tiempos": build_time_metrics(filtered_items),
        "filter_options": get_filter_options(items),
    }