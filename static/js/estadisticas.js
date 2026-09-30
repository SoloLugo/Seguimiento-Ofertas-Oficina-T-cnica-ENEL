// Código identificado para Valentina Becerra. Marca interna; no se muestra en la interfaz.
/* ============================================================
   ESTADÍSTICAS
============================================================ */

window.statsItemsCache = window.statsItemsCache || [];
window.estadisticasInicializadas = false;
window.cargandoEstadisticas = false;
window.statsRecargaPendiente = false;
window.statsDebounceTimer = null;
window.statsUltimaQuery = "";

function getActiveTabTargetStats() {
    return document.querySelector(".app-tabs .nav-link.active")?.getAttribute("data-bs-target") || "#tabListado";
}

function restoreActiveTabStats(target) {
    if (!target) return;
    const btn = document.querySelector(`.app-tabs [data-bs-target="${target}"]`);
    if (btn && window.bootstrap) {
        bootstrap.Tab.getOrCreateInstance(btn).show();
    }
}

/* ============================================================
   HELPERS SEGUROS DOM
============================================================ */

function getElStats(id) {
    return document.getElementById(id);
}

function setTextStatsSafe(id, value) {
    const el = getElStats(id);

    if (!el) {
        return;
    }

    el.innerText = value;
}

function setHtmlStatsSafe(id, html) {
    const el = getElStats(id);

    if (!el) {
        return;
    }

    el.innerHTML = html;
}

