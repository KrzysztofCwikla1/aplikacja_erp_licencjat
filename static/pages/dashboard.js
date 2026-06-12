let dashLciChart;

async function loadOverview() {
    const d = await api("/api/overview");
    if (!d) return;
    document.getElementById("m-revenue").textContent = fmtMoney(d.model.total_revenue);
    document.getElementById("m-production").textContent = d.model.total_production_m2.toLocaleString("pl-PL");
    document.getElementById("m-inventory").textContent = fmtMoney(d.model.total_inventory_value);
    document.getElementById("m-co2").textContent = d.lci.total_co2 + " t";
    document.getElementById("ov-cloud").innerHTML = d.continuity.cloud_connected ?
        '<span class="badge bg-success">Online</span>' : '<span class="badge bg-danger">Offline</span>';
    document.getElementById("ov-buffer").textContent = d.continuity.buffer_fill + "%";
    document.getElementById("ov-uptime").textContent = d.continuity.uptime_30d + "%";
    document.getElementById("ov-pending").textContent = d.continuity.pending_operations;

    const ctx = document.getElementById("dash-lci-chart");
    if (dashLciChart) dashLciChart.destroy();
    dashLciChart = new Chart(ctx, {
        type: "bar", data: { labels: d.lci.phases, datasets: [{ label: "t CO₂e", data: d.lci.co2,
            backgroundColor: ["#e24b4a", "#ef9f27", "#639922", "#378add"] }] },
        options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });
}
document.addEventListener("DOMContentLoaded", loadOverview);
