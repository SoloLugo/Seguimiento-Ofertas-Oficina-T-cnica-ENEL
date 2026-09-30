# Código identificado para Valentina Becerra. Marca interna; no se muestra en la interfaz.
"""Motor del reporte gerencial tipo Power BI.

Todos los indicadores se calculan en vivo desde la lista de SharePoint que lee
`sp_client.get_public_items()`. No hay valores quemados: las tarjetas, tablas,
gráficas, ANS y pendientes salen de los registros filtrados.
"""

# ============================================================
# DOCUMENTACIÓN GENERAL DEL MÓDULO
# ============================================================
# Motor de reportes gerenciales: calcula indicadores, tablas, ANS, pendientes, tiempos y estructuras listas para consumir desde la interfaz.
#
# Criterio de mantenimiento:
# - Mantener aquí únicamente lógica propia de este módulo.
# - Evitar valores quemados cuando puedan venir de configuración o SharePoint.
# - Conservar nombres canónicos de campos para no romper filtros, reportes ni exportaciones.
# - Antes de cambiar reglas de ANS, tiempos o clasificación, validar impacto en reportes y Excel/PDF.
# ============================================================

from collections import Counter
from datetime import date, timedelta
import unicodedata

from stats import (
    parse_date,
    business_days_between,
    get_version_type,
    get_year_from_item,
    get_month_from_item,
    get_estado_oferta_ot,
    lower,
    clean,
)

MONTHS = [
    ("1", "Enero"), ("2", "Febrero"), ("3", "Marzo"), ("4", "Abril"),
    ("5", "Mayo"), ("6", "Junio"), ("7", "Julio"), ("8", "Agosto"),
    ("9", "Septiembre"), ("10", "Octubre"), ("11", "Noviembre"), ("12", "Diciembre"),
]

ALIADOS_JEFATURA = {"AP", "CIDET", "Interna Enel", "Navidad", "Lighting", "Lightning", "PV", "SICTE"}

# Cambiar este identificador invalida el caché del reporte cuando se ajusta lógica crítica.
REPORT_CALC_VERSION = "2026-07-09-v5-corte-enero-junio-fecha-aceptacion-ultima-version"

ESTADOS_JEFATURA = {
    "Cotizacion Equipos ENEL", "Cotización Equipos ENEL",
    "Estructuración Oferta - Aliado", "Estructuracion Oferta - Aliado",
    "Estructuración Oferta - Oficina Técnica", "Estructuracion Oferta - Oficina Tecnica",
    "Factibilidad - Doc Ptes Cliente", "Factibilidad - OR Estandar", "Factibilidad - OR Estándar",
    "Pendiente gestion documental KAM", "Pendiente gestión documental KAM",
    "Sin Visita - Aliado", "Visita Programada",
}

ESTADOS_EXCLUIR_NO_GESTION = [
    "brief sin documentos",
    "brief rechaz",
    "rechaz",
    "cancel",
    "abandon",
    "cerrada para recotizar",
    "cerrado por inviabilidad",
    "inviabilidad",
]

ESTADOS_PENDIENTES_KAM = [
    "factibilidad",
    "doc ptes cliente",
    "gestion documental kam",
    "gestión documental kam",
]

ESTADOS_PENDIENTES_CONTRATO = [
    "visita",
    "sin visita",
    "estructuración oferta - aliado",
    "estructuracion oferta - aliado",
]

ESTADOS_PROCESO = [
    "visita",
    "estructuración",
    "estructuracion",
    "cotizacion",
    "cotización",
    "factibilidad",
]

ESTADOS_ALERTA = [
    "visita programada",
    "estructuración oferta",
    "estructuracion oferta",
    "sin visita",
    "cotizacion equipos",
    "cotización equipos",
]

ESTADOS_PV_PERMITIDOS = {
    "sin visita - aliado",
    "pendiente gestion documental kam",
    "pendiente gestión documental kam",
    "estructuración oferta - aliado",
    "estructuracion oferta - aliado",
    "estructuración oferta - oficina técnica",
    "estructuracion oferta - oficina tecnica",
    "visita programada",
}

ESTADOS_ALERTA_EXACTOS = {
    "cotizacion equipos enel",
    "cotización equipos enel",
    "estructuración oferta - oficina técnica",
    "estructuracion oferta - oficina tecnica",
}

TAM_PERMITIDOS = [
    "luis salazar",
    "luis zuñiga",
    "luis santiago zuñiga",
    "edson",
    "alexandra",
    "juan carlos",
]

ESTADOS_JEFATURA_KEYS = {
    "cotizacion equipos enel",
    "cotización equipos enel",
    "estructuración oferta - aliado",
    "estructuracion oferta - aliado",
    "estructuración oferta - oficina técnica",
    "estructuracion oferta - oficina tecnica",
    "factibilidad - doc ptes cliente",
    "factibilidad - or estandar",
    "factibilidad - or estándar",
    "pendiente gestion documental kam",
    "pendiente gestión documental kam",
    "sin visita - aliado",
    "sin visita cliente",
    "sin visita - cliente",
    "pendiente respuesta kam",
    "validacion ifbp",
    "validación ifbp",
    "visita programada",
}

ESTADOS_ALERTA_MATRIX_KEYS = {
    "cotizacion equipos enel",
    "cotización equipos enel",
    "estructuración oferta - oficina técnica",
    "estructuracion oferta - oficina tecnica",
    "estructuración ot",
    "estructuracion ot",
}

ESTADOS_ALERTA_DONA_KEYS = {
    "visita programada",
    "estructuración oferta - aliado",
    "estructuracion oferta - aliado",
    "sin visita - aliado",
}

TIPOS_PROYECTO_VALIDOS = [
    "Pequeño",
    "Pequeño con factibilidad",
    "Mediano",
    "Grande",
    "Megaproyecto",
]


def norm(value):
    """
        Propósito:
            Normaliza texto para comparar valores con tildes, mayúsculas, espacios o variantes de escritura.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return clean(value) or "Sin dato"


def normkey(value):
    """
        Propósito:
            Normaliza texto para comparar valores con tildes, mayúsculas, espacios o variantes de escritura.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return lower(value).replace("  ", " ").strip()


def normkey_ascii(value):
    """Normaliza texto para comparar estados sin depender de tildes."""
    text = normkey(value)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.replace(".", " ").replace("_", " ").split())


def estado_key_ascii(item):
    """
        Propósito:
            Documenta la función `estado_key_ascii` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return normkey_ascii(item.get("EstadoOfertaOT") or get_estado_oferta_ot(item))


def yes(value):
    """
        Propósito:
            Documenta la función `yes` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return normkey(value) in {
        "si",
        "sí",
        "s",
        "yes",
        "true",
        "1",
        "si aplica",
        "sí aplica",
        "aplica",
    }


def to_number(value):
    """
        Propósito:
            Convierte números desde texto, moneda o formatos con separadores a float seguro.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if value in (None, ""):
        return 0.0

    try:
        text = str(value).replace("$", "").replace("COP", "").strip().replace(" ", "")

        if not text:
            return 0.0

        if text.count(".") > 1 and "," not in text:
            text = text.replace(".", "")
        elif "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(".", "").replace(",", ".")

        return float(text)
    except Exception:
        return 0.0


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
    return d.strftime("%d/%m/%Y") if d else ""


def format_cop_value(value):
    """
        Propósito:
            Da formato visual en pesos colombianos para valores monetarios del reporte.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    n = to_number(value)

    if not n:
        return ""

    return "$" + f"{n:,.0f}".replace(",", ".")


