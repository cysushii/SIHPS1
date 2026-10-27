from datetime import datetime, timezone
import os
import secrets
import datetime as dt_module
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models.database import get_db
from models.models import (
    Institute,
    InstituteProgram,
    Student,
    FlaggedRecord,
    AuditLog,
    TrustScoreHistory,
    HoneytokenID,
    Checkpoint,
    Batch,
    StudentBatch,
    VerificationToken,
    EmailLog,
)
from api.rbac import require_role, create_access_token
from ingestion.parsers import ingest_institutes, ingest_courses, ingest_students
from validation.capacity_check import check_capacity
from engines.trust_score import compute_trust_score
from engines.dedup import run_deduplication
from engines.graph_fraud import analyze_graph_fraud
from security.hash_chain import verify_chain, log_event
from security.doc_signer import sign_document, verify_document, get_public_key_pem
from security.honeytokens import seed_honeytokens
from security.anchoring import create_checkpoint, verify_against_checkpoints

router = APIRouter()

# --- Auth Helper Schemas & Route for Hackathon Demo Convenience ---
class TokenRequest(BaseModel):
    username: str
    role: str # "institute_admin", "aicte_admin", "verifier"
    institute_id: int | None = None

class DocumentVerifyRequest(BaseModel):
    document: dict
    signature: str

class FlagReviewRequest(BaseModel):
    status: str = "reviewed" # "reviewed"
    notes: str | None = None

@router.post("/auth/token", summary="Generate JWT token for hackathon testing")
def generate_demo_token(req: TokenRequest):
    """Convenience endpoint to get test JWT tokens for each role."""
    token = create_access_token({
        "sub": req.username,
        "role": req.role,
        "institute_id": req.institute_id
    })
    return {"access_token": token, "token_type": "bearer", "role": req.role}

@router.get("/institutes/list", summary="List all institutes (public for login dropdown)")
def list_all_institutes(db: Session = Depends(get_db)):
    """Returns all registered institutions for easy login dropdown selection."""
    insts = db.query(Institute).all()
    return {
        "institutes": [
            {
                "id": i.id,
                "name": i.name,
                "aicte_code": i.aicte_code,
                "state": i.state,
                "district": i.district,
                "type": i.type
            }
            for i in insts
        ]
    }

