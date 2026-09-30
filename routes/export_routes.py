"""Rutas de exportación: genera Excel, PDF general y PDF de tiempos con filtros aplicados."""

# ============================================================
# DOCUMENTACIÓN GENERAL DEL MÓDULO
# ============================================================
# Rutas de exportación: genera archivos Excel/PDF a partir de estadísticas, detalle de tiempos y reportes gerenciales.
#
# Criterio de mantenimiento:
# - Mantener aquí únicamente lógica propia de este módulo.
# - Evitar valores quemados cuando puedan venir de configuración o SharePoint.
# - Conservar nombres canónicos de campos para no romper filtros, reportes ni exportaciones.
# - Antes de cambiar reglas de ANS, tiempos o clasificación, validar impacto en reportes y Excel/PDF.
# ============================================================

from io import BytesIO
from datetime import datetime

from flask import jsonify, request, send_file

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak
)

from sharepoint_client import sp_client
from stats import (
    build_stats,
    build_time_metrics,
    filter_items_for_stats,
)


# ============================================================
# UTILIDADES GENERALES
# ============================================================

def normalizar_lista(values):
    """
        Propósito:
            Normaliza texto para comparar valores con tildes, mayúsculas, espacios o variantes de escritura.
    
        Entradas:
            values.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
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


def get_filters_from_request():
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return {
        "year": normalizar_lista(
            request.args.getlist("year")
            or request.args.getlist("anio")
        ),
        "month": normalizar_lista(
            request.args.getlist("month")
            or request.args.getlist("mes")
        ),
        "segmento": normalizar_lista(request.args.getlist("segmento")),
        "producto": normalizar_lista(request.args.getlist("producto")),
        "estado_general": normalizar_lista(request.args.getlist("estado_general")),
        "tipo_version": normalizar_lista(request.args.getlist("tipo_version")),
    }


def get_filtered_items():
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    filters = get_filters_from_request()
    items = sp_client.get_public_items()

    return filter_items_for_stats(
        items,
        year=filters["year"],
        month=filters["month"],
        segmento=filters["segmento"],
        producto=filters["producto"],
        estado_general=filters["estado_general"],
        tipo_version=filters["tipo_version"],
    )


def texto_filtros():
    """
        Propósito:
            Documenta la función `texto_filtros` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    filters = get_filters_from_request()

    partes = []

    if filters["year"]:
        partes.append("Año: " + ", ".join(filters["year"]))

    if filters["month"]:
        partes.append("Mes: " + ", ".join(filters["month"]))

    if filters["segmento"]:
        partes.append("Segmento: " + ", ".join(filters["segmento"]))

    if filters["producto"]:
        partes.append("Producto: " + ", ".join(filters["producto"]))

    if filters["estado_general"]:
        partes.append("Estado: " + ", ".join(filters["estado_general"]))

    if filters["tipo_version"]:
        partes.append("Tipo versión: " + ", ".join(filters["tipo_version"]))

    if not partes:
        return "Filtros aplicados: Todos"

    return "Filtros aplicados: " + " | ".join(partes)


def limpiar_texto(value):
    """
        Propósito:
            Documenta la función `limpiar_texto` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return str(value or "").strip()


def format_cop(value):
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
    if value in (None, ""):
        return ""

    try:
        number = float(str(value).replace("$", "").replace(".", "").replace(",", "."))
        return "${:,.0f}".format(number).replace(",", ".")
    except Exception:
        return str(value)


def format_fecha(value):
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
    if not value:
        return ""

    text = str(value).strip()

    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        yyyy, mm, dd = text[:10].split("-")
        return f"{dd}/{mm}/{yyyy}"

    return text


# ============================================================
# EXPORTAR DATA EXCEL
# ============================================================

def export_data_excel():
    """
        Propósito:
            Prepara o genera una salida descargable en Excel/PDF para el usuario.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    items = get_filtered_items()

    wb = Workbook()
    ws = wb.active
    ws.title = "Data"

    if not items:
        ws.append(["Sin registros"])
    else:
        headers = list(items[0].keys())
        ws.append(headers)

        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="003B5C")
            cell.alignment = Alignment(horizontal="center")

        for item in items:
            ws.append([item.get(h, "") for h in headers])

        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter

            for cell in col:
                value = str(cell.value or "")
                max_len = max(max_len, len(value))

            ws.column_dimensions[col_letter].width = min(max_len + 2, 45)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"estadisticas_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================================================
# PDF ESTADÍSTICAS GENERALES
# ============================================================

