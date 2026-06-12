async function loadIntegration() {
    const m = await api("/api/integration/model"); if (!m) return;
    document.getElementById("int-wh").textContent = m.warehouse_records;
    document.getElementById("int-inv").textContent = m.invoice_records;
    document.getElementById("int-prod").textContent = m.production_records;
    const d = await api("/api/integration/mappings");
    document.getElementById("mappings-body").innerHTML = d.mappings.map(mp =>
        `<tr><td><small>${mp.source}</small></td><td><small><code>${mp.transform}</code></small></td><td><small>${mp.target}</small></td></tr>`
    ).join("");
    const lg = await api("/api/integration/log");
    document.getElementById("integration-log").innerHTML = lg.log.map(l =>
        `<div class="log-line"><span class="text-muted">[${l.time}]</span> ${l.action}</div>`).join("");
}
document.addEventListener("DOMContentLoaded", loadIntegration);
