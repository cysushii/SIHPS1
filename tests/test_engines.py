import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.models import Institute, InstituteProgram, Student, AuditLog
from engines.trust_score import compute_trust_score
from engines.dedup import run_deduplication
from engines.graph_fraud import analyze_graph_fraud

@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

def test_trust_score_engine(db_session):
    inst = Institute(aicte_code="1-TEST", name="Test Engineering College")
    db_session.add(inst)
    db_session.flush()

    # Program: approved intake 10
    prog = InstituteProgram(institute_id=inst.id, program="CSE", approved_intake=10)
    db_session.add(prog)
    db_session.flush()

    # Enrolled: 15 students (overflow by 5)
    for i in range(15):
        s = Student(apaar_id=f"2400000000{i:02d}", name=f"Student {i}", institute_id=inst.id, program="CSE", enrollment_year=2024)
        db_session.add(s)
    db_session.commit()

    score_result = compute_trust_score(inst.id, db_session)
    assert score_result["trust_score"] < 100
    assert score_result["breakdown"]["capacity_mismatch_rate"] == 1.0

def test_dedup_exact_and_fuzzy(db_session):
    inst1 = Institute(aicte_code="1-A", name="College A")
    inst2 = Institute(aicte_code="1-B", name="College B")
    db_session.add_all([inst1, inst2])
    db_session.flush()

    # Exact APAAR duplicate across 2 institutes
    s1 = Student(apaar_id="241111222233", name="Same Student", institute_id=inst1.id, program="CSE", enrollment_year=2024)
    s2 = Student(apaar_id="241111222233", name="Same Student", institute_id=inst2.id, program="CSE", enrollment_year=2024)

    # Fuzzy duplicate: similar name (>90%), same DOB, distinct APAAR
    s3 = Student(apaar_id="249999888877", name="Rahul Sharma", institute_id=inst1.id, program="CSE", enrollment_year=2024, dob="2002-01-01")
    s4 = Student(apaar_id="249999888866", name="Rahul Sharma", institute_id=inst2.id, program="CSE", enrollment_year=2024, dob="2002-01-01")

    db_session.add_all([s1, s2, s3, s4])
    db_session.commit()

    flags = run_deduplication(db_session)
    assert len(flags) >= 2
    # flags include exact match dicts and fuzzy match dicts
    exact_matches = [f for f in flags if f.get("duplicate_type") == "cross_institute_duplicate"]
    fuzzy_matches = [f for f in flags if "similarity_score" in f]
    assert len(exact_matches) >= 1
    assert len(fuzzy_matches) >= 1

def test_graph_fraud_sybil_cluster(db_session):
    inst = Institute(aicte_code="1-C", name="College C")
    db_session.add(inst)
    db_session.flush()

    addr = "Hostel Block 4, Room 102"
    s1 = Student(apaar_id="241111111111", name="Alpha", institute_id=inst.id, program="CSE", enrollment_year=2024, address=addr)
    s2 = Student(apaar_id="242222222222", name="Beta", institute_id=inst.id, program="CSE", enrollment_year=2024, address=addr)
    s3 = Student(apaar_id="243333333333", name="Gamma", institute_id=inst.id, program="CSE", enrollment_year=2024, address=addr)

    db_session.add_all([s1, s2, s3])
    db_session.commit()

    clusters = analyze_graph_fraud(db_session)
    assert len(clusters) == 1
    assert clusters[0]["student_count"] == 3
