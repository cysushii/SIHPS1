from sqlalchemy.orm import Session
from rapidfuzz import fuzz
from models.models import Student, FlaggedRecord
from security.hash_chain import log_event

"""
Deduplication Engine (engines/dedup.py)

1. Exact Match:
   - Same apaar_id, DIFFERENT institute_id -> CONFIRMED duplicate enrollment, severity "confirmed"
   - Same apaar_id, SAME institute_id -> likely re-upload, severity "needs_review"
2. Fuzzy Match:
   - RapidFuzz token_sort_ratio on names >= threshold (default 90) AND DOB matches (if available),
     but apaar_id differs -> SUSPECTED duplicate, severity "needs_review" (never "confirmed").

Logs events to the audit hash chain for every duplicate flag raised.
"""

def check_exact_duplicate(apaar_id: str, institute_id: int, db: Session, exclude_student_id: int | None = None) -> dict:
    """
    Checks for exact APAAR ID duplication across the student database.
    - Same apaar_id, DIFFERENT institute_id -> CONFIRMED duplicate enrollment (severity: 'confirmed')
    - Same apaar_id, SAME institute_id -> likely re-upload / dual entry (severity: 'needs_review')
    Returns {is_duplicate: bool, duplicate_type: str | None, matched_record_id: int | None, severity: str | None}
    """
    if not apaar_id:
        return {"is_duplicate": False, "duplicate_type": None, "matched_record_id": None, "severity": None}

    clean_apaar = str(apaar_id).strip()
    query = db.query(Student).filter(Student.apaar_id == clean_apaar)
    if exclude_student_id:
        query = query.filter(Student.id != exclude_student_id)

    matches = query.all()
    if not matches:
        return {"is_duplicate": False, "duplicate_type": None, "matched_record_id": None, "severity": None}

    # Prioritize cross-institute collision
    for m in matches:
        if m.institute_id != institute_id:
            return {
                "is_duplicate": True,
                "duplicate_type": "cross_institute_duplicate",
                "matched_record_id": m.id,
                "matched_institute_id": m.institute_id,
                "severity": "confirmed",
                "reason": f"Exact APAAR ID '{clean_apaar}' already enrolled in another Institute (ID {m.institute_id}, Student {m.id})."
            }

    # Same institute match
    first_match = matches[0]
    return {
        "is_duplicate": True,
        "duplicate_type": "same_institute_reupload",
        "matched_record_id": first_match.id,
        "matched_institute_id": first_match.institute_id,
        "severity": "needs_review",
        "reason": f"Exact APAAR ID '{clean_apaar}' already exists in same Institute (Student {first_match.id}). Likely re-upload or duplicate entry."
    }

def check_fuzzy_duplicate(
    name: str,
    dob: str | None,
    institute_id: int,
    db: Session,
    current_apaar_id: str | None = None,
    exclude_student_id: int | None = None,
    threshold: float = 90.0
) -> list[dict]:
    """
    RapidFuzz token_sort_ratio on names.
    If similarity >= threshold AND dob matches (if available) but apaar_id differs:
    -> SUSPECTED duplicate, severity "needs_review" (never "confirmed" — could be 2 people with similar names).
    Returns list of matches with similarity_score.
    """
    if not name or not name.strip():
        return []

    clean_name = name.strip().lower()
    clean_dob = str(dob).strip() if dob else None

    query = db.query(Student)
    if exclude_student_id:
        query = query.filter(Student.id != exclude_student_id)

    all_students = query.all()
    suspected_duplicates = []

    for s in all_students:
        # Only compare if APAAR differs
        if current_apaar_id and s.apaar_id == current_apaar_id:
            continue

        sim_score = fuzz.token_sort_ratio(clean_name, s.name.strip().lower())
        if sim_score >= threshold:
            dob_matches = True
            if clean_dob and s.dob:
                dob_matches = (clean_dob == s.dob.strip())

            if dob_matches:
                suspected_duplicates.append({
                    "matched_student_id": s.id,
                    "matched_student_name": s.name,
                    "matched_apaar_id": s.apaar_id,
                    "matched_institute_id": s.institute_id,
                    "similarity_score": round(float(sim_score), 2),
                    "dob_matched": bool(clean_dob and s.dob),
                    "severity": "needs_review",
                    "reason": f"High name similarity ({sim_score:.1f}%) with different APAAR ID ({current_apaar_id} vs {s.apaar_id})."
                })

    return suspected_duplicates

def run_deduplication(db: Session, student_id: int | None = None) -> list[dict]:
    """
    Batch helper: runs deduplication scans across the DB or for a single student.
    Logs each raised flag to the AuditLog hash chain.
    """
    flagged_results = []
    students = db.query(Student).all()
    if not students or len(students) < 2:
        return flagged_results

    targets = [s for s in students if s.id == student_id] if student_id else students

    for s1 in targets:
        # Check exact duplicate
        exact_res = check_exact_duplicate(s1.apaar_id, s1.institute_id, db, exclude_student_id=s1.id)
        if exact_res["is_duplicate"]:
            rec_id_str = f"{s1.id},{exact_res['matched_record_id']}"
            existing = db.query(FlaggedRecord).filter(
                FlaggedRecord.record_type == "Student",
                FlaggedRecord.record_id.in_([rec_id_str, f"{exact_res['matched_record_id']},{s1.id}"]),
                FlaggedRecord.flag_reason.like("%APAAR Duplicate%")
            ).first()

            if not existing:
                flag = FlaggedRecord(
                    record_type="Student",
                    record_id=rec_id_str,
                    flag_reason=f"APAAR Duplicate: {exact_res['reason']}",
                    severity=exact_res["severity"],
                    status="open"
                )
                db.add(flag)
                db.commit()
                log_event(db, "FlaggedRecord", flag.id, "FLAGGED", "dedup_engine")
                flagged_results.append(exact_res)

        # Check fuzzy duplicate
        fuzzy_matches = check_fuzzy_duplicate(
            name=s1.name,
            dob=s1.dob,
            institute_id=s1.institute_id,
            db=db,
            current_apaar_id=s1.apaar_id,
            exclude_student_id=s1.id
        )
        for fm in fuzzy_matches:
            if s1.id < fm["matched_student_id"]:
                rec_id_str = f"{s1.id},{fm['matched_student_id']}"
                existing = db.query(FlaggedRecord).filter(
                    FlaggedRecord.record_type == "Student",
                    FlaggedRecord.record_id.in_([rec_id_str, f"{fm['matched_student_id']},{s1.id}"]),
                    FlaggedRecord.flag_reason.like("%Suspected Identity Duplicate%")
                ).first()

                if not existing:
                    flag = FlaggedRecord(
                        record_type="Student",
                        record_id=rec_id_str,
                        flag_reason=f"Suspected Identity Duplicate: {fm['reason']}",
                        severity=fm["severity"],
                        status="open"
                    )
                    db.add(flag)
                    db.commit()
                    log_event(db, "FlaggedRecord", flag.id, "FLAGGED", "dedup_engine")
                    flagged_results.append(fm)

    return flagged_results
