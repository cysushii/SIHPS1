from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import AuditLog, InstituteProgram, Student, TrustScoreHistory, FlaggedRecord, VerificationToken, StudentBatch, Batch

def compute_trust_score(institute_id: int, db: Session, last_upload_missing_field_rate: float | None = None) -> dict:
    """
    Computes explainable, rules-based trust score for an institute:
    Signals (normalized 0-1):
    1. capacity_mismatch_rate (weight: 0.22):
       % of programs where active enrolled students > approved intake.
    2. missing_field_rate (weight: 0.18):
       % of required fields missing/null in the last upload or existing student records.
    3. data_correction_frequency (weight: 0.13):
       How many times this institute's records were edited (UPDATE) in the last 90 days.
       Normalized: count / max_expected (e.g. min(1.0, count / 20)).
    4. duplicate_rate (weight: 0.13):
       % of enrolled students involved in exact or suspected duplicate flags.
    5. geographic_mismatch_rate (weight: 0.13):
       % of enrolled students with geographic mismatch flags (embedded state != institute state)
    6. lifecycle_flag_rate (weight: 0.09):
       % of enrolled students with lifecycle implausibility or review flags.
    7. unverified_rate (weight: 0.12):
       % of students in pushed/approved batches who remain unverified (pending or unresponsive).

    Total Weights: 0.22 + 0.18 + 0.13 + 0.13 + 0.13 + 0.09 + 0.12 = 1.00 (100%)
    Score = 100 - (weighted_sum * 100)
    """
    # 1. Capacity Mismatch Rate
    programs = db.query(InstituteProgram).filter(InstituteProgram.institute_id == institute_id).all()
    if not programs:
        capacity_mismatch_rate = 0.0
        total_programs = 0
        mismatched_programs = 0
        course_data_status = "no_course_data_available"
        course_data_reason = "multi_year_extended_approval"
    else:
        course_data_status = "active"
        course_data_reason = None
        total_programs = len(programs)
        mismatched_programs = 0
        for p in programs:
            enrolled = db.query(Student).filter(
                Student.institute_id == institute_id,
                Student.program.ilike(p.program.strip()),
                Student.status == "Active"
            ).count()
            if enrolled > p.approved_intake:
                mismatched_programs += 1
        capacity_mismatch_rate = round(mismatched_programs / total_programs, 4)

    # Student records of this institute
    students = db.query(Student).filter(Student.institute_id == institute_id).all()
    student_ids = [str(s.id) for s in students]
    total_students = len(students)

    # 2. Missing Field Rate
    if last_upload_missing_field_rate is not None:
        missing_field_rate = max(0.0, min(1.0, float(last_upload_missing_field_rate)))
    else:
        if not students:
            missing_field_rate = 0.0
        else:
            total_required_cells = total_students * 4 # apaar_id, name, program, enrollment_year
            missing_count = 0
            for s in students:
                if not s.apaar_id: missing_count += 1
                if not s.name: missing_count += 1
                if not s.program: missing_count += 1
                if not s.enrollment_year: missing_count += 1
            missing_field_rate = round(missing_count / total_required_cells, 4)

    # 3. Data Correction Frequency (last 90 days)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    all_target_ids = [str(institute_id)] + student_ids

    correction_count = db.query(AuditLog).filter(
        AuditLog.event_type == "UPDATE",
        AuditLog.record_id.in_(all_target_ids),
        AuditLog.timestamp >= cutoff
    ).count() if all_target_ids else 0

    correction_frequency_norm = min(1.0, round(correction_count / 20.0, 4))

    # 4. Duplicate Rate (Exact and Fuzzy duplicates involving this institute's students)
    duplicate_flags_count = 0
    if total_students > 0 and student_ids:
        # Match single or comma-separated pairs in record_id
        for s_id in student_ids:
            has_dup = db.query(FlaggedRecord).filter(
                FlaggedRecord.record_type == "Student",
                (FlaggedRecord.record_id == s_id) | 
                (FlaggedRecord.record_id.like(f"{s_id},%")) | 
                (FlaggedRecord.record_id.like(f"%,{s_id}")),
                (FlaggedRecord.flag_reason.like("%duplicate%")) | (FlaggedRecord.flag_reason.like("%Duplicate%"))
            ).first()
            if has_dup:
                duplicate_flags_count += 1
        duplicate_rate = min(1.0, round(duplicate_flags_count / total_students, 4))
    else:
        duplicate_rate = 0.0

    # 5. Geographic Mismatch Rate (weight: 0.15)
    if total_students > 0 and student_ids:
        geo_flags_count = db.query(FlaggedRecord).filter(
            FlaggedRecord.record_type == "Student",
            FlaggedRecord.record_id.in_(student_ids),
            FlaggedRecord.flag_reason == "geographic_mismatch"
        ).count()
        geographic_mismatch_rate = min(1.0, round(geo_flags_count / total_students, 4))
    else:
        geo_flags_count = 0
        geographic_mismatch_rate = 0.0

    # 6. Lifecycle Flag Rate (weight: 0.10)
    if total_students > 0 and student_ids:
        life_flags_count = db.query(FlaggedRecord).filter(
            FlaggedRecord.record_type == "Student",
            FlaggedRecord.record_id.in_(student_ids),
            FlaggedRecord.flag_reason == "lifecycle_implausible"
        ).count()
        lifecycle_flag_rate = min(1.0, round(life_flags_count / total_students, 4))
    else:
        life_flags_count = 0
        lifecycle_flag_rate = 0.0

    # 7. Unverified Rate — students in pushed/approved batches who have not yet confirmed their records
    try:
        tokenized = (
            db.query(VerificationToken)
            .filter(VerificationToken.student_id.in_([s.id for s in students]))
            .all()
        ) if students else []
        total_tokenized = len(tokenized)
        unverified_count = sum(1 for t in tokenized if t.status in ("pending", "unresponsive"))
        unverified_rate = min(1.0, round(unverified_count / total_tokenized, 4)) if total_tokenized > 0 else 0.0
    except Exception:
        unverified_count = 0
        total_tokenized = 0
        unverified_rate = 0.0

    # Weighted penalties — 7 signals summing to 1.00
    w_capacity = 0.22
    w_missing = 0.18
    w_correction = 0.13
    w_duplicate = 0.13
    w_geographic = 0.13
    w_lifecycle = 0.09
    w_unverified = 0.12

    weighted_penalty = (
        (w_capacity * capacity_mismatch_rate) +
        (w_missing * missing_field_rate) +
        (w_correction * correction_frequency_norm) +
        (w_duplicate * duplicate_rate) +
        (w_geographic * geographic_mismatch_rate) +
        (w_lifecycle * lifecycle_flag_rate) +
        (w_unverified * unverified_rate)
    )

    final_score = int(round(max(0.0, 100.0 - (weighted_penalty * 100.0))))

    breakdown = {
        "course_data_status": course_data_status,
        "course_data_reason": course_data_reason,
        "capacity_mismatch_rate": capacity_mismatch_rate,
        "mismatched_programs_count": mismatched_programs,
        "total_programs_count": total_programs,
        "missing_field_rate": missing_field_rate,
        "data_correction_frequency": correction_frequency_norm,
        "raw_correction_count_90d": correction_count,
        "duplicate_rate": duplicate_rate,
        "duplicate_students_count": duplicate_flags_count,
        "geographic_mismatch_rate": geographic_mismatch_rate,
        "geographic_mismatches_count": geo_flags_count,
        "lifecycle_flag_rate": lifecycle_flag_rate,
        "lifecycle_flags_count": life_flags_count,
        "unverified_rate": unverified_rate,
        "unverified_students_count": unverified_count,
        "total_tokenized_students": total_tokenized,
        "weights": {
            "capacity_mismatch": w_capacity,
            "missing_field": w_missing,
            "data_correction": w_correction,
            "duplicate_rate": w_duplicate,
            "geographic_mismatch": w_geographic,
            "lifecycle_flag": w_lifecycle,
            "unverified_rate": w_unverified,
        },
        "weighted_deductions": {
            "capacity_deduction": round(w_capacity * capacity_mismatch_rate * 100.0, 2),
            "missing_field_deduction": round(w_missing * missing_field_rate * 100.0, 2),
            "correction_deduction": round(w_correction * correction_frequency_norm * 100.0, 2),
            "duplicate_deduction": round(w_duplicate * duplicate_rate * 100.0, 2),
            "geographic_deduction": round(w_geographic * geographic_mismatch_rate * 100.0, 2),
            "lifecycle_deduction": round(w_lifecycle * lifecycle_flag_rate * 100.0, 2),
            "unverified_deduction": round(w_unverified * unverified_rate * 100.0, 2),
        }
    }

    # Record in history
    history = TrustScoreHistory(
        institute_id=institute_id,
        score=final_score,
        signal_breakdown=breakdown,
    )
    db.add(history)
    db.commit()

    return {
        "institute_id": institute_id,
        "trust_score": final_score,
        "breakdown": breakdown,
    }
