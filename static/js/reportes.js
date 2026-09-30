// Código identificado para Valentina Becerra. Marca interna; no se muestra en la interfaz.
/* ============================================================
   REPORTE POWER BI LOCAL
   - Datos en vivo desde /api/report.
   - Gráficas con tooltip, etiquetas, selección como filtro.
   - Exportación por hoja y global a PDF.
============================================================ */

window.reportesInicializados = false;
window.cargandoReportes = false;
window.reporteActual = null;
window.reportesRecargaPendiente = false;
window.reportesDebounceTimer = null;

function getActiveMainTabReportes() {
    return document.querySelector(".app-tabs .nav-link.active")?.getAttribute("data-bs-target") || "#tabListado";
}

function getActiveReportSheet() {
    return document.querySelector("#tabReportes .nav-link.active")?.getAttribute("data-bs-target") || "#repGeneral";
}

function restoreActiveTabsReportes(mainTarget, sheetTarget) {
    if (mainTarget) {
        const mainBtn = document.querySelector(`.app-tabs [data-bs-target="${mainTarget}"]`);
        if (mainBtn && window.bootstrap) bootstrap.Tab.getOrCreateInstance(mainBtn).show();
    }
    if (sheetTarget) {
        const sheetBtn = document.querySelector(`#tabReportes [data-bs-target="${sheetTarget}"]`);
        if (sheetBtn && window.bootstrap) bootstrap.Tab.getOrCreateInstance(sheetBtn).show();
    }
}

function valorTablaReporte(value) {
    if (value === null || value === undefined) return "";
    return String(value);
}

const REP_SHEETS = [
    ["general", "General", "#repGeneral"],
    ["detalle_op", "Detalle de brief", "#repDetalleOP"],
    ["tiempos_global", "Tiempos global", "#repTiemposGlobal"],
    ["detalle_ofertas", "Detalle Ofertas", "#repDetalleOfertas"],
    ["ans_ot", "ANS O.T", "#repANSOT"],
    ["pendientes_kam", "Pendientes KAM", "#repPendientesKAM"],
    ["pendientes_contratos", "Pendientes Contratos", "#repPendientesContratos"],
    ["pv", "PV", "#repPV"],
    ["ap_lighting", "AP / Navidad", "#repAPLighting"],
    ["bp", "BP", "#repBP"],
    ["mobility", "Mobility", "#repMobility"],
    ["vigentes_proceso", "Vigentes", "#repVigentesProceso"],
    ["jefatura", "Ofertas en proceso", "#repJefatura"],
    ["alerta_tiempos", "Alerta Tiempos", "#repAlertaTiempos"]
];

function crearFiltrosReportesBasicos() {
    const filtros = [
        ["repFiltroAnio", "Año"],
        ["repFiltroMes", "Mes"],
        ["repFiltroDia", "Día"],
        ["repFiltroEstadoAC", "Activa/Cerrada"],
        ["repFiltroEstadoOT", "Estado Oferta O.T."],
        ["repFiltroTipoProyecto", "Tipo de proyecto"],
        ["repFiltroProducto", "Producto"],
        ["repFiltroSegmento", "Segmento"],
        ["repFiltroAliado", "Aliado"]
    ];

    filtros.forEach(([id, label]) => {
        const el = document.getElementById(id);

        if (el && !el.classList.contains("custom-multiselect")) {
            crearMultiselect({
                id,
                label,
                options: [],
                selected: [],
                onChange: null
            });
        }
    });
}

function getReportValues(id) {
    return typeof getMultiselectValues === "function"
        ? getMultiselectValues(id)
        : [];
}

function getReportQueryString(extra = {}) {
    const params = new URLSearchParams();

    getReportValues("repFiltroAnio").forEach(v => params.append("year", v));
    getReportValues("repFiltroMes").forEach(v => params.append("month", v));
    getReportValues("repFiltroDia").forEach(v => params.append("day", v));
    getReportValues("repFiltroEstadoAC").forEach(v => params.append("estado_ac", v));
    getReportValues("repFiltroEstadoOT").forEach(v => params.append("estado_ot", v));
    getReportValues("repFiltroTipoProyecto").forEach(v => params.append("tipo_proyecto", v));
    getReportValues("repFiltroProducto").forEach(v => params.append("producto", v));
    getReportValues("repFiltroSegmento").forEach(v => params.append("segmento", v));
    getReportValues("repFiltroAliado").forEach(v => params.append("aliado", v));

    Object.entries(extra || {}).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") {
            params.append(k, v);
        }
    });

    return params.toString();
}


function getReportFiltersBody(extra = {}) {
    const payload = {
        years: getReportValues("repFiltroAnio"),
        months: getReportValues("repFiltroMes"),
        days: getReportValues("repFiltroDia"),
        estados_activa_cerrada: getReportValues("repFiltroEstadoAC"),
        estados_ot: getReportValues("repFiltroEstadoOT"),
        tipos_proyecto: getReportValues("repFiltroTipoProyecto"),
        productos: getReportValues("repFiltroProducto"),
        segmentos: getReportValues("repFiltroSegmento"),
        aliados: getReportValues("repFiltroAliado")
    };

    Object.entries(extra || {}).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") payload[k] = v;
    });

    return payload;
}

function snapshotFiltrosReportes() {
    return {
        years: getReportValues("repFiltroAnio"),
        months: getReportValues("repFiltroMes"),
        days: getReportValues("repFiltroDia"),
        estadosAC: getReportValues("repFiltroEstadoAC"),
        estados: getReportValues("repFiltroEstadoOT"),
        tipos: getReportValues("repFiltroTipoProyecto"),
        productos: getReportValues("repFiltroProducto"),
        segmentos: getReportValues("repFiltroSegmento"),
        aliados: getReportValues("repFiltroAliado")
    };
}

function restoreFiltrosReportes(snap) {
    if (!snap) return;

    setMultiselectValues("repFiltroAnio", snap.years || []);
    setMultiselectValues("repFiltroMes", snap.months || []);
    setMultiselectValues("repFiltroDia", snap.days || []);
    setMultiselectValues("repFiltroEstadoAC", snap.estadosAC || []);
    setMultiselectValues("repFiltroEstadoOT", snap.estados || []);
    setMultiselectValues("repFiltroTipoProyecto", snap.tipos || []);
    setMultiselectValues("repFiltroProducto", snap.productos || []);
    setMultiselectValues("repFiltroSegmento", snap.segmentos || []);
    setMultiselectValues("repFiltroAliado", snap.aliados || []);
}

function toOpts(raw) {
    return (raw || []).map(v => {
        return typeof v === "object"
            ? v
            : { value: v, text: v };
    });
}

