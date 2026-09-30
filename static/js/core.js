// Código identificado para Valentina Becerra. Marca interna; no se muestra en la interfaz.
let registrosCache = [];
let opcionesCargadas = false;
let opcionesStatsCargadas = false;
let statsItemsCache = [];

/* ============================================================
   ALERTAS / API
============================================================ */

function mostrarAlerta(tipo, mensaje) {
    const clase = tipo === "ok" ? "alert-success" : "alert-danger";
    const alertBox = document.getElementById("alertBox");

    if (!alertBox) return;

    alertBox.innerHTML = `
        <div class="alert ${clase} alert-dismissible fade show" role="alert">
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
}

function limpiarAlerta() {
    const alertBox = document.getElementById("alertBox");
    if (alertBox) {
        alertBox.innerHTML = "";
    }
}

async function apiGet(url) {
    const r = await fetch(url);
    const data = await r.json();

    if (!r.ok || data.error) {
        throw new Error(data.error || "Error desconocido");
    }

    return data;
}

async function apiPost(url, body) {
    const r = await fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
    });

    const data = await r.json();

    if (!r.ok || data.error) {
        throw new Error(data.error || "Error desconocido");
    }

    return data;
}

function limpiarBackdropsBootstrap() {
    document.querySelectorAll(".modal-backdrop").forEach(el => el.remove());
    document.body.classList.remove("modal-open");
    document.body.style.removeProperty("overflow");
    document.body.style.removeProperty("padding-right");
}

function cerrarModalBootstrap(modalId) {
    return new Promise(resolve => {
        const modalEl = document.getElementById(modalId);

        if (!modalEl) {
            limpiarBackdropsBootstrap();
            resolve();
            return;
        }

        const modal = bootstrap.Modal.getInstance(modalEl);

        if (!modal || !modalEl.classList.contains("show")) {
            limpiarBackdropsBootstrap();
            resolve();
            return;
        }

        modalEl.addEventListener("hidden.bs.modal", () => {
            limpiarBackdropsBootstrap();
            resolve();
        }, { once: true });

        modal.hide();

        setTimeout(() => {
            limpiarBackdropsBootstrap();
            resolve();
        }, 350);
    });
}
