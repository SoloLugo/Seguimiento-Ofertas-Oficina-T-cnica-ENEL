/* ============================================================
   LISTAS DESPLEGABLES DEL FORMULARIO
============================================================ */

async function cargarOpcionesDinamicas() {
    if (opcionesCargadas) return;

    try {
        const data = await apiGet("/api/choices");
        const choices = data.choices || {};

        document.querySelectorAll("[data-choice]").forEach(select => {
            const key = select.getAttribute("data-choice");
            const values = choices[key] || [];

            select.innerHTML = `<option value=""></option>`;

            values.forEach(v => {
                const option = document.createElement("option");
                option.value = v;
                option.textContent = v;
                select.appendChild(option);
            });
        });

        opcionesCargadas = true;

    } catch (e) {
        mostrarAlerta("error", "Error cargando listas desplegables desde SharePoint: " + e.message);
    }
}

/* ============================================================
   NAVEGACIÓN
============================================================ */

function abrirTabFormulario() {
    const tab = new bootstrap.Tab(document.querySelector('[data-bs-target="#tabFormulario"]'));
    tab.show();
}

function abrirTabListado() {
    const tab = new bootstrap.Tab(document.querySelector('[data-bs-target="#tabListado"]'));
    tab.show();
}

async function abrirNuevo() {
    await nuevoRegistro();
    abrirTabFormulario();
}

/* ============================================================
   FORMULARIO
============================================================ */

async function nuevoRegistro() {
    await cargarOpcionesDinamicas();

    document.getElementById("formOP").reset();
    document.getElementById("ItemId").value = "";
    document.getElementById("tituloFormulario").innerText = "Nuevo registro";
    document.getElementById("lblId").classList.add("d-none");
    document.getElementById("lblId").innerText = "";
    document.getElementById("btnEliminarEditar").classList.add("d-none");
    document.getElementById("btnPrepararRecotizacion")?.classList.add("d-none");

    aplicarCamposOpcionalesVisitaV7();
    aplicarCampoCantidadLuminariasProductoAP();
    limpiarAlerta();
}

async function editarRegistro(id) {
    try {
        limpiarAlerta();
        await cargarOpcionesDinamicas();

        const data = await apiGet("/api/item/" + id);
        const item = data.item;

        document.getElementById("formOP").reset();

        document.getElementById("ItemId").value = id;
        document.getElementById("tituloFormulario").innerText = "Editar registro";
        document.getElementById("lblId").classList.remove("d-none");
        document.getElementById("lblId").innerText = "ID SharePoint: " + id;
        document.getElementById("btnEliminarEditar").classList.remove("d-none");
        document.getElementById("btnPrepararRecotizacion")?.classList.remove("d-none");

        document.querySelectorAll("[data-title]").forEach(input => {
            const title = input.getAttribute("data-title");
            let value = item[title] ?? "";

            if (input.type === "date" && value) {
                const texto = String(value).trim();
                const matchIso = texto.match(/^(\d{4})-(\d{2})-(\d{2})/);

                if (matchIso) {
                    value = `${matchIso[1]}-${matchIso[2]}-${matchIso[3]}`;
                } else {
                    const d = new Date(value);
                    if (!isNaN(d.getTime())) {
                        value = d.toISOString().substring(0, 10);
                    }
                }
            }

            if (input.tagName === "SELECT" && value) {
                asegurarOpcionSelect(input, value);
            }

            input.value = value;
        });

        document.getElementById("OP").value = item["OP"] || item["Title"] || "";

        aplicarCamposOpcionalesVisitaV7();
        aplicarCampoCantidadLuminariasProductoAP();

        abrirTabFormulario();

    } catch (e) {
        mostrarAlerta("error", "Error cargando registro: " + e.message);
    }
}

function asegurarOpcionSelect(select, value) {
    const existe = Array.from(select.options).some(o => o.value === value);

    if (!existe) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
    }
}

function incrementarVersionActual() {
    const inputVersion = Array.from(document.querySelectorAll("[data-title]")).find(x => x.getAttribute("data-title") === "Número de Versión");
    const actual = Number(String(inputVersion?.value || "0").replace(",", "."));
    if (inputVersion) inputVersion.value = !isNaN(actual) && actual > 0 ? String(Math.floor(actual) + 1) : "2";
}