def crear_tabla_simple(titulo, rows, styles):
    """
        Propósito:
            Documenta la función `crear_tabla_simple` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            titulo, rows, styles.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    elements = []

    elements.append(Paragraph(titulo, styles["SectionTitle"]))
    elements.append(Spacer(1, 0.15 * cm))

    if not rows:
        elements.append(Paragraph("Sin datos.", styles["NormalSmall"]))
        elements.append(Spacer(1, 0.35 * cm))
        return elements

    data = [["Nombre", "Cantidad"]]

    for row in rows:
        data.append([
            limpiar_texto(row.get("name")),
            limpiar_texto(row.get("value")),
        ])

    table = Table(data, colWidths=[13 * cm, 3 * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003B5C")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F6F9FC")
        ]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.45 * cm))

    return elements


def export_pdf_stats():
    """
        Propósito:
            Prepara o genera una salida descargable en Excel/PDF para el usuario.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    items = get_filtered_items()
    stats_data = build_stats(items)

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm
    )

    styles = get_pdf_styles()

    elements = []

    elements.append(Paragraph("Reporte de estadísticas generales", styles["TitleMain"]))
    elements.append(Paragraph(datetime.now().strftime("Generado el %d/%m/%Y %H:%M"), styles["NormalSmall"]))
    elements.append(Paragraph(texto_filtros(), styles["NormalSmall"]))
    elements.append(Spacer(1, 0.45 * cm))

    resumen = [
        ["Indicador", "Valor"],
        ["Total registros", stats_data.get("total", 0)],
        ["Ofertas ganadas", stats_data.get("ganadas", 0)],
        ["Ofertas perdidas", stats_data.get("perdidas", 0)],
        ["Entregadas a KAM", stats_data.get("entregadas", 0)],
        ["Activas", stats_data.get("activas", 0)],
        ["Cerradas", stats_data.get("cerradas", 0)],
    ]

    table = Table(resumen, colWidths=[10 * cm, 4 * cm], repeatRows=1)
    table.setStyle(get_default_table_style())
    elements.append(table)
    elements.append(Spacer(1, 0.6 * cm))

    elements.extend(crear_tabla_simple("Distribución por segmento", stats_data.get("por_segmento", []), styles))
    elements.extend(crear_tabla_simple("Distribución por producto", stats_data.get("por_producto", []), styles))
    elements.extend(crear_tabla_simple("Distribución por KAM", stats_data.get("por_kam", []), styles))
    elements.extend(crear_tabla_simple("Distribución por estado de oferta", stats_data.get("por_estado", []), styles))

    doc.build(elements)
    output.seek(0)

    filename = f"estadisticas_generales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )


# ============================================================
# PDF TIEMPOS GENERAL / COTIZACIÓN INICIAL / RECOTIZACIÓN
# ============================================================

def get_pdf_styles():
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="TitleMain",
        parent=styles["Title"],
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#003B5C"),
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="SectionTitle",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0057B8"),
        spaceBefore=8,
        spaceAfter=4
    ))

    styles.add(ParagraphStyle(
        name="NormalSmall",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#37474F")
    ))

    return styles


