import pandas as pd
from database import get_connection


def get_lci_factors():
    conn = get_connection()
    rows = conn.execute("SELECT factor_name,label,value,unit FROM lci_factors ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _factors_dict():
    return {f["factor_name"]: f["value"] for f in get_lci_factors()}


def update_factor(factor_name, value):
    conn = get_connection()
    exists = conn.execute("SELECT 1 FROM lci_factors WHERE factor_name=?", (factor_name,)).fetchone()
    if not exists:
        conn.close()
        return None
    conn.execute("UPDATE lci_factors SET value=? WHERE factor_name=?", (value, factor_name))
    conn.commit()
    conn.close()
    return {"factor_name": factor_name, "value": value}


def calculate_lci():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM production_orders", conn)
    conn.close()

    if df.empty:
        return {"phases": [], "co2": [], "energy": [], "water": [],
                "total_co2": 0, "total_energy": 0, "total_water": 0, "target_co2": 401.0}

    factors = _factors_dict()
    df["co2_energy"] = df["energy_kwh"] * factors.get("co2_per_kwh", 0.65)
    df["co2_raw"] = df["raw_material_kg"] * factors.get("co2_per_kg_raw", 0.42)
    df["co2_transport"] = df["transport_km"] * factors.get("co2_per_km", 0.12)
    df["co2_total"] = df["co2_energy"] + df["co2_raw"] + df["co2_transport"]

    grouped = df.groupby("phase").agg(
        co2=("co2_total", "sum"), energy=("energy_kwh", "sum"), water=("water_m3", "sum")
    ).reset_index()

    phase_order = ["Surowce i dostawa", "Suszenie i opalanie",
                   "Ciecie i glazurowanie", "Pakowanie i dystrybucja"]
    grouped["order"] = grouped["phase"].apply(lambda x: phase_order.index(x) if x in phase_order else 99)
    grouped = grouped.sort_values("order")

    co2_vals = [round(v / 1000, 1) for v in grouped["co2"].tolist()]
    energy_vals = [round(v / 1000, 1) for v in grouped["energy"].tolist()]
    water_vals = [round(v, 1) for v in grouped["water"].tolist()]

    return {
        "phases": grouped["phase"].tolist(),
        "co2": co2_vals, "energy": energy_vals, "water": water_vals,
        "total_co2": round(sum(co2_vals), 1),
        "total_energy": round(sum(energy_vals), 1),
        "total_water": round(sum(water_vals), 1),
        "target_co2": 401.0,
    }


def scenario_analysis(energy_reduction_pct=0, transport_reduction_pct=0):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM production_orders", conn)
    conn.close()
    f = _factors_dict()

    base_co2 = ((df["energy_kwh"] * f["co2_per_kwh"]).sum()
                + (df["raw_material_kg"] * f["co2_per_kg_raw"]).sum()
                + (df["transport_km"] * f["co2_per_km"]).sum())
    alt_co2 = ((df["energy_kwh"] * (1 - energy_reduction_pct / 100) * f["co2_per_kwh"]).sum()
               + (df["raw_material_kg"] * f["co2_per_kg_raw"]).sum()
               + (df["transport_km"] * (1 - transport_reduction_pct / 100) * f["co2_per_km"]).sum())

    return {
        "base_co2": round(base_co2 / 1000, 1),
        "alt_co2": round(alt_co2 / 1000, 1),
        "savings": round((base_co2 - alt_co2) / 1000, 1),
        "savings_pct": round((base_co2 - alt_co2) / base_co2 * 100, 1) if base_co2 else 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(calculate_lci(), indent=2, ensure_ascii=False))
