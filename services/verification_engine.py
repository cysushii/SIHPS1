"""
Verification Engine for SIH26263 (Section 3).
Executes real automated verification runs against submitted batches and streams live results
per-student and per-batch via Server-Sent Events (SSE).

Checks performed:
 1. apaar_format: Structural APAAR ID format validation
 2. honeytoken_scan: Reserved canary ID check (intrusion / breach indicator)
 3. exact_duplicate: Same APAAR ID already enrolled in overlapping period
 4. fuzzy_duplicate: Name + Date of Birth similarity match
 5. self_verification: Student confirmation state (Verified / Correction requested / Unresponsive / Pending)
 6. geographic_plausibility: State / district alignment with institution
 7. lifecycle_plausibility: Schooling to higher-ed timeline consistency
 8. field_consistency: Missing mandatory fields, NRI/OCI/Foreign validity
 9. capacity_check: Approved intake capacity vs enrolled count from loaded AICTE data
10. closure_check: Check against real AICTE course closure notices
"""
import os
import json
import asyncio
import datetime
from sqlalchemy.orm import Session
from models.models import (
    Batch, Student, StudentBatch, Institute, InstituteProgram,
    VerificationToken, VerificationRun, StudentVerificationResult, FlaggedRecord
)
from validation.apaar_validator import (
    validate_apaar_format, check_geographic_consistency, check_lifecycle_plausibility
)
from security.honeytokens import check_honeytoken
from engines.dedup import check_exact_duplicate, check_fuzzy_duplicate
from validation.capacity_check import check_capacity
from security.hash_chain import log_event
import pandas as pd

