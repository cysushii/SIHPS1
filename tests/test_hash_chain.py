import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.models import AuditLog
from security.hash_chain import log_event, verify_chain

@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

def test_hash_chain_append_and_verify(db_session):
    # Empty chain is valid
    is_valid, broken = verify_chain(db_session)
    assert is_valid is True
    assert broken is None

    # Log 3 events
    log1 = log_event(db_session, "Student", 1, "CREATE", "admin_user")
    log2 = log_event(db_session, "Student", 1, "UPDATE", "admin_user")
    log3 = log_event(db_session, "Institute", 2, "CREATE", "super_admin")

    assert log1.prev_hash == "0" * 64
    assert log2.prev_hash == log1.event_hash
    assert log3.prev_hash == log2.event_hash

    is_valid, broken = verify_chain(db_session)
    assert is_valid is True
    assert broken is None

def test_hash_chain_detects_tamper(db_session):
    log1 = log_event(db_session, "Student", 101, "CREATE", "admin")
    log2 = log_event(db_session, "Student", 102, "CREATE", "admin")

    # Tamper with log1 actor directly in DB
    log1.actor = "malicious_hacker"
    db_session.commit()

    is_valid, broken_id = verify_chain(db_session)
    assert is_valid is False
    assert broken_id == log1.id

