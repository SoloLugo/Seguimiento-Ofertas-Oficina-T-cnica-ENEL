"""Punto de entrada Flask: define APIs, filtros comunes, conexión con SharePoint y arranque local en puerto 5001."""

# Código identificado para Valentina Becerra. Marca interna; no se muestra en la interfaz.

# ============================================================
# DOCUMENTACIÓN GENERAL DEL MÓDULO
# ============================================================
# Controlador principal Flask: registra vistas HTML, APIs REST, filtros comunes, normalización de formularios y arranque local de la aplicación.
#
# Criterio de mantenimiento:
# - Mantener aquí únicamente lógica propia de este módulo.
# - Evitar valores quemados cuando puedan venir de configuración o SharePoint.
# - Conservar nombres canónicos de campos para no romper filtros, reportes ni exportaciones.
# - Antes de cambiar reglas de ANS, tiempos o clasificación, validar impacto en reportes y Excel/PDF.
# ============================================================

from catalog_names import canonical_catalog_value
import os
import threading
import time
import webbrowser

from flask import Flask, jsonify, request, render_template

from sharepoint_client import sp_client
from stats import (
    build_stats,
    build_time_detail,
    get_year_from_item,
    get_month_from_item,
    get_version_type,
    get_filter_options,
)
from reports import build_report, REPORT_CALC_VERSION


app = Flask(__name__)

# Caché liviana para respuestas pesadas de estadísticas/reportes.
# Evita recalcular todo cuando el usuario solo cambia/retoma filtros dentro del TTL.
_STATS_REPORT_CACHE = {}
_STATS_REPORT_CACHE_TTL = 900


def clear_stats_report_cache():
    _STATS_REPORT_CACHE.clear()


def cached_json_payload(cache_key, builder, force=False):
    now = time.time()
    if not force:
        cached = _STATS_REPORT_CACHE.get(cache_key)
        if cached and (now - cached[0]) < _STATS_REPORT_CACHE_TTL:
            return cached[1]

    payload = builder()
    _STATS_REPORT_CACHE[cache_key] = (now, payload)
    return payload





def compact_list_item(item):
    """DTO liviano para listado/búsqueda. Evita enviar cientos de campos al navegador."""
    keys = (
        "Id", "Title", "OP", "NumeroVersion", "NombreCliente", "KAM",
        "Segmento", "Producto", "EstadoOfertaOT", "EstadoGeneral",
        "FechaUltimaVersion", "FechaAceptacionBrief", "ValorUltimaOferta",
        "Aliado", "NumeroCRM"
    )
    return {key: item.get(key) for key in keys}

def parse_money_value(value):
    """
        Propósito:
            Convierte valores monetarios escritos en formatos comunes de Colombia/Excel/SharePoint a número decimal para cálculos.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if value in (None, ""):
        return 0.0
    text = str(value).strip().replace("$", "").replace("COP", "")
    text = text.replace(" ", "")
    if text.count(".") > 1 and "," not in text:
        text = text.replace(".", "")
    elif "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except Exception:
        return 0.0


def is_yes_value(value):
    """
        Propósito:
            Normaliza respuestas tipo Sí/No y devuelve verdadero cuando el valor representa una afirmación.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return str(value or "").strip().lower() in {"si", "sí", "s", "yes", "true", "1"}


def derive_tipo_proyecto_from_form(form_data):
    """
        Propósito:
            Clasifica automáticamente el tipo de proyecto según valor antes de IVA y requerimiento de factibilidad.
    
        Entradas:
            form_data.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    valor = parse_money_value(form_data.get("Valor última oferta antes de IVA"))
    requiere_fact = is_yes_value(form_data.get("Requiere Factibilidad"))
    if valor <= 0:
        return form_data.get("Tipo de proyecto", "")
    if valor < 100_000_000:
        return "Pequeño con factibilidad" if requiere_fact else "Pequeño"
    if valor < 500_000_000:
        return "Mediano"
    if valor < 1_000_000_000:
        return "Grande"
    return "Megaproyecto"




def derive_estado_general_from_estado_ot(estado_ot):
    """Devuelve Cerrada cuando el Estado Oferta O.T. corresponde a un cierre del flujo."""
    text = str(estado_ot or "").strip().lower()

    closed_keywords = [
        "entregada a kam",
        "entregada",
        "ganada",
        "ganado",
        "perdida",
        "perdido",
        "cancel",
        "abandon",
        "rechaz",
        "cerrad",
        "inviabilidad",
    ]

    if any(keyword in text for keyword in closed_keywords):
        return "Cerrada"

    return ""

def normalize_form_payload(form_data):
    """
        Propósito:
            Homologa campos equivalentes del formulario antes de enviarlos a SharePoint, preservando datos ya diligenciados.
    
        Entradas:
            form_data.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    form_data = dict(form_data or {})
    for field in ("Segmento", "Producto", "Aliado"):
        if field in form_data:
            form_data[field] = canonical_catalog_value(field, form_data[field])

    # Si SharePoint ya trae o el usuario diligenció Tipo py / TipoProyecto,
    # se conserva ese valor. Solo se calcula automáticamente cuando viene vacío.
    tipo_existente = (
        form_data.get("Tipo de proyecto")
        or form_data.get("TipoProyecto")
        or form_data.get("Tipo py")
        or form_data.get("Tipo Py")
    )

    if tipo_existente:
        form_data["Tipo py"] = tipo_existente
        form_data["Tipo de proyecto"] = tipo_existente

    estado_ot = (
        form_data.get("Estado Oferta O.T.")
        or form_data.get("EstadoOfertaOT")
        or form_data.get("Estado Oferta OT")
        or form_data.get("Estado O.T.")
        or form_data.get("Estado OT")
    )

    estado_general_derivado = derive_estado_general_from_estado_ot(estado_ot)

    # Regla de negocio: si el estado O.T. ya representa cierre del flujo
    # —por ejemplo "Entregada a KAM"— el Estado general debe guardarse como Cerrada.
    if estado_general_derivado:
        form_data["Estado"] = estado_general_derivado
        form_data["EstadoGeneral"] = estado_general_derivado

    # No se inventa Tipo py cuando viene vacío: la lista real de SharePoint puede tenerlo sin dato.
    return form_data