function limpiarCamposProcesoParaRecotizacion() {
    const camposALimpiar = [
        "Fecha última versión",
        "Estado Oferta O.T.",
        "Fecha Aceptación Brief",
        "Fecha envío brief a Aliado",
        "Fecha real contacto Cliente",
        "Fecha programación visita",
        "Fecha de visita al Cliente",
        "Fecha solicitud de Factibilidad",
        "Fecha radicación Factibilidad",
        "Fecha solicitud de equipos",
        "Fecha recibido cotización de equipos",
        "Fecha entrega oferta por parte Aliado",
        "Fecha Fin construcción oferta OT",
        "Fecha Entrega Validación Staff",
        "Fecha Inicio Circuito de Firmas",
        "Fecha de Entrega a KAM",
        "Valor última oferta antes de IVA",
        "Fecha de Vigencia de Oferta"
    ];

    document.querySelectorAll("[data-title]").forEach(input => {
        if (camposALimpiar.includes(input.getAttribute("data-title"))) {
            input.value = "";
        }
    });
}

function prepararRecotizacionDesdeFormulario() {
    const op = document.getElementById("OP")?.value || "";
    document.getElementById("ItemId").value = "";
    document.getElementById("tituloFormulario").innerText = "Nuevo registro - Recotización";
    document.getElementById("lblId").classList.add("d-none");
    document.getElementById("lblId").innerText = "";
    document.getElementById("btnEliminarEditar")?.classList.add("d-none");
    document.getElementById("btnPrepararRecotizacion")?.classList.add("d-none");

    incrementarVersionActual();
    limpiarCamposProcesoParaRecotizacion();
    mostrarAlerta("ok", `Se copiaron los datos base de ${op}. Diligencia solo la información de la nueva recotización y guarda.`);
}

async function crearRecotizacionDesdeRegistro(id) {
    await editarRegistro(id);
    prepararRecotizacionDesdeFormulario();
}

function recogerFormulario() {
    const data = {};

    document.querySelectorAll("[data-title]").forEach(input => {
        const title = input.getAttribute("data-title");
        let value = input.value;

        if (value === "") {
            return;
        }

        if (input.type === "number") {
            value = Number(value);
        }

        data[title] = value;
    });

    return data;
}

async function guardarRegistro() {
    try {
        limpiarAlerta();

        // Si el usuario escribió el valor y no tocó el select, llenar Tipo py antes de guardar.
        calcularTipoProyectoAutomatico(false);

        const id = document.getElementById("ItemId").value;
        const data = recogerFormulario();

        if (!data["OP"]) {
            mostrarAlerta("error", "Debes diligenciar la OP.");
            return;
        }

        if (id) {
            await apiPost("/api/update/" + id, data);
            mostrarAlerta("ok", "Registro actualizado correctamente.");
        } else {
            await apiPost("/api/create", data);
            mostrarAlerta("ok", "Registro creado correctamente.");
            document.getElementById("formOP").reset();
        }

        registrosCache = [];
        statsItemsCache = [];

    } catch (e) {
        mostrarAlerta("error", "Error guardando registro: " + e.message);
    }
}

async function eliminarRegistroDesdeFormulario() {
    const id = document.getElementById("ItemId").value;
    const op = document.getElementById("OP").value;

    if (!id) {
        mostrarAlerta("error", "Solo puedes eliminar un registro existente.");
        return;
    }

    const confirmar1 = confirm(`¿Seguro que deseas eliminar el registro ${op || id}?`);
    if (!confirmar1) return;

    const confirmar2 = confirm("Esta acción no se puede deshacer. ¿Confirmas nuevamente la eliminación?");
    if (!confirmar2) return;

    try {
        limpiarAlerta();

        await apiPost("/api/delete/" + id, {});

        mostrarAlerta("ok", "Registro eliminado correctamente.");

        document.getElementById("formOP").reset();
        document.getElementById("ItemId").value = "";
        document.getElementById("btnEliminarEditar").classList.add("d-none");

        registrosCache = registrosCache.filter(x => x.Id !== Number(id));
        statsItemsCache = statsItemsCache.filter(x => x.Id !== Number(id));

        abrirTabListado();
        aplicarFiltrosTabla();

    } catch (e) {
        mostrarAlerta("error", "Error eliminando registro: " + e.message);
    }
}


/* ============================================================
   AJUSTES V4: Tipo py real y reglas de aplica/no aplica
============================================================ */
function getInputByTitle(title) {
    return Array.from(document.querySelectorAll('[data-title]')).find(x => x.getAttribute('data-title') === title);
}


function getTipoProyectoInput() {
    return getInputByTitle('Tipo py')
        || getInputByTitle('Tipo de proyecto')
        || getInputByTitle('TipoProyecto');
}

