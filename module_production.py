from database import get_connection


def get_recipes():
    
    conn = get_connection()
    products = conn.execute(
        "SELECT code, name, unit, quantity FROM warehouse WHERE category='produkt' ORDER BY name"
    ).fetchall()
    result = []
    for p in products:
        ingredients = conn.execute("""
            SELECT r.raw_code, w.name AS raw_name, w.unit AS raw_unit,
                   r.raw_per_unit, w.quantity AS stock
            FROM recipes r JOIN warehouse w ON w.code = r.raw_code
            WHERE r.product_code = ?
        """, (p["code"],)).fetchall()
        result.append({
            "product_code": p["code"],
            "product_name": p["name"],
            "product_unit": p["unit"],
            "current_stock": p["quantity"],
            "ingredients": [dict(i) for i in ingredients],
        })
    conn.close()
    return result


def check_production(product_code, amount):
    conn = get_connection()
    recipe = conn.execute("""
        SELECT r.raw_code, w.name AS raw_name, w.unit AS raw_unit,
               r.raw_per_unit, w.quantity AS stock
        FROM recipes r JOIN warehouse w ON w.code = r.raw_code
        WHERE r.product_code = ?
    """, (product_code,)).fetchall()
    conn.close()

    if not recipe:
        return {"feasible": False, "reason": "Brak receptury dla produktu", "requirements": []}

    requirements, feasible = [], True
    for ing in recipe:
        needed = round(ing["raw_per_unit"] * amount, 3)
        enough = ing["stock"] >= needed
        if not enough:
            feasible = False
        requirements.append({
            "raw_code": ing["raw_code"], "raw_name": ing["raw_name"], "raw_unit": ing["raw_unit"],
            "needed": needed, "stock": round(ing["stock"], 2), "enough": enough,
        })
    return {"feasible": feasible, "requirements": requirements}


def run_production(product_code, amount):
    check = check_production(product_code, amount)
    if not check["requirements"]:
        return {"ok": False, "error": "Brak receptury dla wybranego produktu"}
    if not check["feasible"]:
        braki = [r["raw_name"] for r in check["requirements"] if not r["enough"]]
        return {"ok": False, "error": "Za mało surowców: " + ", ".join(braki),
                "requirements": check["requirements"]}

    conn = get_connection()
    for r in check["requirements"]:
        conn.execute("UPDATE warehouse SET quantity = quantity - ? WHERE code=?",
                     (r["needed"], r["raw_code"]))
    conn.execute("UPDATE warehouse SET quantity = quantity + ? WHERE code=?", (amount, product_code))
    conn.commit()
    prod = conn.execute("SELECT name, quantity, unit FROM warehouse WHERE code=?", (product_code,)).fetchone()
    conn.close()

    return {
        "ok": True,
        "product_name": prod["name"],
        "product_total": round(prod["quantity"], 1),
        "product_unit": prod["unit"],
        "consumed": [{"name": r["raw_name"], "amount": r["needed"], "unit": r["raw_unit"]}
                     for r in check["requirements"]],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_recipes(), indent=2, ensure_ascii=False))
    print("--- Test produkcji 500 m2 Marmo ---")
    print(json.dumps(check_production("PLT-MARMO", 500), indent=2, ensure_ascii=False))