function cargarOpcionesReportes(options) {
    const snap = snapshotFiltrosReportes();

    const map = [
        ["repFiltroAnio", toOpts(options.years), snap.years],
        ["repFiltroMes", toOpts(options.months), snap.months],
        ["repFiltroDia", toOpts(options.days), snap.days],
        ["repFiltroEstadoAC", toOpts(options.estados_activa_cerrada), snap.estadosAC],
        ["repFiltroEstadoOT", toOpts(options.estados_ot), snap.estados],
        ["repFiltroTipoProyecto", toOpts(options.tipos_proyecto), snap.tipos],
        ["repFiltroProducto", toOpts(options.productos), snap.productos],
        ["repFiltroSegmento", toOpts(options.segmentos), snap.segmentos],
        ["repFiltroAliado", toOpts(options.aliados), snap.aliados]
    ];

    map.forEach(([id, raw, selected]) => {
        const optsMap = new Map();

        [
            ...(raw || []),
            ...(selected || []).map(v => ({ value: v, text: v }))
        ].forEach(o => {
            optsMap.set(String(o.value), o);
        });

        recargarMultiselect(
            id,
            Array.from(optsMap.values()).filter(o => o.value),
            selected || []
        );
    });
}

function actualizarReportesPorFiltro() {
    clearTimeout(window.reportesDebounceTimer);
    window.reportesDebounceTimer = setTimeout(() => {
        window.reportesInicializados = false;
        cargarReportes(true, false);
    }, 180);
}

function limpiarFiltrosReportes() {
    [
        "repFiltroAnio",
        "repFiltroMes",
        "repFiltroDia",
        "repFiltroEstadoAC",
        "repFiltroEstadoOT",
        "repFiltroTipoProyecto",
        "repFiltroProducto",
        "repFiltroSegmento",
        "repFiltroAliado"
    ].forEach(id => setMultiselectValues(id, []));

    actualizarReportesPorFiltro();
}

async function cargarReportes(forzar = false, recargarSharePoint = false) {
    if (window.cargandoReportes) {
        window.reportesRecargaPendiente = true;
        return;
    }
    if (window.reportesInicializados && !forzar) return;

    const activeMainTab = getActiveMainTabReportes();
    const activeReportSheet = getActiveReportSheet();

    try {
        window.cargandoReportes = true;
        window.reportesRecargaPendiente = false;

        crearFiltrosReportesBasicos();

        const snap = snapshotFiltrosReportes();

        document.getElementById("reportLoading")?.classList.remove("d-none");

        // El reporte puede tener muchos valores seleccionados. Enviarlos por GET
        // termina superando maxQueryStringLength en IIS/ASP.NET. Usamos POST
        // con JSON para que el tamaño de los filtros no dependa de la URL.
        const payload = getReportFiltersBody(recargarSharePoint ? { refresh: true } : {});
        const data = await apiPost("/api/report", payload);

        if (!data.ok) {
            throw new Error(data.error || "No fue posible cargar el reporte.");
        }

        const report = data.report || {};
        window.reporteActual = report;

        cargarOpcionesReportes(report.filters_options || {});
        restoreFiltrosReportes(snap);
        pintarReporteCompleto(report);

        window.reportesInicializados = true;
    } catch (e) {
        mostrarAlerta("error", "Error cargando reporte Power BI: " + e.message);
    } finally {
        window.cargandoReportes = false;
        document.getElementById("reportLoading")?.classList.add("d-none");
        restoreActiveTabsReportes(activeMainTab, activeReportSheet);

        if (window.reportesRecargaPendiente) {
            window.reportesRecargaPendiente = false;
            window.reportesInicializados = false;
            setTimeout(() => cargarReportes(true, false), 80);
        }
    }
}

function recargarReportesDesdeSharePoint() {
    window.reportesInicializados = false;
    cargarReportes(true, true);
}

function abrirVentanaImpresion(title, htmlContent) {
    const win = window.open("", "_blank", "width=1400,height=900");
    if (!win) return;

    const estilos = Array.from(document.querySelectorAll('link[rel="stylesheet"], style'))
        .map(node => node.outerHTML)
        .join("\n");

    win.document.write(`<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>${title}</title>
${estilos}
<style>
    body {
        background: #fff !important;
        padding: 18px !important;
        overflow: visible !important;
    }

    .no-export,
    button {
        display: none !important;
    }

    .card {
        box-shadow: none !important;
        border: 0 !important;
    }

    .tab-pane {
        display: block !important;
        opacity: 1 !important;
    }

    .rep-panel,
    .rep-card {
        break-inside: avoid-page;
        page-break-inside: avoid;
    }

    .rep-dona,
    .rep-bar-fill,
    .rep-stack div,
    .rep-ans b,
    .rep-ans i {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }

    table {
        font-size: 11px;
    }
</style>
</head>
<body>${htmlContent}</body>
</html>`);

    win.document.close();

    setTimeout(() => {
        win.focus();
        win.print();
    }, 1500);
}

function exportSheetExcel(sheetKey) {
    const qs = getReportQueryString();
    const sep = qs ? `&${qs}` : "";
    window.open(`/api/export/report/sheet-excel?sheet=${encodeURIComponent(sheetKey)}${sep}`, '_blank');
}

function exportTableExcel(tableKey) {
    const qs = getReportQueryString();
    const sep = qs ? `&${qs}` : "";
    window.open(`/api/export/report/table-excel?table=${encodeURIComponent(tableKey)}${sep}`, '_blank');
}

function btnTablaExcel(tableKey, text = "Exportar tabla Excel") {
    return `
        <button class="btn btn-sm btn-outline-success" onclick="exportTableExcel('${tableKey}')">
            ${escapeHtml(text)}
        </button>
    `;
}

function exportSheetPdf(sheetKey) {
    const map = Object.fromEntries(REP_SHEETS.map(x => [x[0], x[2]]));
    const sel = map[sheetKey];
    const pane = sel ? document.querySelector(sel) : null;

    if (!pane) return;

    abrirVentanaImpresion(
        `Reporte ${sheetKey}`,
        `<div class="card p-3">${pane.innerHTML}</div>`
    );
}

function exportWholeReportExcel() {
    const qs = getReportQueryString();
    const sep = qs ? `?${qs}` : "";
    window.open(`/api/export/report/excel${sep}`, '_blank');
}

function exportWholeReportPdf() {
    const blocks = REP_SHEETS.map(([key, name, sel]) => {
        const pane = document.querySelector(sel);
        if (!pane) return "";

        return `
            <section style="margin-bottom:24px;">
                <h2 style="margin:0 0 12px 0;font-size:22px;">${name}</h2>
                ${pane.innerHTML}
            </section>
        `;
    }).join("");

    abrirVentanaImpresion("Reporte General", blocks);
}

function fmtNum(v) {
    return new Intl.NumberFormat("es-CO", {
        maximumFractionDigits: 2
    }).format(Number(v || 0));
}

function fmtCOP(v) {
    return new Intl.NumberFormat("es-CO", {
        style: "currency",
        currency: "COP",
        maximumFractionDigits: 0
    }).format(Number(v || 0));
}

function pct(v, total) {
    return total
        ? `${Math.round((Number(v || 0) / total) * 100)}%`
        : "0%";
}

