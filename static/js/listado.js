// Código identificado para Valentina Becerra. Marca interna; no se muestra en la interfaz.
/* ============================================================
   LISTAR / BUSCAR
============================================================ */

window.listadoPaginaActual = 1;
window.listadoTamanoPagina = 150;
window.listadoItemsFiltrados = [];

async function listarTodo() {
    try {
        limpiarAlerta();

        const tbody = document.getElementById("tablaRegistros");
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center loading-text">Cargando registros...</td>
                </tr>
            `;
        }

        const data = await apiGet("/api/items");
        registrosCache = data.items || [];
        inicializarFiltrosFijosListado();
        cargarFiltrosExcel(registrosCache);
        aplicarFiltrosTabla();

    } catch (e) {
        mostrarAlerta("error", "Error listando registros: " + e.message);
    }
}

async function buscarRegistros() {
    try {
        limpiarAlerta();

        const q = document.getElementById("txtBuscar").value.trim();

        if (!q) {
            mostrarAlerta("error", "Debes ingresar una OP o cliente para buscar.");
            return;
        }

        const tbody = document.getElementById("tablaRegistros");
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center loading-text">Buscando...</td>
                </tr>
            `;
        }

        const data = await apiGet("/api/search?q=" + encodeURIComponent(q));
        registrosCache = data.items || [];
        inicializarFiltrosFijosListado();
        cargarFiltrosExcel(registrosCache);
        aplicarFiltrosTabla();

    } catch (e) {
        mostrarAlerta("error", "Error buscando registros: " + e.message);
    }
}

function cargarFiltrosExcel(items) {
    llenarFiltro("filtroOP", items.map(x => x.OP || x.Title || ""));
    llenarFiltro("filtroCliente", items.map(x => x.NombreCliente || ""));
    llenarFiltro("filtroKAM", items.map(x => x.KAM || ""));
    llenarFiltro("filtroSegmento", items.map(x => x.Segmento || ""));
    llenarFiltro("filtroProducto", items.map(x => x.Producto || ""));
    llenarFiltro("filtroEstado", items.map(x => x.EstadoOfertaOT || ""));
    llenarFiltro("filtroEstadoTop", items.map(x => x.EstadoOfertaOT || ""));
    llenarFiltro("filtroEstadoGeneral", items.map(x => x.EstadoGeneral || ""));
    llenarFiltro("filtroAliadoTop", items.map(x => x.Aliado || ""));
}

function getSelectedFiltroValues(id) {
    return getMultiselectValues(id);
}

function limpiarFiltroMultipleTabla(id) {
    limpiarMultiselect(id);
}

function coincideFiltroMultiple(valoresSeleccionados, valorItem) {
    if (!valoresSeleccionados || valoresSeleccionados.length === 0) return true;

    const valorNormalizado = String(valorItem || "").trim();
    return valoresSeleccionados.includes(valorNormalizado);
}

function llenarFiltro(id, valores) {
    const valoresActuales = getSelectedFiltroValues(id);

    const unicos = [...new Set(
        valores
            .map(v => String(v || "").trim())
            .filter(v => v !== "")
    )].sort((a, b) => a.localeCompare(b, "es"));

    crearMultiselect({
        id,
        label: "Todos",
        options: unicos.map(v => ({ value: v, text: v })),
        selected: valoresActuales,
        onChange: "aplicarFiltrosTabla"
    });
}

function aplicarFiltrosTabla() {
    const ops = getSelectedFiltroValues("filtroOP");
    const clientes = getSelectedFiltroValues("filtroCliente");
    const kams = getSelectedFiltroValues("filtroKAM");
    const segmentos = getSelectedFiltroValues("filtroSegmento");
    const productos = getSelectedFiltroValues("filtroProducto");
    const estados = [...getSelectedFiltroValues("filtroEstado"), ...getSelectedFiltroValues("filtroEstadoTop")];
    const estadosGenerales = getSelectedFiltroValues("filtroEstadoGeneral");
    const aliadosTop = getSelectedFiltroValues("filtroAliadoTop");
    const anios = getSelectedFiltroValues("filtroAnio");
    const meses = getSelectedFiltroValues("filtroMes");

    const filtrados = registrosCache.filter(item => {
        const fechaBase = item.FechaUltimaVersion || "";
        const anioItem = obtenerAnio(fechaBase);
        const mesItem = obtenerMes(fechaBase);

        return coincideFiltroMultiple(ops, item.OP || item.Title || "")
            && coincideFiltroMultiple(clientes, item.NombreCliente || "")
            && coincideFiltroMultiple(kams, item.KAM || "")
            && coincideFiltroMultiple(segmentos, item.Segmento || "")
            && coincideFiltroMultiple(productos, item.Producto || "")
            && coincideFiltroMultiple(estados, item.EstadoOfertaOT || "")
            && coincideFiltroMultiple(estadosGenerales, item.EstadoGeneral || "")
            && coincideFiltroMultiple(aliadosTop, item.Aliado || "")
            && coincideFiltroMultiple(anios, anioItem)
            && coincideFiltroMultiple(meses, mesItem);
    });

    window.listadoPaginaActual = 1;
    pintarTabla(filtrados);
}

