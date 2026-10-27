import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.models import Institute, Student
from engines.dedup import check_exact_duplicate, check_fuzzy_duplicate

@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

def test_check_exact_duplicate_different_institute(db_session):
    inst1 = Institute(aicte_code="1-A", name="College A")
    inst2 = Institute(aicte_code="1-B", name="College B")
    db_session.add_all([inst1, inst2])
    db_session.commit()

    # Pre-existing student in Institute 1
    s1 = Student(
        apaar_id="241234567890",
        name="Aarav Sharma",
        institute_id=inst1.id,
        program="CSE",
        enrollment_year=2024
    )
    db_session.add(s1)
    db_session.commit()

    # Checking same APAAR for Institute 2 (different institute -> confirmed)
    res = check_exact_duplicate("241234567890", inst2.id, db_session)
    assert res["is_duplicate"] is True
    assert res["duplicate_type"] == "cross_institute_duplicate"
    assert res["severity"] == "confirmed"
    assert res["matched_record_id"] == s1.id

def test_check_exact_duplicate_same_institute(db_session):
    inst1 = Institute(aicte_code="1-A", name="College A")
    db_session.add(inst1)
    db_session.commit()

    s1 = Student(
        apaar_id="241234567890",
        name="Aarav Sharma",
        institute_id=inst1.id,
        program="CSE",
        enrollment_year=2024
    )
    db_session.add(s1)
    db_session.commit()

    # Checking same APAAR for Institute 1 (same institute -> needs_review re-upload)
    res = check_exact_duplicate("241234567890", inst1.id, db_session)
    assert res["is_duplicate"] is True
    assert res["duplicate_type"] == "same_institute_reupload"
    assert res["severity"] == "needs_review"
    assert res["matched_record_id"] == s1.id

def test_check_fuzzy_duplicate(db_session):
    inst = Institute(aicte_code="1-A", name="College A")
    db_session.add(inst)
    db_session.commit()

    s1 = Student(
        apaar_id="241111111111",
        name="Rohan Verma",
        dob="2002-05-15",
        institute_id=inst.id,
        program="CSE",
        enrollment_year=2024
    )
    db_session.add(s1)
    db_session.commit()

    # Fuzzy match with same DOB, high similarity (>90), but different APAAR
    matches = check_fuzzy_duplicate(
        name="Rohan Verma",
        dob="2002-05-15",
        institute_id=inst.id,
        db=db_session,
        current_apaar_id="242222222222",
        threshold=90.0
    )

    assert len(matches) == 1
    assert matches[0]["matched_student_id"] == s1.id
    assert matches[0]["severity"] == "needs_review"
    assert matches[0]["similarity_score"] >= 90.0

