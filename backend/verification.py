"""Step 1: compare the submitted form with the historical land records."""
import re
from difflib import SequenceMatcher

# How many square metres in one unit (all areas are compared in square metres)
UNIT_TO_SQM = {"sqm": 1.0, "sqft": 0.09290304, "acre": 4046.8564224, "hectare": 10000.0}

CHECK_KEYS = [
    "property_id", "khasra_no", "khata_no", "survey_no", "state", "district", "tehsil",
    "address", "area", "property_type", "seller_name", "seller_id", "ownership_status",
]


def norm_text(value):
    """'  Rajesh   SHARMA ' -> 'rajesh sharma'"""
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def norm_code(value):
    """'KH-3001' and 'kh 3001' both become 'KH3001'. The '/' is kept for Khasra like 245/1."""
    return re.sub(r"[^A-Z0-9/]", "", str(value or "").upper())


def mask_name(name):
    """Rajesh Sharma -> R***** S*****  (we never show the real owner to the person submitting)"""
    return " ".join(w[0] + "*" * (len(w) - 1) for w in str(name).split())


def mask_id(value):
    value = str(value)
    return value[:3] + "*" * max(len(value) - 5, 1) + value[-2:] if len(value) > 5 else "*" * len(value)


def make_check(key, ok, entered, recorded=None, fmt="text", masked=False):
    return {"key": key, "ok": ok, "entered": entered, "recorded": recorded,
            "fmt": fmt, "masked": masked}


def find_record(conn, form):
    """Look up by Property ID. If the ID is wrong, try the Khasra + Khata + Survey combination.
    Returns (record, found_only_by_numbers)."""
    row = conn.execute(
        "SELECT * FROM properties WHERE UPPER(property_id) = ?",
        (form["property_id"].strip().upper(),),
    ).fetchone()
    if row:
        return row, False
    wanted = (norm_code(form["khasra_no"]), norm_code(form["khata_no"]), norm_code(form["survey_no"]))
    for r in conn.execute("SELECT * FROM properties"):
        if (norm_code(r["khasra_no"]), norm_code(r["khata_no"]), norm_code(r["survey_no"])) == wanted:
            return r, True
    return None, False


def verify(conn, form):
    """Returns {"status": Verified | Mismatch | Not Found, "checks": [...], "record": row, "via_numbers": bool}"""
    record, via_numbers = find_record(conn, form)
    if record is None:
        return {"status": "Not Found", "checks": [], "record": None, "via_numbers": False}

    entered_sqm = form["area"] * UNIT_TO_SQM[form["unit"]]
    recorded_sqm = record["area_sqm"]
    checks = []

    # Property ID (if we got here only through the other numbers, the ID the user typed is wrong)
    checks.append(make_check("property_id", not via_numbers, form["property_id"]))

    # Khasra, Khata, Survey: must match exactly (ignoring spaces / dashes / case)
    for key in ("khasra_no", "khata_no", "survey_no"):
        ok = norm_code(form[key]) == norm_code(record[key])
        checks.append(make_check(key, ok, form[key], None if ok else record[key]))

    # Location
    for key in ("state", "district", "tehsil"):
        ok = norm_text(form[key]) == norm_text(record[key])
        checks.append(make_check(key, ok, form[key], None if ok else record[key]))
    address_ok = SequenceMatcher(None, norm_text(form["address"]), norm_text(record["address"])).ratio() >= 0.6
    checks.append(make_check("address", address_ok, form["address"], None if address_ok else record["address"]))

    # Area: allow a 2% difference to cover rounding and unit conversion
    area_ok = abs(entered_sqm - recorded_sqm) / recorded_sqm <= 0.02
    checks.append(make_check("area", area_ok, round(entered_sqm, 1),
                             None if area_ok else round(recorded_sqm, 1), fmt="area"))

    type_ok = norm_text(form["property_type"]) == norm_text(record["property_type"])
    checks.append(make_check("property_type", type_ok, form["property_type"],
                             None if type_ok else record["property_type"]))

    # Seller must be the recorded owner. We show only a masked version if it is wrong.
    name_ok = norm_text(form["seller_name"]) == norm_text(record["owner_name"])
    checks.append(make_check("seller_name", name_ok, form["seller_name"],
                             None if name_ok else mask_name(record["owner_name"]), masked=not name_ok))
    id_ok = norm_code(form["seller_id"]) == norm_code(record["owner_id"])
    checks.append(make_check("seller_id", id_ok, form["seller_id"],
                             None if id_ok else mask_id(record["owner_id"]), masked=not id_ok))

    # Ownership status must be Clear (not deceased, not disputed)
    status_ok = record["ownership_status"] == "Clear"
    checks.append(make_check("ownership_status", status_ok, None, record["ownership_status"]))

    status = "Verified" if all(c["ok"] for c in checks) else "Mismatch"
    return {"status": status, "checks": checks, "record": record, "via_numbers": via_numbers}


def passing_checks(form):
    """All-green checks, used only for the synthetic past registrations created by seed_data.py."""
    values = dict(form)
    values["area"] = round(form["area"], 1)
    return [make_check(k, True, values.get(k), fmt="area" if k == "area" else "text")
            for k in CHECK_KEYS if k != "ownership_status"] + [make_check("ownership_status", True, None, "Clear")]