function obtenerAnio(fecha) {
    if (!fecha) return "";

    const d = new Date(fecha);

    if (!isNaN(d.getTime())) {
        return d.getFullYear();
    }

    const texto = String(fecha).trim();

    const matchIso = texto.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (matchIso) {
        return Number(matchIso[1]);
    }

    const matchLatam = texto.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
    if (matchLatam) {
        return Number(matchLatam[3]);
    }

    return "";
}

function obtenerMes(fecha) {
    if (!fecha) return "";

    const d = new Date(fecha);

    if (!isNaN(d.getTime())) {
        return d.getMonth() + 1;
    }

    const texto = String(fecha).trim();

    const matchIso = texto.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (matchIso) {
        return Number(matchIso[2]);
    }

    const matchLatam = texto.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
    if (matchLatam) {
        return Number(matchLatam[2]);
    }

    return "";
}

function limpiarFiltrosTabla() {
    const buscar = document.getElementById("txtBuscar");
    if (buscar) buscar.value = "";

    [
        "filtroOP",
        "filtroCliente",
        "filtroKAM",
        "filtroSegmento",
        "filtroProducto",
        "filtroEstado",
        "filtroEstadoTop",
        "filtroEstadoGeneral",
        "filtroAliadoTop",
        "filtroAnio",
        "filtroMes"
    ].forEach(id => limpiarFiltroMultipleTabla(id));

    pintarTabla(registrosCache);
}

