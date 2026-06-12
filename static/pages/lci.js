let lciBarChart, lciPieChart;

async function loadLci() {
    const d = await api("/api/lci"); if (!d) return;
    document.getElementById("lci-co2").textContent = d.total_co2 + " t";
    document.getElementById("lci-energy").textContent = d.total_energy + " MWh";
    document.getElementById("lci-water").textContent = d.total_water + " m³";
    const colors = ["#e24b4a", "#ef9f27", "#639922", "#378add"];
    const ctxBar = document.getElementById("lci-bar-chart");
    if (lciBarChart) lciBarChart.destroy();
    lciBarChart = new Chart(ctxBar, { type: "bar", data: { labels: d.phases, datasets: [{ label: "t CO₂e", data: d.co2, backgroundColor: colors }] },
        options: { plugins: { legend: { display: false } } } });
    const ctxPie = document.getElementById("lci-pie-chart");
    if (lciPieChart) lciPieChart.destroy();
    lciPieChart = new Chart(ctxPie, { type: "doughnut", data: { labels: d.phases, datasets: [{ data: d.co2, backgroundColor: colors }] },
        options: { plugins: { legend: { position: "bottom", labels: { font: { size: 11 } } } } } });
    loadFactors();
}
async function loadFactors() {
    const d = await api("/api/lci/factors"); if (!d) return;
    document.getElementById("factors-body").innerHTML = d.factors.map(f =>
        `<tr><td>${f.label}</td><td><small class="text-muted">${f.unit}</small></td>
        <td><input type="number" step="0.01" class="form-control form-control-sm" id="f-${f.factor_name}" value="${f.value}"></td>
        <td><button class="btn btn-sm btn-outline-primary" onclick="saveFactor('${f.factor_name}')">Zapisz</button></td></tr>`
    ).join("");
}
async function saveFactor(name) {
    const value = parseFloat(document.getElementById("f-" + name).value);
    const d = await api("/api/lci/factors", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ factor_name: name, value }) });
    if (!d) return;
    toast(`Zaktualizowano współczynnik. Emisja przeliczona.`, "success");
    loadLci();
}
document.getElementById("energy-slider").addEventListener("input", e => document.getElementById("energy-val").textContent = e.target.value);
document.getElementById("transport-slider").addEventListener("input", e => document.getElementById("transport-val").textContent = e.target.value);
async function runScenario() {
    const en = document.getElementById("energy-slider").value, tr = document.getElementById("transport-slider").value;
    const d = await api(`/api/lci/scenario?energy=${en}&transport=${tr}`); if (!d) return;
    document.getElementById("scenario-result").innerHTML =
        `<div class="alert alert-success mb-0">Emisja bazowa: <strong>${d.base_co2} t</strong> &rarr; scenariusz: <strong>${d.alt_co2} t</strong><br>
        Oszczędność: <strong>${d.savings} t CO₂e (${d.savings_pct}%)</strong></div>`;
}
document.addEventListener("DOMContentLoaded", loadLci);
