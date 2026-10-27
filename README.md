# APAAR ID Student Data Verification Platform (SIH26263)

A prototype platform designed for official regulatory review, cryptographic auditability, and real student self-verification of APAAR (Automated Permanent Academic Account Registry) ID student rosters.

> **Notice**: Prototype built for SIH26263. Not an official Government of India service.

---

## Key Features

1. **Deterministic Verification Engine (SSE Streamed)**:
   - 10-check validation pipeline executed in real-time against authentic uploaded roster and AICTE reference datasets.
   - Per-student validation: APAAR ID format (exactly 12 digits), Honeytoken canary detection, cross-institution duplicate enrollment, fuzzy name + DOB matching, student confirmation state, geographic/lifecycle plausibility, field consistency.
   - Batch-level checks: Approved intake capacity comparison against official AICTE Extension of Approval data, closed courses check.
   - Live streaming execution via Server-Sent Events (SSE).
   - Approval gate blocking batch approval until all flagged records have reviewer notes.

2. **Real Email & Student Self-Verification**:
   - Outbound email dispatch via SMTP (STARTTLS) or HTTPS Email API (Resend / Brevo).
   - Cryptographically secured single-use verification tokens (32 random bytes, SHA-256 hashed in database).
   - Strict student privacy: confirmation tokens and verification links are never exposed to institute or AICTE staff.
   - Discrepancy reporting / correction workflow with institute admin accept/reject.
   - `TEST_EMAIL_REDIRECT` support for live testing without disturbing real recipients.

3. **Tamper-Evident Cryptographic Ledger**:
   - Every action (batch creation, push, token generation, review decisions, EoA approval) is cryptographically linked in a SHA-256 hash-chain audit log.
   - External anchor checkpointing prevents post-hoc database alterations.
   - Digitally signed Extension of Approval (EoA) documents with RSA-SHA256 signatures, verifiable via public key endpoint.

---

## Setup & CLI Commands

### 1. Database Initialization & Reference Data Loading

The database contains **zero mock or dummy data**. All reference datasets are loaded via explicit CLI commands:

```bash
# 1. Drop and recreate all database tables, seed genesis block, initialize honeytokens
python cli.py reset-db

# 2. Ingest authentic AICTE approval data (institutes, courses, closures)
python cli.py load-reference-data
```

### 2. User Account Creation

Find your institution ID using:
```bash
python cli.py list-institutes
```

Accounts are provisioned securely via CLI or through the AICTE Admin "Onboard Institute" portal:

```bash
# Create an AICTE Regulatory Admin:
python cli.py create-user --email admin@example.com --password "<STRONG_PASSWORD>" --role aicte_admin --name "AICTE Administrator"

# Create an Institution Administrator:
python cli.py create-user --email principal@example.com --password "<STRONG_PASSWORD>" --role institute_admin --institute-id 1 --name "Institute Admin"
```

### 3. Running Backend & Frontend

```bash
# Start FastAPI backend (port 8000)
python -m uvicorn main:app --reload --port 8000

# Start Frontend (Vite)
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|---|---|
| `APP_BASE_URL` | Public frontend URL used to build student verification links in emails |
| `MAIL_FROM_NAME` | Display sender name in verification emails (e.g. `Student Data Platform Verification`) |
| `SMTP_HOST` | Outbound SMTP host (e.g., `smtp.gmail.com`) |
| `SMTP_PORT` | Outbound SMTP port (`587`) |
| `SMTP_USER` | SMTP username / email address |
| `SMTP_PASSWORD` | SMTP password / App Password |
| `MAIL_FROM` | Sender email address |
| `RESEND_API_KEY` | (Alternative) Resend HTTPS API key |
| `BREVO_API_KEY` | (Alternative) Brevo HTTPS API key |
| `TEST_EMAIL_REDIRECT` | Optional: Redirect all outgoing emails to a safe testing inbox |
| `TOKEN_EXPIRY_DAYS` | Verification link expiration (default: 7 days) |
| `SECRET_KEY` | JWT signature key |
