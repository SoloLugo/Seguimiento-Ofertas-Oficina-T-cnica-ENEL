"""Cliente SharePoint: reutiliza una sesión Chrome con Playwright para leer y escribir en la lista corporativa."""

# Código identificado para Valentina Becerra. Marca interna; no se muestra en la interfaz.

# ============================================================
# DOCUMENTACIÓN GENERAL DEL MÓDULO
# ============================================================
# Cliente SharePoint vía navegador autenticado: resuelve metadatos, campos internos, CRUD, caché y transformación de ítems.
#
# Criterio de mantenimiento:
# - Mantener aquí únicamente lógica propia de este módulo.
# - Evitar valores quemados cuando puedan venir de configuración o SharePoint.
# - Conservar nombres canónicos de campos para no romper filtros, reportes ni exportaciones.
# - Antes de cambiar reglas de ANS, tiempos o clasificación, validar impacto en reportes y Excel/PDF.
# ============================================================


from catalog_names import canonical_catalog_value
from pathlib import Path
import json
import time
import threading

from playwright.sync_api import Error as PlaywrightError, sync_playwright

from config import SITE_URL, LIST_TITLE, URL_LISTA, FIELD_ALIASES, CHOICE_FIELDS

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "perfil_chrome_sharepoint"


class SharePointClient:
    """
        Propósito:
            Encapsula la integración con SharePoint, incluyendo autenticación web, consultas REST, caché, mapeo de campos y CRUD.
    
        Responsabilidad:
            Agrupar comportamiento relacionado y mantener separada esta responsabilidad del resto de módulos.
        
    """
    def __init__(self):
        """
            Propósito:
                Inicializa atributos internos de la instancia, incluyendo caché, navegador y mapas de campos.
        
            Entradas:
                no recibe parámetros relevantes o usa contexto interno.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        self.playwright = None
        self.browser_context = None
        self.sp_page = None
        self.field_map = {}
        self._normalized_field_index = {}
        self._display_title_cache = {}
        self._internal_name_cache = {}
        self._items_cache = None
        self._public_items_cache = None
        self._items_cache_at = 0
        self.cache_ttl_seconds = 900
        self._cache_lock = threading.RLock()
        self._request_lock = threading.RLock()

    def invalidate_cache(self):
        """Vacía la caché de registros después de crear, actualizar o eliminar."""
        with self._cache_lock:
            self._items_cache = None
            self._public_items_cache = None
            self._items_cache_at = 0

    def _cache_is_valid(self):
        """
            Propósito:
                Documenta la función `_cache_is_valid` dentro del módulo `sharepoint_client.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                no recibe parámetros relevantes o usa contexto interno.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        return (
            self._items_cache is not None
            and (time.time() - self._items_cache_at) < self.cache_ttl_seconds
        )

    def reset_browser_refs(self):
        """Limpia referencias cuando Chrome/Playwright pierde la sesión."""
        try:
            if self.browser_context:
                self.browser_context.close()
        except Exception:
            pass

        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

        self.sp_page = None
        self.browser_context = None
        self.playwright = None

    def _context_is_alive(self):
        """
            Propósito:
                Documenta la función `_context_is_alive` dentro del módulo `sharepoint_client.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                no recibe parámetros relevantes o usa contexto interno.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        if not self.browser_context:
            return False
        try:
            _ = self.browser_context.pages
            _ = self.browser_context.request
            return True
        except Exception:
            return False

    def _page_is_alive(self):
        """
            Propósito:
                Documenta la función `_page_is_alive` dentro del módulo `sharepoint_client.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                no recibe parámetros relevantes o usa contexto interno.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        if not self.sp_page:
            return False
        try:
            return not self.sp_page.is_closed()
        except Exception:
            return False

    def init_browser(self, force=False):
        """Abre Chrome en SharePoint y garantiza que exista un contexto válido."""
        if force:
            self.reset_browser_refs()

        if self.playwright and self._context_is_alive():
            if not self._page_is_alive():
                try:
                    self.sp_page = self.browser_context.new_page()
                    self.sp_page.goto(URL_LISTA, wait_until="domcontentloaded", timeout=120000)
                except Exception:
                    self.reset_browser_refs()
                    raise
            return

        self.reset_browser_refs()
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        self.playwright = sync_playwright().start()

        self.browser_context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            channel="chrome",
            viewport=None,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        paginas_abiertas = []
        try:
            paginas_abiertas = [p for p in self.browser_context.pages if not p.is_closed()]
        except Exception:
            paginas_abiertas = []

        self.sp_page = paginas_abiertas[0] if paginas_abiertas else self.browser_context.new_page()

        try:
            self.sp_page.bring_to_front()
        except Exception:
            pass

        self.sp_page.goto(URL_LISTA, wait_until="domcontentloaded", timeout=120000)

        print("Chrome abierto con SharePoint.")
        print("Si pide inicio de sesión, inicia sesión en la ventana de Chrome.")
        print("No cierres esa ventana mientras uses la app.")

    def _sp_fetch_once(self, url, method="GET", body=None, extra_headers=None):
        """
        Consulta SharePoint usando el request context de Playwright.
        Esto evita el error Page.evaluate: Target page/context/browser has been closed.
        La página visible queda solo para abrir SharePoint y conservar login/cookies.
        """
        self.init_browser()

        headers = {
            "Accept": "application/json;odata=nometadata",
        }

        payload = None
        if method != "GET":
            headers["Content-Type"] = "application/json;odata=nometadata"
            payload = json.dumps(body or {})

        if extra_headers:
            headers.update(extra_headers)

        with self._request_lock:
            response = self.browser_context.request.fetch(
                url,
                method=method,
                headers=headers,
                data=payload,
                timeout=120000,
            )

            text = response.text()
        try:
            parsed = json.loads(text) if text else {}
        except Exception:
            parsed = {"raw": text}

        if not response.ok:
            raise Exception(text)

        return parsed

    def sp_fetch(self, url, method="GET", body=None, extra_headers=None):
        """Ejecuta fetch contra SharePoint y reconstruye Chrome/contexto si se cerró."""
        ultimo_error = None

        for intento in range(3):
            try:
                return self._sp_fetch_once(url, method=method, body=body, extra_headers=extra_headers)
            except PlaywrightError as e:
                ultimo_error = e
                mensaje = str(e)

                if (
                    "Target page" in mensaje
                    or "context or browser has been closed" in mensaje
                    or "Browser closed" in mensaje
                    or "Page closed" in mensaje
                    or "Target closed" in mensaje
                    or "has been closed" in mensaje
                ):
                    self.reset_browser_refs()
                    time.sleep(1)
                    continue

                raise
            except Exception as e:
                ultimo_error = e
                mensaje = str(e)
                if (
                    "Target page" in mensaje
                    or "context or browser has been closed" in mensaje
                    or "Browser closed" in mensaje
                    or "Page closed" in mensaje
                    or "Target closed" in mensaje
                    or "has been closed" in mensaje
                ):
                    self.reset_browser_refs()
                    time.sleep(1)
                    continue
                raise

        raise Exception(
            "No se pudo leer SharePoint porque Chrome o la sesión de Playwright se cerró antes de consultar. "
            "Cierra todas las ventanas de Chrome abiertas por esta app, vuelve a ejecutar el .bat o app.py, "
            "espera a que se abra SharePoint e inicia sesión si lo pide. Detalle: " + str(ultimo_error)
        )

    def list_title_safe(self):
        """
            Propósito:
                Documenta la función `list_title_safe` dentro del módulo `sharepoint_client.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                no recibe parámetros relevantes o usa contexto interno.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        return LIST_TITLE.replace("'", "''")

    def get_digest(self):
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
        url = f"{SITE_URL}/_api/contextinfo"

        result = self.sp_fetch(
            url,
            method="POST",
            body={},
            extra_headers={
                "Accept": "application/json;odata=nometadata"
            }
        )

        return result["FormDigestValue"]

    def load_field_map(self, force=False):
        """
            Propósito:
                Carga metadatos de columnas de SharePoint y construye el mapa nombre visible ↔ nombre interno.
        
            Entradas:
                force.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        if self.field_map and not force:
            return self.field_map

        url = (
            f"{SITE_URL}/_api/web/lists/getbytitle('{self.list_title_safe()}')/fields"
            f"?$select=Title,InternalName,TypeAsString,Hidden,ReadOnlyField,Choices"
            f"&$filter=Hidden eq false"
        )

        data = self.sp_fetch(url)
        fields = data.get("value", [])

        self.field_map = {}
        self._normalized_field_index = {}
        self._display_title_cache = {}
        self._internal_name_cache = {}

        for f in fields:
            title = f["Title"]
            internal = f["InternalName"]
            self.field_map[title] = {
                "internal": internal,
                "type": f.get("TypeAsString", ""),
                "choices": f.get("Choices", []) or []
            }

            # Índice normalizado para resolver aliases sin recorrer todos los campos por cada fila.
            self._normalized_field_index[self.normalize_field_name(title)] = title
            self._normalized_field_index[self.normalize_field_name(internal)] = title

        return self.field_map

    @staticmethod
    def normalize_field_name(value):
        """Normaliza nombres de columnas para evitar fallos por espacios, puntos, mayúsculas o acentos."""
        import unicodedata

        text = str(value or "").strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return "".join(ch for ch in text.lower() if ch.isalnum())

    def resolve_display_title(self, canonical_title):
        """
            Propósito:
                Documenta la función `resolve_display_title` dentro del módulo `sharepoint_client.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                canonical_title.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        if canonical_title in self._display_title_cache:
            return self._display_title_cache[canonical_title]

        fm = self.load_field_map()
        aliases = FIELD_ALIASES.get(canonical_title, [canonical_title])

        # 1) Match exacto por título visible.
        for alias in aliases:
            if alias in fm:
                self._display_title_cache[canonical_title] = alias
                return alias

        # 2) Match normalizado por título visible o InternalName usando índice precalculado.
        for alias in aliases:
            display = self._normalized_field_index.get(self.normalize_field_name(alias))
            if display:
                self._display_title_cache[canonical_title] = display
                return display

        self._display_title_cache[canonical_title] = None
        return None

    def internal_name(self, canonical_title):
        """
            Propósito:
                Documenta la función `internal_name` dentro del módulo `sharepoint_client.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                canonical_title.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        if canonical_title in self._internal_name_cache:
            return self._internal_name_cache[canonical_title]

        display = self.resolve_display_title(canonical_title)

        if not display:
            self._internal_name_cache[canonical_title] = None
            return None

        internal = self.load_field_map()[display]["internal"]
        self._internal_name_cache[canonical_title] = internal
        return internal

    def get_display_value(self, raw_item, canonical_title):
        """
            Propósito:
                Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
        
            Entradas:
                raw_item, canonical_title.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        internal = self.internal_name(canonical_title)

        if not internal:
            return ""

        return raw_item.get(internal, "")

    def get_values_by_field_pattern(self, raw_item, required_terms, excluded_terms=None):
        """Devuelve valores no vacíos de columnas reales de SharePoint cuyo nombre coincide con términos.

        Se usa especialmente en Mobility para grupos de columnas numeradas, por ejemplo
        Potencia cargador, Potencia cargador 2, Potencia cargador 3, etc.
        """
        self.load_field_map()
        required = [self.normalize_field_name(x) for x in (required_terms or []) if x]
        excluded = [self.normalize_field_name(x) for x in (excluded_terms or []) if x]
        values = []

        for display, meta in self.field_map.items():
            internal = meta.get("internal", "")
            normalized = self.normalize_field_name(display)
            normalized_internal = self.normalize_field_name(internal)
            haystack = normalized + " " + normalized_internal

            if required and not all(term in haystack for term in required):
                continue
            if excluded and any(term in haystack for term in excluded):
                continue

            value = raw_item.get(internal, "")
            if value in ["", None]:
                continue
            if isinstance(value, (list, tuple)):
                candidates = value
            else:
                candidates = [value]
            for candidate in candidates:
                text = str(candidate).strip()
                if text and text not in values:
                    values.append(text)

        return values

    def get_first_value_by_field_pattern(self, raw_item, required_terms, excluded_terms=None):
        values = self.get_values_by_field_pattern(raw_item, required_terms, excluded_terms)
        return values[0] if values else ""

    def get_combined_potencias_cargador(self, raw_item):
        """Resume todas las columnas Potencia cargador, Potencia cargador 2, 3, etc."""
        values = self.get_values_by_field_pattern(raw_item, ["potencia", "cargador"])
        # Fallback al campo canónico por compatibilidad con listas antiguas.
        if not values:
            value = self.get_display_value(raw_item, "Potencia cargador")
            if value not in ["", None]:
                values = [str(value).strip()]
        return " | ".join(values)

    def get_any_value(self, raw_item, possible_names):
        """
            Propósito:
                Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
        
            Entradas:
                raw_item, possible_names.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        self.load_field_map()

        for name in possible_names:
            display = self.resolve_display_title(name)
            if display:
                internal = self.field_map[display]["internal"]
                value = raw_item.get(internal, "")
                if value not in ["", None]:
                    return value

            display = self._normalized_field_index.get(self.normalize_field_name(name))
            if display:
                internal = self.field_map[display]["internal"]
                value = raw_item.get(internal, "")
                if value not in ["", None]:
                    return value

        return ""

    def _public_select_internals(self):
        """Columnas mínimas usadas por listado, filtros, estadísticas y reportes."""
        canonical_fields = [
            "OP", "Title", "Origen de la oferta", "Nombre cliente", "KAM", "Segmento", "Producto",
            "Número de versión", "Número de Versión", "Fecha última cotización", "Fecha última versión",
            "Aliado", "TAM O.T.", "Estado Oferta O.T.", "Fecha Aceptación Brief",
            "Fecha envío brief a Aliado", "Fecha real contacto Cliente", "Fecha programación visita",
            "Fecha de visita al Cliente", "Requiere Factibilidad", "Fecha solicitud de Factibilidad",
            "Fecha radicación Factibilidad", "Número de factibilidad", "Observación factibilidad",
            "Requiere cotización de equipos", "Fecha solicitud de equipos",
            "Fecha recibido cotización de equipos", "Fecha entrega oferta por parte Aliado",
            "Fecha Fin construcción oferta OT", "Fecha Entrega Validación Staff",
            "Fecha Inicio Circuito de Firmas", "Fecha de Entrega a KAM",
            "Fecha entrega oferta al Cliente", "Valor última oferta antes de IVA",
            "Fecha de Vigencia de Oferta", "Historico Observaciones", "Histórico observaciones OP",
            "Observaciones", "Estado", "Tipo de proyecto", "TipoProyecto", "Tipo py",
            "Requiere visita", "Requiere visita ?", "Requiere visitaa ?", "Cantidad Luminarias",
            "Cantidad de luminarias", "Cantidad Cargadores OT", "Número CRM", "Canal de venta BP", "CC / NIT cliente",
            "Persona de contacto BP", "Teléfono contacto BP", "Dirección BP", "Zona U.O.",
            "Localidad / Municipio", "Subzona U.O.", "Requerimiento BP", "Radicado recibo de obra",
            "Fecha solicitud ODS visita", "Número ODS visita",
            "Fecha envío ODS visita Planeación a Back Office",
            "Fecha envío ODS visita Back Office a U.O.", "Número S visita", "Fecha visita U.O.",
            "Fecha solicitud presupuesto BP", "Fecha envío presupuesto U.O. a Planeación/Back",
            "Fecha envío presupuesto CREG015", "Fecha envío presupuesto final a canal",
            "Valor presupuesto final U.O. antes IVA", "Valor presupuesto final U.O. después CREG015",
            "Valor presupuesto Salesforce XC", "Valor margen Enel X antes IVA", "Acta de visita",
            "Caso nota crédito", "Caso XC", "Causal ejecución BP", "Causal presupuesto BP",
            "Estado proyecto BP", "Fecha confirmación de pago", "Fecha confirmación respuesta cliente",
            "Fecha creación deudor", "Fecha ejecución U.O.", "Fecha entrega factura",
            "Fecha envío ODS ejecución Back Office a U.O.",
            "Fecha envío ODS ejecución Planeación a Back Office", "Fecha solicitud deudor",
            "Fecha solicitud factura", "Fecha solicitud ODS ejecución", "Margen final Enel X %",
            "Número AGP", "Número deudor SAP", "Número factura de venta",
            "Número ODS ejecución", "Responsable estado proyecto BP",
            "Valor facturado final U.O. / LM antes IVA",
            "Valor facturado margen Enel X antes IVA", "Valor presupuesto final cliente antes IVA",
            "Canal Mobility", "Servicio Mobility", "Tipo cliente Mobility", "Contacto Mobility",
            "Celular Mobility", "Dirección Mobility", "Localidad Mobility", "Ciudad Mobility",
            "Departamento Mobility", "Marca vehículo", "Modelo vehículo", "Marca cargador",
            "Tipo cargador", "Potencia cargador", "Requiere instalación Mobility",
            "Requiere compra cargador", "Cantidad cargadores", "Cantidad instalaciones",
            "Tipo pagador", "Nombre pagador", "Documento pagador", "Fecha visita Mobility",
            "Fecha instalación Mobility", "Fecha entrega cargador", "Valor instalación Mobility",
            "Valor cargador Mobility", "IVA Mobility", "Número factura Mobility", "Vendedor",
            "Observaciones vendedor", "ID Forms Mobility", "Número oferta cargador"
        ]

        internals = ["Id", "Title"]
        for field in canonical_fields:
            internal = self.internal_name(field)
            if internal and internal not in internals:
                internals.append(internal)

        # Mobility puede tener columnas repetidas/numeradas (p. ej. Potencia cargador 2, 3...).
        # Las añadimos dinámicamente al $select para que estén disponibles en el resumen.
        self.load_field_map()
        for display, meta in self.field_map.items():
            normalized = self.normalize_field_name(display)
            internal = meta.get("internal")
            if not internal:
                continue
            is_potencia_cargador = "potencia" in normalized and "cargador" in normalized
            is_nombre_cliente = "nombre" in normalized and "cliente" in normalized and "contacto" not in normalized and "pagador" not in normalized
            if (is_potencia_cargador or is_nombre_cliente) and internal not in internals:
                internals.append(internal)

        return internals

    def to_public_item(self, raw_item):
        """
            Propósito:
                Transforma un ítem crudo de SharePoint en un diccionario estable para la aplicación.
        
            Entradas:
                raw_item.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        op_value = self.get_display_value(raw_item, "OP") or raw_item.get("Title", "")

        numero_version = self.get_display_value(raw_item, "Número de Versión") or self.get_any_value(raw_item, [
            "Número de versión",
            "Número de Versión",
            "Numero de versión",
            "Numero de Version",
            "Versión",
            "Version"
        ])

        fecha_ultima_version = self.get_display_value(raw_item, "Fecha última versión") or self.get_any_value(raw_item, [
            "Fecha última cotización",
            "Fecha ultima cotización",
            "Fecha última cotizacion",
            "Fecha ultima cotizacion",
            "Fecha última versión",
            "Fecha ultima version"
        ])

        return {
            "Id": raw_item.get("Id"),
            "Title": raw_item.get("Title", ""),

            "OP": op_value,
            "OrigenOferta": self.get_display_value(raw_item, "Origen de la oferta"),
            "NombreCliente": (
                self.get_display_value(raw_item, "Nombre cliente")
                or self.get_first_value_by_field_pattern(
                    raw_item, ["nombre", "cliente"], ["contacto", "pagador"]
                )
            ),
            "KAM": self.get_display_value(raw_item, "KAM"),
            "Segmento": canonical_catalog_value("Segmento", self.get_display_value(raw_item, "Segmento")),
            "Producto": canonical_catalog_value("Producto", self.get_display_value(raw_item, "Producto")),
            "CantidadLuminarias": self.get_any_value(raw_item, ["Cantidad Luminarias", "Cantidad de luminarias"]),
            "CantidadCargadoresOT": self.get_display_value(raw_item, "Cantidad Cargadores OT"),
            "EstadoGeneral": self.get_display_value(raw_item, "Estado"),
            "EstadoOfertaOT": self.get_display_value(raw_item, "Estado Oferta O.T."),
            "NumeroVersion": numero_version,
            "FechaUltimaVersion": fecha_ultima_version,

            "FechaAceptacionBrief": self.get_display_value(raw_item, "Fecha Aceptación Brief"),
            "FechaEnvioBriefAliado": self.get_display_value(raw_item, "Fecha envío brief a Aliado"),

            "FechaRealContactoCliente": self.get_display_value(raw_item, "Fecha real contacto Cliente"),
            "RequiereVisita": (
                self.get_display_value(raw_item, "Requiere visita")
                or self.get_display_value(raw_item, "Requiere visita ?")
                or self.get_display_value(raw_item, "Requiere visitaa ?")
            ),
            "FechaProgramacionVisita": self.get_display_value(raw_item, "Fecha programación visita"),
            "FechaVisitaCliente": self.get_display_value(raw_item, "Fecha de visita al Cliente"),

            "RequiereFactibilidad": self.get_display_value(raw_item, "Requiere Factibilidad"),
            "FechaSolicitudFactibilidad": self.get_display_value(raw_item, "Fecha solicitud de Factibilidad"),
            "FechaRadicacionFactibilidad": self.get_display_value(raw_item, "Fecha radicación Factibilidad"),

            "FechaSolicitudEquipos": self.get_display_value(raw_item, "Fecha solicitud de equipos"),
            "FechaRecibidoCotizacionEquipos": self.get_display_value(raw_item, "Fecha recibido cotización de equipos"),
            "RequiereCotizacionEquipos": self.get_display_value(raw_item, "Requiere cotización de equipos"),

            "FechaEntregaOfertaAliado": self.get_display_value(raw_item, "Fecha entrega oferta por parte Aliado"),
            "FechaFinConstruccionOfertaOT": self.get_display_value(raw_item, "Fecha Fin construcción oferta OT"),
            "FechaEntregaValidacionStaff": self.get_display_value(raw_item, "Fecha Entrega Validación Staff"),
            "FechaInicioCircuitoFirmas": self.get_display_value(raw_item, "Fecha Inicio Circuito de Firmas"),
            "FechaEntregaKAM": self.get_display_value(raw_item, "Fecha de Entrega a KAM"),
            "FechaEntregaCliente": self.get_display_value(raw_item, "Fecha entrega oferta al Cliente"),
            "TipoProyecto": (
                self.get_display_value(raw_item, "Tipo de proyecto")
                or self.get_display_value(raw_item, "TipoProyecto")
                or self.get_any_value(raw_item, [
                    "Tipo py",
                    "Tipo Py",
                    "Tipo py ",
                    "Tipopy",
                    "Tipo de proyecto",
                    "TipoPry",
                    "Tipo Pry",
                    "TipoProyecto",
                    "Tipo Proyecto"
                ])
            ),
            "NumeroCotizacion": numero_version,
            "ValorUltimaOferta": (
    self.get_display_value(raw_item, "Valor última oferta antes de IVA")
    or self.get_any_value(raw_item, [
        "Valor última oferta antes de IVA",
        "Valor ultima oferta antes de IVA",
        "ValorUltimaOferta",
        "Valor de Oferta antes de IVA",
        "Valor oferta antes de IVA"
    ])
            ),
            "FechaVigenciaOferta": self.get_display_value(raw_item, "Fecha de Vigencia de Oferta"),
            "Aliado": canonical_catalog_value("Aliado", self.get_display_value(raw_item, "Aliado")),
            "TAMOT": self.get_display_value(raw_item, "TAM O.T."),

            # Campos específicos BP / Boletín de Pago para la hoja BP del reporte.
            # Solo se incluyen campos reales existentes en SharePoint según los títulos confirmados.
            "NumeroCRM": self.get_any_value(raw_item, ["Número CRM", "Numero CRM"]),
            "CanalVentaBP": self.get_any_value(raw_item, ["Canal de venta BP"]),
            "CCNITCliente": self.get_any_value(raw_item, ["CC / NIT cliente"]),
            "PersonaContactoBP": self.get_any_value(raw_item, ["Persona de contacto BP"]),
            "TelefonoContactoBP": self.get_any_value(raw_item, ["Teléfono contacto BP", "Telefono contacto BP"]),
            "DireccionBP": self.get_any_value(raw_item, ["Dirección BP", "Direccion BP"]),
            "ZonaUO": self.get_any_value(raw_item, ["Zona U.O.", "Zona UO"]),
            "LocalidadMunicipio": self.get_any_value(raw_item, ["Localidad / Municipio", "Localidad/Municipio", "Localidad Municipio"]),
            "SubzonaUO": self.get_any_value(raw_item, ["Subzona U.O.", "Subzona UO"]),
            "NumeroFactibilidad": self.get_any_value(raw_item, ["Número de factibilidad", "Numero de factibilidad", "Número factibilidad"]),
            "ObservacionFactibilidad": self.get_any_value(raw_item, ["Observación factibilidad", "Observacion factibilidad"]),
            "RequerimientoBP": self.get_any_value(raw_item, ["Requerimiento BP"]),
            "RadicadoReciboObra": self.get_any_value(raw_item, ["Radicado recibo de obra"]),
            "FechaSolicitudODSVisita": self.get_any_value(raw_item, ["Fecha solicitud ODS visita"]),
            "NumeroODSVisita": self.get_any_value(raw_item, ["Número ODS visita", "Numero ODS visita"]),
            "FechaEnvioODSVisitaPlaneacionBackOffice": self.get_any_value(raw_item, ["Fecha envío ODS visita Planeación a Back Office", "Fecha envio ODS visita Planeacion a Back Office"]),
            "FechaEnvioODSVisitaBackOfficeUO": self.get_any_value(raw_item, ["Fecha envío ODS visita Back Office a U.O.", "Fecha envio ODS visita Back Office a U.O."]),
            "NumeroSVisita": self.get_any_value(raw_item, ["Número S visita", "Numero S visita"]),
            "FechaVisitaUO": self.get_any_value(raw_item, ["Fecha visita U.O.", "Fecha visita UO"]),
            "FechaSolicitudPresupuestoBP": self.get_any_value(raw_item, ["Fecha solicitud presupuesto BP"]),
            "FechaEnvioPresupuestoUOPlaneacionBack": self.get_any_value(raw_item, ["Fecha envío presupuesto U.O. a Planeación/Back", "Fecha envio presupuesto U.O. a Planeacion/Back"]),
            "FechaEnvioPresupuestoCREG015": self.get_any_value(raw_item, ["Fecha envío presupuesto CREG015", "Fecha envio presupuesto CREG015"]),
            "FechaEnvioPresupuestoFinalCanal": self.get_any_value(raw_item, ["Fecha envío presupuesto final a canal", "Fecha envio presupuesto final a canal"]),
            "ValorPresupuestoUOAntesIVA": self.get_any_value(raw_item, ["Valor presupuesto final U.O. antes IVA", "Valor presupuesto final UO antes IVA"]),
            "ValorPresupuestoUODespuesCREG015": self.get_any_value(raw_item, ["Valor presupuesto final U.O. después CREG015", "Valor presupuesto final U.O. despues CREG015"]),
            "ValorPresupuestoSalesforceXC": self.get_any_value(raw_item, ["Valor presupuesto Salesforce XC"]),
            "ValorMargenEnelXAntesIVA": self.get_any_value(raw_item, ["Valor margen Enel X antes IVA"]),
            "ActaVisita": self.get_any_value(raw_item, ["Acta de visita"]),
            "CasoNotaCredito": self.get_any_value(raw_item, ["Caso nota crédito", "Caso nota credito"]),
            "CasoXC": self.get_any_value(raw_item, ["Caso XC"]),
            "CausalEjecucionBP": self.get_any_value(raw_item, ["Causal ejecución BP", "Causal ejecucion BP"]),
            "CausalPresupuestoBP": self.get_any_value(raw_item, ["Causal presupuesto BP"]),
            "EstadoProyectoBP": self.get_any_value(raw_item, ["Estado proyecto BP"]),
            "FechaConfirmacionPago": self.get_any_value(raw_item, ["Fecha confirmación de pago", "Fecha confirmacion de pago"]),
            "FechaConfirmacionRespuestaCliente": self.get_any_value(raw_item, ["Fecha confirmación respuesta cliente", "Fecha confirmacion respuesta cliente"]),
            "FechaCreacionDeudor": self.get_any_value(raw_item, ["Fecha creación deudor", "Fecha creacion deudor"]),
            "FechaEjecucionUO": self.get_any_value(raw_item, ["Fecha ejecución U.O.", "Fecha ejecucion U.O.", "Fecha ejecución UO"]),
            "FechaEntregaFactura": self.get_any_value(raw_item, ["Fecha entrega factura"]),
            "FechaEnvioODSEjecucionBackOfficeUO": self.get_any_value(raw_item, ["Fecha envío ODS ejecución Back Office a U.O.", "Fecha envio ODS ejecucion Back Office a U.O."]),
            "FechaEnvioODSEjecucionPlaneacionBackOffice": self.get_any_value(raw_item, ["Fecha envío ODS ejecución Planeación a Back Office", "Fecha envio ODS ejecucion Planeacion a Back Office"]),
            "FechaSolicitudDeudor": self.get_any_value(raw_item, ["Fecha solicitud deudor"]),
            "FechaSolicitudFactura": self.get_any_value(raw_item, ["Fecha solicitud factura"]),
            "FechaSolicitudODSEjecucion": self.get_any_value(raw_item, ["Fecha solicitud ODS ejecución", "Fecha solicitud ODS ejecucion"]),
            "MargenFinalEnelXPorcentaje": self.get_any_value(raw_item, ["Margen final Enel X %"]),
            "NumeroAGP": self.get_any_value(raw_item, ["Número AGP", "Numero AGP"]),
            "NumeroDeudorSAP": self.get_any_value(raw_item, ["Número deudor SAP", "Numero deudor SAP"]),
            "NumeroFacturaVenta": self.get_any_value(raw_item, ["Número factura de venta", "Numero factura de venta"]),
            "NumeroODSEjecucion": self.get_any_value(raw_item, ["Número ODS ejecución", "Numero ODS ejecucion", "Número ODS ejecucion"]),
            "ResponsableEstadoProyectoBP": self.get_any_value(raw_item, ["Responsable estado proyecto BP"]),
            "ValorFacturadoFinalUOLMAntesIVA": self.get_any_value(raw_item, ["Valor facturado final U.O. / LM antes IVA", "Valor facturado final UO / LM antes IVA"]),
            "ValorFacturadoMargenEnelXAntesIVA": self.get_any_value(raw_item, ["Valor facturado margen Enel X antes IVA"]),
            "ValorPresupuestoFinalClienteAntesIVA": self.get_any_value(raw_item, ["Valor presupuesto final cliente antes IVA"]),

            "CanalMobility": self.get_display_value(raw_item, "Canal Mobility"),
            "ServicioMobility": (
                self.get_display_value(raw_item, "Servicio Mobility")
                or self.get_any_value(raw_item, ["Tipo servicio Mobility", "Tipo Servicio Mobility"])
            ),
            "TipoClienteMobility": self.get_display_value(raw_item, "Tipo cliente Mobility"),
            "ContactoMobility": self.get_display_value(raw_item, "Contacto Mobility"),
            "CelularMobility": self.get_display_value(raw_item, "Celular Mobility"),
            "DireccionMobility": self.get_display_value(raw_item, "Dirección Mobility"),
            "LocalidadMobility": self.get_display_value(raw_item, "Localidad Mobility"),
            "CiudadMobility": self.get_display_value(raw_item, "Ciudad Mobility"),
            "DepartamentoMobility": self.get_display_value(raw_item, "Departamento Mobility"),
            "MarcaVehiculo": self.get_display_value(raw_item, "Marca vehículo"),
            "ModeloVehiculo": self.get_display_value(raw_item, "Modelo vehículo"),
            "MarcaCargador": self.get_display_value(raw_item, "Marca cargador"),
            "TipoCargador": self.get_display_value(raw_item, "Tipo cargador"),
            "PotenciaCargador": self.get_combined_potencias_cargador(raw_item),
            "RequiereInstalacionMobility": self.get_display_value(raw_item, "Requiere instalación Mobility"),
            "RequiereCompraCargador": self.get_display_value(raw_item, "Requiere compra cargador"),
            "CantidadCargadores": self.get_display_value(raw_item, "Cantidad cargadores"),
            "CantidadInstalaciones": self.get_display_value(raw_item, "Cantidad instalaciones"),
            "TipoPagador": self.get_display_value(raw_item, "Tipo pagador"),
            "NombrePagador": self.get_display_value(raw_item, "Nombre pagador"),
            "DocumentoPagador": self.get_display_value(raw_item, "Documento pagador"),
            "FechaVisitaMobility": self.get_display_value(raw_item, "Fecha visita Mobility"),
            "FechaInstalacionMobility": self.get_display_value(raw_item, "Fecha instalación Mobility"),
            "FechaEntregaCargador": self.get_display_value(raw_item, "Fecha entrega cargador"),
            "ValorInstalacionMobility": self.get_display_value(raw_item, "Valor instalación Mobility"),
            "ValorCargadorMobility": self.get_display_value(raw_item, "Valor cargador Mobility"),
            "IVAMobility": self.get_display_value(raw_item, "IVA Mobility"),
            "NumeroFacturaMobility": self.get_display_value(raw_item, "Número factura Mobility"),
            "Vendedor": self.get_display_value(raw_item, "Vendedor"),
            "ObservacionesVendedor": self.get_display_value(raw_item, "Observaciones vendedor"),
            "IDFormsMobility": self.get_display_value(raw_item, "ID Forms Mobility"),
            "NumeroOfertaCargador": self.get_display_value(raw_item, "Número oferta cargador"),

            "ObservacionesOP": self.get_any_value(raw_item, ["Historico Observaciones", "Histórico Observaciones", "Histórico observaciones OP"]),
            "Observaciones": self.get_display_value(raw_item, "Observaciones"),
        }

    def raw_to_display_item(self, raw_item):
        """
            Propósito:
                Documenta la función `raw_to_display_item` dentro del módulo `sharepoint_client.py` y centraliza una parte de la lógica de la aplicación.
        
            Entradas:
                raw_item.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        fm = self.load_field_map()

        result = {
            "Id": raw_item.get("Id"),
            "Title": raw_item.get("Title", "")
        }

        for display, info in fm.items():
            result[display] = raw_item.get(info["internal"], "")

        for canonical_title in FIELD_ALIASES.keys():
            internal = self.internal_name(canonical_title)

            if internal:
                result[canonical_title] = raw_item.get(internal, "")

        result["OP"] = result.get("OP") or raw_item.get("Title", "")

        numero_version = result.get("Número de Versión", "")

        if not numero_version:
            numero_version = self.get_any_value(raw_item, [
                "Número de versión",
                "Número de Versión",
                "Numero de versión",
                "Numero de Version",
                "Versión",
                "Version"
            ])

        result["Número de Versión"] = numero_version

        fecha_version = result.get("Fecha última versión", "")

        if not fecha_version:
            fecha_version = self.get_any_value(raw_item, [
                "Fecha última cotización",
                "Fecha ultima cotización",
                "Fecha última cotizacion",
                "Fecha ultima cotizacion",
                "Fecha última versión",
                "Fecha ultima version"
            ])

        result["Fecha última versión"] = fecha_version

        historico_op = result.get("Histórico observaciones OP", "")

        if not historico_op:
            historico_op = self.get_any_value(raw_item, [
                "Historico Observaciones",
                "Histórico Observaciones",
                "Historico Observaciones OP",
                "Histórico observaciones OP",
                "Historico observaciones OP",
                "Histórico Observaciones OP"
            ])

        result["Histórico observaciones OP"] = historico_op

        tipo_proyecto = (
            result.get("Tipo de proyecto", "")
            or result.get("Tipo py", "")
            or result.get("TipoProyecto", "")
            or self.get_any_value(raw_item, [
                "Tipo py",
                "Tipo Py",
                "Tipo py ",
                "Tipopy",
                "Tipo de proyecto",
                "TipoPry",
                "Tipo Pry",
                "TipoProyecto",
                "Tipo Proyecto"
            ])
        )

        result["Tipo de proyecto"] = tipo_proyecto
        result["TipoProyecto"] = tipo_proyecto

        cantidad_luminarias = (
            result.get("Cantidad de luminarias", "")
            or self.get_any_value(raw_item, [
                "Cantidad de luminarias",
                "Cantidad luminarias",
                "Cantidad Luminarias",
                "Cantidad de Luminarias",
                "Nro luminarias",
                "Número de luminarias",
                "Numero de luminarias",
                "Luminarias"
            ])
        )
        result["Cantidad de luminarias"] = cantidad_luminarias
        result["CantidadLuminarias"] = cantidad_luminarias

        cantidad_cargadores_ot = (
            result.get("Cantidad Cargadores OT", "")
            or self.get_any_value(raw_item, [
                "Cantidad Cargadores OT",
                "Cantidad cargadores OT",
                "Cantidad de Cargadores OT",
                "Cantidad de cargadores OT"
            ])
        )
        result["Cantidad Cargadores OT"] = cantidad_cargadores_ot
        result["CantidadCargadoresOT"] = cantidad_cargadores_ot

        observacion_factibilidad = result.get("Observación factibilidad", "")

        if not observacion_factibilidad:
            observacion_factibilidad = self.get_any_value(raw_item, [
                "Observación factibilidad",
                "Observacion factibilidad",
                "Observación Factibilidad",
                "Observacion Factibilidad"
            ])

        result["Observación factibilidad"] = observacion_factibilidad

        return result

    def form_to_sharepoint_payload(self, form_data):
        """
            Propósito:
                Convierte datos del formulario al payload esperado por SharePoint usando nombres internos.
        
            Entradas:
                form_data.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        payload = {}

        for canonical_title, value in form_data.items():
            if value in ["", None]:
                continue

            internal = self.internal_name(canonical_title)

            if not internal:
                continue

            payload[internal] = value

        if form_data.get("OP"):
            payload["Title"] = form_data["OP"]

        return payload

    def get_items(self, force=False):
        """
            Propósito:
                Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
        
            Entradas:
                force.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        with self._cache_lock:
            if not force and self._cache_is_valid():
                return list(self._items_cache)

        # Listas grandes: lectura por lotes usando Id (indexado por SharePoint).
        # IMPORTANTE: no enviamos un $select gigantesco en la URL. Con las columnas
        # Mobility/BP el query string superaba maxQueryStringLength de IIS/ASP.NET.
        # Al omitir $select, SharePoint devuelve los campos normales del item y la URL
        # queda corta; el filtro por Id mantiene cada consulta por debajo del threshold.
        base_url = f"{SITE_URL}/_api/web/lists/getbytitle('{self.list_title_safe()}')/items"
        page_size = 2000
        last_id = 0
        items = []

        while True:
            url = (
                f"{base_url}?$filter=Id gt {last_id}"
                f"&$orderby=Id asc&$top={page_size}"
            )
            data = self.sp_fetch(url)
            batch = data.get("value", []) or []
            if not batch:
                break

            items.extend(batch)
            ids = []
            for row in batch:
                try:
                    ids.append(int(row.get("Id")))
                except (TypeError, ValueError):
                    pass

            if not ids:
                break
            new_last_id = max(ids)
            if new_last_id <= last_id:
                break
            last_id = new_last_id

            if len(batch) < page_size:
                break

        items.sort(key=lambda x: int(x.get("Id") or 0), reverse=True)
        public_items = [self.to_public_item(x) for x in items]

        with self._cache_lock:
            self._items_cache = items
            self._public_items_cache = public_items
            self._items_cache_at = time.time()

        return list(items)

    def get_public_items(self, force=False):
        """
            Propósito:
                Obtiene ítems listos para UI, usando caché salvo que se solicite recarga forzada.
        
            Entradas:
                force.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        with self._cache_lock:
            if not force and self._cache_is_valid() and self._public_items_cache is not None:
                return list(self._public_items_cache)

        self.get_items(force=force)

        with self._cache_lock:
            return list(self._public_items_cache or [])

    def get_item(self, item_id):
        """
            Propósito:
                Obtiene un valor normalizado desde registros, filtros o configuración para reutilizarlo en cálculos.
        
            Entradas:
                item_id.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        url = f"{SITE_URL}/_api/web/lists/getbytitle('{self.list_title_safe()}')/items({item_id})"
        return self.sp_fetch(url)

    def create_item(self, form_data):
        """
            Propósito:
                Crea un registro nuevo en la lista de SharePoint.
        
            Entradas:
                form_data.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        payload = self.form_to_sharepoint_payload(form_data)
        digest = self.get_digest()

        url = f"{SITE_URL}/_api/web/lists/getbytitle('{self.list_title_safe()}')/items"

        self.sp_fetch(
            url,
            method="POST",
            body=payload,
            extra_headers={
                "X-RequestDigest": digest
            }
        )
        self.invalidate_cache()

    def update_item(self, item_id, form_data):
        """
            Propósito:
                Actualiza un registro existente en SharePoint.
        
            Entradas:
                item_id, form_data.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        payload = self.form_to_sharepoint_payload(form_data)
        digest = self.get_digest()

        url = f"{SITE_URL}/_api/web/lists/getbytitle('{self.list_title_safe()}')/items({item_id})"

        self.sp_fetch(
            url,
            method="POST",
            body=payload,
            extra_headers={
                "X-RequestDigest": digest,
                "X-HTTP-Method": "MERGE",
                "IF-MATCH": "*"
            }
        )
        self.invalidate_cache()

    def delete_item(self, item_id):
        """
            Propósito:
                Elimina un registro de SharePoint por ID.
        
            Entradas:
                item_id.
        
            Salida:
                Devuelve un valor listo para ser usado por la capa que llama esta función.
        
            Notas:
                La documentación fue agregada para facilitar mantenimiento; no modifica la lógica original.
            
        """
        digest = self.get_digest()

        url = f"{SITE_URL}/_api/web/lists/getbytitle('{self.list_title_safe()}')/items({item_id})"

        self.sp_fetch(
            url,
            method="POST",
            body={},
            extra_headers={
                "X-RequestDigest": digest,
                "X-HTTP-Method": "DELETE",
                "IF-MATCH": "*"
            }
        )
        self.invalidate_cache()

    def get_choices(self):
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
        fm = self.load_field_map(force=True)
        result = {}

        for canonical in CHOICE_FIELDS:
            display = self.resolve_display_title(canonical)

            if not display:
                result[canonical] = []
                continue

            info = fm.get(display, {})
            choices = info.get("choices", []) or []

            result[canonical] = list(dict.fromkeys(
                canonical_catalog_value(canonical, value) for value in choices
            ))

        return result


sp_client = SharePointClient()