def get_default_table_style():
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003B5C")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F6F9FC")
        ]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def valor_promedio(value):
    """
        Propósito:
            Documenta la función `valor_promedio` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if value in ("", None):
        return "Sin dato"

    return f"{value} días"


def crear_tabla_tiempos(titulo, rows, tipo):
    """
    tipo:
    - general
    - inicial
    - recotizacion
    """
    data = [[
        "Tramo",
        "Promedio días hábiles",
        "Registros"
    ]]

    for row in rows:
        if tipo == "general":
            promedio = row.get("avg_days", "")
            registros = row.get("count", 0)

        elif tipo == "inicial":
            promedio = row.get("initial_avg_days", "")
            registros = row.get("initial_count", 0)

        else:
            promedio = row.get("recot_avg_days", "")
            registros = row.get("recot_count", 0)

        data.append([
            Paragraph(limpiar_texto(row.get("name", "")), get_pdf_styles()["NormalSmall"]),
            valor_promedio(promedio),
            registros,
        ])

    table = Table(
        data,
        colWidths=[
            15.5 * cm,
            5 * cm,
            3 * cm,
        ],
        repeatRows=1
    )

    table.setStyle(get_default_table_style())

    return [
        Paragraph(titulo, get_pdf_styles()["SectionTitle"]),
        Spacer(1, 0.15 * cm),
        table,
        Spacer(1, 0.55 * cm),
    ]


def export_pdf_tiempos():
    """
        Propósito:
            Prepara o genera una salida descargable en Excel/PDF para el usuario.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    items = get_filtered_items()
    tiempos = build_time_metrics(items)

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=1.1 * cm,
        leftMargin=1.1 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm
    )

    styles = get_pdf_styles()

    elements = []

    elements.append(Paragraph("Reporte de tiempos del proceso", styles["TitleMain"]))
    elements.append(Paragraph(datetime.now().strftime("Generado el %d/%m/%Y %H:%M"), styles["NormalSmall"]))
    elements.append(Paragraph(texto_filtros(), styles["NormalSmall"]))
    elements.append(Spacer(1, 0.45 * cm))

    elements.append(Paragraph(
        "Los tiempos se calculan en días hábiles, excluyendo sábados, domingos y festivos de Colombia.",
        styles["NormalSmall"]
    ))
    elements.append(Spacer(1, 0.45 * cm))

    elements.extend(crear_tabla_tiempos(
        "1. General",
        tiempos,
        "general"
    ))

    elements.extend(crear_tabla_tiempos(
        "2. Cotización inicial",
        tiempos,
        "inicial"
    ))

    elements.extend(crear_tabla_tiempos(
        "3. Recotización",
        tiempos,
        "recotizacion"
    ))

    doc.build(elements)
    output.seek(0)

    filename = f"reporte_tiempos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )


# ============================================================
# REGISTRO DE RUTAS
# ============================================================

def register_export_routes(app):
    """
        Propósito:
            Documenta la función `register_export_routes` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            app.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """

    @app.route("/api/export/data")
    def api_export_data():
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
            return export_data_excel()
        except Exception as e:
            return jsonify({
                "ok": False,
                "error": str(e)
            }), 500

    @app.route("/api/export/pdf")
    def api_export_pdf():
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
            return export_pdf_stats()
        except Exception as e:
            return jsonify({
                "ok": False,
                "error": str(e)
            }), 500

    @app.route("/api/export/pdf-tiempos")
    def api_export_pdf_tiempos():
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
            return export_pdf_tiempos()
        except Exception as e:
            return jsonify({
                "ok": False,
                "error": str(e)
            }), 500
# ============================================================
# EXPORTACIÓN REPORTE POWER BI LOCAL: PDF, PPTX Y TABLAS EXCEL
# ============================================================
from reports import build_report

REPORT_TITLES = {
    "general": "General",
    "detalle_op": "Detalle de brief",
    "tiempos_global": "Tiempos global",
    "detalle_ofertas": "Detalle Ofertas",
    "ans_ot": "Detalle ANS O.T",
    "pendientes_kam": "Pendientes KAM",
    "pendientes_contratos": "Pendientes Contratos",
    "pv": "PV",
    "ap_lighting": "AP / Navidad",
    "bp": "BP",
    "vigentes_proceso": "Vigentes",
    "jefatura": "Ofertas en proceso",
    "alerta_tiempos": "Alerta Tiempos",
}


def get_report_filters_from_request():
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    return {
        "years": normalizar_lista(request.args.getlist("year")),
        "months": normalizar_lista(request.args.getlist("month")),
        "days": normalizar_lista(request.args.getlist("day")),
        "segmentos": normalizar_lista(request.args.getlist("segmento")),
        "productos": normalizar_lista(request.args.getlist("producto")),
        "estados_ot": normalizar_lista(request.args.getlist("estado_ot")),
        "tipos_proyecto": normalizar_lista(request.args.getlist("tipo_proyecto")),
        "aliados": normalizar_lista(request.args.getlist("aliado")),
        "estados_activa_cerrada": normalizar_lista(request.args.getlist("estado_ac")),
    }


def get_report_data():
    """
        Propósito:
            Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
    
        Entradas:
            no recibe parámetros relevantes o usa contexto interno.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    items = sp_client.get_public_items()
    return build_report(items, get_report_filters_from_request())


def rows_from_section(section):
    """
        Propósito:
            Documenta la función `rows_from_section` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            section.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    rows = []
    if isinstance(section, dict):
        for key, value in section.items():
            if key == "filters_options":
                continue
            if isinstance(value, (int, float, str)):
                rows.append([key, value])
            elif isinstance(value, list):
                for item in value[:25]:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        rows.append([key + " - " + str(item.get("name", "")), item.get("value", "")])
            elif isinstance(value, dict) and "rows" in value:
                rows.append([key, f"{len(value.get('rows', []))} filas"])
    return rows or [["Sin datos", ""]]


