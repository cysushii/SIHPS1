import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.models import Institute, InstituteProgram, Student
from validation.capacity_check import check_capacity
from engines.trust_score import compute_trust_score
from ingestion.parsers import ingest_courses

@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

def test_capacity_check_extended_approval_no_courses(db_session):
    # Institute with Extended Extension of Approval (no program rows)
    inst = Institute(
        aicte_code="1-EXTENDED-AUTO",
        name="Autonomous Deemed Institute with Extended Approval",
        state="Haryana",
        district="Gurgaon",
        approval_status="Approved"
    )
    db_session.add(inst)
    db_session.commit()

    # Call capacity_check
    res = check_capacity(
        institute_id=inst.id,
        program="Management",
        submitted_enrollment=120,
        db=db_session
    )

    assert res["status"] == "no_course_data_available"
    assert res["reason"] == "multi_year_extended_approval"
    assert res["approved_intake"] is None
    assert res["exceeded"] is False
    assert res["delta"] == 0
    assert "multi-year extended approval" in res["message"]

    # Verify trust score handles this without crashing and reports status
    score_res = compute_trust_score(inst.id, db_session)
    assert score_res["trust_score"] == 100
    assert score_res["breakdown"]["course_data_status"] == "no_course_data_available"
    assert score_res["breakdown"]["course_data_reason"] == "multi_year_extended_approval"

def test_ingest_courses_new_schema(db_session):
    inst = Institute(
        aicte_code="1-COURSE-TEST",
        name="Test Engineering College",
        state="Kerala",
        district="Ernakulam",
        approval_status="Approved"
    )
    db_session.add(inst)
    db_session.commit()

    # CSV with new schema: level, program, course, affiliating_body, intake_prev, intake_current, approval_year, nri_approved, fn_oci_approved, aicte_permanent_id, source_file
    csv_data = """level,program,course,affiliating_body,intake_prev,intake_current,approval_year,nri_approved,fn_oci_approved,aicte_permanent_id,source_file
UNDER GRADUATE,ENGINEERING AND TECHNOLOGY,ARTIFICIAL INTELLIGENCE,KTU,60,120,2024-25,Yes,No,1-COURSE-TEST,test_eoa.pdf
"""
    result = ingest_courses(csv_data.encode("utf-8"), "courses.csv", db_session)
    assert result["inserted"] == 1
    assert result["rejected"] == 0

    prog = db_session.query(InstituteProgram).filter(
        InstituteProgram.institute_id == inst.id,
        InstituteProgram.program == "ARTIFICIAL INTELLIGENCE"
    ).first()
    assert prog is not None
    assert prog.approved_intake == 120

