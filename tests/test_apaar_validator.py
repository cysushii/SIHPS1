import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.models import Institute
from validation.apaar_validator import (
    validate_apaar_format,
    check_geographic_consistency,
    check_lifecycle_plausibility,
)

@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

def test_valid_apaar():
    is_valid, msg = validate_apaar_format("241234567890")
    assert is_valid is True
    assert "Valid" in msg

def test_invalid_length():
    is_valid, msg = validate_apaar_format("241234")
    assert is_valid is False
    assert "12 digits" in msg

def test_non_numeric():
    is_valid, msg = validate_apaar_format("24123456789A")
    assert is_valid is False
    assert "numeric" in msg

def test_future_unreasonable_year():
    is_valid, msg = validate_apaar_format("991234567890")
    assert is_valid is False
    assert "year prefix" in msg

def test_identical_digits():
    is_valid, msg = validate_apaar_format("111111111111")
    assert is_valid is False
    assert "identical digits" in msg

def test_sequential_digits():
    is_valid, msg = validate_apaar_format("012345678901")
    assert is_valid is False
    assert "sequential series" in msg

# --- FUNCTION 1: Geographic Consistency Check Tests ---
def test_geographic_consistency_match(db_session):
    # Institute in Maharashtra (State code 27, district 01 Mumbai Suburban)
    inst = Institute(aicte_code="1-TEST-MUM", name="Test College Mumbai", state="Maharashtra", district="Mumbai Suburban")
    db_session.add(inst)
    db_session.commit()

    # APAAR ID with year 24, geo code 2701 (digits 3-6)
    apaar_id = "242701567890"
    res = check_geographic_consistency(apaar_id, inst.id, db_session)

    assert res["match"] is True
    assert "Maharashtra" in res["embedded_location"]
    assert "Mumbai Suburban" in res["embedded_location"]
    assert "Maharashtra" in res["institute_location"]
    assert "soft signal" in res["note"]

def test_geographic_consistency_mismatch(db_session):
    # Institute in Delhi (State code 07)
    inst = Institute(aicte_code="1-TEST-DEL", name="Test College Delhi", state="Delhi", district="South Delhi")
    db_session.add(inst)
    db_session.commit()

    # APAAR ID with Maharashtra code 2701
    apaar_id = "242701567890"
    res = check_geographic_consistency(apaar_id, inst.id, db_session)

    assert res["match"] is False
    assert "Maharashtra" in res["embedded_location"]
    assert "Delhi" in res["institute_location"]

# --- FUNCTION 2: Lifecycle Plausibility Check Tests ---
def test_lifecycle_plausibility_valid():
    # APAAR year 2012 ("12"), admission 2024 -> gap = 12 years (plausible schooling to higher-ed)
    res = check_lifecycle_plausibility("121234567890", 2024)
    assert res["plausible"] is True
    assert res["gap_years"] == 12
    assert res["severity"] == "none"

def test_lifecycle_plausibility_negative_gap_impossible():
    # APAAR year 2024 ("24"), admission claimed in 2020 -> gap = -4 (APAAR registered after admission)
    res = check_lifecycle_plausibility("241234567890", 2020)
    assert res["plausible"] is False
    assert res["gap_years"] == -4
    assert res["severity"] == "implausible"
    assert "after claimed admission" in res["reason"]

def test_lifecycle_plausibility_excessive_gap():
    # APAAR year 1995 ("95" -> 1995), admission 2025 -> gap = 30 years (> 25)
    res = check_lifecycle_plausibility("951234567890", 2025)
    assert res["plausible"] is False
    assert res["gap_years"] == 30
    assert res["severity"] == "implausible"

def test_lifecycle_plausibility_needs_review_short_gap():
    # APAAR year 2022 ("22"), admission 2025 -> gap = 3 years (< 8 years)
    res = check_lifecycle_plausibility("221234567890", 2025)
    assert res["plausible"] is False
    assert res["gap_years"] == 3
    assert res["severity"] == "needs_review"
