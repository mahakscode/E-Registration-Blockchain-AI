"""Creates the SQLite database and fills it with SYNTHETIC historical land records.

Run:  python seed_data.py
(Running it again wipes the database and starts fresh - handy before a demo.)
"""
import json
import random
from datetime import datetime, timedelta

from database import DB_PATH, SCHEMA, get_conn, make_mutation_id, make_registration_id, save_registration
from verification import passing_checks

TOTAL_RECORDS = 150

FIRST_NAMES = ["Rajesh", "Amit", "Sunita", "Priya", "Vikram", "Neha", "Suresh", "Anita", "Manoj", "Kavita",
               "Deepak", "Pooja", "Rahul", "Meena", "Sanjay", "Ritu", "Arun", "Seema", "Vijay", "Geeta",
               "Naveen", "Shalini", "Mohit", "Anjali", "Harish", "Rekha", "Ashok", "Nisha"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Singh", "Yadav", "Mishra", "Jain", "Agarwal", "Kumar", "Chauhan",
              "Patel", "Joshi", "Tiwari", "Saxena", "Pandey", "Bansal", "Mehta", "Kapoor", "Malhotra", "Rawat"]
LOCATIONS = {
    "Delhi": {"South West Delhi": ["Vasant Vihar", "Kapashera"], "North West Delhi": ["Narela", "Alipur"]},
    "Uttar Pradesh": {"Lucknow": ["Sarojini Nagar", "Mohanlalganj"], "Gautam Buddh Nagar": ["Dadri", "Jewar"]},
    "Haryana": {"Gurugram": ["Badshahpur", "Sohna"], "Faridabad": ["Ballabgarh", "Badkhal"]},
    "Rajasthan": {"Jaipur": ["Sanganer", "Amer"], "Alwar": ["Behror", "Neemrana"]},
    "Maharashtra": {"Pune": ["Haveli", "Mulshi"], "Nashik": ["Igatpuri", "Sinnar"]},
}
LOCALITIES = ["Sector 12", "Shanti Nagar", "Gandhi Colony", "Rampur Road", "Green Park Extension",
              "Model Town", "Lakshmi Nagar", "Ashok Vihar", "Nehru Enclave", "Krishna Vihar"]
VILLAGES = ["Rampur", "Sultanpur", "Bhagwanpur", "Kheri", "Nangla", "Madanpur", "Gopalpur", "Shahpur"]

# Fixed records used by the demo scenarios (see demo.py)
FIXED_OWNERS = {1: ("Rajesh Sharma", "OWN100001"), 2: ("Priya Singh", "OWN100002"),
                3: ("Mahesh Yadav", "OWN100003"), 4: ("Suresh Mishra", "OWN100004"),
                5: ("Anita Jain", "OWN100005"), 6: ("Vikram Chauhan", "OWN100006")}
FIXED_TYPES = {1: "Residential", 2: "Residential", 3: "Agricultural", 4: "Residential",
               5: "Residential", 6: "Commercial"}
REGISTERED_BEFORE = [7, 8, 9, 10, 11]      # these already have one completed registration
CONFLICT_PAIRS = [(4, 5), (60, 61)]         # second record copies the first one's Khasra/Khata/Survey

CIRCLE_RATE_RANGE = {"Residential": (9000, 45000), "Commercial": (20000, 90000), "Agricultural": (600, 4500)}
AREA_RANGE = {"Residential": (60, 450), "Commercial": (30, 600), "Agricultural": (4000, 40000)}


