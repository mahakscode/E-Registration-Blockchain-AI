"""Step 2: simple rule-based fraud screening.

Every rule that fires adds a "finding" with a severity and some points.
  - High findings block the registration.
  - Risk score = sum of points (max 100). A High finding forces the score to at least 60.
  - Level: 0-29 Low, 30-59 Medium, 60-100 High.
"""
from datetime import datetime, timedelta

from verification import UNIT_TO_SQM, norm_code, norm_text


def screen(conn, form, v):
    record = v["record"]
    checks = {c["key"]: c for c in v["checks"]}
    findings = []

    def add(code, severity, points, **params):
        findings.append({"code": code, "severity": severity, "points": points, "params": params})

    now = datetime.now()

    if record is None:
        add("record_not_found", "medium", 50)
    else:
        # --- Wrong identifiers ---
        if v["via_numbers"]:
            add("incorrect_property_id", "high", 45)
        if not checks["khasra_no"]["ok"]:
            add("incorrect_khasra", "high", 40)

        # --- Seller is not the recorded owner ---
        if not checks["seller_name"]["ok"]:
            add("seller_not_owner", "high", 50)
        elif not checks["seller_id"]["ok"]:
            add("seller_id_mismatch", "high", 45)

        # --- Deceased owner / disputed record ---
        if record["ownership_status"] == "Owner Deceased":
            add("owner_deceased", "high", 60)
        elif record["ownership_status"] == "Disputed":
            add("disputed_record", "high", 50)

        # --- Conflicting records: another record has the same Khasra + Khata + Survey but another owner ---
        triple = (norm_code(record["khasra_no"]), norm_code(record["khata_no"]), norm_code(record["survey_no"]))
        others = [r for r in conn.execute("SELECT * FROM properties WHERE property_id != ?", (record["property_id"],))
                  if (norm_code(r["khasra_no"]), norm_code(r["khata_no"]), norm_code(r["survey_no"])) == triple
                  and norm_text(r["owner_name"]) != norm_text(record["owner_name"])]
        if others:
            add("conflicting_records", "high", 45, count=len(others))

        # --- Suspicious ownership changes (look at the recorded ownership history) ---
        history = conn.execute(
            "SELECT * FROM ownership_history WHERE property_id = ? ORDER BY acquired_on",
            (record["property_id"],),
        ).fetchall()
        recent = [h for h in history
                  if h["transfer_type"] != "Original allotment"
                  and datetime.fromisoformat(h["acquired_on"]) >= now - timedelta(days=730)]
        if len(recent) >= 3:
            add("frequent_transfers", "medium", 20, count=len(recent))
        current = [h for h in history if h["ceased_on"] is None]
        if current and current[0]["transfer_type"] != "Original allotment":
            days = (now - datetime.fromisoformat(current[0]["acquired_on"])).days
            if days < 90:
                add("rapid_transfer", "medium", 20, days=days)

    # --- Duplicate registration ---
    deed = norm_code(form["sale_deed_ref"])
    done = conn.execute("SELECT sale_deed_ref, matched_property_id, seller_name, buyer_name "
                        "FROM registrations WHERE registration_id IS NOT NULL").fetchall()
    if any(norm_code(d["sale_deed_ref"]) == deed for d in done):
        add("duplicate_deed", "high", 60)
    elif record is not None and any(
            d["matched_property_id"] == record["property_id"]
            and norm_text(d["seller_name"]) == norm_text(form["seller_name"])
            and norm_text(d["buyer_name"]) == norm_text(form["buyer_name"]) for d in done):
        add("duplicate_registration", "high", 60)

    # --- Buyer and seller are the same person ---
    if norm_text(form["buyer_name"]) == norm_text(form["seller_name"]) or \
            norm_code(form["buyer_id"]) == norm_code(form["seller_id"]):
        add("self_transfer", "high", 50)

    # --- Price too low compared with circle rate and with the last sale price ---
    circle_value = form["circle_rate"] * form["area"] * UNIT_TO_SQM[form["unit"]]
    price = form["declared_price"]
    if price < 0.5 * circle_value:
        add("price_below_half_circle", "high", 45, price=price, circle=round(circle_value))
    elif price < circle_value:
        add("price_below_circle", "medium", 20, price=price, circle=round(circle_value))
    if record is not None:
        previous = record["previous_sale_price"]
        if price < 0.4 * previous:
            add("price_far_below_history", "high", 40, price=price, previous=previous)
        elif price < 0.7 * previous:
            add("price_below_history", "medium", 20, price=price, previous=previous)

    # --- Score, level and decision ---
    score = min(100, sum(f["points"] for f in findings))
    if any(f["severity"] == "high" for f in findings):
        score = max(score, 60)
    level = "High" if score >= 60 else "Medium" if score >= 30 else "Low"
    decision = "blocked" if level == "High" else "warning" if findings else "clear"
    return {"score": score, "level": level, "decision": decision, "findings": findings}