function escapeHtml(value) {
    if (value === null || value === undefined) return "";

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

/* ============================================================
   FALLBACK MULTISELECT
============================================================ */

if (typeof window.crearMultiselect !== "function") {
    window.crearMultiselect = function ({ id, label = "Todos", options = [], selected = [] }) {
        const container = getElStats(id);
        if (!container) return;

        const selectedSet = new Set((selected || []).map(String));

        container.classList.add("custom-multiselect");

        container.innerHTML = `
            <button type="button" class="custom-multiselect-button" onclick="toggleMultiselectStats('${id}')">
                <span id="${id}_label">${escapeHtml(label)}</span>
                <span class="custom-multiselect-arrow">▾</span>
            </button>

            <div class="custom-multiselect-menu" id="${id}_menu">
                <div class="custom-multiselect-actions">
                    <button type="button" onclick="seleccionarTodoMultiselectStats('${id}')">Todos</button>
                    <button type="button" onclick="limpiarMultiselectStats('${id}')">Limpiar</button>
                </div>

                <div class="custom-multiselect-options">
                    ${(options || []).map(opt => {
                        const value = String(opt.value ?? opt);
                        const text = String(opt.text ?? opt);
                        const checked = selectedSet.has(value) ? "checked" : "";

                        return `
                            <label class="custom-multiselect-option">
                                <input
                                    type="checkbox"
                                    value="${escapeHtml(value)}"
                                    ${checked}
                                    onchange="actualizarLabelMultiselectStats('${id}')"
                                >
                                <span>${escapeHtml(text)}</span>
                            </label>
                        `;
                    }).join("")}
                </div>
            </div>
        `;

        container.dataset.placeholder = label;
        actualizarLabelMultiselectStats(id);
    };
}

if (typeof window.getMultiselectValues !== "function") {
    window.getMultiselectValues = function (id) {
        const container = getElStats(id);
        if (!container) return [];

        return Array.from(container.querySelectorAll("input[type='checkbox']:checked"))
            .map(input => String(input.value || "").trim())
            .filter(Boolean);
    };
}

if (typeof window.limpiarMultiselect !== "function") {
    window.limpiarMultiselect = function (id) {
        limpiarMultiselectStats(id);
    };
}

if (typeof window.recargarMultiselect !== "function") {
    window.recargarMultiselect = function (id, options = [], selected = []) {
        const container = getElStats(id);
        if (!container) return;

        const placeholder = container.dataset.placeholder || "Todos";

        crearMultiselect({
            id,
            label: placeholder,
            options,
            selected
        });
    };
}

/* ============================================================
   FUNCIONES MULTISELECT
============================================================ */

function toggleMultiselectStats(id) {
    const menu = getElStats(`${id}_menu`);
    if (!menu) return;

    document.querySelectorAll(".custom-multiselect-menu.show").forEach(m => {
        if (m.id !== `${id}_menu`) {
            m.classList.remove("show");
        }
    });

    menu.classList.toggle("show");
}

function limpiarMultiselectStats(id) {
    const container = getElStats(id);
    if (!container) return;

    container.querySelectorAll("input[type='checkbox']").forEach(input => {
        input.checked = false;
    });

    actualizarLabelMultiselectStats(id);
}

function seleccionarTodoMultiselectStats(id) {
    const container = getElStats(id);
    if (!container) return;

    container.querySelectorAll("input[type='checkbox']").forEach(input => {
        input.checked = true;
    });

    actualizarLabelMultiselectStats(id);
}

function actualizarLabelMultiselectStats(id) {
    const container = getElStats(id);
    const labelElement = getElStats(`${id}_label`);

    if (!container || !labelElement) return;

    const placeholder = container.dataset.placeholder || "Todos";
    const checks = Array.from(container.querySelectorAll("input[type='checkbox']"));
    const selected = checks.filter(input => input.checked);

    if (selected.length === 0) {
        labelElement.innerText = placeholder;
        return;
    }

    if (selected.length === checks.length && checks.length > 0) {
        labelElement.innerText = "Todos";
        return;
    }

    if (selected.length === 1) {
        const text = selected[0].closest("label")?.querySelector("span")?.innerText || selected[0].value;
        labelElement.innerText = text;
        return;
    }

    labelElement.innerText = `${selected.length} seleccionados`;
}

document.addEventListener("click", function (event) {
    if (!event.target.closest(".custom-multiselect")) {
        document.querySelectorAll(".custom-multiselect-menu.show").forEach(menu => {
            menu.classList.remove("show");
        });
    }
});

/* ============================================================
   FILTROS
============================================================ */

function getSelectedValues(id) {
    if (typeof getMultiselectValues === "function") {
        return getMultiselectValues(id);
    }

    return [];
}

function selectedValuesIncludes(selectedValues, value) {
    if (!selectedValues || !selectedValues.length) return true;
    return selectedValues.map(String).includes(String(value || ""));
}

function getStatsQueryString() {
    const params = new URLSearchParams();

    getSelectedValues("statsFiltroAnio").forEach(value => params.append("year", value));
    getSelectedValues("statsFiltroMes").forEach(value => params.append("month", value));
    getSelectedValues("statsFiltroSegmento").forEach(value => params.append("segmento", value));
    getSelectedValues("statsFiltroProducto").forEach(value => params.append("producto", value));
    getSelectedValues("statsFiltroEstadoGeneral").forEach(value => params.append("estado_general", value));
    getSelectedValues("statsFiltroEstadoOT").forEach(value => params.append("estado_ot", value));
    getSelectedValues("statsFiltroTipoVersion").forEach(value => params.append("tipo_version", value));

    return params.toString();
}

function getFiltrosStatsActuales() {
    return {
        anio: getSelectedValues("statsFiltroAnio"),
        mes: getSelectedValues("statsFiltroMes"),
        segmento: getSelectedValues("statsFiltroSegmento"),
        producto: getSelectedValues("statsFiltroProducto"),
        estadoGeneral: getSelectedValues("statsFiltroEstadoGeneral"),
        estadoOT: getSelectedValues("statsFiltroEstadoOT"),
        tipoVersion: getSelectedValues("statsFiltroTipoVersion")
    };
}

function setValoresMultiselectStats(id, values) {
    const container = getElStats(id);

    if (!container) return;

    const selectedSet = new Set((values || []).map(v => String(v)));

    container.querySelectorAll("input[type='checkbox']").forEach(input => {
        input.checked = selectedSet.has(String(input.value));
    });

    actualizarLabelMultiselectStats(id);

    if (typeof actualizarMultiselect === "function") {
        actualizarMultiselect(id, false);
    }
}

function refrescarLabelStatsVisible(id) {
    if (typeof actualizarMultiselect === "function") {
        actualizarMultiselect(id, false);
    }

    actualizarLabelMultiselectStats(id);
}

function restaurarFiltrosStats(filtros) {
    if (!filtros) return;

    setValoresMultiselectStats("statsFiltroAnio", filtros.anio);
    setValoresMultiselectStats("statsFiltroMes", filtros.mes);
    setValoresMultiselectStats("statsFiltroSegmento", filtros.segmento);
    setValoresMultiselectStats("statsFiltroProducto", filtros.producto);
    setValoresMultiselectStats("statsFiltroEstadoGeneral", filtros.estadoGeneral);
    setValoresMultiselectStats("statsFiltroEstadoOT", filtros.estadoOT);
    setValoresMultiselectStats("statsFiltroTipoVersion", filtros.tipoVersion);

    [
        "statsFiltroAnio",
        "statsFiltroMes",
        "statsFiltroSegmento",
        "statsFiltroProducto",
        "statsFiltroEstadoGeneral",
        "statsFiltroEstadoOT",
        "statsFiltroTipoVersion"
    ].forEach(refrescarLabelStatsVisible);
}

function existeMultiselectConOpciones(id) {
    const container = getElStats(id);

    if (!container) return false;

    return container.classList.contains("custom-multiselect")
        && container.querySelectorAll("input[type='checkbox']").length > 0;
}

function crearFiltrosStatsBasicos() {
    const idsNecesarios = [
        "statsFiltroAnio",
        "statsFiltroMes",
        "statsFiltroSegmento",
        "statsFiltroProducto",
        "statsFiltroEstadoGeneral",
        "statsFiltroEstadoOT",
        "statsFiltroTipoVersion"
    ];

    const existen = idsNecesarios.every(id => getElStats(id));

    if (!existen) {
        console.warn("No existen todos los filtros de estadísticas en el HTML.");
        return false;
    }

    if (!existeMultiselectConOpciones("statsFiltroAnio")) {
        crearMultiselect({
            id: "statsFiltroAnio",
            label: "Todos",
            options: [
                { value: "2024", text: "2024" },
                { value: "2025", text: "2025" },
                { value: "2026", text: "2026" }
            ],
            selected: []
        });
    }

    if (!existeMultiselectConOpciones("statsFiltroMes")) {
        crearMultiselect({
            id: "statsFiltroMes",
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
            selected: []
        });
    }

    if (!existeMultiselectConOpciones("statsFiltroSegmento")) {
        crearMultiselect({
            id: "statsFiltroSegmento",
            label: "Todos",
            options: [],
            selected: []
        });
    }

    if (!existeMultiselectConOpciones("statsFiltroProducto")) {
        crearMultiselect({
            id: "statsFiltroProducto",
            label: "Todos",
            options: [],
            selected: []
        });
    }

    if (!existeMultiselectConOpciones("statsFiltroEstadoGeneral")) {
        crearMultiselect({
            id: "statsFiltroEstadoGeneral",
            label: "Todos",
            options: [
                { value: "Activa", text: "Activa" },
                { value: "Cerrada", text: "Cerrada" }
            ],
            selected: []
        });
    }

    if (!existeMultiselectConOpciones("statsFiltroEstadoOT")) {
        crearMultiselect({
            id: "statsFiltroEstadoOT",
            label: "Todos",
            options: [],
            selected: []
        });
    }

    if (!existeMultiselectConOpciones("statsFiltroTipoVersion")) {
        crearMultiselect({
            id: "statsFiltroTipoVersion",
            label: "Todos",
            options: [
                { value: "Cotización inicial", text: "Cotización inicial" },
                { value: "Recotización", text: "Recotización" },
                { value: "Sin versión", text: "Sin versión" }
            ],
            selected: []
        });
    }

    return true;
}

function actualizarOpcionesFiltrosStats(filterOptions) {
    if (!filterOptions) return;

    const filtrosActuales = getFiltrosStatsActuales();

    const segmentos = (filterOptions.segmentos || []).map(v => ({ value: v, text: v }));
    const productos = (filterOptions.productos || []).map(v => ({ value: v, text: v }));
    const estadosOT = (filterOptions.estados_ot || []).map(v => ({ value: v, text: v }));

    recargarMultiselect("statsFiltroSegmento", segmentos, filtrosActuales.segmento);
    recargarMultiselect("statsFiltroProducto", productos, filtrosActuales.producto);
    recargarMultiselect("statsFiltroEstadoOT", estadosOT, filtrosActuales.estadoOT);

    restaurarFiltrosStats(filtrosActuales);
}

function limpiarFiltrosStats() {
    [
        "statsFiltroAnio",
        "statsFiltroMes",
        "statsFiltroSegmento",
        "statsFiltroProducto",
        "statsFiltroEstadoGeneral",
        "statsFiltroEstadoOT",
        "statsFiltroTipoVersion"
    ].forEach(id => {
        limpiarMultiselectStats(id);
    });

    actualizarDatosStats();
}

/* ============================================================
   API
============================================================ */

async function apiGetConTimeoutStats(url, timeoutMs = 90000) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(url, {
            signal: controller.signal,
            cache: "no-store"
        });

        clearTimeout(timeout);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        clearTimeout(timeout);

        if (error.name === "AbortError") {
            throw new Error("La consulta tardó demasiado. Intente nuevamente.");
        }

        throw error;
    }
}

