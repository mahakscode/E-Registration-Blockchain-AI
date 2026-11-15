# Property E-Registration Portal (academic prototype)

B.Tech CSE (Cyber Security) project: **Blockchain-Based Secure E-Registration System for Real Estate in India**.

This version is the proposed e-registration website. A user submits one form and the system
**verifies** it against historical land records, **screens for fraud**, **registers** the property and
**auto-mutates** the owner record immediately in SQLite.

> **Disclaimer:** all historical records are synthetic and mutation is simulated for academic
> demonstration. This is not a government-approved legal registration or mutation.
> Blockchain, smart contracts and Hyperledger Besu are future scope and are not implemented.

## Tech stack
| Part | Technology |
|------|-----------|
| Website | React (Vite), English / हिंदी selector |
| Backend APIs | Python FastAPI |
| Database | SQLite (`backend/ereg.db`, created automatically) |
| Synthetic data | Python (`backend/seed_data.py`) |

## Run it

You need Python 3.10+ and Node.js 18+. Open two terminals.

**Terminal 1: backend**
```bash
cd backend
pip install -r requirements.txt
python seed_data.py            # optional: creates 150 synthetic records (also runs automatically on first start)
uvicorn main:app --reload --port 8000
```

**Terminal 2: website**
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. (API docs are at http://127.0.0.1:8000/docs.)

To reset everything before a presentation, stop the backend and run `python seed_data.py` again.

## Project structure
```
backend/
  database.py      table definitions + ID generators
  seed_data.py     generates 150 synthetic property records (+ ownership history, 5 past registrations)
  verification.py  compares the form with the historical record
  fraud.py         rule-based fraud screening, risk score 0-100
  service.py       the workflow: verify -> fraud -> register -> auto-mutate (one DB transaction)
  demo.py          builds one-click demo scenarios from the real database
  main.py          FastAPI endpoints
frontend/src/
  App.jsx, i18n.js (all English + Hindi text), api.js
  pages/           Dashboard, NewRegistration, History (with detail view)
  components/      ResultPanel (verification + fraud + confirmation), Pipeline
```

## API
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/registrations` | Verify, fraud-screen, register and mutate (only if everything passes) |
| GET | `/api/registrations` | Registration history |
| GET | `/api/registrations/{id}` | One registration/case with checks, fraud result and ownership history |
| GET | `/api/stats` | Dashboard numbers |
| GET | `/api/demo-cases` | Demo scenarios built from real records |

## How the workflow decides
1. **Verification** compares Property ID, Khasra, Khata, Survey, state/district/tehsil/address, area (2% tolerance after unit conversion), property type, seller name, seller ID and ownership status with the record. Result: **Verified**, **Details do not match** (with the exact fields), or **Record not found**. The real owner's name and ID are masked in messages shown to the submitter.
2. **Fraud rules** (points in brackets):
   - Seller not the recorded owner (50) or seller ID mismatch (45)
   - Wrong Property ID (45) or wrong Khasra (40)
   - Duplicate sale deed or duplicate registration (60)
   - Deceased owner (60), disputed record (50)
   - Conflicting records with the same Khasra/Khata/Survey (45)
   - Buyer and seller are the same (50)
   - Quick resale within 90 days (20), 3+ ownership changes in 24 months (20)
   - Price below half of circle value (45) or below circle value (20); price under 40% (40) or 70% (20) of last sale price
   - Risk score = sum of points (max 100). Any High-severity rule forces a score of at least 60. **0-29 Low, 30-59 Medium, 60+ High.**
3. **Decision:** registration proceeds only if verification is *Verified* and the risk level is not *High*. Otherwise nothing is registered or mutated, and the submission is saved with a **Case ID** marked for manual verification. Medium and Low findings are shown as warnings but do not block.
4. **Auto-mutation** (same database transaction as the registration): the old owner's period in `ownership_history` is closed, the buyer is added as the current owner, and the `properties` row gets the new owner, previous owner, Mutation ID, status *Completed* and timestamp. The previous owners stay in the history, visible from the Registration History detail page.

## Demo scenarios
The **Fill with demo data** menu on the registration page fills the form from real database records. The results come from the real code, nothing is pre-set.

| Scenario | Expected result |
|----------|-----------------|
| Valid sale (PROP1001, Rajesh Sharma sells to Amit Verma) | Verified, risk Low, **registered and mutated** |
| Frequent recent transfers (PROP1006) | Registered with a Medium-risk warning |
| Seller is not the recorded owner | Mismatch, High risk, held for manual verification |
| Wrong Khasra / wrong Property ID | Mismatch, High risk, held |
| Recorded owner is deceased | Held |
| Price far below circle rate | Verified but High risk, held |
| Conflicting historical records | Verified but High risk, held |
| Duplicate registration | Held |
| Property not in records | Record Not Found, held |

After a valid sale, run it again to see the next sale on the same property (the new owner becomes the seller) and watch the ownership history grow. A repeat sale within 90 days correctly raises a quick-resale warning.

## Switching language
Use **English / हिंदी** in the header. All labels, buttons, verification messages, fraud reasons, confirmations and mutation messages switch language. Names, IDs and addresses that you type are never translated.

## Future scope
Anchoring registration and mutation records on a blockchain (Hyperledger Besu) with smart contracts for tamper-proof ownership history.