def estado_text(item):
    """
        Propósito:
            Documenta la función `estado_text` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return lower(get_estado_oferta_ot(item))


def normalizar_tipo_proyecto(value):
    """Devuelve el valor exacto permitido para Tipo py o vacío si no hay dato real."""
    raw = clean(value)

    if not raw or raw == "Sin dato":
        return ""

    key = (
        normkey(raw)
        .replace("<100m", "")
        .replace(">100m<500m", "")
        .replace(">500m<1000m", "")
        .replace(">1000m", "")
        .strip()
    )

    if "peque" in key and "fact" in key:
        return "Pequeño con factibilidad"

    if "pequeno" in key or "pequeño" in key or "peque" in key:
        return "Pequeño"

    if "mediano" in key:
        return "Mediano"

    if "mega" in key:
        return "Megaproyecto"

    if "grande" in key:
        return "Grande"

    return raw if raw in TIPOS_PROYECTO_VALIDOS else ""


def tipo_proyecto_item(item):
    """
    Lee el Tipo py real de SharePoint.

    No calcula por valor.
    No inventa 'En definición'.
    Si no tiene dato, devuelve vacío.
    """
    return normalizar_tipo_proyecto(
        item.get("TipoProyecto")
        or item.get("Tipo py")
        or item.get("Tipo de proyecto")
        or item.get("Tipopy")
    )


def sla_global_item(item):
    """ANS total de oferta según la tabla enviada por el usuario."""
    recot = get_version_type(item) == "Recotización"
    tipo = normkey(tipo_proyecto_item(item))

    if recot:
        if "grande" in tipo or "mega" in tipo:
            return 17
        return 12

    if "pequeño con factibilidad" in tipo or "pequeno con factibilidad" in tipo:
        return 22

    if "pequeño" in tipo or "pequeno" in tipo:
        return 15

    if "mediano" in tipo:
        return 24

    if "grande" in tipo:
        return 27

    if "mega" in tipo:
        return 37

    return 24


def count_rows(items, field, *, use_tipo=False):
    """
        Propósito:
            Cuenta registros agrupados o filtrados según la regla indicada por el nombre de la función.
    
        Entradas:
            items, field.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    def value_for(item):
        """
            Propósito:
                Documenta la función `value_for` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                item.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        if use_tipo:
            return tipo_proyecto_item(item) or "Sin info"
        return norm(item.get(field))

    c = Counter(value_for(item) for item in items)

    return [
        {"name": k, "value": v, "field": field}
        for k, v in c.most_common()
        if k != "Sin dato"
    ]


def fecha_base_reporte(item):
    """Fecha base unificada para filtros generales del reporte.

    Regla v5: para cortes mensuales/anuales del reporte se usa estrictamente
    FechaAceptacionBrief. Esto evita que una OP entre al corte enero-junio por
    FechaUltimaVersion, FechaEntregaKAM o Modified cuando su aceptación real
    pertenece a otro periodo.
    """
    return parse_date(item.get("FechaAceptacionBrief"))


def fecha_gestion_op_mes(item):
    """Fecha para OP gestionadas por mes.

    Regla solicitada: usar Fecha Aceptación Brief; si está vacía, corroborar con
    Fecha envío brief a Aliado. No usa otros respaldos para evitar conteos de más.
    """
    return parse_date(item.get("FechaAceptacionBrief")) or parse_date(item.get("FechaEnvioBriefAliado"))


def count_by_month_date_getter(items, date_getter):
    """
        Propósito:
            Cuenta registros agrupados o filtrados según la regla indicada por el nombre de la función.
    
        Entradas:
            items, date_getter.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    c = Counter()

    for item in items:
        d = date_getter(item)
        if d and d <= date.today():
            c[str(d.month)] += 1

    return [
        {"name": label, "value": c.get(value, 0), "field": "month", "raw": value}
        for value, label in MONTHS
        if c.get(value, 0)
    ]


def apply_period_filter_date_getter(items, filters, date_getter):
    """
        Propósito:
            Documenta la función `apply_period_filter_date_getter` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            items, filters, date_getter.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    years = selected_filter_values(filters, "years") if "selected_filter_values" in globals() else set()
    months = selected_filter_values(filters, "months") if "selected_filter_values" in globals() else set()
    days = selected_filter_values(filters, "days") if "selected_filter_values" in globals() else set()

    if not years and not months and not days:
        return list(items)

    result = []

    for item in items:
        d = date_getter(item)
        if not d:
            continue
        if years and str(d.year) not in years:
            continue
        if months and str(d.month) not in months:
            continue
        if days and str(d.day) not in days:
            continue
        result.append(item)

    return result


def weekdays_between_no_holidays(start, end):
    """Días hábiles lunes-viernes, excluyendo fecha inicial e incluyendo final.

    Esta regla replica el cálculo manual que se está usando en la matriz mensual
    de tiempos globales: fecha final - fecha inicial en días hábiles, sin restar
    festivos configurados en Colombia.
    """
    if not start or not end:
        return None
    if end < start:
        return None
    if end == start:
        return 0

    total_days = (end - start).days
    count = 0
    for i in range(1, total_days + 1):
        current = start + timedelta(days=i)
        if current.weekday() < 5:
            count += 1
    return count


def get_report_year(item):
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
    d = fecha_base_reporte(item)
    return str(d.year) if d else ""


def get_report_month(item):
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
    d = fecha_base_reporte(item)
    return str(d.month) if d else ""


def count_by_month(items, date_field="FechaAceptacionBrief", current_year_only=False, fallback_to_base=True):
    """
        Propósito:
            Cuenta registros agrupados o filtrados según la regla indicada por el nombre de la función.
    
        Entradas:
            items, date_field, current_year_only, fallback_to_base.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    c = Counter()
    current_year = str(date.today().year)

    for item in items:
        base = fecha_base_reporte(item)

        if current_year_only and (not base or str(base.year) != current_year):
            continue

        if date_field in (None, "", "base", "FechaAceptacionBrief"):
            d = base
        else:
            d = parse_date(item.get(date_field))
            if not d and fallback_to_base:
                d = base

        if d and d <= date.today():
            c[str(d.month)] += 1

    return [
        {"name": label, "value": c.get(value, 0), "field": "month", "raw": value}
        for value, label in MONTHS
        if c.get(value, 0)
    ]


def count_by_year(items, date_field="FechaAceptacionBrief", fallback_to_base=True):
    """
        Propósito:
            Cuenta registros agrupados o filtrados según la regla indicada por el nombre de la función.
    
        Entradas:
            items, date_field, fallback_to_base.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    c = Counter()

    for item in items:
        base = fecha_base_reporte(item)

        if date_field in (None, "", "base", "FechaAceptacionBrief"):
            d = base
        else:
            d = parse_date(item.get(date_field))
            if not d and fallback_to_base:
                d = base

        if d and d <= date.today():
            c[str(d.year)] += 1

    return [
        {"name": k, "value": v, "field": "year", "raw": k}
        for k, v in sorted(c.items())
        if k != "Sin año"
    ]


def count_by_two_fields(items, row_field, col_field, *, use_month_rows=False, use_tipo_col=False):
    """
        Propósito:
            Cuenta registros agrupados o filtrados según la regla indicada por el nombre de la función.
    
        Entradas:
            items, row_field, col_field.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    month_order = {label: idx for idx, (_, label) in enumerate(MONTHS, start=1)}

    def row_val(item):
        """
            Propósito:
                Documenta la función `row_val` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                item.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        if use_month_rows:
            m = get_report_month(item)
            return dict(MONTHS).get(m, "Sin mes")
        return norm(item.get(row_field))

    def col_val(item):
        """
            Propósito:
                Documenta la función `col_val` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                item.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        return tipo_proyecto_item(item) if use_tipo_col else norm(item.get(col_field))

    rows = sorted(
        {row_val(item) for item in items if row_val(item) != "Sin dato"},
        key=lambda x: month_order.get(x, 999) if use_month_rows else x,
    )

    cols = sorted(
        {col_val(item) for item in items if col_val(item) != "Sin dato"}
    )

    matrix = []

    for r in rows:
        row = {"name": r, "total": 0, "values": {}}

        for c in cols:
            value = sum(
                1 for item in items
                if row_val(item) == r and col_val(item) == c
            )

            row["values"][c] = value
            row["total"] += value

        if row["total"]:
            matrix.append(row)

    return {
        "columns": cols,
        "rows": matrix,
        "total": sum(x["total"] for x in matrix),
    }


def version_number(item):
    """Devuelve el número de versión/cotización como entero comparable."""
    raw = item.get("NumeroVersion") or item.get("NumeroCotizacion") or 0
    try:
        return int(float(str(raw).replace(",", ".").strip()))
    except Exception:
        return 0


