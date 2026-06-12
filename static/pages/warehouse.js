async function loadWarehouse() {
    const d = await api("/api/warehouse"); if (!d) return;
    document.getElementById("warehouse-body").innerHTML = d.items.map(it => {
        const status = it.category === "produkt" ? '<span class="badge bg-secondary">produkt</span>' :
            (it.low_stock ? '<span class="badge bg-danger">niski stan</span>' : '<span class="badge bg-success">OK</span>');
        const orderBtn = (it.category === "surowiec") ?
            `<button class="btn btn-sm btn-outline-primary" onclick="orderMaterial('${it.code}','${it.name}')">Zamów</button>` : "";
        return `<tr><td><code>${it.code}</code></td><td>${it.name}</td><td>${it.category}</td>
            <td class="text-end">${it.quantity.toFixed(1)} ${it.unit}</td>
            <td class="text-end">${it.min_level.toFixed(1)} ${it.unit}</td><td>${status}</td><td>${orderBtn}</td></tr>`;
    }).join("");
    loadPurchaseOrders();
}
async function loadPurchaseOrders() {
    const d = await api("/api/purchase-orders"); if (!d) return;
    document.getElementById("po-body").innerHTML = d.orders.map(o => {
        const sb = o.status === "przyjęte" ? "success" : (o.offline_created ? "secondary" : "info");
        const btn = o.status !== "przyjęte" ?
            `<button class="btn btn-sm btn-outline-success" onclick="receivePO(${o.id})"><i class="bi bi-box-arrow-in-down"></i> Przyjmij</button>` :
            '<span class="text-success"><i class="bi bi-check-circle"></i></span>';
        return `<tr><td><code>${o.po_number}</code></td><td>${o.material_name}</td><td class="text-end">${o.quantity}</td>
        <td>${o.supplier}</td><td><span class="badge bg-${sb}">${o.status}</span></td><td>${btn}</td></tr>`;
    }).join("") || "<tr><td colspan='6' class='text-muted'>Brak zamówień</td></tr>";
}
async function orderMaterial(code, name) {
    document.getElementById("order-mat-code").value = code;
    document.getElementById("order-mat-name").textContent = name;
    document.getElementById("order-qty").value = 30;
    const info = document.getElementById("order-supplier-info");
    info.classList.add("d-none");
    new bootstrap.Modal(document.getElementById("orderModal")).show();
    const s = await api("/api/supplier/" + code);
    if (s) {
        info.innerHTML = `<i class="bi bi-truck"></i> Dostawca: <strong>${s.supplier}</strong> · cena ${s.price_per_t} EUR/t · dostawa ${s.lead_time_days} dni · dostępne ${s.available} t`;
        info.classList.remove("d-none");
    }
}
async function submitOrder() {
    const code = document.getElementById("order-mat-code").value;
    const qty = parseFloat(document.getElementById("order-qty").value);
    if (!qty || qty <= 0) { toast("Podaj poprawną ilość", "danger"); return; }
    const d = await api("/api/purchase-order", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ material_code: code, quantity: qty }) });
    if (!d) return;
    bootstrap.Modal.getInstance(document.getElementById("orderModal")).hide();
    if (d.offline) toast(`Zamówienie ${d.po_number} dodane do kolejki offline (bufor lokalny)`, "warning");
    else toast(`Zamówienie ${d.po_number} wysłane do ${d.supplier}. Koszt: ${fmtMoney(d.estimated_cost)}, dostawa ${d.lead_time_days} dni.`, "success");
    loadWarehouse();
}
async function receivePO(id) {
    const d = await api(`/api/purchase-order/${id}/receive`, { method: "POST" });
    if (!d) return;
    toast(`Przyjęto dostawę: +${d.added} do ${d.material}. Nowy stan: ${d.new_quantity}.`, "success");
    loadWarehouse();
}
document.addEventListener("DOMContentLoaded", loadWarehouse);
