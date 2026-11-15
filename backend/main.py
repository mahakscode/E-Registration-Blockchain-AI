"""FastAPI backend.  Start it with:  uvicorn main:app --reload --port 8000"""
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from database import DB_PATH, get_conn
from demo import build_demo_cases
from seed_data import seed
from service import build_response, process_registration

app = FastAPI(title="Property E-Registration (academic demo)")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def make_sure_database_exists():
    if not DB_PATH.exists():
        seed()


class RegistrationIn(BaseModel):
    """The registration form. FastAPI rejects bad input automatically (HTTP 422)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    property_id: str = Field(min_length=1, max_length=40)
    property_name: str = Field(min_length=1, max_length=200)
    khasra_no: str = Field(min_length=1, max_length=40)
    khata_no: str = Field(min_length=1, max_length=40)
    survey_no: str = Field(min_length=1, max_length=40)
    address: str = Field(min_length=1, max_length=300)
    state: str = Field(min_length=1, max_length=80)
    district: str = Field(min_length=1, max_length=80)
    tehsil: str = Field(min_length=1, max_length=80)
    area: float = Field(gt=0)
    unit: Literal["sqm", "sqft", "acre", "hectare"]
    property_type: Literal["Residential", "Commercial", "Agricultural"]
    land_category: Literal["Abadi", "Irrigated", "Unirrigated", "NonAgricultural", "CommercialPlot"]
    circle_rate: float = Field(gt=0)
    declared_price: float = Field(gt=0)
    seller_name: str = Field(min_length=1, max_length=120)
    seller_id: str = Field(min_length=1, max_length=40)
    seller_contact: str = Field(pattern=r"^[6-9]\d{9}$")
    existing_ownership: str = Field(min_length=1, max_length=500)
    buyer_name: str = Field(min_length=1, max_length=120)
    buyer_id: str = Field(min_length=1, max_length=40)
    buyer_contact: str = Field(pattern=r"^[6-9]\d{9}$")
    registration_date: date
    sale_deed_ref: str = Field(min_length=1, max_length=60)
    transaction_details: str = Field(min_length=1, max_length=500)

    @field_validator("registration_date")
    @classmethod
    def not_in_future(cls, value):
        if value > date.today():
            raise ValueError("Registration date cannot be in the future")
        return value


@app.get("/api/stats")
def stats():
    conn = get_conn()
    try:
        one = lambda sql: conn.execute(sql).fetchone()[0]
        average = one("SELECT AVG(mutation_ms) FROM registrations WHERE mutation_ms IS NOT NULL")
        return {
            "records": one("SELECT COUNT(*) FROM properties"),
            "registered": one("SELECT COUNT(*) FROM registrations WHERE registration_status = 'Registered'"),
            "held": one("SELECT COUNT(*) FROM registrations WHERE registration_status = 'Manual Verification'"),
            "avg_mutation_ms": round(average) if average is not None else None,
        }
    finally:
        conn.close()


@app.get("/api/demo-cases")
def demo_cases():
    conn = get_conn()
    try:
        return build_demo_cases(conn)
    finally:
        conn.close()


@app.post("/api/registrations")
def create_registration(data: RegistrationIn):
    """Verify -> fraud screening -> register -> auto-mutate (only if everything passes)."""
    form = data.model_dump()
    form["registration_date"] = form["registration_date"].isoformat()
    conn = get_conn()
    try:
        row_id = process_registration(conn, form)
        ref = conn.execute("SELECT COALESCE(registration_id, case_id) FROM registrations WHERE id = ?",
                           (row_id,)).fetchone()[0]
        return build_response(conn, ref)
    finally:
        conn.close()


@app.get("/api/registrations")
def list_registrations(limit: int = 200):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT registration_id, case_id, property_id, property_name, buyer_name, seller_name,"
            " registration_date, submitted_at, verification_status, mutation_status, registration_status, risk_level"
            " FROM registrations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/registrations/{ref}")
def get_registration(ref: str):
    conn = get_conn()
    try:
        result = build_response(conn, ref)
        if result is None:
            raise HTTPException(status_code=404, detail="Registration not found")
        return result
    finally:
        conn.close()