function normalizarSiNo(value) {
    return String(value || '').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function calcularTipoProyectoPorValor(valor, requiereFactibilidad) {
    const v = Number(String(valor || '0').replace(/\./g, '').replace(',', '.')) || 0;
    const reqFact = ['si', 's', 'yes', 'true', '1', 'si aplica', 'aplica'].includes(normalizarSiNo(requiereFactibilidad));
    if (v <= 0) return '';
    if (v < 100000000) return reqFact ? 'Pequeño con factibilidad' : 'Pequeño';
    if (v < 500000000) return 'Mediano';
    if (v < 1000000000) return 'Grande';
    return 'Megaproyecto';
}

function actualizarTipoProyectoAutomatico(forzar = false) {
    const valor = getInputByTitle('Valor última oferta antes de IVA')?.value || '';
    const requiereFact = getInputByTitle('Requiere Factibilidad')?.value || '';
    const tipo = calcularTipoProyectoPorValor(valor, requiereFact);
    const inputTipo = getTipoProyectoInput();
    if (!inputTipo || !tipo) return;

    // No pisar el valor real que viene desde SharePoint en Tipo py / Tipopy.
    // Solo calcular si el campo está vacío o si se fuerza desde una acción futura.
    if (!forzar && String(inputTipo.value || '').trim()) return;

    if (inputTipo.tagName === 'SELECT') asegurarOpcionSelect(inputTipo, tipo);
    inputTipo.value = tipo;
}

function actualizarFechasAplicablesEquiposFactibilidad() {
    const requiereEquipos = normalizarSiNo(getInputByTitle('Requiere cotización de equipos')?.value);
    const requiereFact = normalizarSiNo(getInputByTitle('Requiere Factibilidad')?.value);
    const requiereVisita = normalizarSiNo(getInputByTitle('Requiere visita')?.value);
    const aplicaEquipos = ['si', 's', 'yes', 'true', '1', 'si aplica', 'aplica'].includes(requiereEquipos);
    const aplicaFact = ['si', 's', 'yes', 'true', '1', 'si aplica', 'aplica'].includes(requiereFact);
    const aplicaVisita = ['si', 's', 'yes', 'true', '1', 'si aplica', 'aplica'].includes(requiereVisita);
    ['Fecha solicitud de equipos', 'Fecha recibido cotización de equipos'].forEach(t => {
        const input = getInputByTitle(t);
        if (!input) return;
        input.disabled = !aplicaEquipos;
        if (!aplicaEquipos) input.value = '';
        input.closest('.col-md-3')?.classList.toggle('campo-no-aplica', !aplicaEquipos);
    });
    ['Fecha solicitud de Factibilidad', 'Fecha radicación Factibilidad'].forEach(t => {
        const input = getInputByTitle(t);
        if (!input) return;
        input.disabled = !aplicaFact;
        if (!aplicaFact) input.value = '';
        input.closest('.col-md-3')?.classList.toggle('campo-no-aplica', !aplicaFact);
    });
    ['Fecha programación visita', 'Fecha de visita al Cliente'].forEach(t => {
        const input = getInputByTitle(t);
        if (!input) return;
        input.disabled = !aplicaVisita;
        if (!aplicaVisita) input.value = '';
        input.closest('.col-md-3')?.classList.toggle('campo-no-aplica', !aplicaVisita);
    });
}

function prepararReglasFormularioV4() {
    const valorOferta = getInputByTitle('Valor última oferta antes de IVA');
    const tipoProyecto = getTipoProyectoInput();
    const requiereFact = getInputByTitle('Requiere Factibilidad');
    const requiereEquipos = getInputByTitle('Requiere cotización de equipos');
    const requiereVisita = getInputByTitle('Requiere visita');

    // Tamaño / Tipo py automático:
    // Se recalcula cuando cambia el valor de la oferta o la factibilidad.
    const recalcularTipoProyecto = () => {
        calcularTipoProyectoAutomatico(true);
    };

    valorOferta?.addEventListener('input', recalcularTipoProyecto);
    valorOferta?.addEventListener('change', recalcularTipoProyecto);

    requiereFact?.addEventListener('change', () => {
        actualizarFechasAplicablesEquiposFactibilidad();
        recalcularTipoProyecto();
    });

    tipoProyecto?.addEventListener('change', () => {
        // Permite que el usuario ajuste manualmente el valor si lo necesita.
    });

    requiereEquipos?.addEventListener('change', actualizarFechasAplicablesEquiposFactibilidad);
    requiereVisita?.addEventListener('change', actualizarFechasAplicablesEquiposFactibilidad);
}

document.addEventListener('DOMContentLoaded', prepararReglasFormularioV4);

// Refuerzo para que recotizar siempre deje versión y OP dentro del payload antes de guardar.
const guardarRegistroOriginalV4 = guardarRegistro;
guardarRegistro = async function () {
    actualizarFechasAplicablesEquiposFactibilidad();
    aplicarCampoCantidadLuminariasProductoAP();
    const inputVersion = getInputByTitle('Número de Versión');
    if (document.getElementById('tituloFormulario')?.innerText?.toLowerCase().includes('recotización')) {
        const actual = Number(String(inputVersion?.value || '0').replace(',', '.'));
        if (inputVersion && (!actual || actual < 2)) inputVersion.value = '2';
    }
    await guardarRegistroOriginalV4();
};

const editarRegistroOriginalV4 = editarRegistro;
editarRegistro = async function(id) {
    await editarRegistroOriginalV4(id);

    actualizarFechasAplicablesEquiposFactibilidad();
    aplicarCampoCantidadLuminariasProductoAP();
};

const nuevoRegistroOriginalV4 = nuevoRegistro;
nuevoRegistro = async function() {
    await nuevoRegistroOriginalV4();
    actualizarFechasAplicablesEquiposFactibilidad();
    aplicarCampoCantidadLuminariasProductoAP();
};


function valorNumericoMoneda(raw) {
    const text = String(raw || '').replace(/[$\s]/g, '');
    if (!text) return 0;
    let clean = text;
    if ((clean.match(/\./g) || []).length > 1 && !clean.includes(',')) clean = clean.replace(/\./g, '');
    else if (clean.includes(',') && clean.includes('.')) clean = clean.lastIndexOf(',') > clean.lastIndexOf('.') ? clean.replace(/\./g, '').replace(',', '.') : clean.replace(/,/g, '');
    else if (clean.includes(',')) clean = clean.replace(/\./g, '').replace(',', '.');
    const n = Number(clean);
    return isNaN(n) ? 0 : n;
}

function calcularTipoProyectoAutomatico(forzar = false) {
    const valorInput = Array.from(document.querySelectorAll('[data-title]')).find(x => x.getAttribute('data-title') === 'Valor última oferta antes de IVA');
    const factInput = Array.from(document.querySelectorAll('[data-title]')).find(x => x.getAttribute('data-title') === 'Requiere Factibilidad');
    const tipoSelect = getTipoProyectoInput();
    if (!valorInput || !tipoSelect) return;

    // Evita que el cálculo automático reemplace el dato real leído de SharePoint.
    if (!forzar && String(tipoSelect.value || '').trim()) return;
    const valor = valorNumericoMoneda(valorInput.value);
    const requiereFact = ['si','sí','s','1','true','yes','si aplica','sí aplica','aplica'].includes(String(factInput?.value || '').trim().toLowerCase());
    let tipo = '';
    if (valor > 0 && valor < 100000000) tipo = requiereFact ? 'Pequeño con factibilidad' : 'Pequeño';
    else if (valor >= 100000000 && valor < 500000000) tipo = 'Mediano';
    else if (valor >= 500000000 && valor < 1000000000) tipo = 'Grande';
    else if (valor >= 1000000000) tipo = 'Megaproyecto';
    if (tipo) {
        asegurarOpcionSelect(tipoSelect, tipo);
        tipoSelect.value = tipo;
    }
}

function valorSiFormulario(value) {
    return ['si','sí','s','1','true','yes','si aplica','sí aplica'].includes(String(value || '').trim().toLowerCase());
}

function setCampoOpcional(title, enabled) {
    const el = Array.from(document.querySelectorAll('[data-title]')).find(x => x.getAttribute('data-title') === title);
    if (!el) return;
    el.disabled = !enabled;
    el.closest('.col-md-3, .col-md-6, .col-md-12')?.classList.toggle('campo-no-aplica', !enabled);
    if (!enabled) el.value = '';
}

function esProductoAPFormulario(value) {
    const v = String(value || '')
        .trim()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');

    return (
        v === 'ap uaesp' ||
        v === 'ap' ||
        v === 'alumbrado publico' ||
        v.includes('ap uaesp')
    );
}

function aplicarCampoCantidadLuminariasProductoAP() {
    const producto = getInputByTitle('Producto');
    const habilitar = esProductoAPFormulario(producto?.value);
    setCampoOpcional('Cantidad de luminarias', habilitar);
}

function aplicarCamposOpcionalesVisitaV7() {
    const reqVisita = Array.from(document.querySelectorAll('[data-title]')).find(x => x.getAttribute('data-title') === 'Requiere visita');
    const habilitar = valorSiFormulario(reqVisita?.value);
    setCampoOpcional('Fecha programación visita', habilitar);
    setCampoOpcional('Fecha de visita al Cliente', habilitar);
}

document.addEventListener('change', function(event) {
    if (event.target?.matches('[data-title="Requiere visita"]')) aplicarCamposOpcionalesVisitaV7();
    if (event.target?.matches('[data-title="Producto"]')) aplicarCampoCantidadLuminariasProductoAP();
});
