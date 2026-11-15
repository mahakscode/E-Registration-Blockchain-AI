"""Database helpers: connection, table definitions and small ID generators.

SQLite stores everything in one file (ereg.db) next to this script.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "ereg.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read columns by name: row["owner_name"]
    return conn


SCHEMA = """
-- The historical land records (synthetic). One row per property, holding the CURRENT owner.
CREATE TABLE IF NOT EXISTS properties (
    property_id         TEXT PRIMARY KEY,
    property_name       TEXT NOT NULL,
    khasra_no           TEXT NOT NULL,
    khata_no            TEXT NOT NULL,
    survey_no           TEXT NOT NULL,
    owner_name          TEXT NOT NULL,
    owner_id            TEXT NOT NULL,
    address             TEXT NOT NULL,
    state               TEXT NOT NULL,
    district            TEXT NOT NULL,
    tehsil              TEXT NOT NULL,
    area_sqm            REAL NOT NULL,
    property_type       TEXT NOT NULL,
    ownership_status    TEXT NOT NULL DEFAULT 'Clear',   -- Clear / Owner Deceased / Disputed
    previous_sale_price INTEGER NOT NULL,
    previous_owner_name TEXT,
    mutation_status     TEXT NOT NULL DEFAULT 'None',
    last_mutation_id    TEXT,
    last_mutation_at    TEXT
);

-- Every owner a property has ever had. Auto-mutation adds a row here and closes the old one.
CREATE TABLE IF NOT EXISTS ownership_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id     TEXT NOT NULL,
    owner_name      TEXT NOT NULL,
    owner_id        TEXT NOT NULL,
    acquired_on     TEXT NOT NULL,
    ceased_on       TEXT,                 -- NULL means "current owner"
    transfer_type   TEXT NOT NULL,        -- Original allotment / Sale / Inheritance / Gift
    sale_price      INTEGER,
    registration_id TEXT,
    mutation_id     TEXT
);

-- Every submission made through the website (successful or stopped).
CREATE TABLE IF NOT EXISTS registrations (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_id      TEXT UNIQUE,     -- only set when registration succeeded
    case_id              TEXT UNIQUE,     -- only set when the case is held for manual verification
    submitted_at         TEXT,
    property_id          TEXT,
    matched_property_id  TEXT,            -- the historical record that was matched (if any)
    property_name        TEXT,
    khasra_no            TEXT,
    khata_no             TEXT,
    survey_no            TEXT,
    address              TEXT,
    state                TEXT,
    district             TEXT,
    tehsil               TEXT,
    area                 REAL,
    unit                 TEXT,
    property_type        TEXT,
    land_category        TEXT,
    circle_rate          REAL,
    declared_price       REAL,
    seller_name          TEXT,
    seller_id            TEXT,
    seller_contact       TEXT,
    existing_ownership   TEXT,
    buyer_name           TEXT,
    buyer_id             TEXT,
    buyer_contact        TEXT,
    registration_date    TEXT,
    sale_deed_ref        TEXT,
    transaction_details  TEXT,
    verification_status  TEXT,            -- Verified / Mismatch / Not Found
    fraud_status         TEXT,            -- clear / warning / blocked
    risk_score           INTEGER,
    risk_level           TEXT,            -- Low / Medium / High
    registration_status  TEXT,            -- Registered / Manual Verification
    mutation_status      TEXT,            -- Completed / Not Performed
    mutation_id          TEXT,
    mutation_at          TEXT,
    previous_owner       TEXT,
    mutation_ms          INTEGER,
    checks_json          TEXT,
    findings_json        TEXT
);
"""

# Columns we fill when inserting a registration (the IDs are added right after the insert).
REG_COLUMNS = [
    "submitted_at", "property_id", "matched_property_id", "property_name", "khasra_no",
    "khata_no", "survey_no", "address", "state", "district", "tehsil", "area", "unit",
    "property_type", "land_category", "circle_rate", "declared_price", "seller_name",
    "seller_id", "seller_contact", "existing_ownership", "buyer_name", "buyer_id",
    "buyer_contact", "registration_date", "sale_deed_ref", "transaction_details",
    "verification_status", "fraud_status", "risk_score", "risk_level", "registration_status",
    "mutation_status", "mutation_at", "previous_owner", "checks_json", "findings_json",
]


def save_registration(conn, record):
    """Insert one registration row and return its numeric row id."""
    columns = ", ".join(REG_COLUMNS)
    marks = ", ".join("?" for _ in REG_COLUMNS)
    cur = conn.execute(
        f"INSERT INTO registrations ({columns}) VALUES ({marks})",
        [record.get(c) for c in REG_COLUMNS],
    )
    return cur.lastrowid


def make_registration_id(row_id, when):
    return f"REG-{when:%Y}-{row_id:06d}"


def make_case_id(row_id, when):
    return f"CASE-{when:%Y}-{row_id:06d}"


def make_mutation_id(row_id, when):
    return f"MUT-{when:%Y%m%d}-{row_id:06d}"
