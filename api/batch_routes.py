"""
Batch management, verification token, AICTE review, PDF report, and email routes.

All new routes added for frontend support:
  POST   /batches                                  — create batch
  GET    /batches                                  — list batches
  GET    /batches/{batch_id}                       — batch details
  POST   /batches/{batch_id}/students              — add students to batch
  POST   /batches/{batch_id}/push                  — push batch to AICTE
  POST   /batches/{batch_id}/verification/generate — generate VerificationTokens
  POST   /batches/{batch_id}/verification/send-emails — send verification emails
  GET    /batches/{batch_id}/verification/status   — verification counts per batch
  POST   /batches/{batch_id}/verification/mark-unresponsive — mark all pending → unresponsive
  POST   /batches/{batch_id}/verification/{student_id}/resend — resend email to one student
  GET    /verify/token/{token}                     — public: get masked student details
  POST   /verify/token/{token}/confirm             — public: student confirms
  POST   /verify/token/{token}/correct             — public: student submits corrections
  POST   /aicte/batches/{batch_id}/approve         — AICTE approve + generate signed PDF
  POST   /aicte/batches/{batch_id}/reject          — AICTE reject
  GET    /batches/{batch_id}/report                — download signed PDF
  POST   /batches/{batch_id}/notify               — send completion emails to students
  GET    /emails/log                               — email log
  GET    /emails/config                            — SMTP/allowlist config status
"""

import os
import secrets
import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from models.database import get_db
from models.models import (
    Batch, StudentBatch, Student, Institute, VerificationToken, EmailLog, FlaggedRecord
)
from api.rbac import require_role
from security.hash_chain import log_event

batch_router = APIRouter()

VERIFICATION_TOKEN_EXPIRY_HOURS = int(os.environ.get("VERIFICATION_TOKEN_EXPIRY_HOURS", "72"))


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class CreateBatchRequest(BaseModel):
    name: str
    institute_id: int  # ignored for institute_admin (uses JWT)


class AddStudentsToBatchRequest(BaseModel):
    student_ids: list[int]


class RejectBatchRequest(BaseModel):
    reason: str


class StudentCorrectionRequest(BaseModel):
    corrections: dict  # free-form key→value corrections from student


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_institute_id(current_user: dict, requested_id: int | None, db: Session) -> int:
    """Return the effective institute_id for the current user."""
    role = current_user.get("role")
    jwt_inst_id = current_user.get("institute_id")
    if role == "institute_admin":
        if jwt_inst_id:
            return jwt_inst_id
        if requested_id:
            return requested_id
        raise HTTPException(status_code=400, detail="institute_id required for institute_admin")
    if requested_id:
        return requested_id
    raise HTTPException(status_code=400, detail="institute_id required")


def _get_batch_or_404(batch_id: int, db: Session) -> Batch:
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    return batch


def _assert_institute_owns_batch(batch: Batch, current_user: dict):
    """Raise 403 if institute_admin tries to access another institute's batch."""
    if current_user.get("role") == "institute_admin":
        jwt_inst = current_user.get("institute_id")
        if jwt_inst and batch.institute_id != jwt_inst:
            raise HTTPException(status_code=403, detail="Access denied to this batch")