# --- Module 2: Ingestion Endpoints ---
@router.post("/institute/upload", summary="Upload Institutes CSV/Excel (institute_admin or aicte_admin)")
async def upload_institutes(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    result = ingest_institutes(
        file_bytes=contents,
        filename=file.filename or "institutes.csv",
        db=db,
        actor=current_user.get("sub", "institute_admin")
    )
    return result

@router.post("/course/upload", summary="Upload Courses CSV/Excel (institute_admin or aicte_admin)")
async def upload_courses(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    result = ingest_courses(
        file_bytes=contents,
        filename=file.filename or "courses.csv",
        db=db,
        actor=current_user.get("sub", "admin")
    )
    return result

@router.get("/dashboard/capacity/{institute_id}", summary="Check capacity & course availability (aicte_admin, institute_admin)")
def get_institute_capacity(
    institute_id: int,
    program: str = Query("ALL", description="Program name or ALL"),
    current_user: dict = Depends(require_role(["aicte_admin", "institute_admin"])),
    db: Session = Depends(get_db)
):
    inst = db.query(Institute).filter(Institute.id == institute_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institute not found.")

    programs = db.query(InstituteProgram).filter(InstituteProgram.institute_id == institute_id).all()
    if not programs:
        return check_capacity(institute_id=institute_id, program=program, db=db)

    results = []
    for p in programs:
        if program == "ALL" or p.program.lower() == program.lower():
            results.append(check_capacity(institute_id=institute_id, program=p.program, db=db))
    return {
        "institute_id": institute_id,
        "institute_name": inst.name,
        "status": "active",
        "programs": results
    }

@router.post("/student/upload", summary="Upload Students CSV/Excel (institute_admin)")
async def upload_students(
    file: UploadFile = File(...),
    institute_id: int | None = Form(None),
    current_user: dict = Depends(require_role(["institute_admin", "aicte_admin"])),
    db: Session = Depends(get_db)
):
    # Enforce institute boundary if institute_admin
    user_inst_id = current_user.get("institute_id")
    if current_user.get("role") == "institute_admin" and user_inst_id:
        institute_id = user_inst_id

    contents = await file.read()
    result = ingest_students(
        file_bytes=contents,
        filename=file.filename or "students.csv",
        db=db,
        default_institute_id=institute_id,
        actor=current_user.get("sub", "institute_admin")
    )

    # Automatically trigger dedup & graph check in background/post-upload for proactive integrity
    run_deduplication(db)
    analyze_graph_fraud(db)

    return result

# --- Module 5: Trust Scores ---
@router.get("/dashboard/trust-scores", summary="List all institutes + trust scores (aicte_admin)")
def get_all_trust_scores(
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db)
):
    institutes = db.query(Institute).all()
    results = []
    for inst in institutes:
        score_info = compute_trust_score(inst.id, db)
        results.append({
            "institute_id": inst.id,
            "aicte_code": inst.aicte_code,
            "name": inst.name,
            "state": inst.state,
            "district": inst.district,
            "trust_score": score_info["trust_score"],
            "breakdown": score_info["breakdown"]
        })
    return {"institutes": results}

@router.post("/dashboard/trust-scores/{institute_id}/recompute", summary="Recompute specific institute score (aicte_admin)")
def recompute_institute_trust_score(
    institute_id: int,
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db)
):
    inst = db.query(Institute).filter(Institute.id == institute_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institute not found.")
    score_info = compute_trust_score(institute_id, db)
    return score_info

# --- Module 6 & 7: Flagged Records Dashboard ---
@router.get("/dashboard/flagged", summary="List flagged anomaly & fraud records (aicte_admin)")
def get_flagged_records(
    status: str = Query("open", description="Filter by status ('open' or 'reviewed')"),
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db)
):
    flags = db.query(FlaggedRecord).filter(FlaggedRecord.status == status).all()
    return {"count": len(flags), "flagged_records": flags}

@router.get("/dashboard/duplicates", summary="List flagged duplicate records grouped by severity (aicte_admin)")
def get_flagged_duplicates(
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db)
):
    """
    Returns all duplicate enrollment and identity flags grouped by severity
    (e.g. 'confirmed' for cross-institute duplicate APAAR IDs, 'needs_review' for fuzzy identity / re-uploads).
    """
    dup_flags = db.query(FlaggedRecord).filter(
        FlaggedRecord.record_type == "Student",
        (FlaggedRecord.flag_reason.like("%duplicate%")) | (FlaggedRecord.flag_reason.like("%Duplicate%"))
    ).all()

    grouped = {
        "confirmed": [],
        "needs_review": [],
        "other": []
    }

    for flag in dup_flags:
        item = {
            "id": flag.id,
            "record_id": flag.record_id,
            "flag_reason": flag.flag_reason,
            "severity": flag.severity,
            "status": flag.status,
            "reviewed_by": flag.reviewed_by,
            "reviewed_at": flag.reviewed_at,
        }
        if flag.severity in grouped:
            grouped[flag.severity].append(item)
        else:
            grouped["other"].append(item)

    return {
        "total_duplicates": len(dup_flags),
        "grouped_by_severity": grouped
    }

