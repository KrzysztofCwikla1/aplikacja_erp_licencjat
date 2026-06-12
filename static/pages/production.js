async function loadProduction() {
    const d = await api("/api/production/recipes"); if (!d) return;
    document.getElementById("prod-product").innerHTML = d.recipes.map(r =>
        `<option value="${r.product_code}">${r.product_name} (stan: ${r.current_stock.toFixed(0)} ${r.product_unit})</option>`).join("");
    updateRecipePreview();
    loadProdStock();
}
async function loadProdStock() {
    const d = await api("/api/warehouse"); if (!d) return;
    document.getElementById("prod-stock-body").innerHTML = d.items.map(it =>
        `<tr><td><code>${it.code}</code></td><td>${it.name}</td><td>${it.category}</td><td class="text-end">${it.quantity.toFixed(1)} ${it.unit}</td></tr>`
    ).join("");
}
async function updateRecipePreview() {
    const code = document.getElementById("prod-product").value;
    const amount = parseFloat(document.getElementById("prod-amount").value) || 0;
    if (!code) return;
    const d = await api(`/api/production/check?product_code=${code}&amount=${amount}`); if (!d) return;
    document.getElementById("recipe-body").innerHTML = d.requirements.map(r => {
        const perUnit = (r.needed / (amount || 1));
        const status = r.enough ? '<span class="badge bg-success">OK</span>' : '<span class="badge bg-danger">brak</span>';
        return `<tr><td>${r.raw_name}</td><td class="text-end">${perUnit.toFixed(4)} ${r.raw_unit}</td>
            <td class="text-end">${r.needed.toFixed(3)} ${r.raw_unit}</td>
            <td class="text-end">${r.stock.toFixed(1)} ${r.raw_unit}</td><td>${status}</td></tr>`;
    }).join("");
    document.getElementById("prod-run-btn").disabled = !d.feasible;
}
async function runProduction() {
    const body = {
        product_code: document.getElementById("prod-product").value,
        amount: parseFloat(document.getElementById("prod-amount").value)
    };
    const r = await fetch("/api/production/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (r.status === 401) { window.location.href = "/login"; return; }
    const d = await r.json();
    if (!r.ok) { toast(d.detail || "Błąd produkcji", "danger"); return; }
    const used = d.consumed.map(c => `${c.amount} ${c.unit} ${c.name}`).join(", ");
    toast(`Wyprodukowano ${body.amount} szt. ${d.product_name}. Zużyto: ${used}. Stan produktu: ${d.product_total}.`, "success");
    loadProduction();
}
document.addEventListener("DOMContentLoaded", loadProduction);
