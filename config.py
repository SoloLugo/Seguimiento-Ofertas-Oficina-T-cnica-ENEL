"""Configuración editable: sitio/lista de SharePoint, URL de login y alias de columnas usadas por la aplicación."""

# ============================================================
# DOCUMENTACIÓN GENERAL DEL MÓDULO
# ============================================================
# Configuración central: URLs de SharePoint, nombre de lista, alias de columnas, campos para formularios y opciones de negocio.
#
# Criterio de mantenimiento:
# - Mantener aquí únicamente lógica propia de este módulo.
# - Evitar valores quemados cuando puedan venir de configuración o SharePoint.
# - Conservar nombres canónicos de campos para no romper filtros, reportes ni exportaciones.
# - Antes de cambiar reglas de ANS, tiempos o clasificación, validar impacto en reportes y Excel/PDF.
# ============================================================

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

SITE_URL = "https://enelcom.sharepoint.com/sites/BDControldeOfertas"

LIST_TITLE = "Seguimiento-Ofertas-OT-Final"

URL_LISTA = "https://enelcom.sharepoint.com/sites/BDControldeOfertas/Lists/SeguimientoOfertasOTFinal/AllItems.aspx"


FIELD_ALIASES = {
    "OP": [
        "Title",
        "OP",
        "Número OP",
        "Numero OP"
    ],

    "Origen de la oferta": [
        "Origen de la oferta"
    ],

    "Nombre cliente": [
        "Nombre cliente",
        "Nombre Cliente",
        "Nombre del cliente",
        "Nombre de cliente",
        "Nombre cliente Mobility",
        "Nombre Cliente Mobility",
        "Nombre / Razón social",
        "Nombre / Razon social",
        "Razón social",
        "Razon social"
    ],

    "KAM": [
        "KAM"
    ],

    "Segmento": [
        "Segmento"
    ],

    "Producto": [
        "Producto"
    ],


    "Cantidad de luminarias": [
        "Cantidad de luminarias",
        "Cantidad luminarias",
        "Cantidad Luminarias",
        "Cantidad de Luminarias",
        "Nro luminarias",
        "Número de luminarias",
        "Numero de luminarias",
        "Luminarias",
        "CantidadLuminarias",
        "Cantidad_x0020_de_x0020_luminarias"
    ],

    "Cantidad Cargadores OT": [
        "Cantidad Cargadores OT",
        "Cantidad cargadores OT",
        "Cantidad de Cargadores OT",
        "Cantidad de cargadores OT"
    ],

    "Tipo de proyecto": [
        "Tipo py",
        "Tipo Py",
        "Tipo py ",
        "Tipopy",
        "TipoPry",
        "Tipo Pry",
        "TipoProyecto",
        "Tipo Proyecto",
        "Tipo de proyecto"
    ],

    "TipoProyecto": [
        "Tipo py",
        "Tipo Py",
        "Tipo py ",
        "Tipopy",
        "TipoPry",
        "Tipo Pry",
        "TipoProyecto",
        "Tipo Proyecto",
        "Tipo de proyecto"
    ],

    "Tipo py": [
        "Tipo py",
        "Tipo Py",
        "Tipo py ",
        "Tipopy",
        "Tipo de proyecto",
        "TipoProyecto",
        "Tipo Proyecto"
    ],

    "Estado": [
        "Estado"
    ],

    "Número de Versión": [
        "Número de versión",
        "Número de Versión",
        "Numero de versión",
        "Numero de Version"
    ],

    "Fecha última versión": [
        "Fecha última cotización",
        "Fecha ultima cotización",
        "Fecha última cotizacion",
        "Fecha ultima cotizacion",
        "Fecha última versión",
        "Fecha ultima version"
    ],

    "Aliado": [
        "Aliado"
    ],

    "TAM O.T.": [
        "TAM O.T."
    ],

    "Estado Oferta O.T.": [
        "Estado Oferta O.T.",
        "EstadoOfertaO.T.",
        "EstadoOfertaOT",
        "Estado Oferta OT",
        "Estado O.T.",
        "Estado OT"
    ],

    "Fecha Aceptación Brief": [
        "Fecha Aceptación Brief",
        "Fecha Aceptacion Brief"
    ],

    "Fecha envío brief a Aliado": [
        "Fecha envío brief a Aliado",
        "Fecha envio brief a Aliado"
    ],

    "Fecha de asignación de brief": [
        "Fecha de asignación de brief",
        "Fecha de asignacion de brief"
    ],

    "Fecha real contacto Cliente": [
        "Fecha real contacto Cliente"
    ],

    "Fecha programación visita": [
        "Fecha programación visita",
        "Fecha programacion visita"
    ],

    "Fecha de visita al Cliente": [
        "Fecha de visita al Cliente"
    ],

    "Requiere Factibilidad": [
        "Requiere Factibilidad"
    ],



    "Requiere visita": [
        "Requiere visita ?",
        "Requiere visita",
        "Requiere Visita",
        "Si requiere visita",
        "¿Requiere visita?",
        "Visita requerida",
        "Requiere visitar cliente",
        "Requiere visita cliente",
        "Requiere Visita Cliente",
        "Requiere programación visita",
        "Requiere programacion visita",
        "Requiere visita comercial",
        "Requiere Visita Comercial"
    ],

    "Solicita Factibilidad": [
            "Solicitud Factibilidad",
        "Solicita factibilidad",
        "Solicitud de Factibilidad"
    ],
    "Fecha solicitud de Factibilidad": [
        "Fecha solicitud de Factibilidad"
    ],

    "Fecha radicación Factibilidad": [
        "Fecha radicación Factibilidad",
        "Fecha radicacion Factibilidad"
    ],

    "Número de factibilidad": [
        "Número de factibilidad",
        "Numero de factibilidad"
    ],

    "Observación factibilidad": [
        "Observación factibilidad",
        "Observacion factibilidad"
    ],

    "Requiere cotización de equipos": [
        "Requiere cotización equipos",
        "Requiere cotización de equipos",
        "Requiere Cotización de equipos",
        "Requiere Cotización de Equipos",
        "Requiere cotizacion de equipos",
        "Requiere Cotizacion de Equipos",
        "Si requiere cotización de equipos",
        "Si requiere cotizacion de equipos",
        "Requiere cotización de equipo",
        "Requiere cotizacion de equipo"
    ],

    "Fecha solicitud de equipos": [
        "Fecha solicitud de equipos",
        "Fecha Solicitud de equipos",
        "Fecha Solicitud Equipos",
        "SolicitudEquipos",
        "6. SolicitudEquipos"
    ],

    "Fecha recibido cotización de equipos": [
        "Fecha recibido cotización de equipos",
        "Fecha recibido cotizacion de equipos",
        "Fecha Recibido Cotización de equipos",
        "Fecha Recibo Cotización Equipos",
        "ReciboCotizEqui",
        "6.1. ReciboCotizEqui"
    ],

    "Fecha entrega oferta por parte Aliado": [
        "Fecha entrega oferta por parte Aliado"
    ],

    "Fecha inicio estructuración OT": [
        "Fecha inicio estructuración OT",
        "Fecha inicio estructuracion OT"
    ],

    "Fecha Fin construcción oferta OT": [
        "Fecha Fin construcción oferta OT",
        "Fecha Fin construccion oferta OT"
    ],

    "Fecha Entrega Validación Staff": [
        "Fecha Entrega Validación Staff",
        "Fecha Entrega Validacion Staff"
    ],

    "Fecha Inicio Circuito de Firmas": [
        "Fecha Inicio Circuito de Firmas"
    ],

    "Fecha de Entrega a KAM": [
        "Fecha de Entrega a KAM"
    ],


    "Valor última oferta antes de IVA": [
        "Valor última oferta antes de IVA",
        "Valor ultima oferta antes de IVA",
        "ValorUltimaOferta",
        "Valor de Oferta antes de IVA",
        "Valor oferta antes de IVA",
        "Suma de Valor de Oferta antes de IVA"
    ],

    "Fecha de Vigencia de Oferta": [
        "Fecha de Vigencia de Oferta"
    ],

    "Histórico observaciones OP": [
        "Historico Observaciones",
        "Histórico Observaciones",
        "Historico Observaciones OP",
        "Histórico observaciones OP",
        "Historico observaciones OP",
        "Histórico Observaciones OP"
    ],

    "Observaciones": [
        "Observaciones"
    ],

    # Mobility - alias de campos adicionales para el reporte SharePoint
    "Canal Mobility": ["Canal", "Canal de venta", "Canal venta", "Canal Mobility", "Canal de venta Mobility"],
    "Servicio Mobility": ["Tipo servicio Mobility", "Tipo Servicio Mobility", "Servicio Mobility", "Tipo servicio", "Tipo de servicio", "Servicio", "Solicitud / Servicio"],
    "Tipo cliente Mobility": ["Tipo de cliente", "Tipo cliente", "Tipo Cliente", "Cliente B2B/B2C", "Tipo cliente Mobility"],
    "Contacto Mobility": ["Contacto", "Nombre contacto", "Nombre de contacto", "Persona de contacto", "Contacto cliente"],
    "Celular Mobility": ["Celular", "No. CEL", "No CEL", "Número celular", "Numero celular", "Celular / WhatsApp", "WhatsApp", "Teléfono", "Telefono"],
    "Dirección Mobility": ["Dirección", "Direccion", "Dirección cliente", "Direccion cliente", "Dirección instalación", "Direccion instalacion"],
    "Localidad Mobility": ["Localidad", "Localidad Mobility"],
    "Ciudad Mobility": ["Ciudad", "Municipio", "Ciudad / Municipio"],
    "Departamento Mobility": ["Departamento", "Departamento Mobility"],
    "Marca vehículo": ["Marca vehículo", "Marca vehiculo", "Marca del vehículo", "Marca del vehiculo"],
    "Modelo vehículo": ["Modelo vehículo", "Modelo vehiculo", "Modelo del vehículo", "Modelo del vehiculo"],
    "Marca cargador": ["Marca cargador", "Marca de cargador", "Marca del cargador"],
    "Tipo cargador": ["Tipo cargador", "Tipo de cargador", "Tipo del cargador"],
    "Potencia cargador": ["Potencia cargador", "Potencia Cargador", "Potencia de cargador", "Potencia del cargador", "Potencia"],
    "Requiere instalación Mobility": ["Requiere instalación", "Requiere instalacion", "Instalación", "Instalacion", "Incluye instalación", "Incluye instalacion"],
    "Requiere compra cargador": ["Requiere compra cargador", "Compra cargador", "Compra de cargador", "Venta cargador", "Venta de cargador"],
    "Cantidad cargadores": ["Cantidad cargadores", "Cantidad de cargadores", "Cantidad total cargadores", "Cantidad total cargadores."],
    "Cantidad instalaciones": ["Cantidad instalaciones", "Cantidad de instalaciones", "Cantidad total instalaciones"],
    "Tipo pagador": ["Tipo pagador", "Tipo de pagador", "Quién paga", "Quien paga"],
    "Nombre pagador": ["Nombre pagador", "Nombre del pagador", "Pagador"],
    "Documento pagador": ["Documento pagador", "Documento del pagador", "NIT / CC pagador", "CC / NIT pagador"],
    "Fecha visita Mobility": ["Fecha visita", "Fecha de visita", "Fecha visita Mobility", "Fecha visita técnica", "Fecha visita tecnica"],
    "Fecha instalación Mobility": ["Fecha instalación", "Fecha instalacion", "Fecha de instalación", "Fecha de instalacion"],
    "Fecha entrega cargador": ["Fecha entrega cargador", "Fecha de entrega cargador", "Fecha entrega de cargador"],
    "Valor instalación Mobility": ["Valor instalación", "Valor instalacion", "Valor de instalación", "Valor de instalacion"],
    "Valor cargador Mobility": ["Valor cargador", "Valor del cargador", "Valor venta cargador"],
    "IVA Mobility": ["IVA", "IVA Mobility", "Valor IVA", "Impuestos"],
    "Número factura Mobility": ["Número factura", "Numero factura", "Número de factura", "Numero de factura", "Factura"],
    "Vendedor": ["Vendedor", "Asesor", "Ejecutivo comercial"],
    "Observaciones vendedor": ["Observaciones vendedor", "Observaciones del vendedor", "Observación vendedor", "Observacion vendedor"],
    "ID Forms Mobility": ["ID Forms Mobility", "ID Form Mobility", "ID Forms", "ID respuesta Forms", "Id Forms Mobility"],
    "Número oferta cargador": ["Número oferta cargador", "Numero oferta cargador", "Número de oferta cargador", "Numero de oferta cargador"]

}


CHOICE_FIELDS = [
    "Origen de la oferta",
    "KAM",
    "Segmento",
    "Producto",
    "Tipo de proyecto",
    "Estado",
    "Aliado",
    "TAM O.T.",
    "Estado Oferta O.T.",
    "Requiere Factibilidad",
    "Requiere visita",
    "Requiere cotización de equipos",
]