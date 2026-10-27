import pytest
import io
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.models import Institute, Student, FlaggedRecord
from ingestion.parsers import ingest_students

@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

def test_ingest_students_creates_geo_and_lifecycle_flags(db_session):
    # Setup institute in Delhi (Code 07)
    inst = Institute(aicte_code="1-DEL-01", name="Delhi Institute", state="Delhi", district="South Delhi")
    db_session.add(inst)
    db_session.commit()

    # Create CSV data with:
    # 1. Geographic mismatch: APAAR with Maharashtra code 2701 (digits 3-6)
    # 2. Lifecycle short gap: year 22, admitted 2024 (gap = 2 < 8)
    csv_content = """apaar_id,name,program,enrollment_year,institute_id
222701123456,Rohan Sharma,B.Tech Computer Science,2024,1
"""
    result = ingest_students(
        file_bytes=csv_content.encode("utf-8"),
        filename="students.csv",
        db=db_session,
        actor="test_admin"
    )

    assert result["inserted"] == 1
    assert result["rejected"] == 0

    student = db_session.query(Student).filter(Student.apaar_id == "222701123456").first()
    assert student is not None

    flags = db_session.query(FlaggedRecord).filter(FlaggedRecord.record_id == str(student.id)).all()
    flag_reasons = [f.flag_reason for f in flags]
    assert "geographic_mismatch" in flag_reasons
    assert "lifecycle_implausible" in flag_reasons