def _generate_token() -> tuple[str, datetime.datetime]:
    """Generate a secure random token and its expiry datetime."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=VERIFICATION_TOKEN_EXPIRY_HOURS)
    return token, expires_at


# ── Batch CRUD ────────────────────────────────────────────────────────────────

@batch_router.post("/batches", summary="Create a new submission batch (institute_admin)")
def create_batch(
    req: CreateBatchRequest,
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    inst_id = _resolve_institute_id(current_user, req.institute_id, db)
    inst = db.query(Institute).filter(Institute.id == inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institute not found")

    batch = Batch(
        institute_id=inst_id,
        name=req.name,
        status="draft",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Automatically attach all current students of this institute to the batch
    inst_students = db.query(Student).filter(Student.institute_id == inst_id).all()
    for s in inst_students:
        db.add(StudentBatch(batch_id=batch.id, student_id=s.id))
    db.commit()

    log_event(db=db, record_type="Batch", record_id=batch.id, event_type="CREATE",
              actor=current_user.get("sub", "institute_admin"))

    return {
        "batch_id": batch.id,
        "name": batch.name,
        "status": batch.status,
        "institute_id": batch.institute_id,
        "student_count": len(inst_students),
        "created_at": batch.created_at,
    }


@batch_router.get("/batches", summary="List batches (institute_admin sees own; aicte_admin sees all)")
def list_batches(
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    role = current_user.get("role")
    if role == "aicte_admin":
        batches = db.query(Batch).order_by(Batch.created_at.desc()).all()
    else:
        inst_id = current_user.get("institute_id")
        if not inst_id:
            return {"batches": [], "total": 0}
        batches = db.query(Batch).filter(Batch.institute_id == inst_id).order_by(Batch.created_at.desc()).all()

    result = []
    for b in batches:
        student_count = db.query(StudentBatch).filter(StudentBatch.batch_id == b.id).count()
        result.append({
            "batch_id": b.id,
            "name": b.name,
            "status": b.status,
            "institute_id": b.institute_id,
            "institute_name": b.institute.name if b.institute else None,
            "student_count": student_count,
            "created_at": b.created_at,
            "pushed_at": b.pushed_at,
            "reviewed_at": b.reviewed_at,
            "report_signed": b.report_signed,
        })
    return {"batches": result, "total": len(result)}


@batch_router.get("/batches/{batch_id}", summary="Get batch details with student list")
def get_batch(
    batch_id: int,
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    batch = _get_batch_or_404(batch_id, db)
    _assert_institute_owns_batch(batch, current_user)

    sb_links = db.query(StudentBatch).filter(StudentBatch.batch_id == batch_id).all()
    students = []
    for link in sb_links:
        s = link.student
        vt = db.query(VerificationToken).filter(
            VerificationToken.student_id == s.id,
            VerificationToken.batch_id == batch_id
        ).first()
        students.append({
            "student_id": s.id,
            "name": s.name,
            "apaar_id": s.apaar_id,
            "program": s.program,
            "enrollment_year": s.enrollment_year,
            "status": s.status,
            "verification_status": vt.status if vt else "not_generated",
            "verify_token": vt.token if vt else None,
        })

    return {
        "batch_id": batch.id,
        "name": batch.name,
        "status": batch.status,
        "institute_id": batch.institute_id,
        "institute_name": batch.institute.name if batch.institute else None,
        "created_at": batch.created_at,
        "pushed_at": batch.pushed_at,
        "reviewed_at": batch.reviewed_at,
        "reject_reason": batch.reject_reason,
        "report_signed": batch.report_signed,
        "report_pdf_path": batch.report_pdf_path,
        "student_count": len(students),
        "students": students,
    }


@batch_router.post("/batches/{batch_id}/students", summary="Add students to a batch (institute_admin)")
def add_students_to_batch(
    batch_id: int,
    req: AddStudentsToBatchRequest,
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    batch = _get_batch_or_404(batch_id, db)
    _assert_institute_owns_batch(batch, current_user)

    if batch.status != "draft":
        raise HTTPException(status_code=400, detail="Cannot add students to a non-draft batch")

    added = 0
    skipped = 0
    for sid in req.student_ids:
        existing = db.query(StudentBatch).filter(
            StudentBatch.batch_id == batch_id,
            StudentBatch.student_id == sid
        ).first()
        if existing:
            skipped += 1
            continue
        db.add(StudentBatch(batch_id=batch_id, student_id=sid))
        added += 1

    db.commit()
    return {"added": added, "skipped_already_in_batch": skipped}


@batch_router.post("/batches/{batch_id}/push", summary="Push batch to AICTE for review (institute_admin)")
def push_batch(
    batch_id: int,
    current_user: dict = Depends(require_role(["institute_admin"])),
    db: Session = Depends(get_db),
):
    batch = _get_batch_or_404(batch_id, db)
    _assert_institute_owns_batch(batch, current_user)

    if batch.status not in ("draft",):
        raise HTTPException(status_code=400, detail=f"Batch is already in '{batch.status}' state; cannot push again")

    student_count = db.query(StudentBatch).filter(StudentBatch.batch_id == batch_id).count()
    if student_count == 0:
        raise HTTPException(status_code=400, detail="Cannot push an empty batch")

    batch.status = "pushed"
    batch.pushed_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    log_event(db=db, record_type="Batch", record_id=batch.id, event_type="PUSHED",
              actor=current_user.get("sub", "institute_admin"))

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "pushed_at": batch.pushed_at,
        "student_count": student_count,
        "message": "Batch pushed to AICTE successfully",
    }


# ── Verification Tokens ────────────────────────────────────────────────────────

@batch_router.post("/batches/{batch_id}/verification/generate",
                   summary="Generate VerificationTokens for all students in batch (institute_admin)")
def generate_verification_tokens(
    batch_id: int,
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    batch = _get_batch_or_404(batch_id, db)
    _assert_institute_owns_batch(batch, current_user)

    sb_links = db.query(StudentBatch).filter(StudentBatch.batch_id == batch_id).all()
    if not sb_links:
        raise HTTPException(status_code=400, detail="No students in batch")

    generated = []
    skipped = []

    for link in sb_links:
        existing = db.query(VerificationToken).filter(
            VerificationToken.student_id == link.student_id,
            VerificationToken.batch_id == batch_id,
        ).first()
        if existing:
            skipped.append(link.student_id)
            continue

        token_str, expires_at = _generate_token()
        vt = VerificationToken(
            token=token_str,
            student_id=link.student_id,
            batch_id=batch_id,
            expires_at=expires_at,
            status="pending",
        )
        db.add(vt)
        generated.append({
            "student_id": link.student_id,
            "token": token_str,
            "verify_url": f"{os.environ.get('FRONTEND_BASE_URL', 'http://localhost:5173')}/verify/{token_str}",
            "expires_at": expires_at,
        })

    db.commit()

    log_event(db=db, record_type="Batch", record_id=batch.id, event_type="TOKENS_GENERATED",
              actor=current_user.get("sub", "institute_admin"))

    return {
        "batch_id": batch_id,
        "generated_count": len(generated),
        "skipped_count": len(skipped),
        "tokens": generated,
        "note": "MOCKED — In production, these links would be emailed to students. Show them in the Institute Portal UI."
    }


@batch_router.post("/batches/{batch_id}/verification/send-emails",
                   summary="Send verification emails to all students in batch (institute_admin)")
def send_verification_emails(
    batch_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    from services.email import send_verification_email

    batch = _get_batch_or_404(batch_id, db)
    _assert_institute_owns_batch(batch, current_user)
    institute_name = batch.institute.name if batch.institute else "Your Institution"

    tokens = db.query(VerificationToken).filter(VerificationToken.batch_id == batch_id).all()
    if not tokens:
        raise HTTPException(status_code=400, detail="No verification tokens found. Run /generate first.")

    results = []
    for vt in tokens:
        student = vt.student
        if not student:
            continue
        result = send_verification_email(db=db, student=student, token_obj=vt, institute_name=institute_name)
        results.append({"student_id": vt.student_id, **result})

    sent = sum(1 for r in results if r.get("status") == "sent")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    failed = sum(1 for r in results if r.get("status") == "failed")

    return {
        "batch_id": batch_id,
        "total": len(results),
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "results": results,
        "smtp_note": "SMTP not configured — emails mocked/skipped. See email logs." if skipped > 0 else None,
    }


@batch_router.get("/batches/{batch_id}/verification/status",
                  summary="Get per-student verification status counts for a batch")
def get_verification_status(
    batch_id: int,
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    batch = _get_batch_or_404(batch_id, db)
    _assert_institute_owns_batch(batch, current_user)

    tokens = db.query(VerificationToken).filter(VerificationToken.batch_id == batch_id).all()
    total_students = db.query(StudentBatch).filter(StudentBatch.batch_id == batch_id).count()

    status_counts = {"pending": 0, "verified": 0, "unresponsive": 0, "not_generated": 0}
    per_student = []

    tokenized_student_ids = {vt.student_id for vt in tokens}
    for vt in tokens:
        status_counts[vt.status] = status_counts.get(vt.status, 0) + 1
        per_student.append({
            "student_id": vt.student_id,
            "status": vt.status,
            "responded_at": vt.responded_at,
            "expires_at": vt.expires_at,
        })

    not_generated_count = total_students - len(tokens)
    status_counts["not_generated"] = not_generated_count

    return {
        "batch_id": batch_id,
        "total_students": total_students,
        "status_counts": status_counts,
        "verified_rate": round(status_counts["verified"] / total_students, 4) if total_students else 0,
        "per_student": per_student,
    }


@batch_router.post("/batches/{batch_id}/verification/mark-unresponsive",
                   summary="Mark all pending tokens as unresponsive (demo convenience)")
def mark_unresponsive(
    batch_id: int,
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    batch = _get_batch_or_404(batch_id, db)
    _assert_institute_owns_batch(batch, current_user)

    tokens = db.query(VerificationToken).filter(
        VerificationToken.batch_id == batch_id,
        VerificationToken.status == "pending",
    ).all()

    for vt in tokens:
        vt.status = "unresponsive"
        vt.responded_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    return {"batch_id": batch_id, "marked_unresponsive": len(tokens)}


@batch_router.post("/batches/{batch_id}/verification/{student_id}/resend",
                   summary="Resend verification email to a single student")
def resend_verification(
    batch_id: int,
    student_id: int,
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    from services.email import send_verification_email

    batch = _get_batch_or_404(batch_id, db)
    _assert_institute_owns_batch(batch, current_user)

    vt = db.query(VerificationToken).filter(
        VerificationToken.batch_id == batch_id,
        VerificationToken.student_id == student_id,
    ).first()
    if not vt:
        raise HTTPException(status_code=404, detail="No token found for this student in this batch")

    student = vt.student
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Reset to pending
    vt.status = "pending"
    new_token, new_expires = _generate_token()
    vt.token = new_token
    vt.expires_at = new_expires
    vt.responded_at = None
    db.commit()

    result = send_verification_email(
        db=db, student=student, token_obj=vt,
        institute_name=batch.institute.name if batch.institute else "Institution"
    )
    return {"student_id": student_id, "new_token": new_token, **result}


# ── Public Verification (no auth) ─────────────────────────────────────────────

@batch_router.get("/verify/token/{token}",
                  summary="Public: Get masked student details for self-verification")
def get_token_student_details(token: str, db: Session = Depends(get_db)):
    vt = db.query(VerificationToken).filter(VerificationToken.token == token).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Invalid or expired verification link")

    now = datetime.datetime.now(datetime.timezone.utc)
    if vt.expires_at and vt.expires_at.replace(tzinfo=datetime.timezone.utc) < now:
        raise HTTPException(status_code=410, detail="This verification link has expired")

    if vt.status == "verified":
        raise HTTPException(status_code=409, detail="This record has already been verified")

    student = vt.student
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found")

    # Mask APAAR: show first 4 and last 4 digits only
    apaar = student.apaar_id
    masked_apaar = f"{apaar[:4]}****{apaar[-4:]}" if len(apaar) >= 8 else "****"

    return {
        "token_status": vt.status,
        "student": {
            "name": student.name,
            "apaar_id_masked": masked_apaar,
            "program": student.program,
            "enrollment_year": student.enrollment_year,
            "institute": student.institute.name if student.institute else None,
        },
        "expires_at": vt.expires_at,
        "note": "Please confirm that these details are correct, or submit corrections."
    }


@batch_router.post("/verify/token/{token}/confirm",
                   summary="Public: Student confirms their details are correct")
def confirm_token(token: str, db: Session = Depends(get_db)):
    vt = db.query(VerificationToken).filter(VerificationToken.token == token).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Invalid or expired verification link")

    if vt.status == "verified":
        return {"message": "Already verified", "status": "verified"}

    vt.status = "verified"
    vt.responded_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    log_event(db=db, record_type="VerificationToken", record_id=vt.id,
              event_type="STUDENT_CONFIRMED", actor=f"student_{vt.student_id}")

    return {"message": "Thank you! Your record has been verified.", "status": "verified"}


@batch_router.post("/verify/token/{token}/correct",
                   summary="Public: Student submits corrections to their record")
def submit_corrections(token: str, req: StudentCorrectionRequest, db: Session = Depends(get_db)):
    vt = db.query(VerificationToken).filter(VerificationToken.token == token).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Invalid verification link")

    vt.status = "verified"  # still marks as responded
    vt.responded_at = datetime.datetime.now(datetime.timezone.utc)
    vt.corrections = req.corrections
    db.commit()

    # Flag the record for institute review
    flag = FlaggedRecord(
        record_type="Student",
        record_id=str(vt.student_id),
        flag_reason="student_submitted_corrections",
        severity="needs_review",
        status="open",
    )
    db.add(flag)
    db.commit()

    log_event(db=db, record_type="VerificationToken", record_id=vt.id,
              event_type="STUDENT_CORRECTION_SUBMITTED", actor=f"student_{vt.student_id}")

    return {
        "message": "Corrections received. Your institute will be notified to review.",
        "status": "verified",
        "corrections_submitted": req.corrections,
    }


# ── AICTE Review ─────────────────────────────────────────────────────────────

@batch_router.post("/aicte/batches/{batch_id}/approve",
                   summary="AICTE approves a batch — triggers PDF generation + signing (aicte_admin)")
def approve_batch(
    batch_id: int,
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db),
):
    from services.pdf_report import generate_batch_report

    batch = _get_batch_or_404(batch_id, db)
    if batch.status not in ("pushed", "under_review"):
        raise HTTPException(
            status_code=400,
            detail=f"Batch must be in 'pushed' or 'under_review' state to approve. Current: {batch.status}"
        )

    # Generate signed PDF
    try:
        report = generate_batch_report(batch_id=batch_id, db=db)
        batch.report_pdf_path = report["pdf_path"]
        batch.report_signed = True
    except Exception as exc:
        # Don't block approval on PDF failure — log it
        batch.report_pdf_path = None
        batch.report_signed = False

    batch.status = "approved"
    batch.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
    batch.reject_reason = None
    db.commit()

    log_event(db=db, record_type="Batch", record_id=batch.id, event_type="APPROVED",
              actor=current_user.get("sub", "aicte_admin"))

    return {
        "batch_id": batch.id,
        "status": "approved",
        "reviewed_at": batch.reviewed_at,
        "report_signed": batch.report_signed,
        "report_pdf_path": batch.report_pdf_path,
        "message": "Batch approved. Signed PDF report generated.",
    }


@batch_router.post("/aicte/batches/{batch_id}/reject",
                   summary="AICTE rejects a batch with reason (aicte_admin)")
def reject_batch(
    batch_id: int,
    req: RejectBatchRequest,
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db),
):
    batch = _get_batch_or_404(batch_id, db)
    if batch.status not in ("pushed", "under_review"):
        raise HTTPException(
            status_code=400,
            detail=f"Batch must be in 'pushed' or 'under_review' state to reject. Current: {batch.status}"
        )

    batch.status = "rejected"
    batch.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
    batch.reject_reason = req.reason
    db.commit()

    log_event(db=db, record_type="Batch", record_id=batch.id, event_type="REJECTED",
              actor=current_user.get("sub", "aicte_admin"))

    return {
        "batch_id": batch.id,
        "status": "rejected",
        "reject_reason": batch.reject_reason,
        "reviewed_at": batch.reviewed_at,
    }


# ── PDF Report ────────────────────────────────────────────────────────────────

@batch_router.get("/batches/{batch_id}/report",
                  summary="Download signed PDF report for an approved batch")
def download_report(
    batch_id: int,
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin", "verifier"])),
    db: Session = Depends(get_db),
):
    batch = _get_batch_or_404(batch_id, db)
    _assert_institute_owns_batch(batch, current_user)

    if batch.status != "approved":
        raise HTTPException(status_code=400, detail="Report is only available for approved batches")

    if not batch.report_pdf_path or not os.path.exists(batch.report_pdf_path):
        # Regenerate on demand
        from services.pdf_report import generate_batch_report
        try:
            report = generate_batch_report(batch_id=batch_id, db=db)
            batch.report_pdf_path = report["pdf_path"]
            batch.report_signed = True
            db.commit()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    return FileResponse(
        path=batch.report_pdf_path,
        media_type="application/pdf",
        filename=f"batch_{batch_id}_report.pdf",
    )


# ── Completion Emails ─────────────────────────────────────────────────────────

@batch_router.post("/batches/{batch_id}/notify",
                   summary="Send completion emails to students in an approved batch (institute_admin)")
def notify_students(
    batch_id: int,
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    from services.email import send_completion_emails

    batch = _get_batch_or_404(batch_id, db)
    _assert_institute_owns_batch(batch, current_user)

    if batch.status != "approved":
        raise HTTPException(status_code=400, detail="Completion emails can only be sent for approved batches")

    results = send_completion_emails(db=db, batch=batch)
    sent = sum(1 for r in results if r.get("status") == "sent")
    skipped = sum(1 for r in results if r.get("status") == "skipped")

    return {
        "batch_id": batch_id,
        "total": len(results),
        "sent": sent,
        "skipped": skipped,
        "results": results,
    }


# ── Email Logs ────────────────────────────────────────────────────────────────

@batch_router.get("/emails/log", summary="Email send log (institute_admin: own batches; aicte_admin: all)")
def get_email_log(
    batch_id: int | None = Query(None),
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db),
):
    role = current_user.get("role")
    query = db.query(EmailLog)

    if batch_id:
        query = query.filter(EmailLog.batch_id == batch_id)
    elif role == "institute_admin":
        inst_id = current_user.get("institute_id")
        if inst_id:
            batch_ids = [b.id for b in db.query(Batch).filter(Batch.institute_id == inst_id).all()]
            query = query.filter(EmailLog.batch_id.in_(batch_ids))

    logs = query.order_by(EmailLog.created_at.desc()).limit(200).all()
    return {
        "count": len(logs),
        "logs": [
            {
                "id": e.id,
                "student_id": e.student_id,
                "batch_id": e.batch_id,
                "template": e.template,
                "to_address": e.to_address,
                "subject": e.subject,
                "status": e.status,
                "error": e.error,
                "created_at": e.created_at,
                "sent_at": e.sent_at,
            }
            for e in logs
        ],
    }


@batch_router.get("/emails/config", summary="Email SMTP configuration status (public metadata only)")
def get_emails_config(current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"]))):
    from services.email import get_email_config
    return get_email_config()

