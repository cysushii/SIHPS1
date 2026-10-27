import os
import io
import re
import pandas as pd
from sqlalchemy.orm import Session
from models.models import Institute, InstituteProgram, Student, FlaggedRecord
from validation.apaar_validator import validate_apaar_format, check_geographic_consistency, check_lifecycle_plausibility
from validation.format_normalizer import normalize_institute_name
from security.hash_chain import log_event
from security.honeytokens import check_honeytoken
from engines.dedup import check_exact_duplicate, check_fuzzy_duplicate

# Header variation mappings
INSTITUTE_HEADER_MAP = {
    "aicte_code": ["aicte_code", "aicte_permanent_id", "aicte code", "code", "institution_code", "aicte id", "institution id"],
    "name": ["name", "institute_name", "institute name", "institution", "college_name", "college name", "university"],
    "state": ["state", "province", "st"],
    "district": ["district", "dist", "city"],
    "type": ["type", "institution_type", "institute_type", "category"],
    "approval_status": ["approval_status", "status", "approval"],
    "programs": ["programs", "program_list", "courses", "branches"],
}

COURSE_HEADER_MAP = {
    "aicte_permanent_id": ["aicte_permanent_id", "aicte_code", "aicte id", "institution id", "code"],
    "level": ["level", "course_level", "degree_level"],
    "program": ["program", "discipline", "branch_type"],
    "course": ["course", "course_name", "branch", "specialization"],
    "intake_current": ["intake_current", "intake_2024_25", "approved_intake", "intake", "sanctioned_intake"],
    "intake_prev": ["intake_prev", "intake_2023_24", "previous_intake"],
    "approval_year": ["approval_year", "academic_year", "year"],
    "affiliating_body": ["affiliating_body", "university", "affiliating_university"],
    "nri_approved": ["nri_approved", "nri"],
    "fn_oci_approved": ["fn_oci_approved", "fn_oci", "foreign_approved"],
    "source_file": ["source_file", "source", "eoa_file"],
}

STUDENT_HEADER_MAP = {
    "apaar_id": ["apaar_id", "apaar id", "apaar", "student_apaar", "apaar_no", "apaar number"],
    "name": ["name", "student_name", "student name", "full_name", "full name"],
    "institute_id": ["institute_id", "institute id", "aicte_code", "aicte_permanent_id", "inst_id"],
    "program": ["program", "course", "branch", "degree", "stream"],
    "enrollment_year": ["enrollment_year", "enrollment year", "year", "batch", "admission_year"],
    "status": ["status", "enrollment_status", "student_status"],
    "dob": ["dob", "date_of_birth", "birth_date", "birthdate"],
    "address": ["address", "residential_address", "addr", "permanent_address"],
}

def _normalize_headers(columns: list[str], header_map: dict[str, list[str]]) -> dict[str, str]:
    """Maps actual dataframe column names to canonical target fields."""
    normalized_cols = {}
    for col in columns:
        col_clean = str(col).strip().lower()
        matched = None
        for canonical, variants in header_map.items():
            if col_clean == canonical or col_clean in variants:
                matched = canonical
                break
        if matched:
            normalized_cols[col] = matched
    return normalized_cols

def _read_file_to_df(file_bytes: bytes, filename: str) -> pd.DataFrame:
    filename_lower = filename.lower()
    if filename_lower.endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_bytes), dtype=str)
    elif filename_lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    else:
        return pd.read_csv(io.BytesIO(file_bytes), dtype=str)