const PALETTE = [
    "#1187e8",
    "#182e8a",
    "#7a1397",
    "#ec6d32",
    "#00a443",
    "#5d6d7e",
    "#0097a7",
    "#8e24aa"
];

const FIELD_TO_FILTER = {
    year: "repFiltroAnio",
    month: "repFiltroMes",
    day: "repFiltroDia",
    estado_ot: "repFiltroEstadoOT",
    tipo_proyecto: "repFiltroTipoProyecto",
    Producto: "repFiltroProducto",
    Segmento: "repFiltroSegmento",
    Aliado: "repFiltroAliado",
    TipoProyecto: "repFiltroTipoProyecto",
    EstadoOfertaOT: "repFiltroEstadoOT",
    tipo_version: "repFiltroTipoVersion",
    tam: null
};

function clickFilter(field, value) {
    if (!field || !value) return;

    const id = FIELD_TO_FILTER[field] || FIELD_TO_FILTER[String(field)] || null;

    if (!id) return;

    setMultiselectValues(id, [String(value)]);
    cargarReportes(true);
}

function itemAttr(r, fallbackField) {
    const field = r.field || fallbackField || "";
    const raw = r.raw || r.name || "";

    return `
        title="${escapeHtml(r.name)}: ${escapeHtml(r.value)} (${pct(r.value, r.total || 0)})"
        onclick="clickFilter('${escapeHtml(field)}','${escapeHtml(raw)}')"
    `;
}

function inyectarEstilosResumenGeneral() {
    if (document.getElementById("rep-flow-v2-style")) return;

    const style = document.createElement("style");
    style.id = "rep-flow-v2-style";

    style.textContent = `
        .rep-flow-v2 {
            padding: 14px 10px;
            border-top: 2px solid #4057b8;
            border-bottom: 2px solid #4057b8;
            background: #fff;
            overflow-x: auto;
        }

        .rep-flow-equation {
            display: grid;
            grid-template-columns:
                300px
                auto
                300px
                auto
                300px
                auto
                300px;
            align-items: center;
            justify-content: center;
            gap: 10px;
            min-width: max-content;
        }

        .rep-flow-item {
            width: 300px;
            min-width: 300px;
            max-width: 300px;
            height: 78px;
            text-align: center;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 8px 8px;
            background: #fff;

            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
        }

        .rep-flow-item strong {
            display: block;
            font-size: 1.65rem;
            color: #111;
            line-height: 1.1;
        }

        .rep-flow-item span {
            display: block;
            font-size: .74rem;
            color: #334;
            font-weight: 700;
            line-height: 1.15;
        }

        .rep-flow-main {
            border-color: #4057b8;
            background: #f5f7ff;
        }

        .rep-flow-main strong {
            color: #182e8a;
        }

        .rep-flow-op {
            font-size: 1.45rem;
            font-weight: 900;
            color: #4057b8;
            text-align: center;
        }

        .rep-flow-support {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            flex-wrap: nowrap;
            margin-top: 10px;
            min-width: max-content;
        }

        .rep-flow-support .rep-flow-item,
        .rep-flow-breakdown .rep-flow-item {
            width: 300px;
            min-width: 300px;
            max-width: 300px;
            height: 78px;
        }

        .rep-flow-support .rep-flow-op {
            font-size: 1.55rem;
            font-weight: 900;
            color: #4057b8;
            min-width: 18px;
            text-align: center;
        }

        .rep-flow-breakdown {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            flex-wrap: nowrap;
            margin-top: 10px;
            min-width: max-content;
        }

        .rep-flow-warning {
            border-color: #f59e0b;
            background: #fff7ed;
        }

        @media (max-width: 1200px) {
            .rep-flow-v2 {
                overflow-x: auto;
            }

            .rep-flow-equation {
                grid-template-columns:
                    300px
                    auto
                    300px
                    auto
                    300px
                    auto
                    300px;
            }

            .rep-flow-support,
            .rep-flow-breakdown {
                flex-wrap: nowrap;
            }

            .rep-flow-support .rep-flow-item,
            .rep-flow-breakdown .rep-flow-item,
            .rep-flow-item {
                width: 300px;
                min-width: 300px;
                max-width: 300px;
                height: 78px;
            }

            .rep-flow-op {
                display: block;
            }
        }

        @media print {
            .rep-flow-v2 {
                break-inside: avoid;
                page-break-inside: avoid;
                overflow: visible;
            }

            .rep-flow-support,
            .rep-flow-breakdown {
                flex-wrap: nowrap;
            }
        }
    `;

    document.head.appendChild(style);
}

function flowGeneral(g) {
    inyectarEstilosResumenGeneral();

    const totalRecibidas = g.total_recibidas ?? g.registros_versiones ?? 0;
    const briefRechazados = g.brief_rechazados ?? 0;
    const canceladas = g.canceladas ?? 0;
    const totalGestionadas = g.total_gestionadas ?? g.total_a_gestionar ?? g.oportunidades_gestionadas ?? 0;
    const enProceso = g.en_proceso ?? 0;
    const circuitoFirmas = g.circuito_firmas ?? 0;
    const procesoComercial = g.proceso_comercial ?? 0;
    const procesoTecnico = g.proceso_tecnico ?? 0;
    const procesoSinClasificar = g.proceso_sin_clasificar ?? 0;
    const gestionadasMenosEnProceso = g.gestionadas_menos_en_proceso ?? g.ya_gestionadas ?? Math.max(totalGestionadas - enProceso, 0);

    const formula = [
        {
            label: "Total recibidas",
            value: totalRecibidas,
            help: "Cuenta todos los registros/versiones cargadas según los filtros aplicados."
        },
        {
            label: "Brief rechazados",
            value: briefRechazados,
            op: "-",
            help: "Registros/versiones que fueron rechazados desde brief."
        },
        {
            label: "Canceladas / abandonadas",
            value: canceladas,
            op: "-",
            help: "Registros/versiones cancelados, abandonados o cerrados por inviabilidad."
        },
        {
            label: "Total gestionadas",
            value: totalGestionadas,
            op: "=",
            highlight: true,
            help: "Total gestionadas = Total recibidas menos brief rechazados y canceladas. Es la base principal de gestión del reporte."
        }
    ];

    const support = [
        {
            label: "Total gestionadas",
            value: totalGestionadas,
            help: "Base de gestión del reporte."
        },
        {
            label: "Ya gestionadas",
            value: gestionadasMenosEnProceso,
            op: "-",
            help: "Registros/versiones que ya salieron del flujo activo. Incluye oferta ganada, oferta perdida, entregada a KAM y otros cierres."
        },
        {
            label: "En proceso",
            value: enProceso,
            op: "=",
            help: "Registros/versiones gestionadas que siguen activas."
        }
    ];

    const breakdown = [
        {
            label: "Proceso comercial",
            value: procesoComercial,
            help: "Factibilidad pendiente cliente, pendiente gestión documental, sin visita cliente / sin visita aliado y pendiente respuesta KAM."
        },
        {
            label: "Proceso técnico",
            value: procesoTecnico,
            op: "+",
            help: "Cotización equipos, validación IFBP, estructuración aliado / OT, visita programada y demás estados de factibilidad."
        },
        {
            label: "Circuito firmas",
            value: circuitoFirmas,
            op: "+",
            help: "Registros/versiones en Circuito Firmas."
        }
    ];

    if (procesoSinClasificar > 0) {
        breakdown.push({
            label: "Sin clasificar",
            value: procesoSinClasificar,
            op: "+",
            warning: true,
            help: "Estados activos que no entraron en comercial, técnico ni circuito firmas. Revisar si deben mapearse."
        });
    }

    return `
        <div class="rep-flow-v2">
            <div class="rep-flow-equation">
                ${formula.map((p, i) => `
                    ${i ? `<div class="rep-flow-op">${escapeHtml(p.op)}</div>` : ""}
                    <div class="rep-flow-item ${p.highlight ? "rep-flow-main" : ""}" title="${escapeHtml(p.help)}">
                        <strong>${fmtNum(p.value)}</strong>
                        <span>${escapeHtml(p.label)}</span>
                    </div>
                `).join("")}
            </div>

            <div class="rep-flow-support rep-flow-support-2">
                ${support.map((p, i) => `
                    ${i ? `<div class="rep-flow-op">${escapeHtml(p.op || '')}</div>` : ""}
                    <div class="rep-flow-item" title="${escapeHtml(p.help)}">
                        <strong>${fmtNum(p.value)}</strong>
                        <span>${escapeHtml(p.label)}</span>
                    </div>
                `).join("")}
            </div>

            <div class="rep-flow-breakdown">
                ${breakdown.map((p, i) => `
                    ${i ? `<div class="rep-flow-op">${escapeHtml(p.op || '+')}</div>` : ""}
                    <div class="rep-flow-item ${p.warning ? 'rep-flow-warning' : ''}" title="${escapeHtml(p.help)}">
                        <strong>${fmtNum(p.value)}</strong>
                        <span>${escapeHtml(p.label)}</span>
                    </div>
                `).join("")}
                <div class="rep-flow-op">=</div>
                <div class="rep-flow-item rep-flow-main" title="Debe cuadrar con En proceso.">
                    <strong>${fmtNum(enProceso)}</strong>
                    <span>En proceso</span>
                </div>
            </div>
        </div>
    `;
}