def run_single_student_checks(student: Student, batch: Batch, db: Session) -> tuple[dict, str]:
    """
    Execute checks 1 to 8 on a single student.
    Returns (checks_dict, verdict).
    Verdict: 'cleared', 'needs_review', or 'blocked'.
    """
    checks = {}
    is_blocked = False
    needs_review = False

    # 1. APAAR Format
    valid_format, format_reason = validate_apaar_format(student.apaar_id)
    if not valid_format:
        checks["apaar_format"] = {"status": "fail", "reason": format_reason, "evidence": None}
        is_blocked = True
    else:
        checks["apaar_format"] = {"status": "pass", "reason": "Valid 12-digit structural format", "evidence": None}

    # 2. Honeytoken Scan
    honey_hit = check_honeytoken(student.apaar_id, db=db, actor="verification_run")
    if honey_hit["triggered"]:
        checks["honeytoken_scan"] = {"status": "fail", "reason": "CRITICAL: Reserved canary honeytoken ID detected", "evidence": honey_hit}
        is_blocked = True
    else:
        checks["honeytoken_scan"] = {"status": "pass", "reason": "No canary tokens detected", "evidence": None}

    # 3. Exact Duplicate (across all batches / other institutes)
    exact_res = check_exact_duplicate(
        apaar_id=student.apaar_id,
        institute_id=student.institute_id,
        db=db,
        exclude_student_id=student.id
    )
    if exact_res["is_duplicate"]:
        if exact_res.get("severity") == "confirmed":
            checks["exact_duplicate"] = {"status": "fail", "reason": exact_res["reason"], "evidence": exact_res}
            is_blocked = True
        else:
            checks["exact_duplicate"] = {"status": "warning", "reason": exact_res["reason"], "evidence": exact_res}
            needs_review = True
    else:
        checks["exact_duplicate"] = {"status": "pass", "reason": "Unique APAAR registration", "evidence": None}

    # 4. Fuzzy Duplicate (name + DOB)
    fuzzy_matches = check_fuzzy_duplicate(
        name=student.name,
        dob=student.dob,
        institute_id=student.institute_id,
        db=db,
        current_apaar_id=student.apaar_id,
        exclude_student_id=student.id
    )
    if fuzzy_matches:
        checks["fuzzy_duplicate"] = {"status": "warning", "reason": f"Suspected identity match with {len(fuzzy_matches)} record(s)", "evidence": fuzzy_matches}
        needs_review = True
    else:
        checks["fuzzy_duplicate"] = {"status": "pass", "reason": "No high-similarity identity matches", "evidence": None}

    # 5. Student Self-Verification Status
    vt = db.query(VerificationToken).filter(
        VerificationToken.student_id == student.id,
        VerificationToken.batch_id == batch.id
    ).first()

    if not vt:
        checks["self_verification"] = {"status": "warning", "reason": "Verification token not yet generated", "evidence": "token_missing"}
        needs_review = True
    elif vt.status == "verified":
        checks["self_verification"] = {"status": "pass", "reason": "Confirmed by student", "evidence": f"Responded at {vt.responded_at}"}
    elif vt.status == "correction_requested":
        checks["self_verification"] = {"status": "warning", "reason": "Student requested correction", "evidence": vt.corrections}
        needs_review = True
    elif vt.status == "unresponsive":
        checks["self_verification"] = {"status": "warning", "reason": "Student link expired without response", "evidence": None}
        needs_review = True
    else:
        checks["self_verification"] = {"status": "warning", "reason": "Pending student confirmation", "evidence": None}
        needs_review = True

    # 6. Geographic Plausibility
    geo_res = check_geographic_consistency(student.apaar_id, student.institute_id, db)
    if not geo_res["match"]:
        checks["geographic_plausibility"] = {"status": "warning", "reason": "Relocation soft signal: embedded district differs from institute location", "evidence": geo_res}
        needs_review = True
    else:
        checks["geographic_plausibility"] = {"status": "pass", "reason": f"Aligned with {geo_res['institute_location']}", "evidence": geo_res}

    # 7. Lifecycle Plausibility
    life_res = check_lifecycle_plausibility(student.apaar_id, student.enrollment_year)
    if not life_res["plausible"]:
        if life_res.get("severity") == "implausible":
            checks["lifecycle_plausibility"] = {"status": "warning", "reason": life_res["reason"], "evidence": life_res}
            needs_review = True
        else:
            checks["lifecycle_plausibility"] = {"status": "warning", "reason": life_res["reason"], "evidence": life_res}
            needs_review = True
    else:
        checks["lifecycle_plausibility"] = {"status": "pass", "reason": "Plausible timeline", "evidence": life_res}

    # 8. Field & Category Consistency (NRI / OCI / Foreign)
    missing = []
    if not student.name or len(student.name.strip()) < 2: missing.append("name")
    if not student.program: missing.append("program")
    if not student.enrollment_year: missing.append("enrollment_year")

    if missing:
        checks["field_consistency"] = {"status": "fail", "reason": f"Missing required fields: {', '.join(missing)}", "evidence": missing}
        is_blocked = True
    else:
        nri_val = getattr(student, "nri_status", None)
        category_note = f"Category: {nri_val}" if nri_val else "Standard enrollment"
        checks["field_consistency"] = {"status": "pass", "reason": category_note, "evidence": None}

    # Assign final student verdict
    if is_blocked:
        verdict = "blocked"
    elif needs_review:
        verdict = "needs_review"
    else:
        verdict = "cleared"

    return checks, verdict

