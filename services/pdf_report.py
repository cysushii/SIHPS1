"""
PDF Report Generation for approved batches.

Generates an AICTE-style approval letter with:
- Header with institute details
- Programme-wise approved intake table
- Per-student summary table
- "DEMO" watermark
- Fictional signatory: "Shri P.K. Verma, Member Secretary (Demo)"
- QR code linking to the signed document verification endpoint

Uses fpdf2 (FPDF) for PDF generation and the existing doc_signer for RSA signing.
"""

import os
import io
import base64
import datetime
from fpdf import FPDF
from sqlalchemy.orm import Session
from models.models import Batch, StudentBatch, Student, InstituteProgram, VerificationToken

SIGNATORY_NAME = "Shri P.K. Verma"
SIGNATORY_TITLE = "Member Secretary (Demo)"
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")

os.makedirs(REPORT_DIR, exist_ok=True)


class _DemoPDF(FPDF):
    """FPDF subclass with DEMO watermark and standard header/footer."""

    def header(self):
        # Logo / Header bar
        self.set_fill_color(26, 58, 92)  # navy #1a3a5c
        self.rect(0, 0, 210, 18, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 13)
        self.set_xy(10, 4)
        self.cell(0, 10, "All India Council for Technical Education (AICTE)", ln=False)
        self.set_text_color(0, 0, 0)
        self.set_y(22)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(
            0, 10,
            "DEMO BUILD -- This document is generated for demonstration purposes only. "
            "No real AICTE data or student records are involved. | "
            f"Page {self.page_no()}",
            align="C",
        )

    def watermark(self):
        """Draw a light DEMO watermark across the page."""
        self.set_font("Helvetica", "B", 48)
        self.set_text_color(230, 230, 230)
        self.set_xy(10, 140)
        self.cell(190, 20, "DEMO -- NOT OFFICIAL", align="C")
        self.set_text_color(0, 0, 0)