def normalize_list(values):
    """
    Recibe los valores repetidos de querystring.
    Ejemplo: ?year=2024&year=2025

    También soporta valores separados por coma por si alguna URL llega así:
    ?year=2024,2025
    """
    result = []

    for value in values:
        if value is None:
            continue

        for part in str(value).split(","):
            clean = part.strip()
            if clean and clean not in result:
                result.append(clean)

    return result


def get_common_filters():
    """
        Propósito:
            Lee todos los filtros comunes enviados por la interfaz y los devuelve en una estructura estándar.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return {
        "years": normalize_list(request.args.getlist("year")),
        "months": normalize_list(request.args.getlist("month")),
        "days": normalize_list(request.args.getlist("day")),
        "segmentos": normalize_list(request.args.getlist("segmento")),
        "productos": normalize_list(request.args.getlist("producto")),
        "estados_generales": normalize_list(request.args.getlist("estado_general")),
        "tipos_version": normalize_list(request.args.getlist("tipo_version")),
        "estados_ot": normalize_list(request.args.getlist("estado_ot")),
        "tipos_proyecto": normalize_list(request.args.getlist("tipo_proyecto")),
        "aliados": normalize_list(request.args.getlist("aliado")),
        "estados_activa_cerrada": normalize_list(request.args.getlist("estado_ac")),
    }


def force_refresh_requested():
    """
        Propósito:
            Documenta la función `force_refresh_requested` dentro del módulo `app.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return str(request.args.get("refresh") or request.args.get("force") or "").strip().lower() in {"1", "true", "si", "sí", "yes"}


def item_matches_any(selected_values, item_value):
    """
        Propósito:
            Documenta la función `item_matches_any` dentro del módulo `app.py` y centraliza una parte de la lógica de la aplicación.
    
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


def filter_items_for_stats_multi(items, filters):
    """
        Propósito:
            Aplica filtros acumulados a los ítems públicos de SharePoint para estadísticas y reportes.
    
        Entradas:
            items, filters.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    filtered = []

    years = filters.get("years", [])
    months = filters.get("months", [])
    segmentos = filters.get("segmentos", [])
    productos = filters.get("productos", [])
    estados_generales = filters.get("estados_generales", [])
    tipos_version = filters.get("tipos_version", [])
    estados_ot = filters.get("estados_ot", [])
    tipos_proyecto = filters.get("tipos_proyecto", [])
    aliados = filters.get("aliados", [])
    days = filters.get("days", [])
    estados_activa_cerrada = filters.get("estados_activa_cerrada", [])

    from stats import parse_date, lower, get_estado_oferta_ot
    def estado_ac(item):
        """
            Propósito:
                Documenta la función `estado_ac` dentro del módulo `app.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                item.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        e = lower(get_estado_oferta_ot(item))
        cerrada = any(x in e for x in ["entregada", "ganada", "ganado", "perdid", "cancel", "abandon", "rechaz", "cerrad", "inviabilidad"])
        if cerrada:
            return "Cerrada"

        exp = str(item.get("EstadoGeneral", "") or "").strip().lower()
        if exp in {"activa", "activo"}: return "Activa"
        if exp in {"cerrada", "cerrado"}: return "Cerrada"
        return "Activa"

    for item in items:
        item_year = get_year_from_item(item)
        item_month = get_month_from_item(item)
        item_date = parse_date(item.get("FechaUltimaVersion") or item.get("FechaAceptacionBrief") or item.get("FechaEntregaKAM"))
        item_day = str(item_date.day) if item_date else ""
        item_segmento = str(item.get("Segmento", "") or "").strip()
        item_producto = str(item.get("Producto", "") or "").strip()
        item_estado_general = str(item.get("EstadoGeneral", "") or "").strip()
        item_tipo_version = get_version_type(item)
        item_estado_ot = str(item.get("EstadoOfertaOT", "") or "").strip()
        item_tipo_proyecto = str(item.get("TipoProyecto", "") or "").strip()
        item_aliado = str(item.get("Aliado", "") or "").strip()

        if not item_matches_any(years, item_year):
            continue

        if not item_matches_any(months, item_month):
            continue

        if not item_matches_any(days, item_day):
            continue

        if not item_matches_any(segmentos, item_segmento):
            continue

        if not item_matches_any(productos, item_producto):
            continue

        if not item_matches_any(estados_generales, item_estado_general):
            continue

        if not item_matches_any(tipos_version, item_tipo_version):
            continue

        if not item_matches_any(estados_ot, item_estado_ot):
            continue

        if not item_matches_any(tipos_proyecto, item_tipo_proyecto):
            continue

        if not item_matches_any(aliados, item_aliado):
            continue

        if not item_matches_any(estados_activa_cerrada, estado_ac(item)):
            continue

        filtered.append(item)

    return filtered


