# APAAR ID Student Data Platform (SIH26263)

AICTE-approved institutional student verification, deduplication, trust-scoring, and tamper-evident auditing platform built with FastAPI, PostgreSQL/SQLite, and React (Vite + Tailwind CSS).

---

## 🚀 Quick Start (Running Both Servers)

### 1. Backend Server (FastAPI)
```bash
# From repository root:
$env:PYTHONPATH="."
python -m uvicorn main:app --reload --port 8000
```
- API Docs (Swagger): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/`

### 2. Frontend Application (React + Vite)
```bash
# In another terminal:
cd frontend
npm run dev
```
- Web Application: `http://localhost:5173/`

### 3. Seed Demo Data
To reset and seed the 5 sample AICTE institutions, 66 students, demo fraud cases, and pre-populated batches:
```bash
$env:PYTHONPATH="."
python data/seed_demo_data.py
```

### 4. Run Automated Test Suite (38 tests)
```bash
$env:PYTHONPATH="."
pytest tests -v
```

---

## 🎯 Demo Personas (1-Click Login on UI)
When opening `http://localhost:5173/login`, choose any preset:
1. **Institute #1 Admin** (`institute_admin`, Institute ID 1) — Regular course intake EOA institution (IIT Delhi)
2. **Institute #2 Admin** (`institute_admin`, Institute ID 2) — Autonomous Multi-Year Extended EOA institution (Velagapudi Siddhartha)
3. **AICTE Central Regulator** (`aicte_admin`) — National regulatory console for cross-institutional deduplication, trust index, and batch approval
4. **Public Verifier** (`/verify-document`) — Public RSA-2048 certificate validator with interactive single-character tamper detection

---

## 📦 What Was Built & Implemented

### New Backend Endpoints Added:
- `POST /batches` — Create submission batch
- `GET /batches` — List batches (filtered by institute or regulator)
- `GET /batches/{batch_id}` — Batch details with attached student records
- `POST /batches/{batch_id}/students` — Attach student IDs to batch
- `POST /batches/{batch_id}/push` — Push batch to AICTE (`draft` → `pushed`)
- `POST /batches/{batch_id}/verification/generate` — Generate per-student `VerificationToken` links
- `POST /batches/{batch_id}/verification/send-emails` — Dispatch verification emails (or mock/dry-run)
- `GET /batches/{batch_id}/verification/status` — Per-student response counts and unverified metrics
- `POST /batches/{batch_id}/verification/mark-unresponsive` — Demo helper: marks pending tokens unresponsive
- `POST /batches/{batch_id}/verification/{student_id}/resend` — Resend token to student
- `GET /verify/token/{token}` — Public: lookup masked student details (`2401****0001`)
- `POST /verify/token/{token}/confirm` — Public: student confirms record is correct
- `POST /verify/token/{token}/correct` — Public: student submits correction requests
- `POST /aicte/batches/{batch_id}/approve` — AICTE approves batch, generates official-style PDF & signs it
- `POST /aicte/batches/{batch_id}/reject` — AICTE rejects batch with regulatory feedback
- `GET /batches/{batch_id}/report` — Download cryptographically signed AICTE EOA PDF
- `POST /batches/{batch_id}/notify` — Send completion emails to approved students
- `GET /emails/log` — Email audit logs
- `GET /emails/config` — SMTP & email allowlist status

### Real-World Realities & Differentiators Handled:
1. **7-Signal Trust Index** (`engines/trust_score.py`):
   - Capacity mismatch (22%), Missing fields (18%), Correction frequency (13%), Duplicate rate (13%), Geographic mismatch (13%), Lifecycle implausibility (9%), Unverified student rate (12%).
2. **Autonomous Multi-Year Extended EOA**:
   - Handles institutes without course rows gracefully (`no_course_data_available`), never crashing or displaying misleading 0-capacity charts.
3. **Honeytoken Canaries** (`security/honeytokens.py`):
   - Reserved APAAR IDs that raise high-priority critical alerts if uploaded.
4. **Tamper-Evident Hash Chain & External Anchoring** (`security/hash_chain.py` + `security/anchoring.py`):
   - Append-only blockchain-style SHA-256 chain; every 20 events anchors to `/data/checkpoints.log` to prove DB rewrites.
5. **Signed PDF Report Generator** (`services/pdf_report.py`):
   - Produces official AICTE approval letters with embedded scannable QR and RSA-2048 digital signatures, signed by fictional signatory `Shri P.K. Verma, Member Secretary (Demo)` with a DEMO watermark.

---

## 🔒 Mocked Items (Hackathon Safe)
- **Email Delivery**: Operates in dry-run mode unless `SMTP_HOST` is supplied in environment variables. All outgoing emails are logged to `EmailLog` table and visible via `/emails/log`. The `EMAIL_ALLOWLIST` prevents emailing real individuals.
- **AICTE Signatures & Watermarks**: Signed by fictional demo authority with clear DEMO markings.