def latest_date_for_version(item):
    """Fecha auxiliar para desempatar versiones iguales de una misma OP.

    Regla v4:
    - Si existe FechaUltimaVersion / Fecha última cotización, se usa como fecha
      principal de desempate.
    - Si esa fecha viene vacía, se usa FechaAceptacionBrief para no dejar que
      registros incompletos ganen artificialmente frente a registros con fecha real.
    - Si tampoco existe, se usan respaldos operativos y finalmente date.min.

    Esto corrige casos donde una misma OP tiene dos filas con el mismo número
    de versión, pero la fila más reciente cambió Producto o Segmento.
    """
    return (
        parse_date(item.get("FechaUltimaVersion"))
        or parse_date(item.get("FechaUltimaCotizacion"))
        or parse_date(item.get("FechaAceptacionBrief"))
        or parse_date(item.get("FechaEntregaKAM"))
        or parse_date(item.get("FechaEntregaCliente"))
        or date.min
    )


def latest_tie_id(item, idx):
    """Desempate final estable y comparable para filas de la misma OP."""
    raw = item.get("Id")
    try:
        return int(float(str(raw).strip()))
    except Exception:
        return int(idx)


def latest_by_op(items):
    """
    Selecciona una sola fila por OP: la última versión real.

    Reglas:
    1. Agrupa por OP/Title.
    2. Escoge el mayor número de versión.
    3. Si hay empate de versión, usa la fecha de última versión/cotización como desempate.
    4. La fila resultante conserva el Producto y Segmento de esa última versión.
    """
    best = {}

    for idx, item in enumerate(items):
        op_raw = item.get("OP") or item.get("Title")
        op = clean(op_raw)

        # Si por alguna razón llega una fila sin OP, no se debe mezclar con otras
        # filas vacías bajo "Sin dato"; se cuenta como registro independiente.
        if not op:
            op = f"__sin_op_{item.get('Id') or idx}"

        version = version_number(item)
        tie_date = latest_date_for_version(item)
        tie_id = latest_tie_id(item, idx)
        candidate_key = (version, tie_date, tie_id)

        if op not in best or candidate_key >= best[op][0]:
            best[op] = (candidate_key, item)

    return [x[1] for x in best.values()]


def amount_total_all_versions(items):
    """Suma el valor de todas las versiones/registros filtrados."""
    return sum(to_number(item.get("ValorUltimaOferta")) for item in items)


def amount_latest_version_by_op(items):
    """Suma únicamente el valor de la última versión registrada por cada OP."""
    return sum(to_number(item.get("ValorUltimaOferta")) for item in latest_by_op(items))


def filters_without_product_dimension(filters):
    """Quita producto/segmento antes de seleccionar la última versión por OP.

    Punto clave del ajuste v3:
    - El Producto y el Segmento válidos para el indicador son los de la última
      versión real de cada OP.
    - Por eso primero se filtra por periodo/estado/tipo/aliado, luego se escoge
      la última versión por OP y solo después se aplican Producto y Segmento.
    """
    filters = dict(filters or {})
    filters.pop("productos", None)
    filters.pop("segmentos", None)
    return filters


def amount_latest_version_by_op_for_report_filters(items, filters=None):
    """Monto de última versión por OP respetando filtros del reporte.

    La selección de la última versión se hace antes de aplicar producto/segmento
    para que la OP quede clasificada según su última versión real.
    """
    filters = filters or {}
    base = filter_report_items(items, filters_without_product_dimension(filters))
    latest = latest_by_op(base)
    latest_filtered = filter_report_items(latest, filters)
    return sum(to_number(item.get("ValorUltimaOferta")) for item in latest_filtered)


def amount_max_by_op(items):
    """Compatibilidad: conserva el nombre antiguo apuntando a la última versión por OP."""
    return amount_latest_version_by_op(items)


def total_offer_days(item):
    """
        Propósito:
            Documenta la función `total_offer_days` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return business_days_between(
        parse_date(item.get("FechaAceptacionBrief")),
        parse_date(item.get("FechaEntregaKAM")),
    )


def avg_total_offer_time(items):
    """
        Propósito:
            Calcula promedios operativos a partir de fechas o indicadores ya normalizados.
    
        Entradas:
            items.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    values = [
        d for d in (total_offer_days(item) for item in items)
        if d is not None
    ]

    return round(sum(values) / len(values), 2) if values else 0


def cot_recot(items):
    """
        Propósito:
            Documenta la función `cot_recot` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            items.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    c = Counter(get_version_type(item) for item in items)

    return [
        {
            "name": "Cotización",
            "value": c.get("Cotización inicial", 0),
            "field": "tipo_version",
            "raw": "Cotización inicial",
        },
        {
            "name": "Recotización",
            "value": c.get("Recotización", 0),
            "field": "tipo_version",
            "raw": "Recotización",
        },
    ]


def is_cancelada(item):
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
    e = estado_text(item)

    return (
        "cancel" in e
        or "abandon" in e
        or "inviabilidad" in e
    )


def is_brief_rechazado(item):
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
    e = estado_text(item)

    return (
        ("brief" in e and "rechaz" in e)
        or "brief sin documentos" in e
        or "brief sin documento" in e
    )


def is_entregada_kam(item):
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
    e = estado_text(item)

    return "entregada" in e and "kam" in e


def is_ganada(item):
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
    e = estado_text(item)

    return (
        "ganada" in e
        or "ganado" in e
        or "oferta ganada" in e
    )


def is_ya_gestionada_estado(item):
    """Regla única por Estado O.T. para Ya gestionadas y Entregadas.

    No usa FechaEntregaKAM para decidir si cuenta o no. La fecha solo se usa
    para ubicar la gráfica por año/mes cuando el registro ya está gestionado
    por estado.
    """
    e = estado_text(item)

    return (
        is_entregada_kam(item)
        or is_ganada(item)
        or "perdid" in e
        or "cerrad" in e
        or "pausad" in e
    )


def fecha_ya_gestionada(item):
    """Fecha de ubicación para registros ya gestionados por Estado O.T."""
    return (
        parse_date(item.get("FechaEntregaKAM"))
        or parse_date(item.get("FechaEntregaCliente"))
        or parse_date(item.get("FechaUltimaVersion"))
        or fecha_gestion_op_mes(item)
        or fecha_base_reporte(item)
    )


def count_by_year_date_getter(items, date_getter):
    """
        Propósito:
            Cuenta registros agrupados o filtrados según la regla indicada por el nombre de la función.
    
        Entradas:
            items, date_getter.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    c = Counter()

    for item in items:
        d = date_getter(item)
        if d and d <= date.today():
            c[str(d.year)] += 1

    return [
        {"name": k, "value": v, "field": "year", "raw": k}
        for k, v in sorted(c.items())
        if k != "Sin año"
    ]


def is_en_firmas(item):
    """Cuenta únicamente el estado real Circuito Firmas.

    No usa búsqueda amplia por la palabra "firma" porque eso infla el indicador
    con estados o textos relacionados que no son exactamente Circuito Firmas.
    """
    e = normkey(item.get("EstadoOfertaOT"))
    return e in {"circuito firmas", "circuito de firmas"}


