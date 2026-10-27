# SIH26263 — Live Hackathon Demo Walkthrough & Cheat Sheet

This document contains everything you need to showcase the platform during evaluation, including demo credentials, step-by-step instructions, and pre-made sample files.

---

## 🌐 Live Deployments
- **Frontend (Vercel)**: Your deployed Vercel URL
- **Backend (Render API)**: `https://sihps1-llq1.onrender.com`
- **Interactive Swagger Docs**: `https://sihps1-llq1.onrender.com/docs`
- **Local Dev Server**: `http://127.0.0.1:5173` (Frontend) & `http://127.0.0.1:8000` (Backend)

---

## 🏛️ 1. Registered Institutions (Dropdown Options)

When logging in as an **Institute Admin**, you can select any of the following colleges directly from the dropdown:

| Institute ID | Institution Name | State | AICTE Code | Approval Type |
|---|---|---|---|---|
| **#1** | Indian Institute of Technology Bombay | Maharashtra | `1-1001` | Standard Course Intake |
| **#2** | Vellore Institute of Technology | Tamil Nadu | `1-1005` | Standard Course Intake |
| **#3** | SRM Institute of Science and Technology | Tamil Nadu | `1-1006` | Standard Course Intake |
| **#4** | College of Engineering Pune | Maharashtra | `1-1008` | Standard Course Intake |
| **#5** | Delhi Technological University | Delhi | `1-1009` | Standard Course Intake |

---

## 📁 2. Sample Files for Upload Demo

Two ready-to-use CSV files are located in the `data/` folder:

### A. Clean / Valid Student Roster
**File**: `data/sample_students_valid.csv`
- Contains 5 students with valid 12-digit APAAR IDs, matched geographic states, and plausible timelines.
- **Demo effect**: All 5 records are verified and inserted cleanly with `✓ 5 Inserted`.

### B. Fraud & Anomaly Test File
**File**: `data/sample_students_anomalies.csv`
- Demonstrates the platform's multi-layered forensic defenses:
  1. `111111111111` $\rightarrow$ **Format Rejection** (identical digits pattern).
  2. `240101000101` $\rightarrow$ **Dual-Enrollment Duplicate Flag** (same APAAR at another institution).
  3. `249999000001` $\rightarrow$ **CRITICAL HONEYTOKEN CANARY HIT** (detects data theft / DB breach).
  4. `153301000001` $\rightarrow$ **Lifecycle Implausibility Flag** (unreasonable schooling-to-college gap).

---

## 🎬 3. Complete Step-by-Step Demo Flow

Follow this exact flow during your pitch or evaluation:

### Step 1: College Side (Institute Portal)
1. Go to the login screen (`/login`).
2. Select **Institute Admin**.
3. In the dropdown, pick **#1 — Indian Institute of Technology Bombay**.
4. Click **Sign In**.
5. **Upload Student Data**:
   - In the *Upload Student Roster* card, choose `data/sample_students_valid.csv`.
   - Click **Ingest & Validate Roster**.
   - Notice the green badge indicating verified student records.
6. **Create a Submission Batch**:
   - In *Create Submission Batch*, type `2024 Final Year EOA Batch` $\rightarrow$ click **Initialize New Batch**.
   - Click on your new batch in the left panel.
7. **Generate Self-Verification Links**:
   - Click **Generate Self-Verify Links**.
   - Each student in the table now has an interactive `Open Link` button.
8. **Push to AICTE**:
   - Click **Push to AICTE**. The batch status changes from `draft` to `pushed`.

---

### Step 2: Student Side (Self-Verification Link)
1. In the batch table, click **Open Link** next to any student (or open `/verify/<token>`).
2. Point out that the APAAR ID is **cryptographically masked** (e.g., `2401****0101`) for student privacy.
3. Click **"Yes, My Details Are Correct"**.
4. Show that the confirmation is written directly to the append-only audit trail.
5. *(Optional)* Click "No, Request a Correction" to show that student disputes raise review flags for the institution.

---

### Step 3: Government Regulator Side (AICTE Portal)
1. Return to `/login` and select **AICTE Admin** (or click the quick 1-Click persona).
2. **Tab 1: Overview & Trust Scores**:
   - Show the dynamic **0–100 Institutional Trust Score** chart computed across 7 weighted signals.
   - Show how over-capacity admissions or duplicate enrollments penalize an institute's score.
3. **Tab 2: Batch Approvals**:
   - View the batch submitted by the college in Step 1.
   - Click **Approve & Sign EOA**.
   - The platform digitally signs the batch using RSA-2048 and produces an official AICTE Extension of Approval PDF with a QR code and fictional signatory `Shri P.K. Verma, Member Secretary (Demo)`.
4. **Tab 3: Cross-Institute Deduplication**:
   - Show how the rapid-fuzz and exact APAAR algorithms detect students enrolled in multiple institutions simultaneously.
5. **Tab 4: Security & Hash Chain**:
   - Show the **Honeytoken Canary** intrusion detection monitor.
   - Click **Trigger Anchor** to show that audit records are anchored to an external log (`checkpoints.log`), preventing even system admins from rewriting history.

---

### Step 4: Public RSA Certificate Verifier (Interactive Tamper Test)
1. Navigate to `/verify-document` from the top navigation bar.
2. Enter APAAR ID: `210101000001` and click **Lookup & Sign**.
3. Click **Verify RSA Signature** $\rightarrow$ shows **CERTIFICATE AUTHENTIC & UNTAMPERED** (green).
4. Change **any single character** in the student's name or degree program in the form.
5. Click **Verify RSA Signature** again $\rightarrow$ immediately shows **TAMPER DETECTED / INVALID SIGNATURE** (red).
6. Explain to the judges: *Even a single-byte alteration invalidates the SHA-256 digest and breaks the RSA-2048 mathematical signature.*
