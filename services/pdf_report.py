"""
AICTE Extension of Approval (EoA) official-style verification report generation.
Signed with RSA-2048 and tamper-evident QR code.
Clearly marked as a prototype document with fictional signatory.
"""
import os
import io
import base64
import datetime
from fpdf import FPDF
from sqlalchemy.orm import Session
from models.models import Batch, StudentBatch, Student, InstituteProgram, VerificationToken
from services.formatters import format_title_case

SIGNATORY_NAME = "Dr. R.K. Srivastav"
SIGNATORY_TITLE = "Adviser, Approval Bureau (Demo Authority)"
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

class EoAPDF(FPDF):
    def header(self):
        # Teal utility header bar
        self.set_fill_color(27, 117, 107) # #1b756b
        self.rect(0, 0, 210, 16, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 11)
        self.set_xy(12, 3)
        self.cell(0, 10, "All India Council for Technical Education (Approval Bureau)", ln=False)
        self.set_text_color(0, 0, 0)
        self.set_y(22)

    def footer(self):
        self.set_y(-18)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0, 10,
            "Prototype built for SIH26263. Not an official Government of India service.  |  "
            f"Page {self.page_no()}",
            align="C",
        )

    def watermark(self):
        self.set_font("Helvetica", "B", 42)
        self.set_text_color(240, 240, 240)
        self.set_xy(10, 140)
        self.cell(190, 20, "PROTOTYPE -- SIH26263", align="C")
        self.set_text_color(0, 0, 0)

def generate_batch_report(batch_id: int, db: Session) -> dict:
    from security.doc_signer import sign_document

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    inst = batch.institute
    inst_name = format_title_case(inst.name) if inst else "Educational Institution"
    state = inst.state or "State"
    aicte_code = inst.aicte_code or "1-XXXX"

    programs = db.query(InstituteProgram).filter(InstituteProgram.institute_id == batch.institute_id).all()
    sb_links = db.query(StudentBatch).filter(StudentBatch.batch_id == batch_id).all()

    pdf = EoAPDF()
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()
    pdf.watermark()

    pdf.set_y(24)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    issued_date = datetime.datetime.now().strftime("%d %B %Y")
    pdf.cell(0, 5, f"F.No. Western/1-{aicte_code}/2026/EoA-Verification", ln=True)
    pdf.cell(0, 5, f"Application Id: 1-{batch.id}-2026  |  Date: {issued_date}", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(27, 117, 107)
    pdf.cell(0, 8, "EXTENSION OF APPROVAL -- STUDENT DATA VERIFICATION REPORT", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(39, 39, 39)
    pdf.cell(0, 6, f"Batch: {batch.name}  --  Regulatory Status: APPROVED", align="C", ln=True)
    pdf.ln(3)

    # Institution Details Box
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(10, pdf.get_y(), 190, 24, "DF")
    pdf.set_xy(14, pdf.get_y() + 2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(45, 5, "Permanent Id / AICTE Code:", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(50, 5, aicte_code, ln=False)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(25, 5, "State:", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, state, ln=True)

    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(45, 5, "Institution Name:", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, inst_name[:65], ln=True)
    pdf.ln(5)

    # Approved Intake Table
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(27, 117, 107)
    pdf.cell(0, 6, "APPROVED PROGRAMME INTAKE", ln=True)

    if programs:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(27, 117, 107)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(140, 6, "Programme / Course", fill=True, border=1)
        pdf.cell(50, 6, "Approved Intake", fill=True, border=1, ln=True)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(0, 0, 0)
        for i, p in enumerate(programs):
            fill = i % 2 == 0
            pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(140, 5, p.program[:50], border=1, fill=True)
            pdf.cell(50, 5, str(p.approved_intake), border=1, fill=True, ln=True)
        pdf.ln(4)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, "Autonomous / Deemed status on record (No course-level limits).", ln=True)
        pdf.ln(3)

    # Approved Student Records Summary
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(27, 117, 107)
    pdf.cell(0, 6, f"ENROLLED & VERIFIED STUDENT ROSTER ({len(sb_links)} Records)", ln=True)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(27, 117, 107)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(60, 6, "Student Name", fill=True, border=1)
    pdf.cell(35, 6, "Masked APAAR ID", fill=True, border=1)
    pdf.cell(65, 6, "Programme", fill=True, border=1)
    pdf.cell(30, 6, "Enrolment Year", fill=True, border=1, ln=True)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(0, 0, 0)
    for i, link in enumerate(sb_links):
        s = link.student
        fill = i % 2 == 0
        pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
        masked_id = f"********{s.apaar_id[-4:]}" if len(s.apaar_id) >= 4 else s.apaar_id
        pdf.cell(60, 5, s.name[:32], border=1, fill=True)
        pdf.cell(35, 5, masked_id, border=1, fill=True)
        pdf.cell(65, 5, s.program[:32], border=1, fill=True)
        pdf.cell(30, 5, str(s.enrollment_year), border=1, fill=True, ln=True)

    pdf.ln(8)

    # Cryptographic RSA Signing
    signed = sign_document(
        student_id=f"batch_{batch_id}",
        apaar_id=f"BATCH-{batch_id}",
        name=inst_name,
        institute=inst_name,
        program=f"Batch: {batch.name}",
        issued_date=issued_date,
    )

    qr_bytes = base64.b64decode(signed["qr_code_base64"])
    qr_path = os.path.join(REPORT_DIR, f"temp_qr_{batch_id}.png")
    with open(qr_path, "wb") as f:
        f.write(qr_bytes)

    sig_y = pdf.get_y()
    try:
        pdf.image(qr_path, x=12, y=sig_y, w=28, h=28)
    except Exception:
        pass

    pdf.set_xy(45, sig_y + 2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(27, 117, 107)
    pdf.cell(0, 5, SIGNATORY_NAME, ln=True)
    pdf.set_x(45)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 4, SIGNATORY_TITLE, ln=True)
    pdf.set_x(45)
    pdf.cell(0, 4, f"Digitally Signed on: {issued_date}", ln=True)
    pdf.set_x(45)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 4, f"RSA-2048 SHA-256 Digest: {signed['hash'][:42]}...", ln=True)

    pdf_filename = f"EoA_Batch_{batch_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf_path = os.path.join(REPORT_DIR, pdf_filename)
    pdf.output(pdf_path)

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