def build_report_pdf(sheet=None):
    """
        Propósito:
            Construye una estructura de datos compuesta para la interfaz, exportación o cálculo de indicadores.
    
        Entradas:
            sheet.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    report = get_report_data()
    selected = [sheet] if sheet else [k for k in REPORT_TITLES if k in report]

    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=1.0 * cm,
        leftMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )
    styles = get_pdf_styles()
    elements = [
        Paragraph("Gestión de Ofertas – Oficina Técnica", styles["TitleMain"]),
        Paragraph(datetime.now().strftime("Generado el %d/%m/%Y %H:%M"), styles["NormalSmall"]),
        Spacer(1, 0.4 * cm),
    ]

    for idx, key in enumerate(selected):
        if key not in report:
            continue
        if idx:
            elements.append(PageBreak())
        title = REPORT_TITLES.get(key, key)
        elements.append(Paragraph(title, styles["SectionTitle"]))
        data = [["Indicador", "Valor"]] + rows_from_section(report.get(key, {}))
        table = Table(data, colWidths=[16 * cm, 9 * cm], repeatRows=1)
        table.setStyle(get_default_table_style())
        elements.append(table)
        if key == "vigentes_proceso":
            for subtitle, rows in [("Ofertas vigentes", report[key].get("vigentes", [])), ("Ofertas en proceso", report[key].get("en_proceso", []))]:
                elements.append(Spacer(1, 0.4 * cm))
                elements.append(Paragraph(subtitle, styles["SectionTitle"]))
                cols = ["OP", "NombreCliente", "KAM", "Producto", "Segmento", "EstadoOfertaOT", "FechaVigenciaOferta"]
                data2 = [cols] + [[limpiar_texto(r.get(c, ""))[:45] for c in cols] for r in rows[:40]]
                t2 = Table(data2, repeatRows=1)
                t2.setStyle(get_default_table_style())
                elements.append(t2)

    doc.build(elements)
    output.seek(0)
    suffix = sheet or "completo"
    return send_file(output, as_attachment=True, download_name=f"reporte_powerbi_{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mimetype="application/pdf")


def export_rows_excel(rows, filename_prefix):
    """
        Propósito:
            Prepara o genera una salida descargable en Excel/PDF para el usuario.
    
        Entradas:
            rows, filename_prefix.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    if not rows:
        ws.append(["Sin datos"])
    else:
        headers = list(rows[0].keys())
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="003B5C")
            cell.alignment = Alignment(horizontal="center")
        for row in rows:
            ws.append([row.get(h, "") for h in headers])
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 45)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def safe_sheet_name(name):
    """
        Propósito:
            Documenta la función `safe_sheet_name` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            name.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    text = str(name or "Datos")
    for ch in ["\\", "/", "?", "*", "[", "]", ":"]:
        text = text.replace(ch, " ")
    text = " ".join(text.split()).strip() or "Datos"
    return text[:31]


def flatten_excel_value(value):
    """
        Propósito:
            Documenta la función `flatten_excel_value` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            value.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if isinstance(value, dict):
        return "; ".join(f"{k}: {flatten_excel_value(v)}" for k, v in value.items())
    if isinstance(value, list):
        return "; ".join(flatten_excel_value(v) for v in value)
    return value if value is not None else ""


def normalize_excel_row(row):
    """
        Propósito:
            Normaliza texto para comparar valores con tildes, mayúsculas, espacios o variantes de escritura.
    
        Entradas:
            row.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    if not isinstance(row, dict):
        return {"Valor": flatten_excel_value(row)}

    # Matrices: {name,total,values:{col:val}}
    if isinstance(row.get("values"), dict):
        result = {k: flatten_excel_value(v) for k, v in row.items() if k != "values"}
        for k, v in row.get("values", {}).items():
            result[str(k)] = flatten_excel_value(v)
        return result

    # Barras por etapas: {month/year/stages:[{name,value}]}
    if isinstance(row.get("stages"), list):
        result = {k: flatten_excel_value(v) for k, v in row.items() if k != "stages"}
        for stage in row.get("stages", []):
            if isinstance(stage, dict):
                result[str(stage.get("name", "Etapa"))] = stage.get("value", "")
        return result

    return {k: flatten_excel_value(v) for k, v in row.items()}


def append_rows_sheet(wb, title, rows):
    """
        Propósito:
            Documenta la función `append_rows_sheet` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            wb, title, rows.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    ws = wb.create_sheet(safe_sheet_name(title))

    rows = rows or []
    normalized = [normalize_excel_row(r) for r in rows]

    if not normalized:
        ws.append(["Sin datos"])
        return

    headers = []
    for row in normalized:
        for key in row.keys():
            if key not in headers:
                headers.append(key)

    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="003B5C")
        cell.alignment = Alignment(horizontal="center")

    for row in normalized:
        ws.append([row.get(h, "") for h in headers])

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 55)


