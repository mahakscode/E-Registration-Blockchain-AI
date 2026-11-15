"""The whole workflow in one place: verify -> fraud screening -> register -> auto-mutate."""
import json
import time
from datetime import datetime

from database import make_case_id, make_mutation_id, make_registration_id, save_registration
from fraud import screen
from verification import verify


def process_registration(conn, form):
    """Runs every step and returns the numeric id of the saved registration row."""
    v = verify(conn, form)
    fraud = screen(conn, form, v)
    record = v["record"]
    passed = v["status"] == "Verified" and fraud["decision"] != "blocked"
    now = datetime.now().replace(microsecond=0)
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")

    row = dict(form)
    row.update({
        "submitted_at": stamp,
        "matched_property_id": record["property_id"] if record else None,
        "verification_status": v["status"],
        "fraud_status": fraud["decision"],
        "risk_score": fraud["score"],
        "risk_level": fraud["level"],
        "registration_status": "Registered" if passed else "Manual Verification",
        "mutation_status": "Completed" if passed else "Not Performed",
        "mutation_at": stamp if passed else None,
        "previous_owner": record["owner_name"] if (passed and record) else None,
        "checks_json": json.dumps(v["checks"]),
        "findings_json": json.dumps(fraud["findings"]),
    })

    started = time.perf_counter()
    with conn:  # one transaction: either everything is saved, or nothing is
        row_id = save_registration(conn, row)
        if passed:
            apply_mutation(conn, record, form, row_id, now, stamp)
        else:
            conn.execute("UPDATE registrations SET case_id = ? WHERE id = ?",
                         (make_case_id(row_id, now), row_id))
    if passed:
        elapsed_ms = max(1, round((time.perf_counter() - started) * 1000))
        with conn:
            conn.execute("UPDATE registrations SET mutation_ms = ? WHERE id = ?", (elapsed_ms, row_id))
    return row_id


def apply_mutation(conn, record, form, row_id, now, stamp):
    """Auto-mutation: the buyer becomes the owner, the old owner stays in the history."""
    registration_id = make_registration_id(row_id, now)
    mutation_id = make_mutation_id(row_id, now)
    pid = record["property_id"]

    # 1. Close the previous owner's period in the history
    conn.execute("UPDATE ownership_history SET ceased_on = ? WHERE property_id = ? AND ceased_on IS NULL",
                 (stamp, pid))
    # 2. Add the buyer as the new (current) owner
    conn.execute(
        "INSERT INTO ownership_history (property_id, owner_name, owner_id, acquired_on, ceased_on,"
        " transfer_type, sale_price, registration_id, mutation_id) VALUES (?, ?, ?, ?, NULL, 'Sale', ?, ?, ?)",
        (pid, form["buyer_name"], form["buyer_id"], stamp, round(form["declared_price"]),
         registration_id, mutation_id),
    )
    # 3. Update the historical land record itself
    conn.execute(
        "UPDATE properties SET owner_name = ?, owner_id = ?, previous_owner_name = ?, previous_sale_price = ?,"
        " mutation_status = 'Completed', last_mutation_id = ?, last_mutation_at = ? WHERE property_id = ?",
        (form["buyer_name"], form["buyer_id"], record["owner_name"], round(form["declared_price"]),
         mutation_id, stamp, pid),
    )
    # 4. Stamp the registration with its IDs
    conn.execute("UPDATE registrations SET registration_id = ?, mutation_id = ? WHERE id = ?",
                 (registration_id, mutation_id, row_id))


def build_response(conn, ref):
    """Everything the website needs to show one registration (by Registration ID or Case ID)."""
    row = conn.execute("SELECT * FROM registrations WHERE registration_id = ? OR case_id = ?",
                       (ref, ref)).fetchone()
    if row is None:
        return None
    r = dict(row)
    checks = json.loads(r.pop("checks_json") or "[]")
    findings = json.loads(r.pop("findings_json") or "[]")

    stages = {
        "verify": "pass" if r["verification_status"] == "Verified" else "fail",
        "fraud": {"blocked": "fail", "warning": "warn"}.get(r["fraud_status"], "pass"),
        "register": "pass" if r["registration_status"] == "Registered" else "skip",
        "mutate": "pass" if r["mutation_status"] == "Completed" else "skip",
    }
    history = []
    if r["matched_property_id"]:
        history = [dict(h) for h in conn.execute(
            "SELECT * FROM ownership_history WHERE property_id = ? ORDER BY acquired_on DESC, id DESC",
            (r["matched_property_id"],))]
    return {
        "registration": r,
        "verification": {"status": r["verification_status"], "checks": checks},
        "fraud": {"score": r["risk_score"], "level": r["risk_level"],
                  "decision": r["fraud_status"], "findings": findings},
        "stages": stages,
        "ownership_history": history,
    }