function card(title, value, small = "") {
    return `
        <div class="rep-card">
            <span>${escapeHtml(title)}</span>
            <strong>${escapeHtml(value)}</strong>
            <small>${escapeHtml(small)}</small>
        </div>
    `;
}

function sheetToolbar(sheetKey) {
    return `
        <div class="rep-sheet-toolbar no-export">
            <button class="btn btn-sm btn-outline-primary" onclick="exportSheetPdf('${sheetKey}')">
                Exportar hoja PDF
            </button>
        </div>
    `;
}

function globalToolbar() {
    return `
        <div class="rep-export-toolbar">
            <button class="btn btn-sm btn-app-primary" onclick="exportWholeReportPdf()">
                Exportar reporte completo PDF
            </button>
            <button class="btn btn-sm btn-outline-success" onclick="exportWholeReportExcel()">
                Exportar tablas de datos Excel
            </button>
        </div>
    `;
}

function miniTable(title, rows, cols = ["name", "value"], extraButton = "") {
    return `
        <div class="rep-panel">
            <div class="rep-panel-title-row">
                <h6>${escapeHtml(title)}</h6>
                ${extraButton || ""}
            </div>
            <div class="rep-table-wrap">
                <table class="table table-sm table-striped mb-0">
                    <tbody>
                        ${(rows || []).map(r => `
                            <tr title="${escapeHtml(r[cols[0]] || "")}: ${escapeHtml(r[cols[1]] ?? 0)}">
                                <td>${escapeHtml(r[cols[0]] || "")}</td>
                                <td class="text-end fw-bold">${escapeHtml(r[cols[1]] ?? 0)}</td>
                            </tr>
                        `).join("") || `<tr><td class="text-muted">Sin datos</td></tr>`}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function tipoProyectoNota() {
    return `
        <div class="rep-panel rep-note-panel tipo-proyecto-note">
            <h6>Nota tipo de proyecto</h6>
            <p class="mb-1"><b>Pequeño:</b> menor a $100 M.</p>
            <p class="mb-1"><b>Pequeño con factibilidad:</b> menor a $100 M y requiere factibilidad.</p>
            <p class="mb-1"><b>Mediano:</b> entre $100 M y $500 M.</p>
            <p class="mb-1"><b>Grande:</b> entre $500 M y $1.000 M.</p>
            <p class="mb-0"><b>Megaproyecto:</b> mayor a $1.000 M.</p>
        </div>
    `;
}

function bars(title, rows, horizontal = false, fallbackField = "") {
    const max = Math.max(...(rows || []).map(x => Number(x.value || 0)), 1);
    const total = (rows || []).reduce((a, b) => a + Number(b.value || 0), 0);

    return `
        <div class="rep-panel rep-chart-panel">
            <h6>${escapeHtml(title)}</h6>
            <div class="${horizontal ? "rep-bars-h" : "rep-bars"}">
                ${(rows || []).map((r, i) => {
                    const v = Number(r.value || 0);
                    const width = Math.max(5, Math.round((v / max) * 100));
                    r.total = total;

                    return `
                        <div class="rep-bar-row" ${itemAttr(r, fallbackField)}>
                            <span>${escapeHtml(r.name)}</span>
                            <div class="rep-bar-bg">
                                <div class="rep-bar-fill" style="width:${width}%; background:${PALETTE[i % PALETTE.length]}">
                                    <em>${v}</em>
                                </div>
                            </div>
                            <strong>${pct(v, total)}</strong>
                        </div>
                    `;
                }).join("") || `<p class="text-muted">Sin datos</p>`}
            </div>
        </div>
    `;
}

function dona(title, rows, fallbackField = "") {
    const total = (rows || []).reduce((a, b) => a + Number(b.value || 0), 0);
    let acc = 0;

    const stops = (rows || []).map((r, i) => {
        const start = total ? (acc / total) * 100 : 0;
        acc += Number(r.value || 0);
        const end = total ? (acc / total) * 100 : 0;

        return `${PALETTE[i % PALETTE.length]} ${start}% ${end}%`;
    }).join(", ") || "#e9ecef 0 100%";

    return `
        <div class="rep-panel rep-chart-panel">
            <h6>${escapeHtml(title)}</h6>
            <div class="rep-dona-box">
                <div class="rep-dona" style="background: conic-gradient(${stops})">
                    <span>${fmtNum(total)}</span>
                </div>
                <div class="rep-legend">
                    ${(rows || []).map((r, i) => {
                        r.total = total;

                        return `
                            <button type="button" class="rep-legend-item" ${itemAttr(r, fallbackField)}>
                                <span class="rep-dot" style="background:${PALETTE[i % PALETTE.length]}"></span>
                                <b>${escapeHtml(r.name)}</b>
                                <small>→ ${fmtNum(r.value)} · ${pct(r.value, total)}</small>
                            </button>
                        `;
                    }).join("") || "Sin datos"}
                </div>
            </div>
        </div>
    `;
}

function matrixTable(title, matrix, extraButton = "") {
    const cols = matrix?.columns || [];
    const rows = matrix?.rows || [];

    return `
        <div class="rep-panel">
            <div class="rep-panel-title-row">
                <h6>${escapeHtml(title)}</h6>
                ${extraButton || ""}
            </div>
            <div class="rep-table-wrap">
                <table class="table table-sm table-bordered mb-0">
                    <thead>
                        <tr>
                            <th>Estado / Grupo</th>
                            ${cols.map(c => `<th>${escapeHtml(c)}</th>`).join("")}
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(r => `
                            <tr>
                                <td>${escapeHtml(r.name)}</td>
                                ${cols.map(c => {
                                    const v = r.values?.[c] || 0;

                                    return `
                                        <td class="text-end" title="${escapeHtml(r.name)} - ${escapeHtml(c)}: ${v}">
                                            ${v ? v : ""}
                                        </td>
                                    `;
                                }).join("")}
                                <td class="text-end fw-bold">${r.total || ""}</td>
                            </tr>
                        `).join("") || `<tr><td class="text-muted">Sin datos</td></tr>`}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function detailTable(title, rows, type = "general", extraButton = "") {
    const baseCols = [
        "OP",
        "NombreCliente",
        "KAM",
        "Segmento",
        "CantidadLuminarias",
        "NumeroCotizacion",
        "EstadoOT",
        "EstadoOfertaOT",
        "Aliado",
        "Producto",
        "TipoProyecto",
        "HistoricoObservaciones",
        "Observaciones"
    ];

    const contratoCols = [
        "OP",
        "NombreCliente",
        "KAM",
        "TAMOT",
        "Segmento",
        "CantidadLuminarias",
        "NumeroCotizacion",
        "EstadoOT",
        "EstadoOfertaOT",
        "Aliado",
        "Producto",
        "TipoProyecto",
        "HistoricoObservaciones",
        "Observaciones"
    ];

    const pvCols = [
        "OP",
        "NombreCliente",
        "KAM",
        "Segmento",
        "NumeroCotizacion",
        "EstadoOT",
        "EstadoOfertaOT",
        "Aliado",
        "Producto",
        "TipoProyecto",
        "HistoricoObservaciones",
        "Observaciones"
    ];

    const apLightingCols = [
        "OP",
        "NombreCliente",
        "KAM",
        "TAMOT",
        "Segmento",
        "Producto",
        "CantidadLuminarias",
        "NumeroCotizacion",
        "EstadoOT",
        "EstadoOfertaOT",
        "Aliado",
        "TipoProyecto",
        "HistoricoObservaciones",
        "Observaciones",
        "FechaVigenciaOferta",
        "ValorUltimaOferta"
    ];

    const vigCols = [
        "OP",
        "NombreCliente",
        "KAM",
        "Producto",
        "Segmento",
        "CantidadLuminarias",
        "NumeroCotizacion",
        "EstadoOfertaOT",
        "FechaVigenciaOferta",
        "ValorUltimaOferta"
    ];

    const alertaCols = [
    "OP",
    "NombreCliente",
    "KAM",
    "TAMOT",
    "Segmento",
    "Producto",
    "Aliado",
    "NumeroCotizacion",
    "EstadoOfertaOT",
    "FechaEntregaOfertaAliado",
    "FechaInicioCircuitoFirmas",
    "DiasHabilesTranscurridosOT",
    "EstadoTiempoOT",
    "DiasRetrasoOT",
    "SolicitudEquipos",
    "ReciboCotizacionEquipos",
    "EstadoCotizacionEquipos"
];

    const bpCols = [
        "Title",
        "Origen de la oferta",
        "Nombre cliente",
        "KAM",
        "Segmento",
        "Producto",
        "Número de versión",
        "Fecha última cotización",
        "Aliado",
        "TAM O.T.",
        "Estado Oferta O.T.",
        "Fecha Aceptación Brief",
        "Fecha envío brief a Aliado",
        "Fecha real contacto Cliente",
        "Fecha programación visita",
        "Fecha de visita al Cliente",
        "Requiere Factibilidad",
        "Fecha solicitud de Factibilidad",
        "Fecha radicación Factibilidad",
        "Número de factibilidad",
        "Observación factibilidad",
        "Requiere cotización de equipos",
        "Fecha solicitud de equipos",
        "Fecha recibido cotización de equipos",
        "Fecha entrega oferta por parte Aliado",
        "Fecha Fin construcción oferta OT",
        "Fecha Entrega Validación Staff",
        "Fecha Inicio Circuito de Firmas",
        "Fecha de Entrega a KAM",
        "Fecha entrega oferta al Cliente",
        "Valor última oferta antes de IVA",
        "Fecha de Vigencia de Oferta",
        "Historico Observaciones",
        "Observaciones",
        "Estado",
        "Tipo py",
        "Requiere visitaa ?",
        "Cantidad Luminarias",
        "Número CRM",
        "Canal de venta BP",
        "CC / NIT cliente",
        "Persona de contacto BP",
        "Teléfono contacto BP",
        "Dirección BP",
        "Zona U.O.",
        "Localidad / Municipio",
        "Subzona U.O.",
        "Requerimiento BP",
        "Radicado recibo de obra",
        "Fecha solicitud ODS visita",
        "Número ODS visita",
        "Fecha envío ODS visita Planeación a Back Office",
        "Fecha envío ODS visita Back Office a U.O.",
        "Número S visita",
        "Fecha visita U.O.",
        "Fecha solicitud presupuesto BP",
        "Fecha envío presupuesto U.O. a Planeación/Back",
        "Fecha envío presupuesto CREG015",
        "Fecha envío presupuesto final a canal",
        "Valor presupuesto final U.O. antes IVA",
        "Valor presupuesto final U.O. después CREG015",
        "Valor presupuesto Salesforce XC",
        "Valor margen Enel X antes IVA",
        "Acta de visita",
        "Caso nota crédito",
        "Caso XC",
        "Causal ejecución BP",
        "Causal presupuesto BP",
        "Estado proyecto BP",
        "Fecha confirmación de pago",
        "Fecha confirmación respuesta cliente",
        "Fecha creación deudor",
        "Fecha ejecución U.O.",
        "Fecha entrega factura",
        "Fecha envío ODS ejecución Back Office a U.O.",
        "Fecha envío ODS ejecución Planeación a Back Office",
        "Fecha solicitud deudor",
        "Fecha solicitud factura",
        "Fecha solicitud ODS ejecución",
        "Margen final Enel X %",
        "Número AGP",
        "Número deudor SAP",
        "Número factura de venta",
        "Número ODS ejecución",
        "Responsable estado proyecto BP",
        "Valor facturado final U.O. / LM antes IVA",
        "Valor facturado margen Enel X antes IVA",
        "Valor presupuesto final cliente antes IVA"
    ];

    const mobilityCols = [
        "OP",
        "ID Forms Mobility",
        "Nombre cliente",
        "KAM",
        "Vendedor",
        "Canal",
        "Tipo servicio Mobility",
        "Tipo de cliente",
        "Estado Oferta O.T.",
        "Aliado",
        "Contacto",
        "Celular / WhatsApp",
        "Dirección",
        "Localidad",
        "Ciudad",
        "Departamento",
        "Marca vehículo",
        "Modelo vehículo",
        "Marca cargador",
        "Tipo cargador",
        "Potencia cargador",
        "Requiere instalación",
        "Requiere compra cargador",
        "Cantidad cargadores",
        "Cantidad instalaciones",
        "Tipo pagador",
        "Nombre pagador",
        "Documento pagador",
        "Fecha visita",
        "Fecha instalación",
        "Fecha entrega cargador",
        "Valor instalación",
        "Valor cargador",
        "IVA",
        "Número factura",
        "Número oferta cargador",
        "Fecha Inicio Circuito de Firmas",
        "Fecha de Entrega a KAM",
        "Observaciones vendedor",
        "Observaciones"
    ];

    const cols =
        type === "mobility"
            ? mobilityCols
            : type === "bp"
            ? bpCols
            : type === "vigentes"
                ? vigCols
                : type === "alerta"
                ? alertaCols
                : type === "contrato"
                    ? contratoCols
                    : type === "pv"
                        ? pvCols
                        : type === "ap_lighting"
                            ? apLightingCols
                            : baseCols;

    const labels = {
        NombreCliente: "Nombre cliente",
        CantidadLuminarias: "Cantidad de luminarias",
        NumeroCotizacion: "Versión",
        EstadoOT: "Estado O.T.",
        EstadoOfertaOT: "Estado Oferta O.T.",
        TipoProyecto: "Tipo py",
        HistoricoObservaciones: "Histórico Observaciones",
        TAMOT: "TAM O.T.",
        ValorUltimaOferta: "Valor última oferta",
        FechaVigenciaOferta: "Fecha vigencia oferta",
        FechaEntregaOfertaAliado: "Fecha entrega aliado",
        FechaInicioCircuitoFirmas: "Fecha inicio circuito firmas",
        DiasHabilesTranscurridosOT: "Tiempo OT",
        EstadoTiempoOT: "Estado tiempo OT",
        DiasRetrasoOT: "Días de retraso OT",
        SolicitudEquipos: "Solicitud equipos",
        ReciboCotizacionEquipos: "Recibo cotización equipos",
        EstadoCotizacionEquipos: "Estado cotización equipos"
    };

    return `
        <div class="rep-panel rep-panel-full">
            <div class="rep-panel-title-row">
                <h6>${escapeHtml(title)}</h6>
                ${extraButton || ""}
            </div>
            <div class="rep-table-wrap rep-detail-table">
                <table class="table table-sm table-striped mb-0">
                    <thead>
                        <tr>
                            ${cols.map(c => `<th>${escapeHtml(labels[c] || c)}</th>`).join("")}
                        </tr>
                    </thead>
                    <tbody>
                        ${(rows || []).map(r => `
                            <tr>
                                ${cols.map(c => `
                                    <td title="${escapeHtml(valorTablaReporte(r[c]))}">
                                        ${escapeHtml(valorTablaReporte(r[c]))}
                                    </td>
                                `).join("")}
                            </tr>
                        `).join("") || `<tr><td class="text-muted">Sin datos</td></tr>`}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function stackedStages(title, rows) {
    const legend = [
        "1. Entrega de aliado",
        "2. Construcción OT",
        "3. Circuito firmas"
    ];

    return `
        <div class="rep-panel rep-panel-full">
            <h6>${escapeHtml(title)}</h6>

            <div class="rep-stack-legend">
                ${legend.map((x, i) => `
                    <span>
                        <b style="background:${PALETTE[i]}"></b>
                        ${escapeHtml(x)}
                    </span>
                `).join("")}
            </div>

            ${(rows || []).map(row => {
                const total = Math.max(
                    row.stages.reduce((a, b) => a + Number(b.value || 0), 0),
                    1
                );

                return `
                    <div class="rep-stack-row">
                        <span>${escapeHtml(row.name)}</span>
                        <div class="rep-stack">
                            ${row.stages.map((s, i) => `
                                <div
                                    title="${escapeHtml(s.name)}: ${escapeHtml(s.value)} días"
                                    style="width:${Math.max(4, (Number(s.value || 0) / total) * 100)}%; background:${PALETTE[i % PALETTE.length]}"
                                >
                                    ${escapeHtml(s.value)}
                                </div>
                            `).join("")}
                        </div>
                        <strong>${fmtNum(total)}</strong>
                    </div>
                `;
            }).join("") || `<p class="text-muted">Sin datos</p>`}
        </div>
    `;
}

function ansChart(title, rows) {
    return `
        <div class="rep-panel rep-chart-panel">
            <h6>${escapeHtml(title)}</h6>

            <div class="rep-ans-legend">
                <span><b></b>Cumple ANS</span>
                <span><i></i>No cumple ANS</span>
            </div>

            ${(rows || []).map(r => {
                const total = Number(r.cumple || 0) + Number(r.no_cumple || 0) || 1;

                return `
                    <div class="rep-ans-row" title="${escapeHtml(r.name)}: Cumple ${r.cumple}, No cumple ${r.no_cumple}">
                        <span>${escapeHtml(r.name)}</span>
                        <div class="rep-ans">
                            <b style="width:${Math.max(4, (r.cumple / total) * 100)}%">
                                ${r.cumple}
                            </b>
                            <i style="width:${Math.max(4, (r.no_cumple / total) * 100)}%">
                                ${r.no_cumple}
                            </i>
                        </div>
                    </div>
                `;
            }).join("") || `<p class="text-muted">Sin datos</p>`}
        </div>
    `;
}

function ansRuleTable() {
    const inicialHeaders = [
        "Proceso",
        "Pequeño <100M",
        "Pequeño con Factibilidad <100M",
        "Mediano >100M<500M",
        "Grande >500M<1000M",
        "Megaproyecto >1000M"
    ];

    const inicial = [
        ["Creación Brief", "0,50", "0,50", "0,50", "0,50", "0,50"],
        ["Asignación Aliado", "0,50", "0,50", "0,50", "0,50", "0,50"],
        ["Programación Visita Comercial", "3,00", "3,00", "3,00", "3,00", "3,00"],
        ["Factibilidad O.R.", "", "7,00", "7,00", "7,00", "14,00"],
        ["Preparación Oferta Aliado", "2,00", "2,00", "2,00", "2,00", "2,00"],
        ["Cotización Equipos Enel", "-", "-", "2,00", "5,00", "8,00"],
        ["Estructuración Oferta + AB financiero OT", "2,00", "2,00", "2,00", "2,00", "2,00"],
        ["Cargue oferta en Sing", "1,00", "1,00", "1,00", "1,00", "1,00"],
        ["Firma oferta Sing", "5,00", "5,00", "5,00", "5,00", "5,00"],
        ["Entrega oferta KAM", "1,00", "1,00", "1,00", "1,00", "1,00"],
        ["Duración", "15,00", "22,00", "24,00", "27,00", "37,00"]
    ];

    const recHeaders = [
        "Proceso",
        "Pequeño",
        "Mediano",
        "Grande",
        "Megaproyecto"
    ];

    const rec = [
        ["Creación Brief", "1,00", "1,00", "1,00", "1,00"],
        ["Preparación Oferta Aliado", "2,00", "2,00", "2,00", "2,00"],
        ["Cotización Equipos Enel", "-", "-", "5,00", "5,00"],
        ["Estructuración Oferta + AB financiero OT", "2,00", "2,00", "2,00", "2,00"],
        ["Cargue oferta en Sing", "1,00", "1,00", "1,00", "1,00"],
        ["Firma oferta Sing", "5,00", "5,00", "5,00", "5,00"],
        ["Entrega oferta KAM", "1,00", "1,00", "1,00", "1,00"],
        ["Duración", "12,00", "12,00", "17,00", "17,00"]
    ];

    const makeTable = (title, headers, rows, extraButton = "") => `
        <div class="rep-panel">
            <div class="rep-panel-title-row">
                <h6>${escapeHtml(title)}</h6>
                ${extraButton || ""}
            </div>
            <div class="rep-table-wrap">
                <table class="table table-sm table-bordered ans-rule-table">
                    <thead>
                        <tr>
                            ${headers.map(h => `<th>${escapeHtml(h)}</th>`).join("")}
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(r => `
                            <tr>
                                ${r.map(c => `<td>${escapeHtml(c)}</td>`).join("")}
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    return `
        <div class="rep-grid-1">
            ${makeTable("Oferta Inicial", inicialHeaders, inicial)}
            ${makeTable("Recotización", recHeaders, rec)}
        </div>
    `;
}

function pintarReporteCompleto(r) {
    document.getElementById("reportGlobalExports").innerHTML = globalToolbar();

    const g = r.general || {};

    document.getElementById("repGeneralContent").innerHTML = `
        ${sheetToolbar("general")}
        ${flowGeneral(g)}

        <div class="rep-cards-grid rep-cards-3 mt-3">
            ${card("Monto total ofertado", fmtCOP(g.monto_total_ofertado), "Suma de todas las versiones")}
            ${card("Monto última versión OP", fmtCOP(g.monto_ultima_version_op), "Solo última versión por OP")}
            ${card("Tiempo total oferta", fmtNum(g.tiempo_total_oferta), "Promedio días hábiles")}
        </div>

        <div class="rep-grid-2 mt-3">
            ${dona("Cotizaciones / Recotizaciones", g.cot_recot, "tipo_version")}
            ${bars("Cotizaciones por Producto", g.por_producto, false, "Producto")}
        </div>

        <div class="rep-grid-2 mt-3">
            ${dona("Cotizaciones por Segmento", g.por_segmento, "Segmento")}
            <div class="rep-stacked-panel">
                ${bars("Cotizaciones por Tipo de proyecto", g.por_tipo, true, "tipo_proyecto")}
                ${tipoProyectoNota()}
            </div>
        </div>
    `;

    const d = r.detalle_op || {};

    document.getElementById("repDetalleOPContent").innerHTML = `
        ${sheetToolbar("detalle_op")}

        <div class="rep-cards-grid rep-cards-1">
            ${card("OPORTUNIDADES", d.total, "Gestionadas")}
        </div>

        <div class="rep-grid-2 mt-3">
            ${bars("Brief recibidos por Año", d.por_anio_recibidas, false, "year")}
            ${bars("Brief ya gestionados por Año", d.por_anio_entregadas, false, "year")}
        </div>

        <div class="rep-grid-2 mt-3">
            ${bars("Brief recibidos por Mes", d.por_mes_recibidas, false, "month")}
            ${bars("Brief gestionados por Mes", d.por_mes_gestionadas, false, "month")}
        </div>

        <div class="rep-grid-2 mt-3">
            ${dona("Brief recibidos por Producto", d.por_producto, "Producto")}
            ${bars("Brief recibidos por Segmento", d.por_segmento, true, "Segmento")}
        </div>
    `;

    const tg = r.tiempos_global || {};

    document.getElementById("repTiemposGlobalContent").innerHTML = `
        ${sheetToolbar("tiempos_global")}

        <div class="rep-grid-2">
            ${matrixTable("Cantidad de OP's por mes / Estado", tg.matriz_mes_estado, btnTablaExcel("cantidad_mes_estado"))}
        </div>

        <div class="mt-3">
            ${stackedStages("Promedio Tiempos por Etapas Global", tg.etapas)}
        </div>
    `;

    const of = r.detalle_ofertas || {};

    document.getElementById("repDetalleOfertasContent").innerHTML = `
        ${sheetToolbar("detalle_ofertas")}

        <div class="rep-grid-2">
            ${bars("Ofertas entregadas por Mes", of.entregadas_mes, false, "month")}
            ${bars("Promedio Tiempo Oferta en días hábiles", of.tiempo_mes, true, "month")}
        </div>

        <div class="mt-3">
            ${ansChart("Cumplimiento ANS Global por Tipo Oferta", of.ans)}
        </div>

        <div class="mt-3">
            ${ansRuleTable()}
        </div>
    `;

    const ans = r.ans_ot || {};

    document.getElementById("repANSOTContent").innerHTML = `
        ${sheetToolbar("ans_ot")}

        <div class="rep-cards-grid rep-cards-2">
            ${card("Monto total ofertado", fmtCOP(ans.monto))}
            ${card("Tiempo Oferta total", fmtNum(ans.tiempo), "Días hábiles")}
        </div>

        <div class="rep-grid-2 mt-3">
            ${bars("Ofertas entregadas por Mes y TAM O.T", ans.entregadas_tam, true, "tam")}
            ${bars("Promedio Tiempo en firmas", ans.firmas_mes, true, "month")}
        </div>

        <div class="mt-3">
            ${ansChart("Cumplimiento ANS estructuración O.T. (máx. 2 días)", ans.ans)}
        </div>
    `;

    const pk = r.pendientes_kam || {};

    document.getElementById("repPendientesKAMContent").innerHTML = `
        ${sheetToolbar("pendientes_kam")}

        <div class="rep-grid-2">
            ${matrixTable("Pendientes por Estado Oferta O.T. y Segmento", pk.matrix)}
            ${matrixTable("OP pendientes en gestión por KAM", pk.kam, btnTablaExcel("op_pendientes_kam"))}
        </div>

        <div class="rep-grid-2 mt-3">
            ${dona("OP por Segmento y Estado O.T.", pk.dona, "Segmento")}
            ${detailTable("Tabla Pendientes KAM", pk.rows, "general", btnTablaExcel("pendientes_kam"))}
        </div>
    `;

    const pc = r.pendientes_contratos || {};

    document.getElementById("repPendientesContratosContent").innerHTML = `
        ${sheetToolbar("pendientes_contratos")}

        <div class="rep-grid-2">
            ${matrixTable("Pendientes por Estado Oferta O.T. y Aliado", pc.matrix)}
            ${dona("OP por Aliado y Estado O.T.", pc.dona, "estado_ot")}
        </div>

        <div class="mt-3">
            ${detailTable("Tabla Pendientes Contrato", pc.rows, "contrato", btnTablaExcel("pendientes_contratos"))}
        </div>
    `;

    const pv = r.pv || {};

    document.getElementById("repPVContent").innerHTML = `
        ${sheetToolbar("pv")}

        <div class="rep-grid-2">
            ${matrixTable("Estados de PV", pv.matrix)}
            ${dona("Recuento de Número de OP por Estado Oferta O.T.", pv.dona, "estado_ot")}
        </div>

        <div class="mt-3">
            ${detailTable("Tabla oportunidades PV", pv.rows, "pv", btnTablaExcel("pv"))}
        </div>
    `;

    const apl = r.ap_lighting || {};

    document.getElementById("repAPLightingContent").innerHTML = `
        ${sheetToolbar("ap_lighting")}

        <div class="rep-grid-2">
            ${matrixTable("AP / Navidad por Estado Oferta O.T. y Producto", apl.matrix)}
            ${dona("AP / Navidad por Estado Oferta O.T.", apl.dona, "estado_ot")}
        </div>

        <div class="rep-grid-2 mt-3">
            ${miniTable("AP / Navidad por Producto", apl.por_producto)}
            ${detailTable("Tabla oportunidades AP / Navidad", apl.rows, "ap_lighting", btnTablaExcel("ap_lighting"))}
        </div>
    `;

    const bp = r.bp || {};

    document.getElementById("repBPContent").innerHTML = `
        ${sheetToolbar("bp")}

        <div class="rep-cards-grid rep-cards-1 mb-3">
            ${card("Total BP", bp.total || 0, "Boletines de pago")}
        </div>

        <div class="rep-grid-2">
            ${dona("BP por Estado proyecto", bp.por_estado || [], "estado_proyecto_bp")}
            ${bars("BP por Tipo de proyecto", bp.por_tipo || [], true, "tipo_proyecto")}
        </div>

        <div class="rep-grid-2 mt-3">
            ${miniTable("BP por Subzona U.O.", bp.por_subzona || [])}
            ${detailTable("Detalle BP", bp.rows || [], "bp", btnTablaExcel("bp"))}
        </div>
    `;

    const mobility = r.mobility || {};

    document.getElementById("repMobilityContent").innerHTML = `
        ${sheetToolbar("mobility")}

        <div class="rep-cards-grid rep-cards-3 mb-3">
            ${card("Solicitudes Mobility", mobility.total || 0, "Última versión por OP")}
            ${card("Entregadas a KAM", mobility.entregadas_kam || 0, "Gestión comercial")}
            ${card("Valor total", mobility.valor_total || "$ 0", "Ofertas Mobility antes de IVA")}
        </div>

        <div class="rep-grid-2">
            ${dona("Mobility por Estado Oferta O.T.", mobility.por_estado || [], "estado_ot")}
            ${bars("Mobility por Tipo servicio Mobility", mobility.por_servicio || [], true)}
        </div>

        <div class="rep-grid-2 mt-3">
            ${dona("Mobility por tipo de cliente", mobility.por_tipo_cliente || [])}
            ${dona("Mobility por aliado", mobility.por_aliado || [], "aliado")}
        </div>

        <div class="rep-grid-2 mt-3">
            ${bars("Cargadores por marca", mobility.por_marca_cargador || [], true)}
            ${miniTable("Potencia de cargador", mobility.por_potencia || [], ["label", "value"])}
        </div>

        <div class="mt-3">
            ${detailTable("Detalle Mobility", mobility.rows || [], "mobility", btnTablaExcel("mobility"))}
        </div>
    `;

    const vp = r.vigentes_proceso || {};

    const btnExcelVig = `
        <button
            class="btn btn-sm btn-outline-success"
            onclick="window.open('/api/export/report/vigentes-excel?${getReportQueryString()}','_blank')"
        >
            Exportar esta tabla Excel
        </button>
    `;

    const btnExcelProc = `
        <button
            class="btn btn-sm btn-outline-success"
            onclick="window.open('/api/export/report/proceso-excel?${getReportQueryString()}','_blank')"
        >
            Exportar Excel
        </button>
    `;

    document.getElementById("repVigentesProcesoContent").innerHTML = `
        ${sheetToolbar("vigentes_proceso")}

        <div class="rep-cards-grid rep-cards-1 mb-3">
            ${card("En proceso", vp.en_proceso_total)}
        </div>

        ${detailTable("Ofertas vigentes", vp.vigentes, "vigentes", btnExcelVig)}

        <div class="mt-3">
            ${detailTable("Ofertas en proceso", vp.en_proceso, "general", btnExcelProc)}
        </div>
    `;

    const jf = r.jefatura || {};

    const btnExcelJef = `
        <button
            class="btn btn-sm btn-outline-success"
            onclick="window.open('/api/export/report/jefatura-excel?${getReportQueryString()}','_blank')"
        >
            Exportar Excel
        </button>
    `;

    document.getElementById("repJefaturaContent").innerHTML = `
        ${sheetToolbar("jefatura")}

        <div class="rep-grid-2">
            ${matrixTable("Ofertas en proceso por Estado O.T. y Aliado", jf.matrix)}
            ${dona("OP por Aliado y Estado O.T.", jf.dona, "estado_ot")}
        </div>

        <div class="mt-3">
            ${detailTable("Detalle para ofertas en proceso", jf.rows, "general", btnExcelJef)}
        </div>
    `;

    const al = r.alerta_tiempos || {};

    const btnExcelAlerta = `
        <button
            class="btn btn-sm btn-outline-success"
            onclick="window.open('/api/export/report/alertas-excel?${getReportQueryString()}','_blank')"
        >
            Exportar Excel
        </button>
    `;

    document.getElementById("repAlertaTiemposContent").innerHTML = `
        ${sheetToolbar("alerta_tiempos")}

        <div class="rep-grid-2">
            ${matrixTable("Alertas por Estado Oferta O.T. y Aliado", al.matrix)}
            ${dona("OP por Aliado y Estado O.T.", al.dona, "estado_ot")}
        </div>

        <div class="mt-3">
            ${detailTable("Tabla detallada de alertas de tiempo", al.rows, "alerta", btnExcelAlerta)}
        </div>
    `;
}