def ingest_institutes(file_bytes: bytes, filename: str, db: Session, actor: str = "institute_admin") -> dict:
    df = _read_file_to_df(file_bytes, filename)
    col_map = _normalize_headers(list(df.columns), INSTITUTE_HEADER_MAP)
    df = df.rename(columns=col_map)

    inserted = 0
    rejected = 0
    errors = []

    required = ["aicte_code", "name"]
    for req in required:
        if req not in df.columns:
            return {
                "inserted": 0,
                "rejected": len(df),
                "errors": [f"Missing critical header '{req}'. Found headers: {list(df.columns)}"]
            }

    for idx, row in df.iterrows():
        row_num = idx + 2
        code = str(row.get("aicte_code", "")).strip() if pd.notna(row.get("aicte_code")) else ""
        name = str(row.get("name", "")).strip() if pd.notna(row.get("name")) else ""

        if not code or not name:
            rejected += 1
            errors.append(f"Row {row_num}: Missing aicte_code or name.")
            continue

        # Format normalizer check against AICTE/AISHE reference master
        match_result = normalize_institute_name(name, threshold=85.0)
        canonical_name = match_result["matched_name"] if match_result["is_match"] else name

        inst = db.query(Institute).filter(Institute.aicte_code == code).first()
        is_update = False
        if inst:
            is_update = True
            inst.name = canonical_name
            inst.state = str(row.get("state", inst.state or "")).strip() or None
            inst.district = str(row.get("district", inst.district or "")).strip() or None
            inst.type = str(row.get("type", inst.type or "")).strip() or None
            inst.approval_status = str(row.get("approval_status", inst.approval_status or "Approved")).strip()
        else:
            inst = Institute(
                aicte_code=code,
                name=canonical_name,
                state=str(row.get("state", "")).strip() or None,
                district=str(row.get("district", "")).strip() or None,
                type=str(row.get("type", "")).strip() or None,
                approval_status=str(row.get("approval_status", "Approved")).strip() or "Approved"
            )
            db.add(inst)

        db.flush()

        # Optional intake programs parsing e.g. "B.Tech CS:120; MBA:60"
        programs_str = str(row.get("programs", "")).strip() if "programs" in row and pd.notna(row.get("programs")) else ""
        if programs_str:
            for item in programs_str.split(";"):
                if ":" in item:
                    p_name, intake = item.split(":", 1)
                    p_name = p_name.strip()
                    try:
                        intake_val = int(intake.strip())
                    except ValueError:
                        intake_val = 60

                    prog_obj = db.query(InstituteProgram).filter(
                        InstituteProgram.institute_id == inst.id,
                        InstituteProgram.program.ilike(p_name)
                    ).first()
                    if prog_obj:
                        prog_obj.approved_intake = intake_val
                    else:
                        db.add(InstituteProgram(institute_id=inst.id, program=p_name, approved_intake=intake_val))

        db.commit()
        db.refresh(inst)

        log_event(
            db=db,
            record_type="Institute",
            record_id=inst.id,
            event_type="UPDATE" if is_update else "CREATE",
            actor=actor
        )

        inserted += 1

    return {
        "inserted": inserted,
        "rejected": rejected,
        "errors": errors
    }

def ingest_courses(file_bytes: bytes, filename: str, db: Session, actor: str = "institute_admin") -> dict:
    """
    Parses and ingests AICTE courses CSV matching real-world schema:
    level, program, course, affiliating_body, intake_prev, intake_current, approval_year,
    nri_approved, fn_oci_approved, aicte_permanent_id, source_file
    """
    df = _read_file_to_df(file_bytes, filename)
    col_map = _normalize_headers(list(df.columns), COURSE_HEADER_MAP)
    df = df.rename(columns=col_map)

    inserted = 0
    rejected = 0
    errors = []

    if "aicte_permanent_id" not in df.columns or "course" not in df.columns:
        return {
            "inserted": 0,
            "rejected": len(df),
            "errors": [f"Missing critical header (aicte_permanent_id or course). Headers found: {list(df.columns)}"]
        }

    for idx, row in df.iterrows():
        row_num = idx + 2
        perm_id = str(row.get("aicte_permanent_id", "")).strip() if pd.notna(row.get("aicte_permanent_id")) else ""
        course_name = str(row.get("course", "")).strip() if pd.notna(row.get("course")) else ""
        
        # Use intake_current (migrated from intake_2024_25)
        intake_raw = row.get("intake_current")
        if pd.isna(intake_raw) or str(intake_raw).strip() == "":
            intake_raw = row.get("intake_prev", "60")

        try:
            intake_val = int(float(str(intake_raw).strip()))
        except (ValueError, TypeError):
            intake_val = 60

        if not perm_id or not course_name:
            rejected += 1
            errors.append(f"Row {row_num}: Missing aicte_permanent_id or course.")
            continue

        # Find institute
        inst = db.query(Institute).filter(Institute.aicte_code == perm_id).first()
        if not inst:
            rejected += 1
            errors.append(f"Row {row_num}: Institute with aicte_permanent_id '{perm_id}' not found.")
            continue

        prog_obj = db.query(InstituteProgram).filter(
            InstituteProgram.institute_id == inst.id,
            InstituteProgram.program.ilike(course_name)
        ).first()

        if prog_obj:
            prog_obj.approved_intake = intake_val
        else:
            prog_obj = InstituteProgram(
                institute_id=inst.id,
                program=course_name,
                approved_intake=intake_val
            )
            db.add(prog_obj)

        inserted += 1

    db.commit()
    return {
        "inserted": inserted,
        "rejected": rejected,
        "errors": errors
    }

