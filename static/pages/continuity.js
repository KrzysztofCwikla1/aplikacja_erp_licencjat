async function loadContinuity() {
    const d = await api("/api/continuity"); if (!d) return;
    document.getElementById("cont-uptime").textContent = d.uptime_30d + "%";
    document.getElementById("cont-buffer").textContent = d.buffer_fill + "%";
    document.getElementById("cont-offline").textContent = d.offline_time_30d + " h";
    document.getElementById("cont-pending").textContent = d.pending_operations;
    document.getElementById("cloud-switch").checked = d.cloud_connected;
    document.getElementById("cloud-label").textContent = d.cloud_connected ? "Online" : "Offline";
    document.getElementById("sync-btn").disabled = !d.cloud_connected;
    document.getElementById("offline-banner").innerHTML = d.cloud_connected ? "" :
        `<div class="alert alert-warning"><i class="bi bi-wifi-off"></i> <strong>Tryb offline.</strong>
        Aplikacja działa na lokalnym buforze. Faktury i zamówienia trafiają do kolejki (${d.pending_operations} oczekuje) i zsynchronizują się po przywróceniu połączenia.</div>`;
    const icons = { offline: "wifi-off", online: "wifi", sync: "arrow-repeat", health_check: "heart-pulse" };
    document.getElementById("continuity-body").innerHTML = d.log.map(l =>
        `<tr><td>${l.event_time}</td><td><i class="bi bi-${icons[l.event_type] || 'info-circle'}"></i> ${l.event_type}</td><td>${l.description}</td></tr>`
    ).join("");
}
async function toggleCloud() {
    const connected = document.getElementById("cloud-switch").checked;
    const d = await api("/api/continuity/cloud", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ connected }) });
    if (!d) return;
    toast(connected ? "Przywrócono połączenie z chmurą. Bufor zsynchronizowany." : "Odłączono od chmury. Aktywny tryb offline.", connected ? "success" : "warning");
    loadContinuity();
    loadCommonStatus();
}
async function syncBuffer() {
    const r = await fetch("/api/continuity/sync", { method: "POST" });
    if (r.status === 401) { window.location.href = "/login"; return; }
    const d = await r.json();
    if (!r.ok) { toast(d.detail || "Błąd synchronizacji", "danger"); return; }
    toast(`Bufor zsynchronizowany (${d.synced_operations} operacji).`, "success");
    loadContinuity();
}
document.addEventListener("DOMContentLoaded", loadContinuity);
