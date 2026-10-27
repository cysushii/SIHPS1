import os
import pandas as pd
from sqlalchemy.orm import Session
from models.models import Institute, InstituteProgram, Student

DEFAULT_COURSES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "aicte_courses.csv")

def check_capacity(
    institute_id: int,
    program: str,
    submitted_enrollment: int | None = None,
    db: Session | None = None,
    courses_csv_path: str = DEFAULT_COURSES_PATH
) -> dict:
    """
    Checks if submitted_enrollment exceeds approved_intake for an institute program.
    
    Real-world AICTE edge case handling:
    Some real institutes (e.g. Velagapudi Siddhartha, MDI Gurgaon) have an "Extended Extension of Approval"
    (multi-year grant for autonomous/deemed-university institutes) with only an institute-level row and
    NO course/intake table rows at all.
    If an institute has zero rows in InstituteProgram and zero rows in aicte_courses.csv, this function
    returns a clear status:
        {
            "status": "no_course_data_available",
            "reason": "multi_year_extended_approval",
            "institute_id": institute_id,
            "program": program,
            "approved_intake": None,
            "submitted_enrollment": submitted_enrollment,
            "exceeded": False,
            "delta": 0,
            "message": "Institute has multi-year extended approval with no granular course intake table."
        }
    instead of crashing, erroring, or misleading with a false zero.
    """
    if db is None:
        raise ValueError("A database session (db) is required to lookup approved_intake.")

    # 1. Check if the institute exists in DB
    inst = db.query(Institute).filter(Institute.id == institute_id).first()
    aicte_code = inst.aicte_code if inst else None

    # 2. Check total programs in DB for this institute
    total_inst_programs = db.query(InstituteProgram).filter(
        InstituteProgram.institute_id == institute_id
    ).count()

    # 3. If zero programs in DB, also check if courses exist in aicte_courses.csv for this permanent ID
    has_courses_in_csv = False
    if total_inst_programs == 0 and aicte_code and os.path.exists(courses_csv_path):
        try:
            cdf = pd.read_csv(courses_csv_path, dtype=str)
            if "aicte_permanent_id" in cdf.columns:
                matches = cdf[cdf["aicte_permanent_id"] == aicte_code]
                if not matches.empty:
                    has_courses_in_csv = True
        except Exception:
            pass

    # If institute has no course rows at all (Extended Extension of Approval multi-year grant)
    if total_inst_programs == 0 and not has_courses_in_csv:
        if submitted_enrollment is None:
            submitted_enrollment = db.query(Student).filter(
                Student.institute_id == institute_id,
                Student.program.ilike(program.strip()),
                Student.status == "Active"
            ).count()

        return {
            "status": "no_course_data_available",
            "reason": "multi_year_extended_approval",
            "institute_id": institute_id,
            "program": program,
            "approved_intake": None,
            "submitted_enrollment": submitted_enrollment,
            "exceeded": False,
            "delta": 0,
            "message": "Institute has multi-year extended approval with no granular course intake table."
        }

    # 4. Standard program intake lookup
    prog = db.query(InstituteProgram).filter(
        InstituteProgram.institute_id == institute_id,
        InstituteProgram.program.ilike(program.strip())
    ).first()

    approved_intake = prog.approved_intake if prog else 0

    if submitted_enrollment is None:
        submitted_enrollment = db.query(Student).filter(
            Student.institute_id == institute_id,
            Student.program.ilike(program.strip()),
            Student.status == "Active"
        ).count()

    delta = max(0, submitted_enrollment - approved_intake)
    exceeded = submitted_enrollment > approved_intake

    return {
        "status": "active",
        "reason": None,
        "institute_id": institute_id,
        "program": program,
        "approved_intake": approved_intake,
        "submitted_enrollment": submitted_enrollment,
        "exceeded": exceeded,
        "delta": delta,
    }