function pintarTabla(items) {
    const tbody = document.getElementById("tablaRegistros");
    const contador = document.getElementById("contador");

    if (!tbody) return;

    window.listadoItemsFiltrados = Array.isArray(items) ? items : [];

    if (contador) {
        contador.innerText = `${window.listadoItemsFiltrados.length}`;
    }

    if (!window.listadoItemsFiltrados.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted">No se encontraron registros.</td>
            </tr>
        `;
        return;
    }

    const total = window.listadoItemsFiltrados.length;
    const totalPaginas = Math.max(1, Math.ceil(total / window.listadoTamanoPagina));
    window.listadoPaginaActual = Math.min(Math.max(1, window.listadoPaginaActual), totalPaginas);
    const inicio = (window.listadoPaginaActual - 1) * window.listadoTamanoPagina;
    const pagedItems = window.listadoItemsFiltrados.slice(inicio, inicio + window.listadoTamanoPagina);

    tbody.innerHTML = pagedItems.map(item => `
        <tr>
            <td class="col-acciones">
                <div class="acciones-stack">
                    <button class="btn btn-sm btn-outline-primary btn-accion-tabla" onclick="editarRegistro(${item.Id})">
                        Editar
                    </button>
                    <button class="btn btn-sm btn-ver-registro btn-accion-tabla" onclick="verRegistro(${item.Id})">
                        Ver
                    </button>
                    <button class="btn btn-sm btn-outline-warning btn-accion-tabla" onclick="crearRecotizacionDesdeRegistro(${item.Id})">
                        Recotizar
                    </button>
                </div>
            </td>

            <td class="col-op">
                <div><strong>${escapeHtml(item.OP || item.Title || "")}</strong></div>
                <div class="text-muted small">
                    ${item.NumeroVersion ? "Versión " + escapeHtml(item.NumeroVersion) : "Sin versión"}
                </div>
            </td>

            <td class="col-cliente">${escapeHtml(item.NombreCliente || "")}</td>
            <td class="col-kam">${escapeHtml(item.KAM || "")}</td>
            <td class="col-segmento">${escapeHtml(item.Segmento || "")}</td>
            <td class="col-producto">${escapeHtml(item.Producto || "")}</td>
            <td class="col-estado">${escapeHtml(item.EstadoOfertaOT || "")}</td>
            <td class="col-fecha">${formatearFecha(item.FechaUltimaVersion)}</td>
            <td class="valor-cop col-valor">${formatearCOP(item.ValorUltimaOferta)}</td>
        </tr>
    `).join("");

    actualizarPaginacionListado(total, totalPaginas, inicio, pagedItems.length);
}

function cambiarPaginaListado(delta) {
    window.listadoPaginaActual += delta;
    pintarTabla(window.listadoItemsFiltrados);
}

function actualizarPaginacionListado(total, totalPaginas, inicio, visibles) {
    const info = document.getElementById("listadoPaginacionInfo");
    const prev = document.getElementById("listadoPaginaAnterior");
    const next = document.getElementById("listadoPaginaSiguiente");
    if (info) {
        const desde = total ? inicio + 1 : 0;
        const hasta = inicio + visibles;
        info.textContent = `Mostrando ${desde}-${hasta} de ${total} · Página ${window.listadoPaginaActual} de ${totalPaginas}`;
    }
    if (prev) prev.disabled = window.listadoPaginaActual <= 1;
    if (next) next.disabled = window.listadoPaginaActual >= totalPaginas;
}

/* ============================================================
   VER REGISTRO COMPLETO
============================================================ */

async function verRegistro(id) {
    try {
        limpiarAlerta();

        const data = await apiGet("/api/item/" + id);
        const item = data.item || {};

        const grupos = [
            {
                titulo: "Información general",
                campos: [
                    { label: "OP", keys: ["OP", "Title"] },
                    { label: "Número de versión", keys: ["Número de Versión", "Número de versión", "NumeroVersion", "NumeroCotizacion", "Versión", "Version"] },
                    { label: "Origen de la oferta", keys: ["Origen de la oferta", "OrigenOferta"] },
                    { label: "Nombre cliente", keys: ["Nombre cliente", "NombreCliente"] },
                    { label: "KAM", keys: ["KAM"] },
                    { label: "Segmento", keys: ["Segmento"] },
                    { label: "Producto", keys: ["Producto"] },
                    { label: "Cantidad de luminarias", keys: ["Cantidad de luminarias", "CantidadLuminarias"], soloProductoAP: true },
                    { label: "Cantidad cargadores en oferta", keys: ["Cantidad Cargadores OT", "CantidadCargadoresOT"] },
                    { label: "Tipo py", keys: ["Tipo py", "Tipo de proyecto", "TipoProyecto", "Tipopy"] },
                    { label: "Estado", keys: ["Estado", "EstadoGeneral"] },
                    { label: "Estado Oferta O.T.", keys: ["Estado Oferta O.T.", "EstadoOfertaOT"] },
                    { label: "Aliado", keys: ["Aliado"] },
                    { label: "TAM O.T.", keys: ["TAM O.T.", "TAMOT"] }
                ]
            },
            {
                titulo: "Fechas principales",
                campos: [
                    { label: "Fecha última cotización", keys: ["Fecha última cotización", "Fecha última versión", "FechaUltimaVersion"] },
                    { label: "Fecha Aceptación Brief", keys: ["Fecha Aceptación Brief", "FechaAceptacionBrief"] },
                    { label: "Fecha envío brief a Aliado", keys: ["Fecha envío brief a Aliado", "FechaEnvioBriefAliado"] },
                    { label: "Fecha entrega oferta por parte Aliado", keys: ["Fecha entrega oferta por parte Aliado", "FechaEntregaOfertaAliado"] },
                    { label: "Fecha Fin construcción oferta OT", keys: ["Fecha Fin construcción oferta OT", "FechaFinConstruccionOfertaOT"] },
                    { label: "Fecha Entrega Validación Staff", keys: ["Fecha Entrega Validación Staff", "FechaEntregaValidacionStaff"] },
                    { label: "Fecha Inicio Circuito de Firmas", keys: ["Fecha Inicio Circuito de Firmas", "FechaInicioCircuitoFirmas"] },
                    { label: "Fecha de Entrega a KAM", keys: ["Fecha de Entrega a KAM", "FechaEntregaKAM"] },
                    { label: "Fecha entrega oferta al Cliente", keys: ["Fecha entrega oferta al Cliente", "FechaEntregaCliente"] },
                    { label: "Fecha de Vigencia de Oferta", keys: ["Fecha de Vigencia de Oferta", "FechaVigenciaOferta"] }
                ]
            },
            {
                titulo: "Visita, factibilidad y equipos",
                campos: [
                    { label: "Requiere visita ?", keys: ["Requiere visita ?", "Requiere visitaa ?", "Requiere visita", "RequiereVisita"] },
                    { label: "Fecha real contacto Cliente", keys: ["Fecha real contacto Cliente", "FechaRealContactoCliente"] },
                    { label: "Fecha programación visita", keys: ["Fecha programación visita", "FechaProgramacionVisita"] },
                    { label: "Fecha de visita al Cliente", keys: ["Fecha de visita al Cliente", "FechaVisitaCliente"] },
                    { label: "Requiere Factibilidad", keys: ["Requiere Factibilidad", "RequiereFactibilidad"] },
                    { label: "Fecha solicitud de Factibilidad", keys: ["Fecha solicitud de Factibilidad", "FechaSolicitudFactibilidad"] },
                    { label: "Fecha radicación Factibilidad", keys: ["Fecha radicación Factibilidad", "FechaRadicacionFactibilidad"] },
                    { label: "Número de factibilidad", keys: ["Número de factibilidad", "NumeroFactibilidad"] },
                    { label: "Observación factibilidad", keys: ["Observación factibilidad", "Observacion factibilidad"] },
                    { label: "Requiere cotización de equipos", keys: ["Requiere cotización de equipos", "RequiereCotizacionEquipos"] },
                    { label: "Fecha solicitud de equipos", keys: ["Fecha solicitud de equipos", "FechaSolicitudEquipos"] },
                    { label: "Fecha recibido cotización de equipos", keys: ["Fecha recibido cotización de equipos", "FechaRecibidoCotizacionEquipos"] }
                ]
            },
            {
                titulo: "Valor y observaciones",
                campos: [
                    { label: "Valor última oferta antes de IVA", keys: ["Valor última oferta antes de IVA", "ValorUltimaOferta"] },
                    { label: "Histórico observaciones OP", keys: ["Histórico observaciones OP", "Historico Observaciones", "Historico Observaciones OP"] },
                    { label: "Observaciones", keys: ["Observaciones", "ObservacionesOP"] }
                ]
            }
        ];

        const labelsUsados = new Set();
        const valuesUsados = new Set();

        function valorCampo(keys) {
            for (const key of keys) {
                const value = item[key];
                if (value !== null && value !== undefined && String(value).trim() !== "") {
                    return value;
                }
            }
            return "";
        }

        function esProductoAPVista(value) {
            const v = String(value || "")
                .trim()
                .toLowerCase()
                .normalize("NFD")
                .replace(/[\u0300-\u036f]/g, "");
            return v === "ap" || v === "alumbrado publico";
        }

        function formatearValor(label, value) {
            if (String(label).toLowerCase().includes("fecha")) {
                return formatearFecha(value);
            }
            if (String(label).toLowerCase().includes("valor")) {
                return formatearCOP(value);
            }
            return value;
        }

        function registrarAliases(label, keys) {
            labelsUsados.add(normalizarTexto(label));
            keys.forEach(k => labelsUsados.add(normalizarTexto(k)));
        }

        function claveValor(label, value) {
            return `${normalizarTexto(label)}::${normalizarTexto(value)}`;
        }

        const htmlGrupos = grupos.map(grupo => {
            const camposHtml = grupo.campos.map(campo => {
                if (campo.soloProductoAP && !esProductoAPVista(item.Producto || item["Producto"])) {
                    registrarAliases(campo.label, campo.keys);
                    return "";
                }

                const raw = valorCampo(campo.keys);
                registrarAliases(campo.label, campo.keys);

                if (raw === null || raw === undefined || String(raw).trim() === "") {
                    return "";
                }

                const value = formatearValor(campo.label, raw);
                const valueKey = claveValor(campo.label, value);
                if (valuesUsados.has(valueKey)) {
                    return "";
                }
                valuesUsados.add(valueKey);

                return `
                    <div class="${String(value || "").length > 120 ? "col-md-12" : "col-md-4"}">
                        <div class="ver-campo">
                            <div class="ver-label">${escapeHtml(campo.label)}</div>
                            <div class="ver-valor">${escapeHtml(value || "")}</div>
                        </div>
                    </div>
                `;
            }).join("");

            if (!camposHtml.trim()) return "";

            return `
                <div class="ver-seccion">
                    <div class="ver-seccion-titulo">${escapeHtml(grupo.titulo)}</div>
                    <div class="row g-3">${camposHtml}</div>
                </div>
            `;
        }).join("");

        const otrosCampos = [];
        Object.keys(item).forEach(key => {
            if (debeExcluirCampoVer(key, labelsUsados)) {
                return;
            }

            let value = item[key];
            if (value === null || value === undefined || String(value).trim() === "") {
                return;
            }

            if (key.toLowerCase().includes("fecha")) {
                value = formatearFecha(value);
            }

            if (key.toLowerCase().includes("valor")) {
                value = formatearCOP(value);
            }

            const valueKey = claveValor(key, value);
            if (valuesUsados.has(valueKey)) {
                return;
            }
            valuesUsados.add(valueKey);

            otrosCampos.push([key, value]);
            labelsUsados.add(normalizarTexto(key));
        });

        const htmlOtros = otrosCampos.length ? `
            <div class="ver-seccion">
                <div class="ver-seccion-titulo">Otros datos</div>
                <div class="row g-3">
                    ${otrosCampos.map(([label, value]) => `
                        <div class="${String(value || "").length > 120 ? "col-md-12" : "col-md-4"}">
                            <div class="ver-campo ver-campo-secundario">
                                <div class="ver-label">${escapeHtml(label)}</div>
                                <div class="ver-valor">${escapeHtml(value || "")}</div>
                            </div>
                        </div>
                    `).join("")}
                </div>
            </div>
        ` : "";

        document.getElementById("contenidoVerRegistro").innerHTML = `
            <div class="ver-registro-resumen">
                <div>
                    <span>OP</span>
                    <strong>${escapeHtml(valorCampo(["OP", "Title"]) || "Sin OP")}</strong>
                </div>
                <div>
                    <span>Cliente</span>
                    <strong>${escapeHtml(valorCampo(["Nombre cliente", "NombreCliente"]) || "Sin cliente")}</strong>
                </div>
                <div>
                    <span>Estado O.T.</span>
                    <strong>${escapeHtml(valorCampo(["Estado Oferta O.T.", "EstadoOfertaOT"]) || "Sin estado")}</strong>
                </div>
            </div>
            ${htmlGrupos}
            ${htmlOtros}
        `;

        const modal = new bootstrap.Modal(document.getElementById("modalVerRegistro"));
        modal.show();

    } catch (e) {
        mostrarAlerta("error", "Error viendo registro: " + e.message);
    }
}

function normalizarTexto(texto) {
    return String(texto || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim();
}

function debeExcluirCampoVer(key, labelsUsados) {
    const k = normalizarTexto(key);

    if (!k) return true;
    if (labelsUsados.has(k)) return true;

    const excluirExactos = [
        "id",
        "title",
        "modified",
        "modificado",
        "created",
        "creado",
        "author",
        "editor",
        "edit",
        "linktitle",
        "linktitlenomenu",
        "linktitle2",
        "contenttype",
        "attachments",
        "attachment",
        "datos adjuntos",
        "datos adjunto",
        "adjuntos",
        "version",
        "appauthor",
        "appeditor",
        "itemchildcount",
        "folderchildcount",
        "compliancetag",
        "compliancetagwrittenchoice",
        "complianceassetid",
        "color tag",
        "tipo de contenido",
        "tipo contenido",
        "guid",
        "uniqueid",
        "owshiddencolor",
        "fileleafref",
        "filedirref",
        "fileref",
        "fsobjtype",
        "htmlfiletype",
        "serverurl",
        "encodedabsurl",
        "base name"
    ];

    if (excluirExactos.includes(k)) return true;

    if (key.startsWith("@")) return true;
    if (key.startsWith("odata")) return true;
    if (key.includes("_x005f_")) return true;
    if (key.includes("OData")) return true;
    if (key.includes("odata")) return true;

    const aliasDuplicados = [
        "numero de version",
        "numero de versión",
        "número de version",
        "número de versión",
        "fecha ultima version",
        "fecha última version",
        "fecha ultima versión",
        "fecha última versión",
        "fecha ultima cotizacion",
        "fecha última cotizacion",
        "fecha ultima cotización",
        "fecha última cotización",
        "historico observaciones",
        "historico observaciones op",
        "histórico observaciones",
        "histórico observaciones op",
        "observacion factibilidad",
        "observación factibilidad",
        "numeroversion",
        "numerocotizacion",
        "fechaultimaversion",
        "fechaaceptacionbrief",
        "fechaenviobriefaliado",
        "fecharealcontactocliente",
        "fechaprogramacionvisita",
        "fechavisitacliente",
        "requiervisita",
        "requierevisita",
        "requierefactibilidad",
        "fechasolicitudfactibilidad",
        "fecharadicacionfactibilidad",
        "fechasolicitudequipos",
        "fecharecibidocotizacionequipos",
        "requierecotizacionequipos",
        "fechaentregaofertaaliado",
        "fechafinconstruccionofertaot",
        "fechaentregavalidacionstaff",
        "fechainiciocircuitofirmas",
        "fechaentregakam",
        "fechaentregacliente",
        "fechavigenciaoferta",
        "valorultimaoferta",
        "estadogeneral",
        "estadoofertaot",
        "origenoferta",
        "nombrecliente",
        "tamot",
        "tipoproyecto"
    ];

    if (aliasDuplicados.includes(k)) return true;

    return false;
}

/* ============================================================
   FORMATEO
============================================================ */

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatearFecha(v) {
    if (!v) return "";

    const texto = String(v).trim();

    const matchIso = texto.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (matchIso) {
        return `${matchIso[3]}/${matchIso[2]}/${matchIso[1]}`;
    }

    const d = new Date(texto);

    if (!isNaN(d.getTime())) {
        return d.toLocaleDateString("es-CO");
    }

    const matchLatam = texto.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
    if (matchLatam) {
        return `${matchLatam[1].padStart(2, "0")}/${matchLatam[2].padStart(2, "0")}/${matchLatam[3]}`;
    }

    return texto;
}

function formatearCOP(v) {
    if (v === null || v === undefined || v === "") return "";

    let numero = Number(v);

    if (isNaN(numero)) {
        const limpio = String(v)
            .replace(/\$/g, "")
            .replace(/COP/g, "")
            .replace(/\./g, "")
            .replace(/,/g, ".")
            .trim();

        numero = Number(limpio);
    }

    if (isNaN(numero)) return v;

    return new Intl.NumberFormat("es-CO", {
        style: "currency",
        currency: "COP",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(numero);
}
function inicializarFiltrosFijosListado() {
    if (!document.getElementById("filtroAnio")?.classList.contains("custom-multiselect")) {
        crearMultiselect({
            id: "filtroAnio",
            label: "Todos",
            options: [
                { value: "2024", text: "2024" },
                { value: "2025", text: "2025" },
                { value: "2026", text: "2026" }
            ],
            selected: [],
            onChange: "aplicarFiltrosTabla"
        });
    }

    if (!document.getElementById("filtroMes")?.classList.contains("custom-multiselect")) {
        crearMultiselect({
            id: "filtroMes",
            label: "Todos",
            options: [
                { value: "1", text: "Enero" },
                { value: "2", text: "Febrero" },
                { value: "3", text: "Marzo" },
                { value: "4", text: "Abril" },
                { value: "5", text: "Mayo" },
                { value: "6", text: "Junio" },
                { value: "7", text: "Julio" },
                { value: "8", text: "Agosto" },
                { value: "9", text: "Septiembre" },
                { value: "10", text: "Octubre" },
                { value: "11", text: "Noviembre" },
                { value: "12", text: "Diciembre" }
            ],
            selected: [],
            onChange: "aplicarFiltrosTabla"
        });
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const modalEl = document.getElementById('modalVerRegistro');
    if (modalEl) {
        modalEl.addEventListener('hidden.bs.modal', function () {
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('padding-right');
        });
    }
});

/* Carga automática al abrir la aplicación, como estaba el flujo original esperado. */
document.addEventListener("DOMContentLoaded", () => {
    const tabla = document.getElementById("tablaRegistros");
    if (!tabla) return;

    // Pequeña espera para que Bootstrap y los filtros estén disponibles.
    setTimeout(() => {
        try {
            listarTodo();
        } catch (e) {
            console.error("No se pudo iniciar la carga automática:", e);
        }
    }, 500);
});