def ingest_students(file_bytes: bytes, filename: str, db: Session, default_institute_id: int | None = None, actor: str = "institute_admin") -> dict:
    df = _read_file_to_df(file_bytes, filename)
    col_map = _normalize_headers(list(df.columns), STUDENT_HEADER_MAP)
    df = df.rename(columns=col_map)

    inserted = 0
    rejected = 0
    errors = []

    required = ["apaar_id", "name", "program", "enrollment_year"]
    for req in required:
        if req not in df.columns:
            return {
                "inserted": 0,
                "rejected": len(df),
                "errors": [f"Missing critical header '{req}'. Found headers: {list(df.columns)}"]
            }

    for idx, row in df.iterrows():
        row_num = idx + 2
        apaar = str(row.get("apaar_id", "")).strip() if pd.notna(row.get("apaar_id")) else ""
        name = str(row.get("name", "")).strip() if pd.notna(row.get("name")) else ""
        prog = str(row.get("program", "")).strip() if pd.notna(row.get("program")) else ""
        year_raw = str(row.get("enrollment_year", "")).strip() if pd.notna(row.get("enrollment_year")) else ""
        dob = str(row.get("dob", "")).strip() if pd.notna(row.get("dob")) else None
        address = str(row.get("address", "")).strip() if pd.notna(row.get("address")) else None
        status = str(row.get("status", "Active")).strip() if pd.notna(row.get("status")) else "Active"

        # Resolve institute_id
        inst_id = default_institute_id
        if "institute_id" in row and pd.notna(row.get("institute_id")):
            inst_val = str(row.get("institute_id")).strip()
            if inst_val.isdigit():
                inst_id = int(inst_val)
            else:
                inst_match = db.query(Institute).filter(Institute.aicte_code == inst_val).first()
                if inst_match:
                    inst_id = inst_match.id

        if not inst_id:
            rejected += 1
            errors.append(f"Row {row_num}: Missing or invalid institute reference.")
            continue

        # Module 1 APAAR structural validation
        is_valid, reason = validate_apaar_format(apaar)
        if not is_valid:
            rejected += 1
            errors.append(f"Row {row_num} (APAAR: {apaar}): Invalid APAAR format - {reason}")
            continue

        if not name or not prog or not year_raw.isdigit():
            rejected += 1
            errors.append(f"Row {row_num}: Invalid student fields (name, program, or numeric year missing).")
            continue

        year = int(year_raw)

        student = db.query(Student).filter(Student.apaar_id == apaar).first()
        is_update = False
        if student:
            is_update = True
            student.name = name
            student.institute_id = inst_id
            student.program = prog
            student.enrollment_year = year
            student.status = status
            if dob: student.dob = dob
            if address: student.address = address
        else:
            student = Student(
                apaar_id=apaar,
                name=name,
                institute_id=inst_id,
                program=prog,
                enrollment_year=year,
                status=status,
                dob=dob,
                address=address
            )
            db.add(student)

        db.commit()
        db.refresh(student)

        # SIH Differentiator 1: Geographic Consistency Check
        geo_result = check_geographic_consistency(apaar_id=apaar, institute_id=inst_id, db=db)
        if not geo_result["match"]:
            geo_flag = FlaggedRecord(
                record_type="Student",
                record_id=str(student.id),
                flag_reason="geographic_mismatch",
                severity="needs_review",
                status="open"
            )
            db.add(geo_flag)

        # SIH Differentiator 2: Lifecycle Plausibility Check
        life_result = check_lifecycle_plausibility(apaar_id=apaar, admission_year=year)
        if not life_result["plausible"]:
            life_flag = FlaggedRecord(
                record_type="Student",
                record_id=str(student.id),
                flag_reason="lifecycle_implausible",
                severity=life_result["severity"],
                status="open"
            )
            db.add(life_flag)

        # SIH Security Differentiator: Honeytoken APAAR Check (run before dedup)
        honey_res = check_honeytoken(apaar_id=apaar, db=db, actor=actor)

        # Deduplication Engine Checks: Run both checks after APAAR/geo/lifecycle/honeytoken
        # 1. Exact Duplicate Check
        exact_dup = check_exact_duplicate(apaar_id=apaar, institute_id=inst_id, db=db, exclude_student_id=student.id)
        if exact_dup["is_duplicate"]:
            rec_pair = f"{student.id},{exact_dup['matched_record_id']}"
            dup_flag = FlaggedRecord(
                record_type="Student",
                record_id=rec_pair,
                flag_reason=f"APAAR Duplicate: {exact_dup['reason']}",
                severity=exact_dup["severity"],
                status="open"
            )
            db.add(dup_flag)
            db.commit()
            log_event(db, "FlaggedRecord", dup_flag.id, "FLAGGED", actor)

        # 2. Fuzzy Duplicate Check
        fuzzy_matches = check_fuzzy_duplicate(
            name=name,
            dob=dob,
            institute_id=inst_id,
            db=db,
            current_apaar_id=apaar,
            exclude_student_id=student.id
        )
        for fm in fuzzy_matches:
            rec_pair = f"{student.id},{fm['matched_student_id']}"
            fuz_flag = FlaggedRecord(
                record_type="Student",
                record_id=rec_pair,
                flag_reason=f"Suspected Identity Duplicate: {fm['reason']}",
                severity=fm["severity"],
                status="open"
            )
            db.add(fuz_flag)
            db.commit()
            log_event(db, "FlaggedRecord", fuz_flag.id, "FLAGGED", actor)

        if not geo_result["match"] or not life_result["plausible"]:
            db.commit()

        # Audit log event
        log_event(
            db=db,
            record_type="Student",
            record_id=student.id,
            event_type="UPDATE" if is_update else "CREATE",
            actor=actor
        )

        inserted += 1

    return {
        "inserted": inserted,
        "rejected": rejected,
        "errors": errors
    }