def categoria_proceso(item):
    """
        Propósito:
            Documenta la función `categoria_proceso` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    e = estado_key_ascii(item)

    # Sin clasificar SOLO si Estado Oferta O.T. está vacío
    if not e:
        return "Sin clasificar"

    if is_en_firmas(item):
        return "Circuito firmas"

    # Proceso comercial
    if (
        "factibilidad doc ptes cliente" in e
        or "doc ptes cliente" in e
        or "pendiente gestion documental kam" in e
        or "pendiente gestion documental" in e
        or "sin visita - cliente" in e
    ):
        return "Proceso comercial"

    # Proceso técnico
    if (
        "estructuracion oferta aliado" in e
        or "estructuracion oferta oficina tecnica" in e
        or "sin visita aliado" in e
        or "factibilidad or estandar" in e
        or "validacion ifbp" in e
        or "cotizacion equipos enel" in e
        or "cotizacion equipos" in e
        or "visita programada" in e
    ):
        return "Proceso técnico"

    # Si tiene Estado O.T. pero no está clasificado, NO va a Sin clasificar.
    # Aquí lo dejo como Proceso técnico por defecto para no perderlo,
    # pero si prefieres, podemos crear una categoría "Otro estado activo".
    return "Proceso técnico"


def is_proceso_comercial(item):
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
    return categoria_proceso(item) == "Proceso comercial"


def is_proceso_tecnico(item):
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
    return categoria_proceso(item) == "Proceso técnico"


def is_cerrada(item):
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
    return (
        is_cancelada(item)
        or is_brief_rechazado(item)
        or is_ya_gestionada_estado(item)
    )


def estado_activa_cerrada(item):
    """
        Propósito:
            Documenta la función `estado_activa_cerrada` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if is_cerrada(item):
        return "Cerrada"

    explicit = normkey(item.get("EstadoGeneral"))

    if explicit in {"activa", "activo"}:
        return "Activa"

    if explicit in {"cerrada", "cerrado"}:
        return "Cerrada"

    return "Activa"


def is_en_proceso(item):
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
    return not is_cerrada(item)


def resumen_general(items):
    """
    Resumen superior del reporte.

    La fila principal usa una sola base para que la resta sea clara:

    Total recibidas - Brief rechazados - Canceladas / abandonadas = Total gestionadas

    En esta versión, Total recibidas cuenta todos los registros/versiones cargadas
    después de aplicar filtros. Por eso Brief rechazados y Canceladas también se
    cuentan sobre registros/versiones, no sobre OP únicas.
    """
    total_recibidas = len(items)

    brief_rechazados_items = [
        x for x in items
        if is_brief_rechazado(x)
    ]

    canceladas_items = [
        x for x in items
        if not is_brief_rechazado(x)
        and is_cancelada(x)
    ]

    gestionadas_items = [
        x for x in items
        if not is_brief_rechazado(x)
        and not is_cancelada(x)
    ]

    total_gestionadas = len(gestionadas_items)

    circuito_firmas_items = [
        x for x in items
        if is_en_firmas(x)
    ]

    ya_gestionadas_items = [
        x for x in gestionadas_items
        if is_ya_gestionada_estado(x)
    ]

    en_proceso_items = [
        x for x in gestionadas_items
        if not is_ya_gestionada_estado(x)
    ]

    proceso_comercial_items = [x for x in en_proceso_items if is_proceso_comercial(x)]
    proceso_tecnico_items = [x for x in en_proceso_items if is_proceso_tecnico(x)]
    proceso_sin_clasificar_items = [
        x for x in en_proceso_items
        if categoria_proceso(x) == "Sin clasificar"
    ]

    gestionadas_menos_en_proceso = len(ya_gestionadas_items)

    return {
        "total_recibidas": total_recibidas,
        "brief_rechazados": len(brief_rechazados_items),
        "canceladas": len(canceladas_items),
        "total_gestionadas": total_gestionadas,
        "en_proceso": len(en_proceso_items),
        "circuito_firmas": len(circuito_firmas_items),
        "proceso_comercial": len(proceso_comercial_items),
        "proceso_tecnico": len(proceso_tecnico_items),
        "proceso_sin_clasificar": len(proceso_sin_clasificar_items),
        "gestionadas_menos_en_proceso": gestionadas_menos_en_proceso,
        "ya_gestionadas": gestionadas_menos_en_proceso,

        # Compatibilidad con llaves antiguas usadas por otros componentes.
        "registros_versiones": total_recibidas,
        "op_unicas": len(latest_by_op(items)),
        "oportunidades_gestionadas": total_gestionadas,
        "total_aceptadas": max(total_recibidas - len(brief_rechazados_items), 0),
        "total_a_gestionar": total_gestionadas,
        "gran_total_analizar": total_gestionadas,
        "oportunidades_vigentes": total_gestionadas,

        "monto_total_ofertado": amount_total_all_versions(items),
        "monto_ultima_version_op": amount_latest_version_by_op(items),
        "tiempo_total_oferta": avg_total_offer_time(gestionadas_items),
    }


def get_month_value_from_field(item, *fields):
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
    acept = parse_date(item.get("FechaAceptacionBrief"))

    for field in fields:
        d = parse_date(item.get(field))

        if not d or d > date.today():
            continue

        if acept and d < acept:
            continue

        return str(d.month), str(d.year), d

    return "", "", None


def managed_items_for_timing(items):
    """Base para tiempos del reporte.

    Usa la misma fecha base del reporte y no excluye registros por estado, porque
    los promedios deben coincidir con el cálculo manual sobre las filas que
    tienen fechas de inicio y fin para cada tramo.
    """
    today = date.today()
    result = []

    for item in items:
        d = fecha_base_reporte(item)

        if d and d > today:
            continue

        result.append(item)

    return result


def avg_stage_by_month(items, filters=None):
    """
        Propósito:
            Calcula tiempos promedio por etapa agrupados por mes.
    
        Entradas:
            items, filters.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    stages = [
        ("1. Entrega de aliado", "FechaEnvioBriefAliado", "FechaEntregaOfertaAliado"),
        ("2. Construcción OT", "FechaEntregaOfertaAliado", "FechaFinConstruccionOfertaOT"),
        ("3. Circuito firmas", "FechaInicioCircuitoFirmas", "FechaEntregaKAM"),
    ]

    valid_items = managed_items_for_timing(items)
    filters = filters or {}
    data = []

    for value, label in MONTHS:
        row = {"name": label, "stages": []}
        has_any_value = False

        for name, start_key, end_key in stages:
            vals = []

            for item in valid_items:
                start_date = parse_date(item.get(start_key))
                end_date = parse_date(item.get(end_key))

                # Regla solicitada: el mes de la matriz sale de la fecha inicial
                # de cada etapa. Ej.: Brief→Entrega aliado cae en diciembre si
                # Fecha envío brief a Aliado es de diciembre, aunque el aliado
                # entregue en enero/febrero/marzo.
                if not start_date or str(start_date.month) != value or start_date > date.today():
                    continue

                if not apply_period_filter([item], filters, start_key, fallback_to_base=False):
                    continue

                days = weekdays_between_no_holidays(start_date, end_date)

                if days is not None:
                    vals.append(days)

            value_avg = round(sum(vals) / len(vals), 2) if vals else 0
            if vals:
                has_any_value = True

            row["stages"].append({
                "name": name,
                "value": value_avg,
            })

        if has_any_value:
            data.append(row)

    return data

def avg_offer_time_by_month(items):
    """
        Propósito:
            Calcula promedios operativos a partir de fechas o indicadores ya normalizados.
    
        Entradas:
            items.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    rows = []

    for value, label in MONTHS:
        vals = []

        for item in items:
            if get_report_month(item) != value:
                continue

            d = total_offer_days(item)

            if d is not None:
                vals.append(d)

        if vals:
            rows.append({
                "name": label,
                "value": round(sum(vals) / len(vals), 1),
                "field": "month",
                "raw": value,
            })

    return rows


def firmas_avg_by_month(items):
    """
        Propósito:
            Documenta la función `firmas_avg_by_month` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            items.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    rows = []

    for value, label in MONTHS:
        vals = []

        for item in items:
            m, _, _ = get_month_value_from_field(
                item,
                "FechaEntregaKAM",
                "FechaInicioCircuitoFirmas",
                "FechaUltimaVersion",
            )

            if m != value:
                continue

            d = business_days_between(
                parse_date(item.get("FechaInicioCircuitoFirmas")),
                parse_date(item.get("FechaEntregaKAM")),
            )

            if d is not None:
                vals.append(d)

        if vals:
            rows.append({
                "name": label,
                "value": round(sum(vals) / len(vals), 1),
                "field": "month",
                "raw": value,
            })

    return rows


def ans_global_by_month(items):
    """
        Propósito:
            Calcula cumplimiento de ANS global por mes.
    
        Entradas:
            items.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    rows = []

    for value, label in MONTHS:
        cumple = 0
        no = 0

        for item in items:
            if get_report_month(item) != value:
                continue

            days = total_offer_days(item)

            if days is None:
                continue

            if days <= sla_global_item(item):
                cumple += 1
            else:
                no += 1

        if cumple or no:
            rows.append({
                "name": label,
                "cumple": cumple,
                "no_cumple": no,
                "field": "month",
                "raw": value,
            })

    return rows


