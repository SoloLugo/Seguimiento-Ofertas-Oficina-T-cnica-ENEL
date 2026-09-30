/* ============================================================
   MULTISELECT CON LISTA DESPLEGABLE Y CHECKBOXES
   Optimizado: las opciones se pintan solo cuando se abre el filtro.
============================================================ */

function escapeHtmlMultiselect(value) {
    if (typeof escapeHtml === "function") {
        return escapeHtml(value);
    }
    if (value === null || value === undefined) return "";
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function crearMultiselect({
    id,
    label = "Seleccionar",
    options = [],
    selected = [],
    onChange = null
}) {
    const container = document.getElementById(id);
    if (!container) return;

    const selectedValues = (selected || []).map(v => String(v));
    const selectedSet = new Set(selectedValues);

    container.classList.add("custom-multiselect");
    container.dataset.multiselectId = id;
    container.dataset.placeholder = label;
    container.dataset.onchange = onChange || "";
    container.dataset.optionsRendered = "0";
    container._msOptions = options || [];
    container._msSelectedValues = selectedValues;

    container.innerHTML = `
        <button type="button" class="custom-multiselect-button" onclick="toggleMultiselect('${id}')">
            <span id="${id}_label">${escapeHtmlMultiselect(getMultiselectLabel(label, options, selectedSet))}</span>
            <span class="custom-multiselect-arrow">▾</span>
        </button>

        <div class="custom-multiselect-menu" id="${id}_menu">
            <div class="custom-multiselect-actions">
                <button type="button" onclick="seleccionarTodoMultiselect('${id}')">Todos</button>
                <button type="button" onclick="limpiarMultiselect('${id}')">Limpiar</button>
            </div>

            <div class="custom-multiselect-options" id="${id}_options"></div>
        </div>
    `;
}

function renderMultiselectOptions(id) {
    const container = document.getElementById(id);
    const optionsBox = document.getElementById(`${id}_options`);
    if (!container || !optionsBox || container.dataset.optionsRendered === "1") return;

    const selectedSet = new Set(container._msSelectedValues || []);
    const options = container._msOptions || [];

    optionsBox.innerHTML = options.map(opt => {
        const value = String(opt.value ?? opt);
        const text = String(opt.text ?? opt);
        const checked = selectedSet.has(value) ? "checked" : "";

        return `
            <label class="custom-multiselect-option">
                <input
                    type="checkbox"
                    value="${escapeHtmlMultiselect(value)}"
                    ${checked}
                    onchange="actualizarMultiselect('${id}')"
                >
                <span>${escapeHtmlMultiselect(text)}</span>
            </label>
        `;
    }).join("");

    container.dataset.optionsRendered = "1";
}

function getMultiselectLabel(label, options, selectedSet) {
    const total = options.length;
    const selectedCount = selectedSet.size;

    if (selectedCount === 0) {
        return label;
    }

    if (selectedCount === total && total > 0) {
        return "Todos";
    }

    if (selectedCount === 1) {
        const selectedValue = Array.from(selectedSet)[0];
        const item = options.find(opt => String(opt.value ?? opt) === selectedValue);
        return String(item?.text ?? item?.value ?? selectedValue);
    }

    return `${selectedCount} seleccionados`;
}

function toggleMultiselect(id) {
    const menu = document.getElementById(`${id}_menu`);
    if (!menu) return;

    cerrarOtrosMultiselect(id);
    renderMultiselectOptions(id);
    menu.classList.toggle("show");
}

function cerrarOtrosMultiselect(idActual) {
    document.querySelectorAll(".custom-multiselect-menu.show").forEach(menu => {
        if (menu.id !== `${idActual}_menu`) {
            menu.classList.remove("show");
        }
    });
}

function getMultiselectValues(id) {
    const container = document.getElementById(id);
    if (!container) return [];

    if (container.dataset.optionsRendered !== "1") {
        return [...(container._msSelectedValues || [])]
            .map(v => String(v || "").trim())
            .filter(v => v !== "");
    }

    const values = Array.from(container.querySelectorAll("input[type='checkbox']:checked"))
        .map(input => String(input.value || "").trim())
        .filter(v => v !== "");

    container._msSelectedValues = values;
    return values;
}

function setMultiselectValues(id, values = []) {
    const container = document.getElementById(id);
    if (!container) return;

    const cleanValues = values.map(v => String(v));
    const selectedSet = new Set(cleanValues);
    container._msSelectedValues = cleanValues;

    if (container.dataset.optionsRendered === "1") {
        container.querySelectorAll("input[type='checkbox']").forEach(input => {
            input.checked = selectedSet.has(String(input.value));
        });
    }

    actualizarMultiselect(id, false);
}

function limpiarMultiselect(id) {
    const container = document.getElementById(id);
    if (!container) return;

    container._msSelectedValues = [];

    if (container.dataset.optionsRendered === "1") {
        container.querySelectorAll("input[type='checkbox']").forEach(input => {
            input.checked = false;
        });
    }

    actualizarMultiselect(id);
}

function seleccionarTodoMultiselect(id) {
    const container = document.getElementById(id);
    if (!container) return;

    const options = container._msOptions || [];
    container._msSelectedValues = options.map(opt => String(opt.value ?? opt));

    if (container.dataset.optionsRendered === "1") {
        container.querySelectorAll("input[type='checkbox']").forEach(input => {
            input.checked = true;
        });
    }

    actualizarMultiselect(id);
}

function actualizarMultiselect(id, ejecutarCambio = true) {
    const container = document.getElementById(id);
    const labelElement = document.getElementById(`${id}_label`);

    if (!container || !labelElement) return;

    const placeholder = container.dataset.placeholder || "Seleccionar";
    const values = getMultiselectValues(id);
    const options = container._msOptions || [];

    labelElement.innerText = getMultiselectLabel(
        placeholder,
        options,
        new Set(values)
    );

    if (ejecutarCambio) {
        const callbackName = container.dataset.onchange;

        if (callbackName && typeof window[callbackName] === "function") {
            window[callbackName]();
        }
    }
}

function recargarMultiselect(id, options = [], selected = []) {
    const container = document.getElementById(id);
    if (!container) return;

    const placeholder = container.dataset.placeholder || "Seleccionar";
    const onchange = container.dataset.onchange || "";

    crearMultiselect({
        id,
        label: placeholder,
        options,
        selected,
        onChange: onchange
    });
}

document.addEventListener("click", function (event) {
    if (!event.target.closest(".custom-multiselect")) {
        document.querySelectorAll(".custom-multiselect-menu.show").forEach(menu => {
            menu.classList.remove("show");
        });
    }
});