@router.post("/dashboard/flagged/{flag_id}/review", summary="Mark flagged record as reviewed (aicte_admin)")
def review_flagged_record(
    flag_id: int,
    body: FlagReviewRequest,
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db)
):
    flag = db.query(FlaggedRecord).filter(FlaggedRecord.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flagged record not found.")

    flag.status = body.status
    flag.reviewed_by = current_user.get("sub", "aicte_admin")
    flag.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    # Log to tamper-evident audit log
    log_event(
        db=db,
        record_type="FlaggedRecord",
        record_id=flag.id,
        event_type="REVIEWED",
        actor=current_user.get("sub", "aicte_admin")
    )

    return {"message": "Flag marked as reviewed successfully", "flag_id": flag.id, "status": flag.status}

# --- Module 8: Audit Log Hash Chain ---
@router.get("/audit/verify-chain", summary="Verify complete hash chain integrity (aicte_admin)")
def verify_audit_hash_chain(
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db)
):
    is_valid, first_broken_id = verify_chain(db)
    total_logs = db.query(AuditLog).count()
    return {
        "is_valid": is_valid,
        "total_audit_blocks": total_logs,
        "first_broken_block_id": first_broken_id,
        "message": "Blockchain-style hash chain is intact." if is_valid else f"Tampering detected starting at log id {first_broken_id}!"
    }

# --- Module 9: Document Signer & Verifier ---
@router.get("/verify/public-key", summary="Get public key for certificate verification (public)")
def get_public_verification_key():
    return {
        "algorithm": "RSA-2048-PKCS1v15-SHA256",
        "public_key_pem": get_public_key_pem()
    }

@router.post("/verify/document", summary="Verify a digitally signed document (verifier, public)")
def verify_signed_document(req: DocumentVerifyRequest):
    is_valid = verify_document(req.document, req.signature)
    return {
        "is_valid": is_valid,
        "verified_document": req.document if is_valid else None,
        "status": "CERTIFICATE_AUTHENTIC" if is_valid else "INVALID_SIGNATURE_OR_TAMPERED"
    }

@router.get("/verify/document/{apaar_id}", summary="Lookup and verify student certificate by APAAR (verifier, public)")
def verify_document_by_apaar(
    apaar_id: str,
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.apaar_id == apaar_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student with this APAAR ID not found.")

    institute_name = student.institute.name if student.institute else "AICTE Institution"
    signed_pack = sign_document(
        student_id=student.id,
        apaar_id=student.apaar_id,
        name=student.name,
        institute=institute_name,
        program=student.program,
    )
    return signed_pack

# --- Security Differentiator Endpoints ---
@router.post("/security/checkpoint", summary="Manually trigger external hash-chain checkpoint (aicte_admin)")
def trigger_external_checkpoint(
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db)
):
    """
    Creates an external immutable checkpoint by writing current chain-head hash to /data/checkpoints.log.
    """
    result = create_checkpoint(db)
    return {
        "status": "CHECKPOINT_CREATED",
        "actor": current_user.get("sub", "aicte_admin"),
        "checkpoint": result
    }

@router.get("/security/verify-anchored", summary="Verify complete chain integrity against external checkpoints (aicte_admin)")
def verify_anchored_chain(
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db)
):
    """
    Cryptographic verification against external anchors (/data/checkpoints.log).
    Guarantees that no administrator or attacker has performed a full database rewrite.
    """
    return verify_against_checkpoints(db)

@router.get("/security/honeytokens/status", summary="Check honeytoken canaries status (aicte_admin)")
def get_honeytokens_status(
    current_user: dict = Depends(require_role(["aicte_admin"])),
    db: Session = Depends(get_db)
):
    """
    Returns the status of all reserved honeytoken canary APAAR IDs.
    Any triggered canary indicates near-certain evidence of data scraping or credential misuse.
    """
    tokens = db.query(HoneytokenID).all()
    triggered_count = sum(1 for t in tokens if t.triggered)
    return {
        "total_honeytokens": len(tokens),
        "triggered_count": triggered_count,
        "honeytokens": [
            {
                "id": t.id,
                "apaar_id": t.apaar_id,
                "triggered": t.triggered,
                "created_at": t.created_at,
                "triggered_at": t.triggered_at,
            }
            for t in tokens
        ]
    }