def ans_firmas_by_month(items, sla=2):
    """Cumplimiento ANS de estructuración: aliado -> inicio de firmas."""
    rows = []

    for value, label in MONTHS:
        cumple = 0
        no = 0

        for item in items:
            m, _, _ = get_month_value_from_field(
                item,
                "FechaInicioCircuitoFirmas",
                "FechaFinConstruccionOfertaOT",
                "FechaUltimaVersion",
            )

            if m != value:
                continue

            days = business_days_between(
                parse_date(item.get("FechaEntregaOfertaAliado")),
                parse_date(item.get("FechaInicioCircuitoFirmas")),
            )

            if days is None:
                continue

            if days <= sla:
                cumple += 1
            else:
                no += 1

        if cumple or no:
            rows.append({
                "name": label,
                "cumple": cumple,
                "no_cumple": no,
                "field": "month",
                "raw": value,
            })

    return rows


def entregadas_mes_tam(items):
    """
        Propósito:
            Documenta la función `entregadas_mes_tam` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            items.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    c = Counter()
    order = {}

    for item in items:
        tam_text = normkey(item.get("TAMOT"))

        if not any(nombre in tam_text for nombre in TAM_PERMITIDOS):
            continue

        if not (
            is_entregada_kam(item)
            or parse_date(item.get("FechaEntregaKAM"))
        ):
            continue

        m = get_report_month(item)
        y = get_report_year(item)

        if not m or not y:
            continue

        label = dict(MONTHS).get(m, m)
        key = f"{label} {y} · {norm(item.get('TAMOT'))}"

        c[key] += 1
        order[key] = (int(y), int(m), key)

    return [
        {"name": k, "value": c[k], "field": "tam", "raw": k}
        for k in sorted(c, key=lambda x: order.get(x, (9999, 99, x)))
    ]


def table_rows(items, limit=300):
    """
        Propósito:
            Prepara filas visibles para tablas del reporte limitando volumen y formateando campos clave.
    
        Entradas:
            items, limit.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    rows = []

    for item in items[:limit]:
        rows.append({
            "OP": item.get("OP") or item.get("Title") or "",
            "NombreCliente": item.get("NombreCliente", ""),
            "KAM": item.get("KAM", ""),
            "TAMOT": item.get("TAMOT", ""),
            "Segmento": item.get("Segmento", ""),
            "CantidadLuminarias": item.get("CantidadLuminarias", ""),
            "NumeroCotizacion": item.get("NumeroCotizacion") or item.get("NumeroVersion") or "",
            "EstadoOT": item.get("EstadoOfertaOT", ""),
            "EstadoOfertaOT": item.get("EstadoOfertaOT", ""),
            "Aliado": item.get("Aliado", ""),
            "Producto": item.get("Producto", ""),
            "TipoProyecto": tipo_proyecto_item(item),
            "HistoricoObservaciones": item.get("ObservacionesOP") or "",
            "Observaciones": item.get("Observaciones") or "",
            "FechaVigenciaOferta": format_date(item.get("FechaVigenciaOferta")),
            "ValorUltimaOferta": format_cop_value(item.get("ValorUltimaOferta")),
            "FechaEntregaOfertaAliado": format_date(item.get("FechaEntregaOfertaAliado")),
            "FechaInicioCircuitoFirmas": format_date(item.get("FechaInicioCircuitoFirmas")),
            "FechaEntregaOferta": format_date(item.get("FechaEntregaKAM")),
            "DiasHabilesTranscurridosOT": dias_habiles_tiempo_ot(item),
            "EstadoTiempoOT": estado_tiempo_ot(item),
            "DiasRetrasoOT": dias_retraso_tiempo_ot(item),
            "SolicitudEquipos": format_date(item.get("FechaSolicitudEquipos")),
            "ReciboCotizacionEquipos": format_date(item.get("FechaRecibidoCotizacionEquipos")),
            "EstadoCotizacionEquipos": item.get("RequiereCotizacionEquipos", ""),
            "TAMOT": item.get("TAMOT", ""),
        })

    return rows


