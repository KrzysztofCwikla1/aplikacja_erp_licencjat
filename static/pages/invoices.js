async function loadInvoices() {
    const d = await api("/api/invoices"); if (!d) return;
    document.getElementById("invoices-body").innerHTML = d.invoices.map(inv => {
        const sb = { "opłacona": "success", "wystawiona": "warning", "po terminie": "danger" }[inv.status] || "secondary";
        const file = inv.invoice_number.replace(/\//g, "_");
        return `<tr><td><code>${inv.invoice_number}</code></td><td>${inv.client_name}</td><td>${inv.issue_date}</td>
            <td>${inv.due_date}</td><td class="text-end">${fmtMoney(inv.total_gross)}</td>
            <td><span class="badge bg-${sb}">${inv.status}</span></td>
            <td><a class="btn btn-sm btn-outline-secondary" href="/api/invoices/${file}/pdf" target="_blank"><i class="bi bi-file-pdf"></i></a></td></tr>`;
    }).join("");
}
async function createInvoice() {
    const body = {
        client_name: document.getElementById("inv-client").value,
        client_address: document.getElementById("inv-address").value,
        client_nip: document.getElementById("inv-nip").value,
        items: [{ description: document.getElementById("item-desc").value,
            quantity: parseFloat(document.getElementById("item-qty").value),
            unit_price: parseFloat(document.getElementById("item-price").value) }]
    };
    const d = await api("/api/invoices", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!d) return;
    bootstrap.Modal.getInstance(document.getElementById("invoiceModal")).hide();
    const extra = d.offline ? " (tryb offline – zsynchronizuje się po połączeniu)" : "";
    toast(`Wystawiono fakturę ${d.invoice_number} na ${fmtMoney(d.total_gross)}. PDF gotowy${extra}.`, "success");
    loadInvoices();
}
document.addEventListener("DOMContentLoaded", loadInvoices);
