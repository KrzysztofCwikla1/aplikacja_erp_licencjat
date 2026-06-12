import sqlite3
import os
import bcrypt
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "erp.db")
BUFFER_PATH = os.path.join(os.path.dirname(__file__), "data", "erp_buffer.db")


def get_connection(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
        full_name TEXT, created_at TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS warehouse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL,
        unit TEXT NOT NULL, quantity REAL NOT NULL, min_level REAL NOT NULL,
        unit_cost REAL NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL, client_name TEXT NOT NULL,
        client_address TEXT, client_nip TEXT, issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL, total_net REAL NOT NULL, total_gross REAL NOT NULL,
        status TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id INTEGER NOT NULL,
        description TEXT NOT NULL, quantity REAL NOT NULL, unit_price REAL NOT NULL,
        line_total REAL NOT NULL, FOREIGN KEY (invoice_id) REFERENCES invoices(id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS purchase_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, po_number TEXT UNIQUE NOT NULL,
        material_code TEXT NOT NULL, material_name TEXT NOT NULL, quantity REAL NOT NULL,
        supplier TEXT NOT NULL, order_date TEXT NOT NULL, status TEXT NOT NULL,
        offline_created INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS production_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, order_number TEXT UNIQUE NOT NULL,
        product_name TEXT NOT NULL, quantity_m2 REAL NOT NULL, phase TEXT NOT NULL,
        energy_kwh REAL NOT NULL, water_m3 REAL NOT NULL, raw_material_kg REAL NOT NULL,
        transport_km REAL NOT NULL, order_date TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_code TEXT NOT NULL,
        raw_code TEXT NOT NULL,
        raw_per_unit REAL NOT NULL,
        UNIQUE(product_code, raw_code))""")

    c.execute("""CREATE TABLE IF NOT EXISTS lci_factors (
        id INTEGER PRIMARY KEY AUTOINCREMENT, factor_name TEXT UNIQUE NOT NULL,
        label TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS continuity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, event_time TEXT NOT NULL,
        event_type TEXT NOT NULL, description TEXT NOT NULL, resolved INTEGER DEFAULT 1)""")

    c.execute("""CREATE TABLE IF NOT EXISTS system_state (
        key TEXT PRIMARY KEY, value TEXT NOT NULL)""")

    conn.commit()

    if c.execute("SELECT COUNT(*) FROM warehouse").fetchone()[0] == 0:
        _seed_data(c)
        conn.commit()

    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        c.execute("INSERT INTO users (username,password_hash,full_name,created_at) VALUES (?,?,?,?)",
                  ("admin", hash_password("admin123"), "Administrator", datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()

    if c.execute("SELECT COUNT(*) FROM system_state WHERE key='cloud_connected'").fetchone()[0] == 0:
        c.execute("INSERT INTO system_state (key,value) VALUES ('cloud_connected','1')")
        conn.commit()

    conn.close()
    _init_buffer()


def _seed_data(c):
    today = datetime.now()
    warehouse = [
        ("KAO-A", "Kaolin A (surowiec główny)", "surowiec", "t", 42.4, 20.0, 180.0),
        ("FEL-B2", "Skaleń B2 (topnik)", "surowiec", "t", 38.0, 25.0, 145.0),
        ("QTZ-SIO2", "Kwarc SiO₂ (wypełniacz)", "surowiec", "t", 92.5, 40.0, 95.0),
        ("GZ-44", "Glazura GZ-44", "surowiec", "t", 18.1, 5.0, 320.0),
        ("PLT-MARMO", "Płytki Marmo 60×60", "produkt", "m²", 4200.0, 1000.0, 0.0),
        ("PLT-SABBIA", "Płytki Sabbia 30×60", "produkt", "m²", 2800.0, 800.0, 0.0),
        ("PLT-NERO", "Płytki Nero 90×90", "produkt", "m²", 320.0, 500.0, 0.0),
        ("PLT-BIANCO", "Płytki Bianco 45×45", "produkt", "m²", 3400.0, 700.0, 0.0),
    ]
    c.executemany("INSERT INTO warehouse (code,name,category,unit,quantity,min_level,unit_cost) VALUES (?,?,?,?,?,?,?)", warehouse)

    recipes = [
        ("PLT-MARMO", "KAO-A", 0.0028), ("PLT-MARMO", "FEL-B2", 0.0015),
        ("PLT-MARMO", "QTZ-SIO2", 0.0020), ("PLT-MARMO", "GZ-44", 0.0008),
        ("PLT-SABBIA", "KAO-A", 0.0022), ("PLT-SABBIA", "FEL-B2", 0.0012),
        ("PLT-SABBIA", "QTZ-SIO2", 0.0018),
        ("PLT-NERO", "KAO-A", 0.0035), ("PLT-NERO", "FEL-B2", 0.0018),
        ("PLT-NERO", "QTZ-SIO2", 0.0015), ("PLT-NERO", "GZ-44", 0.0012),
        ("PLT-BIANCO", "KAO-A", 0.0020), ("PLT-BIANCO", "QTZ-SIO2", 0.0016),
        ("PLT-BIANCO", "GZ-44", 0.0006),
    ]
    c.executemany("INSERT INTO recipes (product_code,raw_code,raw_per_unit) VALUES (?,?,?)", recipes)

    factors = [
        ("co2_per_kwh", "Emisja CO₂e z energii elektrycznej", 0.65, "kg CO₂e/kWh"),
        ("co2_per_kg_raw", "Emisja CO₂e z wydobycia surowców", 0.42, "kg CO₂e/kg"),
        ("co2_per_km", "Emisja CO₂e z transportu", 0.12, "kg CO₂e/km"),
    ]
    c.executemany("INSERT INTO lci_factors (factor_name,label,value,unit) VALUES (?,?,?,?)", factors)

    prod = [
        ("ZP-0841", "Płytki Marmo 60×60", 4200, "Surowce i dostawa", 18500, 145, 52000, 320, (today - timedelta(days=5)).strftime("%Y-%m-%d")),
        ("ZP-0842", "Płytki Sabbia 30×60", 2800, "Suszenie i opalanie", 24200, 98, 31000, 180, (today - timedelta(days=4)).strftime("%Y-%m-%d")),
        ("ZP-0843", "Płytki Nero 90×90", 1600, "Cięcie i glazurowanie", 9800, 64, 19500, 95, (today - timedelta(days=2)).strftime("%Y-%m-%d")),
        ("ZP-0844", "Płytki Bianco 45×45", 3400, "Pakowanie i dystrybucja", 6200, 41, 22800, 410, (today - timedelta(days=1)).strftime("%Y-%m-%d")),
    ]
    c.executemany("INSERT INTO production_orders (order_number,product_name,quantity_m2,phase,energy_kwh,water_m3,raw_material_kg,transport_km,order_date) VALUES (?,?,?,?,?,?,?,?,?)", prod)

    inv = [
        ("FV/2026/0541", "Rossi S.r.l.", "Via Emilia 12, Sassuolo", "IT0123456789", (today - timedelta(days=20)).strftime("%Y-%m-%d"), (today - timedelta(days=6)).strftime("%Y-%m-%d"), 68400.0, 84132.0, "opłacona"),
        ("FV/2026/0548", "Bauer GmbH", "Hauptstrasse 5, München", "DE987654321", (today - timedelta(days=8)).strftime("%Y-%m-%d"), (today + timedelta(days=6)).strftime("%Y-%m-%d"), 38200.0, 46986.0, "wystawiona"),
        ("FV/2026/0531", "Moreau SA", "Rue de Paris 8, Lyon", "FR456789123", (today - timedelta(days=40)).strftime("%Y-%m-%d"), (today - timedelta(days=12)).strftime("%Y-%m-%d"), 52800.0, 64944.0, "po terminie"),
    ]
    c.executemany("INSERT INTO invoices (invoice_number,client_name,client_address,client_nip,issue_date,due_date,total_net,total_gross,status) VALUES (?,?,?,?,?,?,?,?,?)", inv)

    log = [
        ((today - timedelta(days=21)).strftime("%Y-%m-%d %H:%M"), "offline", "Przerwa połączenia z chmurą - bufor lokalny przejął obsługę przez 47 min", 1),
        ((today - timedelta(days=21)).strftime("%Y-%m-%d %H:%M"), "sync", "Synchronizacja po przywróceniu połączenia - 0 utraty danych", 1),
        ((today - timedelta(days=37)).strftime("%Y-%m-%d %H:%M"), "offline", "Przerwa połączenia z chmurą - bufor aktywny przez 1h 23min", 1),
    ]
    c.executemany("INSERT INTO continuity_log (event_time,event_type,description,resolved) VALUES (?,?,?,?)", log)


def _init_buffer():
    buf = get_connection(BUFFER_PATH)
    bc = buf.cursor()
    bc.execute("""CREATE TABLE IF NOT EXISTS buffer_meta (
        id INTEGER PRIMARY KEY AUTOINCREMENT, last_sync TEXT, fill_percent REAL)""")
    bc.execute("""CREATE TABLE IF NOT EXISTS offline_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_time TEXT NOT NULL,
        operation TEXT NOT NULL, payload TEXT NOT NULL, synced INTEGER DEFAULT 0)""")
    if bc.execute("SELECT COUNT(*) FROM buffer_meta").fetchone()[0] == 0:
        bc.execute("INSERT INTO buffer_meta (last_sync,fill_percent) VALUES (?,?)",
                   (datetime.now().strftime("%Y-%m-%d %H:%M"), 98.0))
    buf.commit()
    buf.close()


if __name__ == "__main__":
    init_db()
    print(f"Baza danych zainicjalizowana: {DB_PATH}")
    print("Domyslny uzytkownik: admin / admin123")