def bp_detail_rows(items, limit=500):
    """Filas para la hoja BP del reporte Power BI.

    Esta tabla usa únicamente campos reales de SharePoint confirmados para BP.
    No incluye ANS ni tiempos calculados por otras aplicaciones.
    """
    rows = []

    for item in items[:limit]:
        rows.append({
            "Title": item.get("OP") or item.get("Title") or "",
            "Origen de la oferta": item.get("OrigenOferta", ""),
            "Nombre cliente": item.get("NombreCliente", ""),
            "KAM": item.get("KAM", ""),
            "Segmento": item.get("Segmento", ""),
            "Producto": item.get("Producto", ""),
            "Número de versión": item.get("NumeroVersion", ""),
            "Fecha última cotización": format_date(item.get("FechaUltimaVersion")),
            "Aliado": item.get("Aliado", ""),
            "TAM O.T.": item.get("TAMOT", ""),
            "Estado Oferta O.T.": item.get("EstadoOfertaOT", ""),
            "Fecha Aceptación Brief": format_date(item.get("FechaAceptacionBrief")),
            "Fecha envío brief a Aliado": format_date(item.get("FechaEnvioBriefAliado")),
            "Fecha real contacto Cliente": format_date(item.get("FechaRealContactoCliente")),
            "Fecha programación visita": format_date(item.get("FechaProgramacionVisita")),
            "Fecha de visita al Cliente": format_date(item.get("FechaVisitaCliente")),
            "Requiere Factibilidad": item.get("RequiereFactibilidad", ""),
            "Fecha solicitud de Factibilidad": format_date(item.get("FechaSolicitudFactibilidad")),
            "Fecha radicación Factibilidad": format_date(item.get("FechaRadicacionFactibilidad")),
            "Número de factibilidad": item.get("NumeroFactibilidad", ""),
            "Observación factibilidad": item.get("ObservacionFactibilidad", ""),
            "Requiere cotización de equipos": item.get("RequiereCotizacionEquipos", ""),
            "Fecha solicitud de equipos": format_date(item.get("FechaSolicitudEquipos")),
            "Fecha recibido cotización de equipos": format_date(item.get("FechaRecibidoCotizacionEquipos")),
            "Fecha entrega oferta por parte Aliado": format_date(item.get("FechaEntregaOfertaAliado")),
            "Fecha Fin construcción oferta OT": format_date(item.get("FechaFinConstruccionOfertaOT")),
            "Fecha Entrega Validación Staff": format_date(item.get("FechaEntregaValidacionStaff")),
            "Fecha Inicio Circuito de Firmas": format_date(item.get("FechaInicioCircuitoFirmas")),
            "Fecha de Entrega a KAM": format_date(item.get("FechaEntregaKAM")),
            "Fecha entrega oferta al Cliente": format_date(item.get("FechaEntregaCliente")),
            "Valor última oferta antes de IVA": format_cop_value(item.get("ValorUltimaOferta")),
            "Fecha de Vigencia de Oferta": format_date(item.get("FechaVigenciaOferta")),
            "Historico Observaciones": item.get("ObservacionesOP", ""),
            "Observaciones": item.get("Observaciones", ""),
            "Estado": item.get("EstadoGeneral", ""),
            "Tipo py": tipo_proyecto_item(item) or "Sin info",
            "Requiere visitaa ?": item.get("RequiereVisita", ""),
            "Cantidad Luminarias": item.get("CantidadLuminarias", ""),
            "Número CRM": item.get("NumeroCRM", ""),
            "Canal de venta BP": item.get("CanalVentaBP", ""),
            "CC / NIT cliente": item.get("CCNITCliente", ""),
            "Persona de contacto BP": item.get("PersonaContactoBP", ""),
            "Teléfono contacto BP": item.get("TelefonoContactoBP", ""),
            "Dirección BP": item.get("DireccionBP", ""),
            "Zona U.O.": item.get("ZonaUO", ""),
            "Localidad / Municipio": item.get("LocalidadMunicipio", ""),
            "Subzona U.O.": item.get("SubzonaUO", ""),
            "Requerimiento BP": item.get("RequerimientoBP", ""),
            "Radicado recibo de obra": item.get("RadicadoReciboObra", ""),
            "Fecha solicitud ODS visita": format_date(item.get("FechaSolicitudODSVisita")),
            "Número ODS visita": item.get("NumeroODSVisita", ""),
            "Fecha envío ODS visita Planeación a Back Office": format_date(item.get("FechaEnvioODSVisitaPlaneacionBackOffice")),
            "Fecha envío ODS visita Back Office a U.O.": format_date(item.get("FechaEnvioODSVisitaBackOfficeUO")),
            "Número S visita": item.get("NumeroSVisita", ""),
            "Fecha visita U.O.": format_date(item.get("FechaVisitaUO")),
            "Fecha solicitud presupuesto BP": format_date(item.get("FechaSolicitudPresupuestoBP")),
            "Fecha envío presupuesto U.O. a Planeación/Back": format_date(item.get("FechaEnvioPresupuestoUOPlaneacionBack")),
            "Fecha envío presupuesto CREG015": format_date(item.get("FechaEnvioPresupuestoCREG015")),
            "Fecha envío presupuesto final a canal": format_date(item.get("FechaEnvioPresupuestoFinalCanal")),
            "Valor presupuesto final U.O. antes IVA": format_cop_value(item.get("ValorPresupuestoUOAntesIVA")),
            "Valor presupuesto final U.O. después CREG015": format_cop_value(item.get("ValorPresupuestoUODespuesCREG015")),
            "Valor presupuesto Salesforce XC": format_cop_value(item.get("ValorPresupuestoSalesforceXC")),
            "Valor margen Enel X antes IVA": format_cop_value(item.get("ValorMargenEnelXAntesIVA")),
            "Acta de visita": item.get("ActaVisita", ""),
            "Caso nota crédito": item.get("CasoNotaCredito", ""),
            "Caso XC": item.get("CasoXC", ""),
            "Causal ejecución BP": item.get("CausalEjecucionBP", ""),
            "Causal presupuesto BP": item.get("CausalPresupuestoBP", ""),
            "Estado proyecto BP": item.get("EstadoProyectoBP", ""),
            "Fecha confirmación de pago": format_date(item.get("FechaConfirmacionPago")),
            "Fecha confirmación respuesta cliente": format_date(item.get("FechaConfirmacionRespuestaCliente")),
            "Fecha creación deudor": format_date(item.get("FechaCreacionDeudor")),
            "Fecha ejecución U.O.": format_date(item.get("FechaEjecucionUO")),
            "Fecha entrega factura": format_date(item.get("FechaEntregaFactura")),
            "Fecha envío ODS ejecución Back Office a U.O.": format_date(item.get("FechaEnvioODSEjecucionBackOfficeUO")),
            "Fecha envío ODS ejecución Planeación a Back Office": format_date(item.get("FechaEnvioODSEjecucionPlaneacionBackOffice")),
            "Fecha solicitud deudor": format_date(item.get("FechaSolicitudDeudor")),
            "Fecha solicitud factura": format_date(item.get("FechaSolicitudFactura")),
            "Fecha solicitud ODS ejecución": format_date(item.get("FechaSolicitudODSEjecucion")),
            "Margen final Enel X %": item.get("MargenFinalEnelXPorcentaje", ""),
            "Número AGP": item.get("NumeroAGP", ""),
            "Número deudor SAP": item.get("NumeroDeudorSAP", ""),
            "Número factura de venta": item.get("NumeroFacturaVenta", ""),
            "Número ODS ejecución": item.get("NumeroODSEjecucion", ""),
            "Responsable estado proyecto BP": item.get("ResponsableEstadoProyectoBP", ""),
            "Valor facturado final U.O. / LM antes IVA": format_cop_value(item.get("ValorFacturadoFinalUOLMAntesIVA")),
            "Valor facturado margen Enel X antes IVA": format_cop_value(item.get("ValorFacturadoMargenEnelXAntesIVA")),
            "Valor presupuesto final cliente antes IVA": format_cop_value(item.get("ValorPresupuestoFinalClienteAntesIVA")),
        })

    return rows


def mobility_potencia_rows(items):
    """Cuenta cada potencia informada en cualquiera de los campos Potencia cargador N."""
    counts = {}
    for item in items:
        raw = str(item.get("PotenciaCargador") or "").strip()
        if not raw:
            continue
        values = [x.strip() for x in raw.split("|") if x.strip()]
        for value in values:
            counts[value] = counts.get(value, 0) + 1
    return [
        {"label": label, "value": value}
        for label, value in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]


def mobility_detail_rows(items, limit=700):
    """Filas de detalle específicas para Mobility."""
    rows = []
    for item in items[:limit]:
        rows.append({
            "OP": item.get("OP") or item.get("Title") or "",
            "ID Forms Mobility": item.get("IDFormsMobility", ""),
            "Nombre cliente": item.get("NombreCliente", ""),
            "KAM": item.get("KAM", ""),
            "Vendedor": item.get("Vendedor", ""),
            "Canal": item.get("CanalMobility", ""),
            "Tipo servicio Mobility": item.get("ServicioMobility", ""),
            "Tipo de cliente": item.get("TipoClienteMobility", ""),
            "Estado Oferta O.T.": item.get("EstadoOfertaOT", ""),
            "Aliado": item.get("Aliado", ""),
            "Contacto": item.get("ContactoMobility", ""),
            "Celular / WhatsApp": item.get("CelularMobility", ""),
            "Dirección": item.get("DireccionMobility", ""),
            "Localidad": item.get("LocalidadMobility", ""),
            "Ciudad": item.get("CiudadMobility", ""),
            "Departamento": item.get("DepartamentoMobility", ""),
            "Marca vehículo": item.get("MarcaVehiculo", ""),
            "Modelo vehículo": item.get("ModeloVehiculo", ""),
            "Marca cargador": item.get("MarcaCargador", ""),
            "Tipo cargador": item.get("TipoCargador", ""),
            "Potencia cargador": item.get("PotenciaCargador", ""),
            "Requiere instalación": item.get("RequiereInstalacionMobility", ""),
            "Requiere compra cargador": item.get("RequiereCompraCargador", ""),
            "Cantidad cargadores": item.get("CantidadCargadores", ""),
            "Cantidad instalaciones": item.get("CantidadInstalaciones", ""),
            "Tipo pagador": item.get("TipoPagador", ""),
            "Nombre pagador": item.get("NombrePagador", ""),
            "Documento pagador": item.get("DocumentoPagador", ""),
            "Fecha visita": format_date(item.get("FechaVisitaMobility")),
            "Fecha instalación": format_date(item.get("FechaInstalacionMobility")),
            "Fecha entrega cargador": format_date(item.get("FechaEntregaCargador")),
            "Valor instalación": format_cop_value(item.get("ValorInstalacionMobility")),
            "Valor cargador": format_cop_value(item.get("ValorCargadorMobility")),
            "IVA": item.get("IVAMobility", ""),
            "Número factura": item.get("NumeroFacturaMobility", ""),
            "Número oferta cargador": item.get("NumeroOfertaCargador", ""),
            "Fecha Inicio Circuito de Firmas": format_date(item.get("FechaInicioCircuitoFirmas")),
            "Fecha de Entrega a KAM": format_date(item.get("FechaEntregaKAM")),
            "Observaciones vendedor": item.get("ObservacionesVendedor", ""),
            "Observaciones": item.get("Observaciones", ""),
        })
    return rows


SLA_CONSTRUCCION_OT_DIAS = 2


