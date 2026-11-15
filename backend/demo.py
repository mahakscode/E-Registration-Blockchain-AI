"""Builds ready-to-use demo scenarios from the REAL database, so the form can be filled with one click.
The results still come from the real verification, fraud and mutation code - nothing here is faked."""
import random
from datetime import date

BUYERS = [("Amit Verma", "OWN900001"), ("Neha Kapoor", "OWN900002"), ("Karan Malhotra", "OWN900003"),
          ("Divya Menon", "OWN900004"), ("Sandeep Bhatt", "OWN900005")]
LAND_CATEGORY = {"Residential": "Abadi", "Commercial": "CommercialPlot", "Agricultural": "Irrigated"}


def _property(conn, number):
    return conn.execute("SELECT * FROM properties WHERE property_id = ?", (f"PROP{1000 + number}",)).fetchone()


def _form(p, buyer_exclude=None, **changes):
    """A correct, valid sale form for property row p. `changes` overrides single fields."""
    circle_rate = round(p["previous_sale_price"] / p["area_sqm"] / 1.25)   # circle value = 80% of last price
    buyer = next(b for b in BUYERS if b[0] != (buyer_exclude or p["owner_name"]))
    form = {
        "property_id": p["property_id"], "property_name": p["property_name"], "khasra_no": p["khasra_no"],
        "khata_no": p["khata_no"], "survey_no": p["survey_no"], "address": p["address"], "state": p["state"],
        "district": p["district"], "tehsil": p["tehsil"], "area": p["area_sqm"], "unit": "sqm",
        "property_type": p["property_type"], "land_category": LAND_CATEGORY[p["property_type"]],
        "circle_rate": circle_rate, "declared_price": round(p["previous_sale_price"] * 1.15, -3),
        "seller_name": p["owner_name"], "seller_id": p["owner_id"],
        "seller_contact": "98" + str(int(p["property_id"][4:]) * 7919 % 10**8).zfill(8),
        "existing_ownership": "Owner as per land records",
        "buyer_name": buyer[0], "buyer_id": buyer[1], "buyer_contact": "9811122233",
        "registration_date": date.today().isoformat(),
        "sale_deed_ref": f"SD/{date.today():%Y}/{random.randint(30000, 99999)}",
        "transaction_details": "Sale by bank transfer (demo)",
    }
    form.update(changes)
    return form


def build_demo_cases(conn):
    cases = []

    def add(key, form):
        cases.append({"key": key, "form": form})

    p1, p2, p3, p4, p6 = (_property(conn, n) for n in (1, 2, 3, 4, 6))

    if p1:
        add("valid_sale", _form(p1))
    if p6:
        add("suspicious_transfers", _form(p6))
    if p2:
        add("wrong_seller", _form(p2, seller_name="Vinod Kumar", seller_id="OWN555555"))
        a, b = p2["khasra_no"].split("/")
        add("wrong_khasra", _form(p2, khasra_no=f"{int(a) + 500}/{b}"))
        add("wrong_property_id", _form(p2, property_id="PROP9999"))
        circle_value = round(p2["previous_sale_price"] / 1.25)
        add("low_price", _form(p2, declared_price=round(circle_value * 0.35, -3)))
        add("not_found", _form(p2, property_id="PROP7777", khasra_no="999/9", khata_no="KH-9999",
                               survey_no="SVY-9999"))
    if p3:
        add("deceased_owner", _form(p3))
    if p4:
        add("conflicting", _form(p4))

    done = conn.execute("SELECT * FROM registrations WHERE registration_id IS NOT NULL ORDER BY id LIMIT 1").fetchone()
    if done:
        p = conn.execute("SELECT * FROM properties WHERE property_id = ?", (done["matched_property_id"],)).fetchone()
        add("duplicate", _form(p, seller_name=done["seller_name"], seller_id=done["seller_id"],
                               buyer_name=done["buyer_name"], buyer_id=done["buyer_id"],
                               sale_deed_ref=done["sale_deed_ref"], declared_price=done["declared_price"]))
    return cases
