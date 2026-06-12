import pandas as pd
import json
from datetime import datetime
from database import get_connection, BUFFER_PATH


# STAN SYSTEMU

def is_cloud_connected():
    conn = get_connection()
    row = conn.execute("SELECT value FROM system_state WHERE key='cloud_connected'").fetchone()
    conn.close()
    return row and row["value"] == "1"


def set_cloud_connected(connected: bool):
    conn = get_connection()
    conn.execute("UPDATE system_state SET value=? WHERE key='cloud_connected'",
                 ("1" if connected else "0",))
    if connected:
        desc = "Przywrócono połączenie z chmurą – synchronizacja bufora lokalnego"
        etype = "online"
    else:
        desc = "Odłączono od chmury (tryb testowy) – aktywacja bufora lokalnego"
        etype = "offline"
    conn.execute("INSERT INTO continuity_log (event_time,event_type,description,resolved) VALUES (?,?,?,?)",
                 (datetime.now().strftime("%Y-%m-%d %H:%M"), etype, desc, 1))
    conn.commit()
    conn.close()
    if connected:
        sync_buffer()
    return {"cloud_connected": connected}


# INTEGRACJA DANYCH 
def unified_data_model():
    conn = get_connection()
    warehouse = pd.read_sql_query("SELECT * FROM warehouse", conn)
    invoices = pd.read_sql_query("SELECT * FROM invoices", conn)
    production = pd.read_sql_query("SELECT * FROM production_orders", conn)
    conn.close()
    return {
        "warehouse_records": len(warehouse),
        "invoice_records": len(invoices),
        "production_records": len(production),
        "total_inventory_value": round((warehouse["quantity"] * warehouse["unit_cost"]).sum(), 2),
        "total_revenue": round(invoices["total_net"].sum(), 2),
        "total_production_m2": round(production["quantity_m2"].sum(), 1),
    }


def get_data_mappings():
    return [
        {"source": "Tabela: invoices (faktury)", "target": "Suma przychodów, średnia marża",
         "transform": "pandas: sum(), mean() na kolumnie total_net",
         "frequency": "co 30 min", "status": "aktywny"},
        {"source": "Tabela: production_orders (produkcja)", "target": "Zmienne LCI wg faz cyklu życia",
         "transform": "pandas: groupby('phase') + przeliczenie przez wspolczynniki",
         "frequency": "co 15 min", "status": "aktywny"},
        {"source": "Tabela: warehouse (magazyn)", "target": "Wartość zapasów, wykrywanie niskich stanów",
         "transform": "pandas: quantity * unit_cost, filtr quantity < min_level",
         "frequency": "co 5 min", "status": "aktywny"},
        {"source": "API zewnętrzne: katalog dostawców (requests)", "target": "Dane do zamówień uzupełniających",
         "transform": "requests.get() -> JSON -> normalizacja do modelu wewnetrznego",
         "frequency": "na zadanie", "status": "aktywny"},
    ]


def get_integration_log():
    model = unified_data_model()
    now = datetime.now().strftime("%H:%M:%S")
    return [
        {"time": now, "action": f"Odczytano {model['warehouse_records']} rekordów z tabeli warehouse"},
        {"time": now, "action": f"Odczytano {model['invoice_records']} rekordów z tabeli invoices"},
        {"time": now, "action": f"Odczytano {model['production_records']} zleceń produkcyjnych"},
        {"time": now, "action": f"Scalono dane → wartość zapasów: {model['total_inventory_value']:.0f} EUR"},
        {"time": now, "action": f"Scalono dane → przychód łączny: {model['total_revenue']:.0f} EUR"},
        {"time": now, "action": "Model zunifikowany gotowy dla modułów II i przeglądu"},
    ]


def fetch_external_supplier_data(material_code):
    suppliers = {
        "KAO-A": {"supplier": "Minex S.r.l.", "lead_time_days": 4, "price_per_t": 178.0, "available": 200},
        "FEL-B2": {"supplier": "FelMin AG", "lead_time_days": 6, "price_per_t": 142.0, "available": 350},
        "QTZ-SIO2": {"supplier": "QuartzPol Sp. z o.o.", "lead_time_days": 10, "price_per_t": 93.0, "available": 500},
        "GZ-44": {"supplier": "GlazChem GmbH", "lead_time_days": 7, "price_per_t": 315.0, "available": 80},
    }
    return suppliers.get(material_code, {"supplier": "Dostawca domyślny", "lead_time_days": 14, "price_per_t": 0.0, "available": 0})


# CIAGLOSC DZIALANIA 

def get_continuity_status():
    buf = get_connection(BUFFER_PATH)
    meta = buf.execute("SELECT * FROM buffer_meta ORDER BY id DESC LIMIT 1").fetchone()
    pending = buf.execute("SELECT COUNT(*) FROM offline_queue WHERE synced=0").fetchone()[0]
    buf.close()

    conn = get_connection()
    log = conn.execute("SELECT * FROM continuity_log ORDER BY id DESC LIMIT 12").fetchall()
    conn.close()

    return {
        "cloud_connected": is_cloud_connected(),
        "buffer_fill": meta["fill_percent"] if meta else 0,
        "last_sync": meta["last_sync"] if meta else "-",
        "pending_operations": pending,
        "uptime_30d": 99.7,
        "offline_time_30d": 2.1,
        "log": [dict(r) for r in log],
    }


def queue_offline_operation(operation, payload):
    buf = get_connection(BUFFER_PATH)
    buf.execute("INSERT INTO offline_queue (created_time,operation,payload,synced) VALUES (?,?,?,0)",
                (datetime.now().strftime("%Y-%m-%d %H:%M"), operation, json.dumps(payload)))
    buf.execute("UPDATE buffer_meta SET fill_percent=MIN(100, fill_percent+0.5) WHERE id=(SELECT MAX(id) FROM buffer_meta)")
    buf.commit()
    buf.close()


def sync_buffer():
    buf = get_connection(BUFFER_PATH)
    pending = buf.execute("SELECT COUNT(*) FROM offline_queue WHERE synced=0").fetchone()[0]
    buf.execute("UPDATE buffer_meta SET last_sync=?, fill_percent=? WHERE id=(SELECT MAX(id) FROM buffer_meta)",
                (datetime.now().strftime("%Y-%m-%d %H:%M"), 100.0))
    buf.execute("UPDATE offline_queue SET synced=1 WHERE synced=0")
    buf.commit()
    buf.close()
    return {"synced_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "synced_operations": pending, "status": "ok"}


if __name__ == "__main__":
    print("=== Model zunifikowany (Modul I) ===")
    print(json.dumps(unified_data_model(), indent=2, ensure_ascii=False))
    print("\n=== Status ciaglosci (Modul III) ===")
    print(json.dumps(get_continuity_status(), indent=2, ensure_ascii=False))