def generate_batch_report(batch_id: int, db: Session) -> dict:
    """
    Generate a signed PDF report for an approved batch.

    Returns:
        {
            "pdf_path": str,          # path on disk
            "document": dict,         # certificate dict passed to sign_document
            "hash": str,
            "signature": str,
            "qr_code_base64": str,
        }
    """
    from security.doc_signer import sign_document  # local import avoids circular

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    institute = batch.institute
    institute_name = institute.name if institute else "Unknown Institution"
    state = institute.state if institute else ""
    aicte_code = institute.aicte_code if institute else ""

    # Programme intake table
    programs = db.query(InstituteProgram).filter(
        InstituteProgram.institute_id == batch.institute_id
    ).all()

    # Students in this batch + their verification status
    sb_links = db.query(StudentBatch).filter(StudentBatch.batch_id == batch_id).all()
    student_rows = []
    for link in sb_links:
        s = link.student
        vt = (
            db.query(VerificationToken)
            .filter(VerificationToken.student_id == s.id, VerificationToken.batch_id == batch_id)
            .first()
        )
        verify_status = vt.status if vt else "not_generated"
        student_rows.append({
            "name": s.name,
            "apaar_id": s.apaar_id,
            "program": s.program,
            "enrollment_year": s.enrollment_year,
            "verify_status": verify_status,
        })

    # ── Build PDF ─────────────────────────────────────────────────────────
    pdf = _DemoPDF()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    # Watermark before content
    pdf.watermark()

    # Reset position after watermark
    pdf.set_y(24)

    # F.No and date
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    issued_date = datetime.datetime.now().strftime("%d %B %Y")
    pdf.cell(0, 6, f"F.No. AICTE/DEMO/{aicte_code}/{batch.id}", ln=True)
    pdf.cell(0, 6, f"Date: {issued_date}", ln=True)
    pdf.ln(4)

    # Title
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(26, 58, 92)
    pdf.cell(0, 9, "EXTENSION OF APPROVAL -- STUDENT DATA VERIFICATION REPORT", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(13, 148, 136)
    pdf.cell(0, 7, f"Batch: {batch.name} | Status: APPROVED", align="C", ln=True)
    pdf.ln(4)

    # Institute details box
    pdf.set_fill_color(240, 248, 255)
    pdf.set_draw_color(26, 58, 92)
    pdf.rect(10, pdf.get_y(), 190, 28, "DF")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(26, 58, 92)
    pdf.set_xy(14, pdf.get_y() + 3)
    pdf.cell(55, 6, "Institution Name:", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, institute_name, ln=True)
    pdf.set_xy(14, pdf.get_y())
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(26, 58, 92)
    pdf.cell(55, 6, "AICTE Permanent ID:", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(55, 6, aicte_code, ln=False)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(26, 58, 92)
    pdf.cell(30, 6, "State:", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, state, ln=True)
    pdf.ln(6)

    # Programme Intake Table
    if programs:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(26, 58, 92)
        pdf.cell(0, 7, "APPROVED PROGRAMME INTAKE", ln=True)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(26, 58, 92)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(130, 7, "Programme", fill=True, border=1)
        pdf.cell(60, 7, "Approved Intake", fill=True, border=1, ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 0, 0)
        for i, p in enumerate(programs):
            fill = i % 2 == 0
            pdf.set_fill_color(248, 252, 255) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(130, 6, p.program, border=1, fill=True)
            pdf.cell(60, 6, str(p.approved_intake), border=1, fill=True, ln=True)
        pdf.ln(6)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 7, "No course-level intake data available (Multi-year Extended Approval).", ln=True)
        pdf.ln(4)

    # Student Table
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(26, 58, 92)
    pdf.cell(0, 7, f"STUDENT RECORDS IN THIS BATCH  ({len(student_rows)} students)", ln=True)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(26, 58, 92)
    pdf.set_text_color(255, 255, 255)
    col_widths = [55, 35, 50, 25, 25]
    headers = ["Name", "APAAR ID", "Programme", "Enrol. Year", "Verified"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 7, h, fill=True, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(0, 0, 0)
    for i, row in enumerate(student_rows):
        fill = i % 2 == 0
        pdf.set_fill_color(248, 252, 255) if fill else pdf.set_fill_color(255, 255, 255)
        status_label = {"verified": "Yes", "pending": "Pending", "unresponsive": "No resp.", "not_generated": "-"}.get(
            row["verify_status"], row["verify_status"]
        )
        pdf.cell(55, 6, row["name"][:28], border=1, fill=True)
        pdf.cell(35, 6, row["apaar_id"], border=1, fill=True)
        pdf.cell(50, 6, row["program"][:24], border=1, fill=True)
        pdf.cell(25, 6, str(row["enrollment_year"]), border=1, fill=True)
        pdf.cell(25, 6, status_label, border=1, fill=True, ln=True)

    pdf.ln(10)

    # Sign batch-level document
    signed = sign_document(
        student_id=f"batch_{batch_id}",
        apaar_id=f"BATCH-{batch_id}",
        name=institute_name,
        institute=institute_name,
        program=f"Batch: {batch.name}",
        issued_date=issued_date,
    )

    # QR code
    qr_bytes = base64.b64decode(signed["qr_code_base64"])
    qr_buffer = io.BytesIO(qr_bytes)
    qr_path = os.path.join(REPORT_DIR, f"qr_batch_{batch_id}.png")
    with open(qr_path, "wb") as f:
        f.write(qr_bytes)

    # Signatory section
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, "This report is digitally signed. Verify at the QR code or via the verification portal.", ln=True)
    pdf.ln(4)

    sig_y = pdf.get_y()
    # Embed QR
    try:
        pdf.image(qr_path, x=10, y=sig_y, w=32, h=32)
    except Exception:
        pass

    pdf.set_xy(50, sig_y + 4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(26, 58, 92)
    pdf.cell(0, 6, SIGNATORY_NAME, ln=True)
    pdf.set_x(50)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, SIGNATORY_TITLE, ln=True)
    pdf.set_x(50)
    pdf.cell(0, 6, f"Issued: {issued_date}", ln=True)
    pdf.set_x(50)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"Document Hash: {signed['hash'][:32]}...", ln=True)

    # Save PDF
    pdf_filename = f"batch_{batch_id}_report_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf_path = os.path.join(REPORT_DIR, pdf_filename)
    pdf.output(pdf_path)

    # Clean up temp QR file
    try:
        os.remove(qr_path)
    except Exception:
        pass

    return {
        "pdf_path": pdf_path,
        "document": signed["document"],
        "hash": signed["hash"],
        "signature": signed["signature"],
        "qr_code_base64": signed["qr_code_base64"],
        "verification_url": signed["verification_url"],
        "issued_date": issued_date,
    }