def check_closures(program_name: str, institute_code: str) -> dict:
    """Check if course is listed in real aicte_closures.csv."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    closure_file = os.path.join(data_dir, "aicte_closures.csv")
    if not os.path.exists(closure_file):
        return {"is_closed": False}

    try:
        df = pd.read_csv(closure_file)
        matches = df[
            (df["course"].astype(str).str.contains(program_name, case=False, na=False)) &
            (df["aicte_permanent_id"].astype(str) == str(institute_code))
        ]
        if not matches.empty:
            return {
                "is_closed": True,
                "reason": f"Course listed as closed in AICTE records for year {matches.iloc[0].get('academic_year', 'prior')}"
            }
    except Exception:
        pass
    return {"is_closed": False}

async def execute_batch_verification_run(batch_id: int, db: Session):
    """
    Generator yielding live Server-Sent Events (SSE) representing real verification execution.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        yield f"data: {json.dumps({'error': 'Batch not found'})}\n\n"
        return

    # Update batch status to under_review
    batch.status = "under_review"
    db.commit()

    # Create a new VerificationRun record
    run_entry = VerificationRun(
        batch_id=batch.id,
        status="running"
    )
    db.add(run_entry)
    db.commit()
    db.refresh(run_entry)

    yield f"data: {json.dumps({'event': 'run_started', 'run_id': run_entry.id, 'batch_id': batch.id, 'batch_name': batch.name})}\n\n"
    await asyncio.sleep(0.3)

    sb_links = db.query(StudentBatch).filter(StudentBatch.batch_id == batch.id).all()
    students = [link.student for link in sb_links if link.student]

    cleared_count = 0
    needs_review_count = 0
    blocked_count = 0

    student_results = []

    # Run checks 1-8 per student
    for idx, std in enumerate(students):
        checks, verdict = run_single_student_checks(std, batch, db)

        # Log audit entry for this decision
        audit_entry = log_event(
            db=db,
            record_type="StudentVerification",
            record_id=f"{run_entry.id}:{std.id}",
            event_type="VERIFICATION_CHECK",
            actor="aicte_automated_verification_engine"
        )
        audit_hash = audit_entry.event_hash if audit_entry else "0" * 64

        if verdict == "cleared":
            cleared_count += 1
        elif verdict == "needs_review":
            needs_review_count += 1
        else:
            blocked_count += 1

        res_record = StudentVerificationResult(
            run_id=run_entry.id,
            student_id=std.id,
            verdict=verdict,
            checks=checks,
            audit_hash=audit_hash
        )
        db.add(res_record)
        student_results.append(res_record)

        # Stream student row completion
        payload = {
            "event": "student_checked",
            "index": idx + 1,
            "total_students": len(students),
            "student_id": std.id,
            "student_name": std.name,
            "apaar_id": f"********{std.apaar_id[-4:]}" if len(std.apaar_id) >= 4 else std.apaar_id,
            "program": std.program,
            "verdict": verdict,
            "checks": checks,
            "audit_hash": audit_hash,
            "counts": {
                "cleared": cleared_count,
                "needs_review": needs_review_count,
                "blocked": blocked_count,
            }
        }
        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(0.1)

    db.commit()

    # Stage 9: Capacity check per course
    inst = batch.institute
    inst_programs = db.query(InstituteProgram).filter(InstituteProgram.institute_id == batch.institute_id).all()

    course_capacities = []
    if not inst_programs:
        course_capacities.append({
            "course": "All Programmes",
            "approved_intake": None,
            "enrolled_count": len(students),
            "status": "not_assessable",
            "note": "Not assessable: no course-level intake on file (multi-year autonomous/deemed approval). Reviewer decision required."
        })
    else:
        for prog in inst_programs:
            enrolled = db.query(Student).filter(
                Student.institute_id == batch.institute_id,
                Student.program.ilike(prog.program.strip()),
                Student.status == "Active"
            ).count()
            cap_status = "pass" if enrolled <= prog.approved_intake else "over_intake"
            course_capacities.append({
                "course": prog.program,
                "approved_intake": prog.approved_intake,
                "enrolled_count": enrolled,
                "status": cap_status,
                "note": f"{enrolled} / {prog.approved_intake} capacity used"
            })

    # Stage 10: AICTE Closure Check
    closure_results = []
    for cp in course_capacities:
        c_res = check_closures(cp["course"], inst.aicte_code if inst else "")
        closure_results.append({
            "course": cp["course"],
            "is_closed": c_res["is_closed"],
            "reason": c_res.get("reason", "Approved course active")
        })

    summary = {
        "total_students": len(students),
        "cleared": cleared_count,
        "needs_review": needs_review_count,
        "blocked": blocked_count,
        "course_capacities": course_capacities,
        "closure_checks": closure_results,
        "all_decided": False # Requires reviewer notes on flagged before approval
    }

    run_entry.finished_at = datetime.datetime.now(datetime.timezone.utc)
    run_entry.status = "completed"
    run_entry.summary = summary
    db.commit()

    # Final event
    yield f"data: {json.dumps({'event': 'run_completed', 'run_id': run_entry.id, 'summary': summary})}\n\n"

