import os
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field, field_validator

import database
from database import get_connection, verify_password, hash_password
import module_lci
import module_integration
import module_production
from invoice_pdf import generate_invoice_pdf, INVOICE_DIR

BASE_DIR = os.path.dirname(__file__)

app = FastAPI(title="System ERP", version="2.0")
app.add_middleware(SessionMiddleware, secret_key="erp-secret-key-zmien-w-produkcji")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

database.init_db()
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    err = exc.errors()[0] if exc.errors() else {}
    etype = err.get("type", "")
    ctx = err.get("ctx", {}) or {}
    if etype == "greater_than":
        msg = f"Wartość musi być większa niż {ctx.get('gt', 0)}"
    elif etype == "greater_than_equal":
        msg = f"Wartość nie może być mniejsza niż {ctx.get('ge', 0)}"
    elif etype in ("too_short", "string_too_short"):
        min_len = ctx.get("min_length", 1)
        field = err.get("loc", ["pole"])[-1]
        if field == "items":
            msg = "Faktura musi zawierać co najmniej jedną pozycję"
        elif min_len == 1:
            msg = "Pole nie może być puste"
        else:
            msg = f"Pole musi mieć co najmniej {min_len} znaków"
    elif etype == "too_long":
        msg = f"Pole jest zbyt długie (maksymalnie {ctx.get('max_length')} znaków)"
    elif etype in ("float_parsing", "int_parsing", "float_type", "int_type"):
        msg = "Wartość musi być liczbą"
    elif etype == "missing":
        msg = "Brak wymaganego pola"
    else:
        msg = err.get("msg", "Niepoprawne dane wejściowe").replace("Value error, ", "")
    return JSONResponse(status_code=422, content={"detail": msg})

# AUTORYZACJA 

def require_login(request: Request):
    if not request.session.get("user"):
        raise HTTPException(status_code=401, detail="Wymagane logowanie")
    return request.session["user"]


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "login.html")