def seed(total=TOTAL_RECORDS):
    if DB_PATH.exists():
        DB_PATH.unlink()
    rng = random.Random(42)  # fixed seed = same data every time
    now = datetime.now().replace(microsecond=0)
    conn = get_conn()
    conn.executescript(SCHEMA)
    counter = [100006]

    def new_person():
        counter[0] += 1
        return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}", f"OWN{counter[0]}"

    with conn:
        for i in range(1, total + 1):
            pid = f"PROP{1000 + i}"
            ptype = FIXED_TYPES.get(i) or rng.choices(["Residential", "Commercial", "Agricultural"], [50, 25, 25])[0]
            if i == 1:
                state, district, tehsil = "Delhi", "South West Delhi", "Vasant Vihar"
            else:
                state = rng.choice(list(LOCATIONS))
                district = rng.choice(list(LOCATIONS[state]))
                tehsil = rng.choice(LOCATIONS[state][district])

            locality, village, plot = rng.choice(LOCALITIES), rng.choice(VILLAGES), rng.randint(1, 240)
            if ptype == "Residential":
                address, name = f"Plot {plot}, {locality}, {tehsil}", f"{locality} Residential Plot {plot}"
            elif ptype == "Commercial":
                address, name = f"Shop {plot}, {locality} Market, {tehsil}", f"{locality} Commercial Shop {plot}"
            else:
                address, name = f"Khet {plot}, Village {village}, {tehsil}", f"{village} Agricultural Land {plot}"

            area = round(rng.uniform(*AREA_RANGE[ptype]), 1)
            circle_rate = rng.randint(*CIRCLE_RATE_RANGE[ptype])
            last_price = int(round(area * circle_rate * rng.uniform(1.05, 1.45), -3))

            # ---- ownership chain, oldest owner first, current owner last ----
            if i == 6:      # suspicious: sold three times in about 14 months, last time 25 days ago
                ages = [2200, 430, 215, 25]
            else:
                n_prev = 1 if i in REGISTERED_BEFORE else rng.choice([0, 1, 1, 2])
                ages = [130 + rng.randint(0, 170) if i in REGISTERED_BEFORE else rng.randint(400, 3000)]
                for _ in range(n_prev):
                    ages.insert(0, ages[0] + rng.randint(800, 2500))
            owners = [new_person() for _ in ages]
            if i in FIXED_OWNERS:
                owners[-1] = FIXED_OWNERS[i]

            types = ["Original allotment"] + [rng.choice(["Sale", "Sale", "Inheritance", "Gift"]) for _ in ages[1:]]
            if i in REGISTERED_BEFORE or i == 6:
                types = ["Original allotment"] + ["Sale"] * (len(ages) - 1)
            prices, p = [None] * len(ages), last_price
            for k in range(len(ages) - 1, 0, -1):
                prices[k] = p if types[k] == "Sale" else None
                p = int(round(p * rng.uniform(0.6, 0.85), -3))
            acquired = [now - timedelta(days=d) for d in ages]

            for k, (owner, owner_id) in enumerate(owners):
                ceased = acquired[k + 1].strftime("%Y-%m-%d") if k + 1 < len(owners) else None
                conn.execute(
                    "INSERT INTO ownership_history (property_id, owner_name, owner_id, acquired_on, ceased_on,"
                    " transfer_type, sale_price) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (pid, owner, owner_id, acquired[k].strftime("%Y-%m-%d"), ceased, types[k], prices[k]))

            status = "Clear"
            if i == 3:
                status = "Owner Deceased"
            elif i > 11 and all(i not in pair for pair in CONFLICT_PAIRS):
                roll = rng.random()
                status = "Owner Deceased" if roll < 0.04 else "Disputed" if roll < 0.07 else "Clear"

            conn.execute(
                "INSERT INTO properties (property_id, property_name, khasra_no, khata_no, survey_no, owner_name,"
                " owner_id, address, state, district, tehsil, area_sqm, property_type, ownership_status,"
                " previous_sale_price, previous_owner_name, mutation_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (pid, name, f"{244 + i}/{(i % 3) + 1}", f"KH-{3000 + i}", f"SVY-{500 + i}", owners[-1][0],
                 owners[-1][1], address, state, district, tehsil, area, ptype, status, last_price,
                 owners[-2][0] if len(owners) > 1 else None,
                 "Completed" if i in REGISTERED_BEFORE else "None"))

            # ---- a past registration (so the history page is not empty and "duplicate" can be demonstrated) ----
            if i in REGISTERED_BEFORE:
                when = acquired[-1]
                stamp = when.strftime("%Y-%m-%d %H:%M:%S")
                form = {
                    "property_id": pid, "property_name": name, "khasra_no": f"{244 + i}/{(i % 3) + 1}",
                    "khata_no": f"KH-{3000 + i}", "survey_no": f"SVY-{500 + i}", "address": address,
                    "state": state, "district": district, "tehsil": tehsil, "area": area, "unit": "sqm",
                    "property_type": ptype, "land_category": {"Residential": "Abadi", "Commercial": "CommercialPlot",
                                                              "Agricultural": "Irrigated"}[ptype],
                    "circle_rate": round(last_price / area / 1.25), "declared_price": last_price,
                    "seller_name": owners[-2][0], "seller_id": owners[-2][1], "seller_contact": f"98{rng.randint(10**7, 10**8 - 1)}",
                    "existing_ownership": "Purchased earlier through a registered sale deed",
                    "buyer_name": owners[-1][0], "buyer_id": owners[-1][1], "buyer_contact": f"97{rng.randint(10**7, 10**8 - 1)}",
                    "registration_date": when.strftime("%Y-%m-%d"), "sale_deed_ref": f"SD/{when:%Y}/{20000 + i}",
                    "transaction_details": "Sale by bank transfer (synthetic past record)",
                }
                form.update({
                    "submitted_at": stamp, "matched_property_id": pid, "verification_status": "Verified",
                    "fraud_status": "clear", "risk_score": 0, "risk_level": "Low",
                    "registration_status": "Registered", "mutation_status": "Completed", "mutation_at": stamp,
                    "previous_owner": owners[-2][0], "checks_json": json.dumps(passing_checks(form)),
                    "findings_json": "[]"})
                row_id = save_registration(conn, form)
                reg_id, mut_id = make_registration_id(row_id, when), make_mutation_id(row_id, when)
                conn.execute("UPDATE registrations SET registration_id = ?, mutation_id = ? WHERE id = ?",
                             (reg_id, mut_id, row_id))
                conn.execute("UPDATE ownership_history SET registration_id = ?, mutation_id = ?"
                             " WHERE property_id = ? AND ceased_on IS NULL", (reg_id, mut_id, pid))
                conn.execute("UPDATE properties SET last_mutation_id = ?, last_mutation_at = ? WHERE property_id = ?",
                             (mut_id, stamp, pid))

        # ---- conflicting records: two different owners claim the same Khasra / Khata / Survey ----
        for first, second in CONFLICT_PAIRS:
            a = conn.execute("SELECT * FROM properties WHERE property_id = ?", (f"PROP{1000 + first}",)).fetchone()
            conn.execute("UPDATE properties SET khasra_no = ?, khata_no = ?, survey_no = ?, state = ?, district = ?,"
                         " tehsil = ?, ownership_status = 'Clear' WHERE property_id = ?",
                         (a["khasra_no"], a["khata_no"], a["survey_no"], a["state"], a["district"], a["tehsil"],
                          f"PROP{1000 + second}"))
            conn.execute("UPDATE properties SET ownership_status = 'Clear' WHERE property_id = ?", (a["property_id"],))
    conn.close()
    print(f"Created {DB_PATH.name} with {total} synthetic property records.")


if __name__ == "__main__":
    seed()