def detalle_tiempo_ot(item):
    """
    Calcula la alerta de tiempo OT desde FechaEntregaOfertaAliado hasta hoy.

    Regla visible solicitada:
    - 1 día hábil  = A tiempo OT / 0
    - 2 días hábiles = A tiempo OT / 0
    - 3 días hábiles = En retraso OT / 1 día hábil de retraso
    - 4 días hábiles = En retraso OT / 2 días hábiles de retraso
    - 8 días hábiles = En retraso OT / 6 días hábiles de retraso

    Importante:
    - No usa FechaFinConstruccionOfertaOT.
    - No usa FechaEntregaOfertaCliente.
    - No usa lógica de cerrada.
    - Siempre calcula contra hoy.
    """
    inicio = parse_date(item.get("FechaEntregaOfertaAliado"))

    if not inicio:
        return {
            "dias": "",
            "tiempo_ot": "Sin fecha entrega aliado",
            "estado": "Sin fecha entrega aliado",
            "retraso": "",
        }

    corte = date.today()
    dias = business_days_between(inicio, corte)

    if dias is None:
        return {
            "dias": "",
            "tiempo_ot": "Sin cálculo",
            "estado": "Sin cálculo",
            "retraso": "",
        }

    if dias <= SLA_CONSTRUCCION_OT_DIAS:
        return {
            "dias": dias,
            "tiempo_ot": "A tiempo OT",
            "estado": "A tiempo OT",
            "retraso": "0",
        }

    retraso = dias - SLA_CONSTRUCCION_OT_DIAS
    unidad = "día hábil" if retraso == 1 else "días hábiles"
    texto_retraso = f"{retraso} {unidad} de retraso"

    return {
        "dias": dias,
        "tiempo_ot": texto_retraso,
        "estado": "En retraso OT",
        "retraso": texto_retraso,
    }


def dias_habiles_tiempo_ot(item):
    """
        Propósito:
            Documenta la función `dias_habiles_tiempo_ot` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    # Esta columna se muestra en la 
    #. Por solicitud del usuario,
    # no debe mostrar solo el número; debe mostrar A tiempo OT o X días hábiles de retraso.
    return detalle_tiempo_ot(item).get("tiempo_ot", "")


def estado_tiempo_ot(item):
    """
        Propósito:
            Documenta la función `estado_tiempo_ot` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return detalle_tiempo_ot(item).get("estado", "")


def dias_retraso_tiempo_ot(item):
    """
        Propósito:
            Documenta la función `dias_retraso_tiempo_ot` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return detalle_tiempo_ot(item).get("retraso", "")

def selected_filter_values(filters, key):
    """
        Propósito:
            Documenta la función `selected_filter_values` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            filters, key.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return {
        str(x) for x in filters.get(key, [])
        if str(x).strip()
    }


def filters_without_period(filters):
    """
        Propósito:
            Documenta la función `filters_without_period` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            filters.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    filters = dict(filters or {})
    filters.pop("years", None)
    filters.pop("months", None)
    filters.pop("days", None)
    return filters


def apply_period_filter(items, filters, date_field="FechaAceptacionBrief", fallback_to_base=False):
    """
        Propósito:
            Documenta la función `apply_period_filter` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            items, filters, date_field, fallback_to_base.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    years = selected_filter_values(filters, "years")
    months = selected_filter_values(filters, "months")
    days = selected_filter_values(filters, "days")

    if not years and not months and not days:
        return list(items)

    result = []

    for item in items:
        if date_field in (None, "", "base", "FechaAceptacionBrief"):
            d = fecha_base_reporte(item)
        else:
            d = parse_date(item.get(date_field))
            if not d and fallback_to_base:
                d = fecha_base_reporte(item)

        if not d:
            continue

        if years and str(d.year) not in years:
            continue

        if months and str(d.month) not in months:
            continue

        if days and str(d.day) not in days:
            continue

        result.append(item)

    return result


def filter_report_items(items, filters):
    """
        Propósito:
            Aplica filtros específicos del reporte a la base de registros.
    
        Entradas:
            items, filters.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    def selected(key):
        """
            Propósito:
                Documenta la función `selected` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                key.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        return {
            str(x) for x in filters.get(key, [])
            if str(x).strip()
        }
    years = selected("years")
    months = selected("months")
    days = selected("days")
    estados = selected("estados_ot")
    tipos = selected("tipos_proyecto")
    productos = selected("productos")
    segmentos = selected("segmentos")
    aliados = selected("aliados")
    estados_ac = selected("estados_activa_cerrada") or selected("estado_activa_cerrada")

    result = []

    for item in items:
        if years and get_report_year(item) not in years:
            continue

        if months and get_report_month(item) not in months:
            continue

        d = fecha_base_reporte(item)

        if days and (not d or str(d.day) not in days):
            continue

        if estados and norm(item.get("EstadoOfertaOT")) not in estados:
            continue

        if tipos and tipo_proyecto_item(item) not in tipos:
            continue

        if productos and norm(item.get("Producto")) not in productos:
            continue

        if segmentos and norm(item.get("Segmento")) not in segmentos:
            continue

        if aliados and norm(item.get("Aliado")) not in aliados:
            continue

        if estados_ac and estado_activa_cerrada(item) not in estados_ac:
            continue

        result.append(item)

    return result


def has_any_estado(item, keywords):
    """
        Propósito:
            Documenta la función `has_any_estado` dentro del módulo `reports.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            item, keywords.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    e = estado_text(item)
    return any(k in e for k in keywords)



def es_producto_ap_lighting(item):
    """Identifica productos AP / Navidad desde el valor real de SharePoint.

    No agrega opciones al formulario ni a los filtros; solo clasifica para esta
    hoja del reporte cuando el producto ya exista en los datos.
    """
    producto = normkey(item.get("Producto"))
    if not producto:
        return False

    return (
        producto == "navidad"
        or producto.startswith("navidad ")
        or producto == "ap"
        or producto.startswith("ap ")
        or producto.endswith(" ap")
        or " lighting" in producto
        or producto.startswith("lighting")
        or "lightning" in producto
    )


def es_producto_pv(item):
    """
        Propósito:
            Evalúa una condición de negocio en español sobre un registro y devuelve True/False.
    
        Entradas:
            item.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    producto = normkey(item.get("Producto"))
    return producto == "pv" or "pv" in producto