/* ============================================================
   CARGA PRINCIPAL
============================================================ */

async function cargarEstadisticas(forzar = false, recargarSharePoint = false) {
    if (window.cargandoEstadisticas) {
        window.statsRecargaPendiente = true;
        return;
    }

    if (window.estadisticasInicializadas && !forzar) {
        return;
    }

    const activeTabBefore = getActiveTabTargetStats();

    try {
        window.cargandoEstadisticas = true;
        window.statsRecargaPendiente = false;

        if (typeof limpiarAlerta === "function") {
            limpiarAlerta();
        }

        const filtrosOk = crearFiltrosStatsBasicos();

        if (!filtrosOk) {
            window.cargandoEstadisticas = false;
            return;
        }

        let qs = getStatsQueryString();
        if (recargarSharePoint) {
            qs = qs ? `${qs}&refresh=1` : "refresh=1";
        }
        const url = qs ? `/api/stats?${qs}` : "/api/stats";
        window.statsUltimaQuery = qs || "";

        setEstadoBotonStats(true);
        pintarEstadoCargaStats();

        const data = await apiGetConTimeoutStats(url, 90000);

        if (!data.ok) {
            throw new Error(data.error || "No fue posible cargar las estadísticas.");
        }

        const stats = data.stats || {};
        window.statsItemsCache = [];

        if (stats.filter_options) {
            actualizarOpcionesFiltrosStats(stats.filter_options);
        }

        pintarEstadisticas(stats);
        window.estadisticasInicializadas = true;

    } catch (e) {
        limpiarEstadoCargaStats();

        if (typeof mostrarAlerta === "function") {
            mostrarAlerta("error", "Error cargando estadísticas: " + e.message);
        } else {
            console.error("Error cargando estadísticas:", e);
        }
    } finally {
        window.cargandoEstadisticas = false;
        setEstadoBotonStats(false);
        restoreActiveTabStats(activeTabBefore);

        if (window.statsRecargaPendiente) {
            window.statsRecargaPendiente = false;
            window.estadisticasInicializadas = false;
            setTimeout(() => cargarEstadisticas(true, false), 80);
        }
    }
}

function actualizarDatosStats() {
    clearTimeout(window.statsDebounceTimer);
    window.statsDebounceTimer = setTimeout(() => {
        window.estadisticasInicializadas = false;
        cargarEstadisticas(true, false);
    }, 180);
}

function actualizarDatosStatsDesdeSharePoint() {
    clearTimeout(window.statsDebounceTimer);
    window.estadisticasInicializadas = false;
    cargarEstadisticas(true, true);
}

function setEstadoBotonStats(cargando) {
    const btn = getElStats("btnActualizarStats");

    if (!btn) return;

    btn.disabled = !!cargando;
    btn.innerText = cargando ? "Actualizando..." : "Actualizar datos";
}