def collect_section_tables(section, prefix=""):
    """
        Propósito:
            Documenta la función `collect_section_tables` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            section, prefix.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    tables = []

    if isinstance(section, list):
        if all(isinstance(x, dict) for x in section):
            tables.append((prefix or "Datos", section))
        return tables

    if not isinstance(section, dict):
        return tables

    scalars = []
    for key, value in section.items():
        if key == "filters_options":
            continue

        label = f"{prefix} {key}".strip()

        if isinstance(value, (str, int, float)) or value is None:
            scalars.append({"Indicador": key, "Valor": value if value is not None else ""})
        elif isinstance(value, list):
            if all(isinstance(x, dict) for x in value):
                tables.append((label, value))
            else:
                tables.append((label, [{"Valor": flatten_excel_value(x)} for x in value]))
        elif isinstance(value, dict):
            if isinstance(value.get("rows"), list):
                tables.append((label + " detalle", value.get("rows", [])))
            tables.extend(collect_section_tables(value, label))

    if scalars:
        tables.insert(0, (prefix or "Resumen", scalars))

    # Evita duplicados exactos de nombre y contenido.
    dedup = []
    seen = set()
    for name, rows in tables:
        sig = (name, id(rows))
        if sig not in seen:
            seen.add(sig)
            dedup.append((name, rows))
    return dedup




REPORT_DATA_TABLES = {
    "pendientes_kam": {
        "title": "Tabla Pendientes KAM",
        "prefix": "tabla_pendientes_kam",
        "getter": lambda report: report.get("pendientes_kam", {}).get("rows", []),
    },
    "op_pendientes_kam": {
        "title": "OP pendientes en gestión por KAM",
        "prefix": "op_pendientes_gestion_kam",
        "getter": lambda report: report.get("pendientes_kam", {}).get("rows", []),
    },
    "cantidad_mes_estado": {
        "title": "Cantidad de OP por mes Estado",
        "prefix": "cantidad_op_mes_estado_datos",
        "getter": lambda report: report.get("tiempos_global", {}).get("matriz_mes_estado_rows", []),
    },
    "pendientes_contratos": {
        "title": "Tabla Pendientes Contrato",
        "prefix": "tabla_pendientes_contrato",
        "getter": lambda report: report.get("pendientes_contratos", {}).get("rows", []),
    },
    "pv": {
        "title": "Tabla oportunidades PV",
        "prefix": "tabla_oportunidades_pv",
        "getter": lambda report: report.get("pv", {}).get("rows", []),
    },
    "ap_lighting": {
        "title": "Tabla oportunidades AP Navidad",
        "prefix": "tabla_oportunidades_ap_lighting",
        "getter": lambda report: report.get("ap_lighting", {}).get("rows", []),
    },
    "bp": {
        "title": "Detalle BP",
        "prefix": "detalle_bp",
        "getter": lambda report: report.get("bp", {}).get("rows", []),
    },
    "mobility": {
        "title": "Detalle Mobility",
        "prefix": "detalle_mobility",
        "getter": lambda report: report.get("mobility", {}).get("rows", []),
    },
    "vigentes": {
        "title": "Ofertas vigentes",
        "prefix": "ofertas_vigentes",
        "getter": lambda report: report.get("vigentes_proceso", {}).get("vigentes", []),
    },
    "proceso": {
        "title": "Ofertas en proceso",
        "prefix": "ofertas_en_proceso",
        "getter": lambda report: report.get("vigentes_proceso", {}).get("en_proceso", []),
    },
    "jefatura": {
        "title": "Detalle para ofertas en proceso",
        "prefix": "detalle_ofertas_en_proceso",
        "getter": lambda report: report.get("jefatura", {}).get("rows", []),
    },
    "alerta_tiempos": {
        "title": "Tabla detallada de alertas de tiempo",
        "prefix": "detalle_alertas_tiempo",
        "getter": lambda report: report.get("alerta_tiempos", {}).get("rows", []),
    },
}

REPORT_SHEET_DEFAULT_TABLE = {
    "pendientes_kam": "pendientes_kam",
    "pendientes_contratos": "pendientes_contratos",
    "pv": "pv",
    "ap_lighting": "ap_lighting",
    "bp": "bp",
    "mobility": "mobility",
    "vigentes_proceso": "proceso",
    "jefatura": "jefatura",
    "alerta_tiempos": "alerta_tiempos",
}


def export_report_table_excel(table_key):
    """
        Propósito:
            Prepara o genera una salida descargable en Excel/PDF para el usuario.
    
        Entradas:
            table_key.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    report = get_report_data()
    config = REPORT_DATA_TABLES.get(str(table_key or ""))

    if not config:
        raise ValueError("Tabla de reporte no válida: " + str(table_key))

    rows = config["getter"](report)
    return export_rows_excel(rows, config["prefix"])