class LoginData(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def api_login(data: LoginData, request: Request):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username=?", (data.username,)).fetchone()
    conn.close()
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Nieprawidłowy login lub hasło")
    request.session["user"] = {"username": user["username"], "full_name": user["full_name"]}
    return {"status": "ok", "full_name": user["full_name"]}


@app.post("/api/logout")
def api_logout(request: Request):
    request.session.clear()
    return {"status": "ok"}

class NewUser(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=5, max_length=100)
    full_name: str = ""

    @field_validator("username")
    @classmethod
    def username_no_spaces(cls, v):
        v = v.strip()
        if " " in v:
            raise ValueError("Nazwa użytkownika nie może zawierać spacji")
        return v

@app.post("/api/users")
def api_create_user(data: NewUser, user=Depends(require_login)):
    conn = get_connection()
    exists = conn.execute("SELECT 1 FROM users WHERE username=?", (data.username,)).fetchone()
    if exists:
        conn.close()
        raise HTTPException(400, "Użytkownik o tej nazwie już istnieje")
    conn.execute("INSERT INTO users (username,password_hash,full_name,created_at) VALUES (?,?,?,?)",
                 (data.username, hash_password(data.password), data.full_name or data.username,
                  datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return {"status": "ok", "username": data.username}


@app.get("/api/users")
def api_list_users(user=Depends(require_login)):
    conn = get_connection()
    rows = conn.execute("SELECT username,full_name,created_at FROM users ORDER BY id").fetchall()
    conn.close()
    return {"users": [dict(r) for r in rows]}


@app.get("/api/me")
def api_me(user=Depends(require_login)):
    return user


#  INTERFEJS 

_PAGES = {
    "/": ("dashboard.html", "dashboard"),
    "/warehouse": ("warehouse.html", "warehouse"),
    "/production": ("production.html", "production"),
    "/invoices": ("invoices.html", "invoices"),
    "/integration": ("integration.html", "integration"),
    "/lci": ("lci.html", "lci"),
    "/continuity": ("continuity.html", "continuity"),
    "/users": ("users.html", "users"),
}


def _render_page(request: Request, template: str, active: str):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, f"pages/{template}", {"active": active})


@app.get("/", response_class=HTMLResponse)
def page_dashboard(request: Request):
    return _render_page(request, "dashboard.html", "dashboard")


@app.get("/warehouse", response_class=HTMLResponse)
def page_warehouse(request: Request):
    return _render_page(request, "warehouse.html", "warehouse")


@app.get("/production", response_class=HTMLResponse)
def page_production(request: Request):
    return _render_page(request, "production.html", "production")


@app.get("/invoices", response_class=HTMLResponse)
def page_invoices(request: Request):
    return _render_page(request, "invoices.html", "invoices")


@app.get("/integration", response_class=HTMLResponse)
def page_integration(request: Request):
    return _render_page(request, "integration.html", "integration")


@app.get("/lci", response_class=HTMLResponse)
def page_lci(request: Request):
    return _render_page(request, "lci.html", "lci")


@app.get("/continuity", response_class=HTMLResponse)
def page_continuity(request: Request):
    return _render_page(request, "continuity.html", "continuity")


@app.get("/users", response_class=HTMLResponse)
def page_users(request: Request):
    return _render_page(request, "users.html", "users")


# PRZEGLAD 

@app.get("/api/overview")
def api_overview(user=Depends(require_login)):
    model = module_integration.unified_data_model()
    lci = module_lci.calculate_lci()
    cont = module_integration.get_continuity_status()
    return {
        "model": model,
        "lci": lci,
        "continuity": {
            "cloud_connected": cont["cloud_connected"],
            "buffer_fill": cont["buffer_fill"],
            "last_sync": cont["last_sync"],
            "uptime_30d": cont["uptime_30d"],
            "offline_time_30d": cont["offline_time_30d"],
            "pending_operations": cont["pending_operations"],
        },
    }


# MAGAZYN 
@app.get("/api/warehouse")
def api_warehouse(user=Depends(require_login)):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM warehouse ORDER BY category, name").fetchall()
    conn.close()
    items = []
    for r in rows:
        d = dict(r)
        d["low_stock"] = (r["category"] == "surowiec" and r["quantity"] < r["min_level"])
        items.append(d)
    return {"items": items}


class StockUpdate(BaseModel):
    code: str
    delta: float


@app.post("/api/warehouse/adjust")
def api_warehouse_adjust(update: StockUpdate, user=Depends(require_login)):
    conn = get_connection()
    row = conn.execute("SELECT * FROM warehouse WHERE code=?", (update.code,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Nie znaleziono materiału")
    new_qty = max(0, row["quantity"] + update.delta)
    conn.execute("UPDATE warehouse SET quantity=? WHERE code=?", (new_qty, update.code))
    conn.commit()
    conn.close()
    return {"code": update.code, "new_quantity": round(new_qty, 1)}


# ZAMOWIENIA DO DOSTAWCOW 

@app.get("/api/supplier/{material_code}")
def api_supplier_info(material_code: str, user=Depends(require_login)):
    return module_integration.fetch_external_supplier_data(material_code)


class PurchaseOrder(BaseModel):
    material_code: str
    quantity: float = Field(gt=0, description="Ilość musi być dodatnia")


@app.post("/api/purchase-order")
def api_create_po(po: PurchaseOrder, user=Depends(require_login)):
    conn = get_connection()
    mat = conn.execute("SELECT * FROM warehouse WHERE code=?", (po.material_code,)).fetchone()
    if not mat:
        conn.close()
        raise HTTPException(404, "Nie znaleziono materiału")
    supplier = module_integration.fetch_external_supplier_data(po.material_code)
    count = conn.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
    po_number = f"PO/2026/{count + 1:04d}"
    offline = 0 if module_integration.is_cloud_connected() else 1
    status = "wysłane" if not offline else "w kolejce (offline)"
    conn.execute("INSERT INTO purchase_orders (po_number,material_code,material_name,quantity,supplier,order_date,status,offline_created) VALUES (?,?,?,?,?,?,?,?)",
                 (po_number, po.material_code, mat["name"], po.quantity, supplier["supplier"],
                  datetime.now().strftime("%Y-%m-%d"), status, offline))
    conn.commit()
    conn.close()
    if offline:
        module_integration.queue_offline_operation("purchase_order",
            {"po_number": po_number, "material_code": po.material_code, "quantity": po.quantity})
    return {
        "po_number": po_number, "material": mat["name"], "quantity": po.quantity,
        "supplier": supplier["supplier"], "lead_time_days": supplier["lead_time_days"],
        "estimated_cost": round(po.quantity * supplier["price_per_t"], 2),
        "offline": bool(offline),
    }


@app.get("/api/purchase-orders")
def api_list_po(user=Depends(require_login)):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM purchase_orders ORDER BY id DESC").fetchall()
    conn.close()
    return {"orders": [dict(r) for r in rows]}


@app.post("/api/purchase-order/{po_id}/receive")
def api_receive_po(po_id: int, user=Depends(require_login)):
    conn = get_connection()
    po = conn.execute("SELECT * FROM purchase_orders WHERE id=?", (po_id,)).fetchone()
    if not po:
        conn.close()
        raise HTTPException(404, "Nie znaleziono zamówienia")
    if po["status"] == "przyjęte":
        conn.close()
        raise HTTPException(400, "Zamówienie już przyjęte")
    conn.execute("UPDATE warehouse SET quantity = quantity + ? WHERE code=?",
                 (po["quantity"], po["material_code"]))
    conn.execute("UPDATE purchase_orders SET status='przyjęte' WHERE id=?", (po_id,))
    mat = conn.execute("SELECT * FROM warehouse WHERE code=?", (po["material_code"],)).fetchone()
    new_qty = mat["quantity"]
    conn.commit()
    conn.close()
    return {"po_number": po["po_number"], "material": po["material_name"],
            "added": po["quantity"], "new_quantity": round(new_qty, 1)}


# SYMULACJA PRODUKCJI 

@app.get("/api/production/recipes")
def api_recipes(user=Depends(require_login)):
    return {"recipes": module_production.get_recipes()}


@app.get("/api/production/check")
def api_production_check(product_code: str, amount: float, user=Depends(require_login)):
    return module_production.check_production(product_code, amount)


class ProductionRun(BaseModel):
    product_code: str
    amount: float = Field(gt=0, description="Wielkość zlecenia musi być dodatnia")

@app.post("/api/production/run")
def api_production_run(run: ProductionRun, user=Depends(require_login)):
    result = module_production.run_production(run.product_code, run.amount)
    if not result["ok"]:
        raise HTTPException(400, result["error"])
    return result


# FAKTURY 

@app.get("/api/invoices")
def api_invoices(user=Depends(require_login)):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM invoices ORDER BY id DESC").fetchall()
    conn.close()
    return {"invoices": [dict(r) for r in rows]}


class InvoiceItem(BaseModel):
    description: str = Field(min_length=1)
    quantity: float = Field(gt=0, description="Ilość musi być dodatnia")
    unit_price: float = Field(ge=0, description="Cena nie może być ujemna")


class NewInvoice(BaseModel):
    client_name: str = Field(min_length=1)
    client_address: str = ""
    client_nip: str = ""
    items: list[InvoiceItem] = Field(min_length=1, description="Faktura musi mieć co najmniej jedną pozycję")

@app.post("/api/invoices")
def api_create_invoice(inv: NewInvoice, user=Depends(require_login)):
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    invoice_number = f"FV/2026/{600 + count + 1}"
    issue_date = datetime.now().strftime("%Y-%m-%d")
    due_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    items_data, total_net = [], 0.0
    for it in inv.items:
        line = round(it.quantity * it.unit_price, 2)
        total_net += line
        items_data.append({"description": it.description, "quantity": it.quantity,
                           "unit_price": it.unit_price, "line_total": line})
    total_net = round(total_net, 2)
    total_gross = round(total_net * 1.23, 2)

    cur = conn.execute("INSERT INTO invoices (invoice_number,client_name,client_address,client_nip,issue_date,due_date,total_net,total_gross,status) VALUES (?,?,?,?,?,?,?,?,?)",
                       (invoice_number, inv.client_name, inv.client_address, inv.client_nip,
                        issue_date, due_date, total_net, total_gross, "wystawiona"))
    invoice_id = cur.lastrowid
    for it in items_data:
        conn.execute("INSERT INTO invoice_items (invoice_id,description,quantity,unit_price,line_total) VALUES (?,?,?,?,?)",
                     (invoice_id, it["description"], it["quantity"], it["unit_price"], it["line_total"]))
    conn.commit()
    conn.close()

    invoice_data = {"invoice_number": invoice_number, "client_name": inv.client_name,
                    "client_address": inv.client_address, "client_nip": inv.client_nip,
                    "issue_date": issue_date, "due_date": due_date,
                    "total_net": total_net, "total_gross": total_gross}
    generate_invoice_pdf(invoice_data, items_data)
    if not module_integration.is_cloud_connected():
        module_integration.queue_offline_operation("invoice", {"invoice_number": invoice_number})

    return {"invoice_number": invoice_number, "total_net": total_net, "total_gross": total_gross,
            "pdf_url": f"/api/invoices/{invoice_number.replace('/', '_')}/pdf",
            "offline": not module_integration.is_cloud_connected()}


@app.get("/api/invoices/{invoice_file}/pdf")
def api_invoice_pdf(invoice_file: str, user=Depends(require_login)):
    filepath = os.path.join(INVOICE_DIR, f"{invoice_file}.pdf")
    if not os.path.exists(filepath):
        raise HTTPException(404, "Plik faktury nie istnieje")
    return FileResponse(filepath, media_type="application/pdf", filename=f"{invoice_file}.pdf")


#  INTEGRACJA 

@app.get("/api/integration/mappings")
def api_mappings(user=Depends(require_login)):
    return {"mappings": module_integration.get_data_mappings()}


@app.get("/api/integration/model")
def api_unified_model(user=Depends(require_login)):
    return module_integration.unified_data_model()


@app.get("/api/integration/log")
def api_integration_log(user=Depends(require_login)):
    return {"log": module_integration.get_integration_log()}


#  LCI

@app.get("/api/lci")
def api_lci(user=Depends(require_login)):
    return module_lci.calculate_lci()


@app.get("/api/lci/factors")
def api_lci_factors(user=Depends(require_login)):
    return {"factors": module_lci.get_lci_factors()}


class FactorUpdate(BaseModel):
    factor_name: str
    value: float = Field(ge=0, description="Współczynnik nie może być ujemny")


@app.post("/api/lci/factors")
def api_update_factor(data: FactorUpdate, user=Depends(require_login)):
    result = module_lci.update_factor(data.factor_name, data.value)
    if result is None:
        raise HTTPException(404, "Nie znaleziono współczynnika konwersji")
    return result

@app.get("/api/lci/scenario")
def api_lci_scenario(energy: float = 0, transport: float = 0, user=Depends(require_login)):
    return module_lci.scenario_analysis(energy, transport)


# CIAGLOSC DZIALANIA 

@app.get("/api/continuity")
def api_continuity(user=Depends(require_login)):
    return module_integration.get_continuity_status()


class CloudToggle(BaseModel):
    connected: bool


@app.post("/api/continuity/cloud")
def api_toggle_cloud(data: CloudToggle, user=Depends(require_login)):
    return module_integration.set_cloud_connected(data.connected)


@app.post("/api/continuity/sync")
def api_sync(user=Depends(require_login)):
    if not module_integration.is_cloud_connected():
        raise HTTPException(400, "Brak połączenia z chmurą – synchronizacja niemożliwa")
    return module_integration.sync_buffer()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