def build_report(items, filters=None):
    """
        Propósito:
            Construye el objeto completo del reporte gerencial con tarjetas, tablas, series temporales y métricas de ANS.
    
        Entradas:
            items, filters.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    filters = filters or {}

    filtered = filter_report_items(items, filters)
    filtered_no_period = filter_report_items(items, filters_without_period(filters))
    latest = latest_by_op(filtered)
    timing_items = managed_items_for_timing(filtered)
    general_summary = resumen_general(filtered)
    general_summary["monto_ultima_version_op"] = amount_latest_version_by_op_for_report_filters(items, filters)

    ya_gestionadas_items_no_period = [
        x for x in filtered_no_period
        if not is_brief_rechazado(x)
        and not is_cancelada(x)
        and is_ya_gestionada_estado(x)
    ]

    entregadas_items_period = apply_period_filter_date_getter(
        ya_gestionadas_items_no_period,
        filters,
        fecha_ya_gestionada,
    )

    gestionadas_mes_items_period = apply_period_filter_date_getter(
        [
            x for x in filtered_no_period
            if not is_brief_rechazado(x)
            and not is_cancelada(x)
            and fecha_gestion_op_mes(x)
        ],
        filters,
        fecha_gestion_op_mes,
    )

    pendientes_kam = [
        x for x in latest
        if has_any_estado(x, ESTADOS_PENDIENTES_KAM)
        and "planeacion de la red" not in estado_text(x)
        and not is_entregada_kam(x)
    ]

    pendientes_contrato = [
        x for x in latest
        if has_any_estado(x, ESTADOS_PENDIENTES_CONTRATO)
        and "oficina técnica" not in estado_text(x)
        and "oficina tecnica" not in estado_text(x)
    ]

    pv = [
        x for x in latest
        if es_producto_pv(x)
    ]

    pv = [
        x for x in pv
        if estado_text(x) in ESTADOS_PV_PERMITIDOS
    ]

    ap_lighting = [
        x for x in latest
        if es_producto_ap_lighting(x)
    ]

    bp_items = [
        x for x in latest
        if normkey(x.get("Producto")) == "bp"
        or "boletin de pago" in normkey(x.get("OrigenOferta"))
        or "boletín de pago" in lower(x.get("OrigenOferta"))
    ]

    mobility_items = [
        x for x in latest
        if normkey(x.get("Segmento")) == "mobility"
        or normkey(x.get("Producto")) == "mobility"
        or "mobility" in normkey(x.get("Segmento"))
        or "mobility" in normkey(x.get("Producto"))
    ]

    vigentes = [
        x for x in latest
        if ("circuito" in estado_text(x) or is_entregada_kam(x))
        and parse_date(x.get("FechaVigenciaOferta"))
        and parse_date(x.get("FechaVigenciaOferta")) > date.today()
    ]

    en_proceso = [
        x for x in filtered
        if not is_brief_rechazado(x)
        and not is_cancelada(x)
        and is_en_proceso(x)
    ]

    # Hoja "Ofertas en proceso": debe cuadrar con En proceso - Circuito firmas.
    # Por eso usa la misma base de en_proceso y no latest_by_op.
    jefatura = [
        x for x in en_proceso
        if not is_en_firmas(x)
    ]

    alertas_matrix = [
    x for x in latest
    if normkey(x.get("EstadoOfertaOT")) in ESTADOS_ALERTA_MATRIX_KEYS
    ]

    alertas_dona = [
    x for x in latest
    if normkey(x.get("EstadoOfertaOT")) in ESTADOS_ALERTA_DONA_KEYS
    ]

    return {
        "filters_options": {
            "years": sorted({
                get_report_year(x)
                for x in items
                if get_report_year(x)
            }),
            "months": [
                {"value": v, "text": t}
                for v, t in MONTHS
            ],
            "days": [str(i) for i in range(1, 32)],
            "estados_activa_cerrada": ["Activa", "Cerrada"],
            "estados_ot": sorted({
                norm(x.get("EstadoOfertaOT"))
                for x in items
                if norm(x.get("EstadoOfertaOT")) != "Sin dato"
            }),
            "tipos_proyecto": sorted({
                tipo_proyecto_item(x)
                for x in items
                if tipo_proyecto_item(x)
            }),
            "productos": sorted({
                norm(x.get("Producto"))
                for x in items
                if norm(x.get("Producto")) != "Sin dato"
            }),
            "segmentos": sorted({
                norm(x.get("Segmento"))
                for x in items
                if norm(x.get("Segmento")) != "Sin dato"
            }),
            "aliados": sorted({
                norm(x.get("Aliado"))
                for x in items
                if norm(x.get("Aliado")) != "Sin dato"
            }),
        },

        "general": {
            **general_summary,
            "cot_recot": cot_recot(filtered),
            "por_producto": count_rows(filtered, "Producto"),
            "por_segmento": count_rows(filtered, "Segmento"),
            # Esta gráfica se calcula únicamente sobre las ya gestionadas.
            "por_tipo": count_rows(filtered, "TipoProyecto", use_tipo=True),
        },

        "detalle_op": {
            "total": general_summary.get("total_gestionadas", 0),
            "por_anio_recibidas": count_by_year(filtered),
            "por_anio_entregadas": count_by_year_date_getter(
                entregadas_items_period,
                fecha_ya_gestionada,
            ),
            "por_mes_recibidas": count_by_month(filtered),
            "por_mes_gestionadas": count_by_month_date_getter(
                gestionadas_mes_items_period,
                fecha_gestion_op_mes,
            ),
            "por_producto": count_rows(filtered, "Producto"),
            "por_segmento": count_rows(filtered, "Segmento"),
        },

        "tiempos_global": {
            "matriz_mes_estado": count_by_two_fields(
                [
                    x for x in timing_items
                    if is_entregada_kam(x) or is_ganada(x)
                ],
                "FechaUltimaVersion",
                "EstadoOfertaOT",
                use_month_rows=True,
            ),
            "matriz_mes_estado_rows": table_rows([
                x for x in timing_items
                if is_entregada_kam(x) or is_ganada(x)
            ]),
            "etapas": avg_stage_by_month(filtered_no_period, filters),
        },

        "detalle_ofertas": {
            "entregadas_mes": count_by_month_date_getter(
                entregadas_items_period,
                fecha_ya_gestionada,
            ),
            "tiempo_mes": avg_offer_time_by_month(timing_items),
            "ans": ans_global_by_month(timing_items),
        },

        "ans_ot": {
            "monto": general_summary.get("monto_total_ofertado", 0),
            "tiempo": general_summary.get("tiempo_total_oferta", 0),
            "entregadas_tam": entregadas_mes_tam(filtered),
            "firmas_mes": firmas_avg_by_month(filtered),
            "ans": ans_firmas_by_month(filtered),
        },

        "pendientes_kam": {
            "matrix": count_by_two_fields(
                pendientes_kam,
                "EstadoOfertaOT",
                "Segmento",
            ),
            "dona": count_rows(pendientes_kam, "Segmento"),
            "kam": count_by_two_fields(
                pendientes_kam,
                "KAM",
                "EstadoOfertaOT",
            ),
            "rows": table_rows(pendientes_kam),
        },

        "pendientes_contratos": {
            "matrix": count_by_two_fields(
                pendientes_contrato,
                "EstadoOfertaOT",
                "Aliado",
            ),
            "dona": count_rows(pendientes_contrato, "EstadoOfertaOT"),
            "rows": table_rows(pendientes_contrato),
        },

        "pv": {
            "matrix": count_by_two_fields(
                pv,
                "EstadoOfertaOT",
                "Producto",
            ),
            "dona": count_rows(pv, "EstadoOfertaOT"),
            "rows": table_rows([
                x for x in pv
                if not is_entregada_kam(x)
            ]),
        },

        "ap_lighting": {
            "matrix": count_by_two_fields(
                ap_lighting,
                "EstadoOfertaOT",
                "Producto",
            ),
            "dona": count_rows(ap_lighting, "EstadoOfertaOT"),
            "por_producto": count_rows(ap_lighting, "Producto"),
            "rows": table_rows(ap_lighting),
        },

        "bp": {
            "total": len(bp_items),
            "por_estado": count_rows(bp_items, "EstadoProyectoBP"),
            "por_tipo": count_rows(bp_items, "TipoProyecto", use_tipo=True),
            "por_subzona": count_rows(bp_items, "SubzonaUO"),
            "rows": bp_detail_rows(bp_items),
        },

        "mobility": {
            "total": len(mobility_items),
            "entregadas_kam": sum(1 for x in mobility_items if is_entregada_kam(x)),
            # Valor total de las ofertas Mobility (antes de IVA), usando el mismo campo monetario oficial.
            "valor_total": format_cop_value(sum(to_number(x.get("ValorUltimaOferta")) for x in mobility_items)),
            "por_estado": count_rows(mobility_items, "EstadoOfertaOT"),
            "por_servicio": count_rows(mobility_items, "ServicioMobility"),
            "por_tipo_cliente": count_rows(mobility_items, "TipoClienteMobility"),
            "por_aliado": count_rows(mobility_items, "Aliado"),
            "por_marca_cargador": count_rows(mobility_items, "MarcaCargador"),
            "por_potencia": mobility_potencia_rows(mobility_items),
            "rows": mobility_detail_rows(mobility_items),
        },

        "vigentes_proceso": {
            "vigentes": table_rows(vigentes),
            "en_proceso_total": len(en_proceso),
            "en_proceso": table_rows(en_proceso),
        },

        "jefatura": {
            "matrix": count_by_two_fields(
                jefatura,
                "EstadoOfertaOT",
                "Aliado",
            ),
            "dona": count_rows(jefatura, "EstadoOfertaOT"),
            "rows": table_rows(jefatura),
        },

        "alerta_tiempos": {
            "matrix": count_by_two_fields(
                alertas_matrix,
                "EstadoOfertaOT",
                "Aliado",
            ),
            "dona": count_rows(alertas_dona, "EstadoOfertaOT"),
            "rows": table_rows(alertas_matrix),
        },
    }