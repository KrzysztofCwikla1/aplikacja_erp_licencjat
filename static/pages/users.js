async function loadUsers() {
    const d = await api("/api/users"); if (!d) return;
    document.getElementById("users-body").innerHTML = d.users.map(u =>
        `<tr><td><i class="bi bi-person-circle"></i> ${u.username}</td><td>${u.full_name || "-"}</td><td><small class="text-muted">${u.created_at}</small></td></tr>`
    ).join("");
}
async function createUser() {
    const body = {
        username: document.getElementById("nu-username").value,
        full_name: document.getElementById("nu-fullname").value,
        password: document.getElementById("nu-password").value
    };
    if (!body.username || !body.password) { toast("Podaj nazwę i hasło", "danger"); return; }
    const r = await fetch("/api/users", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (r.status === 401) { window.location.href = "/login"; return; }
    const d = await r.json();
    if (!r.ok) { toast(d.detail || "Błąd", "danger"); return; }
    bootstrap.Modal.getInstance(document.getElementById("userModal")).hide();
    toast(`Utworzono użytkownika ${d.username}`, "success");
    document.getElementById("nu-username").value = ""; document.getElementById("nu-fullname").value = ""; document.getElementById("nu-password").value = "";
    loadUsers();
}
document.addEventListener("DOMContentLoaded", loadUsers);
