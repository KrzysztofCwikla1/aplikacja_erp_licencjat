// ===== Wspolne funkcje uzywane na wszystkich stronach =====

function toast(message, type = "success") {
    const id = "t" + Date.now();
    const icons = { success: "check-circle", danger: "exclamation-octagon", warning: "exclamation-triangle", info: "info-circle" };
    const html = `<div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert">
        <div class="d-flex"><div class="toast-body"><i class="bi bi-${icons[type] || 'info-circle'}"></i> ${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div></div>`;
    document.getElementById("toast-container").insertAdjacentHTML("beforeend", html);
    const el = document.getElementById(id);
    const t = new bootstrap.Toast(el, { delay: 4000 });
    t.show();
    el.addEventListener("hidden.bs.toast", () => el.remove());
}

async function api(url, opts) {
    const r = await fetch(url, opts);
    if (r.status === 401) { window.location.href = "/login"; return null; }
    return r.json();
}

function fmtMoney(v) { return Number(v).toLocaleString("pl-PL") + " EUR"; }

async function doLogout() {
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
}

// Pasek statusu w sidebarze + nazwa zalogowanego uzytkownika - na kazdej stronie
async function loadCommonStatus() {
    const me = await api("/api/me");
    if (me) document.getElementById("current-user").textContent = me.full_name || me.username;
    const d = await api("/api/continuity");
    if (!d) return;
    document.getElementById("sb-buffer").textContent = d.buffer_fill;
    document.getElementById("sb-sync").textContent = (d.last_sync || "-").split(" ")[1] || d.last_sync;
    const dot = document.getElementById("sb-cloud-dot"), lbl = document.getElementById("sb-cloud");
    if (d.cloud_connected) { dot.className = "status-dot bg-success"; lbl.textContent = "ERP online"; }
    else { dot.className = "status-dot bg-danger"; lbl.textContent = "ERP offline"; }
}

document.addEventListener("DOMContentLoaded", loadCommonStatus);