def month_label(month):
    """
        Propósito:
            Documenta la función `month_label` dentro del módulo `app.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            month.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    labels = {
        "1": "Enero",
        "2": "Febrero",
        "3": "Marzo",
        "4": "Abril",
        "5": "Mayo",
        "6": "Junio",
        "7": "Julio",
        "8": "Agosto",
        "9": "Septiembre",
        "10": "Octubre",
        "11": "Noviembre",
        "12": "Diciembre",
    }

    return labels.get(str(month), "Todos")


@app.route("/")
def home():
    """
        Propósito:
            Documenta la función `home` dentro del módulo `app.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return render_template("index.html")


@app.route("/health")
def health():
    """
        Propósito:
            Documenta la función `health` dentro del módulo `app.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return "OK - Flask está corriendo en puerto 5001"


@app.route("/api/choices")
def api_choices():
    """
        Propósito:
            Endpoint Flask consumido por la interfaz. Valida parámetros, coordina servicios internos y devuelve JSON o archivo descargable.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    try:
        choices = sp_client.get_choices()
 
        # Fallback para campos Sí/No que SharePoint devuelve vacío
        if not choices.get("Requiere visita"):
            choices["Requiere visita"] = ["Si", "No"]
 
        return jsonify({"ok": True, "choices": choices})
 
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    
@app.route("/api/items")
def api_items():
    """
        Propósito:
            Endpoint Flask consumido por la interfaz. Valida parámetros, coordina servicios internos y devuelve JSON o archivo descargable.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    try:
        items = sp_client.get_public_items(force=force_refresh_requested())
        return jsonify({"ok": True, "items": [compact_list_item(x) for x in items]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/search")
def api_search():
    """
        Propósito:
            Endpoint Flask consumido por la interfaz. Valida parámetros, coordina servicios internos y devuelve JSON o archivo descargable.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    try:
        q = request.args.get("q", "").strip().lower()
        items = sp_client.get_public_items(force=force_refresh_requested())

        if q:
            items = [
                x for x in items
                if q in str(x.get("OP", "")).lower()
                or q in str(x.get("Title", "")).lower()
                or q in str(x.get("NombreCliente", "")).lower()
            ]

        return jsonify({"ok": True, "items": [compact_list_item(x) for x in items]})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/item/<int:item_id>")
def api_item(item_id):
    """
        Propósito:
            Endpoint Flask consumido por la interfaz. Valida parámetros, coordina servicios internos y devuelve JSON o archivo descargable.
    
        Entradas:
            item_id.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    try:
        raw_item = sp_client.get_item(item_id)
        item = sp_client.raw_to_display_item(raw_item)

        return jsonify({"ok": True, "item": item})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/create", methods=["POST"])
def api_create():
    """
        Propósito:
            Endpoint Flask consumido por la interfaz. Valida parámetros, coordina servicios internos y devuelve JSON o archivo descargable.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    try:
        form_data = normalize_form_payload(request.get_json(force=True))
        sp_client.create_item(form_data)
        clear_stats_report_cache()

        return jsonify({
            "ok": True,
            "message": "Registro creado correctamente"
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/update/<int:item_id>", methods=["POST"])
def api_update(item_id):
    """
        Propósito:
            Endpoint Flask consumido por la interfaz. Valida parámetros, coordina servicios internos y devuelve JSON o archivo descargable.
    
        Entradas:
            item_id.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    try:
        form_data = normalize_form_payload(request.get_json(force=True))
        sp_client.update_item(item_id, form_data)
        clear_stats_report_cache()

        return jsonify({
            "ok": True,
            "message": "Registro actualizado correctamente"
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/delete/<int:item_id>", methods=["POST"])
def api_delete(item_id):
    """
        Propósito:
            Endpoint Flask consumido por la interfaz. Valida parámetros, coordina servicios internos y devuelve JSON o archivo descargable.
    
        Entradas:
            item_id.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    try:
        sp_client.delete_item(item_id)
        clear_stats_report_cache()

        return jsonify({
            "ok": True,
            "message": "Registro eliminado correctamente"
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/stats")
def api_stats():
    """
        Propósito:
            Endpoint Flask consumido por la interfaz. Valida parámetros, coordina servicios internos y devuelve JSON o archivo descargable.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    try:
        force = force_refresh_requested()
        cache_key = ("stats", tuple(sorted((k, tuple(v)) for k, v in get_common_filters().items())))

        def builder():
            filters = get_common_filters()
            items = sp_client.get_public_items(force=force)
            filtered_items = filter_items_for_stats_multi(items, filters)

            data = build_stats(filtered_items)
            # Las opciones de los filtros se calculan con toda la lista, no con el resultado ya filtrado.
            data["filter_options"] = get_filter_options(items)
            return {"ok": True, "stats": data}

        return jsonify(cached_json_payload(cache_key, builder, force=force))

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/stats/time-detail")
def api_stats_time_detail():
    """
        Propósito:
            Endpoint Flask consumido por la interfaz. Valida parámetros, coordina servicios internos y devuelve JSON o archivo descargable.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    try:
        metric_id = request.args.get("metric_id", "").strip()
        filters = get_common_filters()

        all_items = sp_client.get_public_items(force=force_refresh_requested())
        items = filter_items_for_stats_multi(all_items, filters)
        detail = build_time_detail(items, metric_id)

        return jsonify({"ok": True, "detail": detail})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/report", methods=["GET", "POST"])
def api_report():
    """
        Propósito:
            Endpoint Flask consumido por la interfaz. Valida parámetros, coordina servicios internos y devuelve JSON o archivo descargable.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    try:
        if request.method == "POST":
            payload = request.get_json(silent=True) or {}

            def clean_list(key):
                value = payload.get(key, [])
                if value is None:
                    return []
                if not isinstance(value, list):
                    value = [value]
                return normalize_list(value)

            filters = {
                "years": clean_list("years"),
                "months": clean_list("months"),
                "days": clean_list("days"),
                "segmentos": clean_list("segmentos"),
                "productos": clean_list("productos"),
                "estados_generales": clean_list("estados_generales"),
                "tipos_version": clean_list("tipos_version"),
                "estados_ot": clean_list("estados_ot"),
                "tipos_proyecto": clean_list("tipos_proyecto"),
                "aliados": clean_list("aliados"),
                "estados_activa_cerrada": clean_list("estados_activa_cerrada"),
            }
            force = str(payload.get("refresh", "")).strip().lower() in {"1", "true", "si", "sí", "yes"}
        else:
            # Compatibilidad con enlaces/versiones anteriores.
            filters = get_common_filters()
            force = force_refresh_requested()

        cache_key = (
            "report",
            REPORT_CALC_VERSION,
            tuple(sorted((k, tuple(v)) for k, v in filters.items())),
        )

        def builder():
            items = sp_client.get_public_items(force=force)
            data = build_report(items, filters)
            return {"ok": True, "report": data}

        return jsonify(cached_json_payload(cache_key, builder, force=force))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500



from routes.export_routes import register_export_routes

register_export_routes(app)


def open_local_app():
    """
        Propósito:
            Documenta la función `open_local_app` dentro del módulo `app.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    time.sleep(2)
    url = "http://127.0.0.1:5001"

    try:
        webbrowser.open(url, new=1)
        return
    except Exception:
        pass

    # Respaldo para Windows cuando webbrowser no encuentra navegador predeterminado.
    try:
        if os.name == "nt":
            os.startfile(url)
    except Exception:
        print(f"Abre manualmente esta URL en el navegador: {url}")


if __name__ == "__main__":
    threading.Thread(target=open_local_app, daemon=True).start()

    # Playwright/Selenium sync no se puede compartir entre hilos.
    # Si Flask corre con threaded=True, una petición puede abrir la sesión
    # de Chrome y otra petición intentar reutilizarla desde otro hilo,
    # causando: "cannot switch to a different thread".
    # Por eso se deja en modo de un solo hilo y la optimización queda
    # soportada por caché de datos, no por concurrencia sobre el navegador.
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False,
        use_reloader=False,
        threaded=False
    )