function pintarEstadoCargaStats() {
    const contadores = [
        "totalRegistros",
        "totalGanadas",
        "totalPerdidas",
        "totalEntregadas",
        "totalActivasEstado",
        "totalCerradasEstado",
        "statTotal",
        "statGanadas",
        "statPerdidas",
        "statEntregadas",
        "statActivas",
        "statCerradas"
    ];

    contadores.forEach(id => {
        const el = getElStats(id);
        if (el) el.innerHTML = `<span class="stats-loading-box">Cargando...</span>`;
    });

    [
        "tablaPorAnio",
        "tablaPorMes",
        "tablaPorSegmento",
        "tablaPorProducto",
        "tablaPorKAM",
        "tablaPorEstado",
        "tablaPorTipoVersion"
    ].forEach(id => {
        const el = getElStats(id);
        if (!el) return;

        if (el.tagName === "TBODY") {
            el.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-muted">Actualizando...</td>
                </tr>
            `;
        } else {
            el.innerHTML = `<p class="text-muted">Actualizando...</p>`;
        }
    });

    setHtmlStatsSafe("cardsTiemposProceso", `
        <div class="col-md-12">
            <div class="stats-loading-box">Actualizando tiempos...</div>
        </div>
    `);
}

function limpiarEstadoCargaStats() {
    setHtmlStatsSafe("cardsTiemposProceso", `
        <div class="col-12 text-muted">
            No fue posible cargar los datos.
        </div>
    `);
}

function pintarEstadisticas(stats) {
    stats = stats || {};

    const total = stats.total ?? 0;
    const ganadas = stats.ganadas ?? 0;
    const perdidas = stats.perdidas ?? 0;
    const entregadas = stats.entregadas_kam ?? stats.entregadas ?? 0;
    const activas = stats.estado_general?.activas ?? stats.activas ?? 0;
    const cerradas = stats.estado_general?.cerradas ?? stats.cerradas ?? 0;

    /*
        Compatibilidad visual:
        - IDs nuevos: totalRegistros, totalGanadas, etc.
        - IDs anteriores: statTotal, statGanadas, etc.
        Así no se rompe si tu HTML todavía tiene la visual anterior.
    */
    setTextStatsSafe("totalRegistros", total);
    setTextStatsSafe("totalGanadas", ganadas);
    setTextStatsSafe("totalPerdidas", perdidas);
    setTextStatsSafe("totalEntregadas", entregadas);
    setTextStatsSafe("totalActivasEstado", activas);
    setTextStatsSafe("totalCerradasEstado", cerradas);

    setTextStatsSafe("statTotal", total);
    setTextStatsSafe("statGanadas", ganadas);
    setTextStatsSafe("statPerdidas", perdidas);
    setTextStatsSafe("statEntregadas", entregadas);
    setTextStatsSafe("statActivas", activas);
    setTextStatsSafe("statCerradas", cerradas);

    pintarTablasResumen(stats);
    pintarCardsTiempos(stats.tiempos || []);
}

function pintarTablasResumen(stats) {
    /*
        Se pintan todas las tablas que existan en el HTML.
        Si el contenedor es <tbody>, se pinta como tabla.
        Si es un <div>, se pinta con la visual bonita anterior: tarjetas + barra.
    */
    pintarTablaResumen("tablaPorAnio", stats.por_anio || []);
    pintarTablaResumen("tablaPorMes", stats.por_mes || []);
    pintarTablaResumen("tablaPorSegmento", stats.por_segmento || []);
    pintarTablaResumen("tablaPorProducto", stats.por_producto || []);
    pintarTablaResumen("tablaPorKAM", stats.por_kam || []);
    pintarTablaResumen("tablaPorEstado", stats.por_estado || []);
    pintarTablaResumen("tablaPorTipoVersion", stats.por_tipo_version || []);
}

function pintarTablaResumen(id, rows) {
    const container = getElStats(id);

    if (!container) {
        console.warn(`No existe tabla/contenedor resumen con id: ${id}`);
        return;
    }

    rows = rows || [];

    if (!rows.length) {
        if (container.tagName === "TBODY") {
            container.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-muted">Sin datos</td>
                </tr>
            `;
        } else {
            container.innerHTML = `<p class="text-muted">Sin datos.</p>`;
        }
        return;
    }

    /*
        Visual anterior bonita:
        Si el HTML tiene divs como tablaPorSegmento, tablaPorProducto, tablaPorKAM, etc.,
        se conserva el diseño de filas tipo tarjeta con barra horizontal.
    */
    if (container.tagName !== "TBODY") {
        const max = Math.max(...rows.map(r => Number(r.value || 0)), 1);

        container.innerHTML = `
            <div class="stats-table-wrap">
                ${rows.map(r => {
                    const value = Number(r.value || 0);
                    const pct = Math.round((value / max) * 100);

                    return `
                        <div class="stats-row">
                            <div class="stats-row-header">
                                <span title="${escapeHtml(r.name || "")}">${escapeHtml(r.name || "")}</span>
                                <strong>${value}</strong>
                            </div>
                            <div class="stats-bar">
                                <div class="stats-bar-fill" style="width:${pct}%"></div>
                            </div>
                        </div>
                    `;
                }).join("")}
            </div>
        `;
        return;
    }

    /*
        Compatibilidad con el HTML nuevo basado en tablas.
    */
    container.innerHTML = rows.map(r => {
        const value = Number(r.value || 0);
        const percent = r.percent !== undefined && r.percent !== null
            ? Number(r.percent || 0)
            : 0;

        return `
            <tr>
                <td>${escapeHtml(r.name || "")}</td>
                <td class="text-end fw-bold">${value}</td>
                <td>
                    <div class="stats-bar">
                        <div class="stats-bar-fill" style="width:${Math.min(100, percent)}%"></div>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

/* ============================================================
   TARJETAS TIEMPOS
============================================================ */

function findMetric(tiempos, id) {
    return (tiempos || []).find(x => x.id === id) || {};
}

function pintarCardsTiempos(tiempos) {
    const container = getElStats("cardsTiemposProceso");

    if (!container) {
        console.warn("No existe el contenedor cardsTiemposProceso");
        return;
    }

    tiempos = tiempos || [];

    if (!tiempos.length) {
        container.innerHTML = `<div class="col-md-12 text-muted">Sin datos.</div>`;
        return;
    }

    const metricOrder = [
        "brief_aliado",
        "contacto_programacion",
        "programacion_visita",
        "solicitud_radicacion_factibilidad",
        "solicitud_recibo_equipos",
        "aliado_fin_estructuracion",
        "fin_validacion_staff",
        "validacion_firmas",
        "firmas_kam"
    ];

    const byId = new Map(tiempos.map(m => [m.id, m]));

    const ordered = [
        ...metricOrder.map(id => byId.get(id)).filter(Boolean),
        ...tiempos.filter(m => !metricOrder.includes(m.id))
    ];

    container.innerHTML = `
        <div class="col-12">
            <div class="time-section-card time-section-total">

                <div class="time-section-header">
                    <span>Tiempos del proceso</span>
                    <small>Total, cotización inicial y recotización por cada tramo</small>
                </div>

                <div class="time-comparison-header">
                    <div>Total</div>
                    <div>Inicial</div>
                    <div>Recotización</div>
                </div>

                <div class="time-comparison-body">
                    ${ordered.map(r => crearFilaTiempoTriple(r)).join("")}
                </div>

            </div>
        </div>
    `;
}

function crearFilaTiempoTriple(r) {
    return `
        <div class="time-comparison-row">

            ${crearCeldaTiempoTriple({
                titulo: r.name || r.id,
                avg: r.avg_days,
                count: r.count,
                applicableCount: r.applicable_count,
                metricId: r.id,
                tipoVersion: "",
                buttonClass: "btn-outline-primary"
            })}

            ${crearCeldaTiempoTriple({
                titulo: r.name || r.id,
                avg: r.initial_avg_days,
                count: r.initial_count,
                applicableCount: r.initial_applicable_count,
                metricId: r.id,
                tipoVersion: "Cotización inicial",
                buttonClass: "btn-outline-success"
            })}

            ${crearCeldaTiempoTriple({
                titulo: r.name || r.id,
                avg: r.recot_avg_days,
                count: r.recot_count,
                applicableCount: r.recot_applicable_count,
                metricId: r.id,
                tipoVersion: "Recotización",
                buttonClass: "btn-outline-warning"
            })}

        </div>
    `;
}

function crearCeldaTiempoTriple({ titulo, avg, count, applicableCount, metricId, tipoVersion, buttonClass }) {
    const promedio = avg === "" || avg === null || avg === undefined
        ? "Sin dato"
        : `${avg} días`;

    const onclick = tipoVersion
        ? `verDetalleTiempo('${metricId}', '${tipoVersion}')`
        : `verDetalleTiempo('${metricId}')`;

    return `
        <div class="time-comparison-cell">
            <div class="time-comparison-title" title="${escapeHtml(titulo)}">
                ${escapeHtml(titulo)}
            </div>

            <div class="time-comparison-info">
                <strong>${promedio}</strong>
                <span>${Number(count || 0)} de ${Number(applicableCount || 0)}</span>
                <button class="btn btn-sm ${buttonClass}" onclick="${onclick}">
                    Ver datos
                </button>
            </div>
        </div>
    `;
}

/* ============================================================
   DETALLE TIEMPOS
============================================================ */

const LABELS_FECHAS_TIEMPOS = {
    FechaAceptacionBrief: "Fecha aceptación brief",
    FechaEnvioBriefAliado: "Fecha envío brief a aliado",
    FechaRealContactoCliente: "Fecha real contacto cliente",
    FechaProgramacionVisita: "Fecha programación visita",
    FechaVisitaCliente: "Fecha visita cliente",
    FechaSolicitudFactibilidad: "Fecha solicitud factibilidad",
    FechaRadicacionFactibilidad: "Fecha radicación factibilidad",
    FechaSolicitudEquipos: "Fecha solicitud equipos",
    FechaRecibidoCotizacionEquipos: "Fecha recibido cotización equipos",
    FechaEntregaOfertaAliado: "Fecha entrega oferta aliado",
    FechaFinConstruccionOfertaOT: "Fecha fin construcción oferta O.T.",
    FechaEntregaValidacionStaff: "Fecha entrega validación staff",
    FechaInicioCircuitoFirmas: "Fecha inicio circuito de firmas",
    FechaEntregaKAM: "Fecha entrega a KAM",
    FechaUltimaVersion: "Fecha última versión"
};

function obtenerLabelFechaTiempo(campo) {
    const key = String(campo || "").trim();
    return LABELS_FECHAS_TIEMPOS[key] || key || "Fecha";
}

function pintarEncabezadoDetalleTiempo(labelInicio, labelFin) {
    const tbody = getElStats("tablaDetalleTiempo");
    const table = tbody?.closest("table");
    const thead = table?.querySelector("thead");

    if (!thead) {
        console.warn("No existe thead para tablaDetalleTiempo");
        return;
    }

    thead.innerHTML = `
        <tr>
            <th>Acción</th>
            <th>OP</th>
            <th>Versión</th>
            <th>Tipo versión</th>
            <th>Cliente</th>
            <th>KAM</th>
            <th>Segmento</th>
            <th>Producto</th>
            <th>Estado O.T.</th>
            <th>${escapeHtml(labelInicio)}</th>
            <th>${escapeHtml(labelFin)}</th>
            <th>Días hábiles</th>
        </tr>
    `;
}

function limpiarBackdropsBootstrapStats() {
    document.querySelectorAll(".modal-backdrop").forEach(el => el.remove());
    document.body.classList.remove("modal-open");
    document.body.style.removeProperty("padding-right");
}

function abrirModalDetalleTiempo() {
    const modalEl = getElStats("modalDetalleTiempo");

    if (!modalEl) {
        console.warn("No existe modalDetalleTiempo");
        return;
    }

    limpiarBackdropsBootstrapStats();

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl, {
        backdrop: true,
        keyboard: true,
        focus: true
    });

    modal.show();
}

function pintarLoadingDetalleTiempo(metricId) {
    const titulo = getElStats("tituloDetalleTiempo");
    const tbody = getElStats("tablaDetalleTiempo");

    if (titulo) {
        titulo.innerText = "Cargando detalle del tiempo...";
    }

    pintarEncabezadoDetalleTiempo("Fecha inicio", "Fecha fin");

    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="12" class="text-center text-muted py-4">
                    Cargando datos...
                </td>
            </tr>
        `;
    }

    abrirModalDetalleTiempo();
}

async function verDetalleTiempo(metricId, tipoVersionOverride = "") {
    pintarLoadingDetalleTiempo(metricId);

    try {
        if (typeof limpiarAlerta === "function") {
            limpiarAlerta();
        }

        const baseQs = getStatsQueryString();
        const params = new URLSearchParams(baseQs);

        params.set("metric_id", metricId);

        if (tipoVersionOverride) {
            params.delete("tipo_version");
            params.append("tipo_version", tipoVersionOverride);
        }

        const data = await apiGetConTimeoutStats(`/api/stats/time-detail?${params.toString()}`, 90000);

        if (!data.ok) {
            throw new Error(data.error || "No fue posible cargar el detalle.");
        }

        const detail = data.detail || {};
        const rows = detail.rows || [];
        const metric = detail.metric || {};
        const aplicables = detail.applicable_count ?? rows.length;

        const campoInicio = metric.start || rows[0]?.CampoFechaInicio || "";
        const campoFin = metric.end || rows[0]?.CampoFechaFin || "";

        const labelInicio = obtenerLabelFechaTiempo(campoInicio);
        const labelFin = obtenerLabelFechaTiempo(campoFin);

        const titulo = getElStats("tituloDetalleTiempo");

        if (titulo) {
            const sufijoTipo = tipoVersionOverride ? ` · ${tipoVersionOverride}` : "";
            titulo.innerText = `${metric.name || "Detalle del tiempo"}${sufijoTipo} (${rows.length} de ${aplicables} aplicables)`;
        }

        pintarEncabezadoDetalleTiempo(labelInicio, labelFin);

        const tbody = getElStats("tablaDetalleTiempo");
        if (!tbody) return;

        if (!rows.length) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="12" class="text-center text-muted py-4">
                        No hay registros con ambas fechas diligenciadas para este tramo.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = rows.map(r => `
            <tr>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editarDesdeDetalleTiempo(${Number(r.Id || 0)})">
                        Editar
                    </button>
                </td>
                <td>${escapeHtml(r.OP || "")}</td>
                <td>${escapeHtml(r.NumeroVersion || "")}</td>
                <td>${escapeHtml(r.TipoVersion || "")}</td>
                <td>${escapeHtml(r.NombreCliente || "")}</td>
                <td>${escapeHtml(r.KAM || "")}</td>
                <td>${escapeHtml(r.Segmento || "")}</td>
                <td>${escapeHtml(r.Producto || "")}</td>
                <td>${escapeHtml(r.EstadoOfertaOT || "")}</td>
                <td>${escapeHtml(r.FechaInicio || "")}</td>
                <td>${escapeHtml(r.FechaFin || "")}</td>
                <td><strong>${escapeHtml(r.DiasHabiles ?? "")}</strong></td>
            </tr>
        `).join("");

        abrirModalDetalleTiempo();

    } catch (e) {
        const tbody = getElStats("tablaDetalleTiempo");

        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="12" class="text-center text-danger py-4">
                        Error cargando detalle de tiempo: ${escapeHtml(e.message)}
                    </td>
                </tr>
            `;
        }

        if (typeof mostrarAlerta === "function") {
            mostrarAlerta("error", "Error cargando detalle de tiempo: " + e.message);
        } else {
            console.error("Error cargando detalle de tiempo:", e);
        }
    }
}

async function editarDesdeDetalleTiempo(id) {
    try {
        if (typeof cerrarModalBootstrap === "function") {
            await cerrarModalBootstrap("modalDetalleTiempo");
        } else {
            const modalEl = getElStats("modalDetalleTiempo");
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }

        if (typeof editarRegistro === "function") {
            await editarRegistro(id);
        }
    } catch (e) {
        if (typeof limpiarBackdropsBootstrap === "function") {
            limpiarBackdropsBootstrap();
        } else {
            limpiarBackdropsBootstrapStats();
        }

        if (typeof mostrarAlerta === "function") {
            mostrarAlerta("error", "Error abriendo el registro para edición: " + e.message);
        }
    }
}

/* ============================================================
   DETALLE ESTADOS
============================================================ */

async function obtenerItemsStats() {
    if (window.statsItemsCache.length) {
        return window.statsItemsCache;
    }

    const data = await apiGetConTimeoutStats("/api/items", 90000);

    if (!data.ok) {
        throw new Error(data.error || "No fue posible cargar los registros.");
    }

    window.statsItemsCache = data.items || [];
    return window.statsItemsCache;
}

function obtenerTipoVersionItem(item) {
    const raw = String(item.NumeroVersion || item.NumeroCotizacion || "").trim().replace(",", ".");
    const version = Number(raw);

    if (!isNaN(version) && version === 1) {
        return "Cotización inicial";
    }

    if (!isNaN(version) && version >= 2) {
        return "Recotización";
    }

    return "Sin versión";
}

function filtrarItemsStatsBase(items) {
    const years = getSelectedValues("statsFiltroAnio");
    const months = getSelectedValues("statsFiltroMes");
    const segmentos = getSelectedValues("statsFiltroSegmento");
    const productos = getSelectedValues("statsFiltroProducto");
    const estadosGenerales = getSelectedValues("statsFiltroEstadoGeneral");
    const estadosOT = getSelectedValues("statsFiltroEstadoOT");
    const tiposVersion = getSelectedValues("statsFiltroTipoVersion");

    return items.filter(item => {
        const anioItem = obtenerAnioStats(item.FechaUltimaVersion || "");
        const mesItem = obtenerMesStats(item.FechaUltimaVersion || "");
        const tipoVersionItem = obtenerTipoVersionItem(item);

        return selectedValuesIncludes(years, anioItem)
            && selectedValuesIncludes(months, mesItem)
            && selectedValuesIncludes(segmentos, item.Segmento || "")
            && selectedValuesIncludes(productos, item.Producto || "")
            && selectedValuesIncludes(estadosGenerales, item.EstadoGeneral || "")
            && selectedValuesIncludes(estadosOT, item.EstadoOfertaOT || "")
            && selectedValuesIncludes(tiposVersion, tipoVersionItem);
    });
}

function filtrarPorIndicadorEstado(items, tipo) {
    if (tipo === "total") {
        return items;
    }

    if (tipo === "ganadas") {
        return items.filter(x =>
            String(x.EstadoOfertaOT || "").toLowerCase().includes("ganada")
            || String(x.EstadoOfertaOT || "").toLowerCase().includes("ganado")
        );
    }

    if (tipo === "perdidas") {
        return items.filter(x =>
            String(x.EstadoOfertaOT || "").toLowerCase().includes("perdida")
            || String(x.EstadoOfertaOT || "").toLowerCase().includes("perdido")
        );
    }

    if (tipo === "entregadas") {
        return items.filter(x =>
            String(x.EstadoOfertaOT || "").toLowerCase().includes("entregada a kam")
            || (
                String(x.EstadoOfertaOT || "").toLowerCase().includes("entregada")
                && String(x.EstadoOfertaOT || "").toLowerCase().includes("kam")
            )
        );
    }

    if (tipo === "activas") {
        return items.filter(x =>
            String(x.EstadoGeneral || "").trim().toLowerCase() === "activa"
        );
    }

    if (tipo === "cerradas") {
        return items.filter(x =>
            String(x.EstadoGeneral || "").trim().toLowerCase() === "cerrada"
        );
    }

    return items;
}

function tituloIndicadorEstado(tipo) {
    if (tipo === "total") return "Total registros";
    if (tipo === "ganadas") return "Ofertas ganadas";
    if (tipo === "perdidas") return "Ofertas perdidas";
    if (tipo === "entregadas") return "Entregadas a KAM";
    if (tipo === "activas") return "Ofertas activas";
    if (tipo === "cerradas") return "Ofertas cerradas";
    return "Detalle de ofertas";
}

async function verDetalleEstadoStats(tipo) {
    try {
        if (typeof limpiarAlerta === "function") {
            limpiarAlerta();
        }

        const allItems = await obtenerItemsStats();
        const filtradosBase = filtrarItemsStatsBase(allItems);
        const rows = filtrarPorIndicadorEstado(filtradosBase, tipo);

        setTextStatsSafe(
            "tituloDetalleEstadoStats",
            `${tituloIndicadorEstado(tipo)} (${rows.length} registros)`
        );

        const tbody = getElStats("tablaDetalleEstadoStats");

        if (!tbody) return;

        if (!rows.length) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="18" class="text-center text-muted">
                        No se encontraron registros con los filtros seleccionados.
                    </td>
                </tr>
            `;
        } else {
            tbody.innerHTML = rows.map(item => `
                <tr>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="editarDesdeDetalleEstado(${Number(item.Id || 0)})">
                            Editar
                        </button>
                    </td>
                    <td>${escapeHtml(item.OP || item.Title || "")}</td>
                    <td>${escapeHtml(item.NumeroVersion || item.NumeroCotizacion || "")}</td>
                    <td>${escapeHtml(obtenerTipoVersionItem(item))}</td>
                    <td>${escapeHtml(item.NombreCliente || "")}</td>
                    <td>${escapeHtml(item.KAM || "")}</td>
                    <td>${escapeHtml(item.Segmento || "")}</td>
                    <td>${escapeHtml(item.Producto || "")}</td>
                    <td>${escapeHtml(item.EstadoGeneral || "")}</td>
                    <td>${escapeHtml(item.EstadoOfertaOT || "")}</td>
                    <td>${escapeHtml(formatearFechaStats(item.FechaUltimaVersion || ""))}</td>
                    <td>${escapeHtml(formatearCOPStats(item.ValorUltimaOferta || ""))}</td>
                </tr>
            `).join("");
        }

        const modalEl = getElStats("modalDetalleEstadoStats");

        if (modalEl) {
            limpiarBackdropsBootstrapStats();
            const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();
        }

    } catch (e) {
        if (typeof mostrarAlerta === "function") {
            mostrarAlerta("error", "Error cargando detalle de ofertas: " + e.message);
        } else {
            console.error("Error cargando detalle de ofertas:", e);
        }
    }
}

async function editarDesdeDetalleEstado(id) {
    try {
        if (typeof cerrarModalBootstrap === "function") {
            await cerrarModalBootstrap("modalDetalleEstadoStats");
        } else {
            const modalEl = getElStats("modalDetalleEstadoStats");
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }

        if (typeof editarRegistro === "function") {
            await editarRegistro(id);
        }
    } catch (e) {
        if (typeof limpiarBackdropsBootstrap === "function") {
            limpiarBackdropsBootstrap();
        } else {
            limpiarBackdropsBootstrapStats();
        }

        if (typeof mostrarAlerta === "function") {
            mostrarAlerta("error", "Error abriendo el registro para edición: " + e.message);
        }
    }
}

/* ============================================================
   EXPORTACIONES
============================================================ */

function exportarDataStats() {
    const qs = getStatsQueryString();
    const url = qs ? `/api/export/data?${qs}` : "/api/export/data";
    window.open(url, "_blank");
}

function exportarPdfStats() {
    const qs = getStatsQueryString();
    const url = qs ? `/api/export/pdf?${qs}` : "/api/export/pdf";
    window.open(url, "_blank");
}

function exportarPdfTiempos() {
    const qs = getStatsQueryString();
    const url = qs ? `/api/export/pdf-tiempos?${qs}` : "/api/export/pdf-tiempos";
    window.open(url, "_blank");
}

/* ============================================================
   HELPERS LOCALES
============================================================ */

function obtenerAnioStats(fecha) {
    if (typeof obtenerAnio === "function") {
        return obtenerAnio(fecha);
    }

    if (!fecha) return "";

    const texto = String(fecha).trim();

    const matchIso = texto.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (matchIso) return Number(matchIso[1]);

    const matchLatam = texto.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
    if (matchLatam) return Number(matchLatam[3]);

    const d = new Date(texto);
    if (!isNaN(d.getTime())) return d.getFullYear();

    return "";
}

function obtenerMesStats(fecha) {
    if (typeof obtenerMes === "function") {
        return obtenerMes(fecha);
    }

    if (!fecha) return "";

    const texto = String(fecha).trim();

    const matchIso = texto.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (matchIso) return Number(matchIso[2]);

    const matchLatam = texto.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
    if (matchLatam) return Number(matchLatam[2]);

    const d = new Date(texto);
    if (!isNaN(d.getTime())) return d.getMonth() + 1;

    return "";
}

function formatearFechaStats(value) {
    if (typeof formatearFecha === "function") {
        return formatearFecha(value);
    }

    if (!value) return "";

    const texto = String(value).trim();
    const matchIso = texto.match(/^(\d{4})-(\d{2})-(\d{2})/);

    if (matchIso) {
        return `${matchIso[3]}/${matchIso[2]}/${matchIso[1]}`;
    }

    return texto;
}

function formatearCOPStats(value) {
    if (typeof formatearCOP === "function") {
        return formatearCOP(value);
    }

    if (value === null || value === undefined || value === "") return "";

    const numero = Number(value);

    if (isNaN(numero)) return value;

    return new Intl.NumberFormat("es-CO", {
        style: "currency",
        currency: "COP",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(numero);
}

/* ============================================================
   INICIALIZACIÓN
============================================================ */

function inicializarEstadisticas() {
    const tabStats = getElStats("tabStats");

    if (!tabStats) return;

    crearFiltrosStatsBasicos();

    const estaVisible =
        tabStats.classList.contains("show")
        || tabStats.classList.contains("active")
        || window.getComputedStyle(tabStats).display !== "none";

    if (estaVisible) {
        cargarEstadisticas(false);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    inicializarEstadisticas();

    const statsTabButton = document.querySelector('[data-bs-target="#tabStats"]');

    if (statsTabButton) {
        statsTabButton.addEventListener("shown.bs.tab", () => {
            inicializarEstadisticas();
            cargarEstadisticas(false);
        });
    }

    setTimeout(inicializarEstadisticas, 300);
    setTimeout(inicializarEstadisticas, 1000);
});

window.addEventListener("load", () => {
    inicializarEstadisticas();
});