def export_report_sheet_excel(sheet_key):
    """Exporta solo la tabla de datos principal de la hoja.

    No exporta tarjetas, matrices, tortas ni conteos para evitar mezclar la
    información. El Excel queda con una sola hoja llamada Datos.
    """
    table_key = REPORT_SHEET_DEFAULT_TABLE.get(str(sheet_key or ""))

    if not table_key:
        raise ValueError("Esta hoja no tiene una tabla de datos directa para Excel: " + str(sheet_key))

    return export_report_table_excel(table_key)

def export_report_full_excel():
    """Exporta únicamente las tablas de datos detalladas del reporte.

    Se excluyen conteos, matrices, gráficas y resúmenes calculados.
    """
    report = get_report_data()

    wb = Workbook()
    wb.remove(wb.active)
    used = set()

    for table_key in [
        "cantidad_mes_estado",
        "pendientes_kam",
        "pendientes_contratos",
        "pv",
        "ap_lighting",
        "bp",
        "mobility",
        "vigentes",
        "proceso",
        "jefatura",
        "alerta_tiempos",
    ]:
        config = REPORT_DATA_TABLES[table_key]
        rows = config["getter"](report)
        base = safe_sheet_name(config["title"] or table_key)
        final = base
        i = 2
        while final in used:
            suffix = f" {i}"
            final = safe_sheet_name(base[:31 - len(suffix)] + suffix)
            i += 1
        used.add(final)
        append_rows_sheet(wb, final, rows)

    if not wb.sheetnames:
        append_rows_sheet(wb, "Datos", [])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"reporte_tablas_datos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# Se agregan las rutas después de definir register_export_routes; Flask permite decorar app aquí
# mediante monkey patch en el registro principal.
_old_register_export_routes = register_export_routes

def register_export_routes(app):
    """
        Propósito:
            Documenta la función `register_export_routes` dentro del módulo `export_routes.py` y centraliza una parte de la lógica de la aplicación.
    
        Entradas:
            app.
    
        Salida:
            Devuelve un valor listo para ser usado por la capa que llama esta función.
    
        Notas:
            La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
        
    """
    _old_register_export_routes(app)

    @app.route("/api/export/report/pdf")
    def api_export_report_pdf():
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
            return build_report_pdf(request.args.get("sheet") or None)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500


    @app.route("/api/export/report/excel")
    def api_export_report_excel():
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
            return export_report_full_excel()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/export/report/sheet-excel")
    def api_export_report_sheet_excel():
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
            return export_report_sheet_excel(request.args.get("sheet") or "")
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/export/report/table-excel")
    def api_export_report_table_excel():
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
            return export_report_table_excel(request.args.get("table") or "")
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/export/report/vigentes-excel")
    def api_export_report_vigentes_excel():
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
            report = get_report_data()
            return export_rows_excel(report.get("vigentes_proceso", {}).get("vigentes", []), "ofertas_vigentes")
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/export/report/proceso-excel")
    def api_export_report_proceso_excel():
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
            report = get_report_data()
            return export_rows_excel(report.get("vigentes_proceso", {}).get("en_proceso", []), "ofertas_en_proceso")
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/export/report/jefatura-excel")
    def api_export_report_jefatura_excel():
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
            report = get_report_data()
            return export_rows_excel(report.get("jefatura", {}).get("rows", []), "detalle_ofertas_en_proceso")
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/export/report/alertas-excel")
    def api_export_report_alertas_excel():
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
            report = get_report_data()
            return export_rows_excel(report.get("alerta_tiempos", {}).get("rows", []), "detalle_alertas_tiempo")
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
