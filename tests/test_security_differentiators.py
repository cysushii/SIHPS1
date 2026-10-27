import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base
from models.models import HoneytokenID, FlaggedRecord, AuditLog
from security.honeytokens import generate_honeytokens, seed_honeytokens, check_honeytoken
from security.anchoring import create_checkpoint, verify_against_checkpoints
from security.hash_chain import log_event

@pytest.fixture
def db_session(tmp_path):
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session, tmp_path
    session.close()

def test_honeytoken_generation_and_trigger(db_session):
    session, _ = db_session
    # Seed 10 honeytokens
    seeded = seed_honeytokens(session, count=10)
    assert len(seeded) == 10
    assert all(len(t.apaar_id) == 12 for t in seeded)

    canary = seeded[0].apaar_id
    res = check_honeytoken(canary, session, actor="suspicious_uploader")
    assert res["is_honeytoken"] is True
    assert res["severity"] == "critical"

    # Verify FlaggedRecord created with critical severity
    flag = session.query(FlaggedRecord).filter(FlaggedRecord.record_id == canary).first()
    assert flag is not None
    assert flag.flag_reason == "honeytoken_triggered"
    assert flag.severity == "critical"

def test_external_checkpoint_and_verification(db_session):
    session, tmp_path = db_session
    log_file = str(tmp_path / "checkpoints.log")

    # Generate some audit logs
    log1 = log_event(session, "Student", 1, "CREATE", "admin")
    log2 = log_event(session, "Student", 2, "CREATE", "admin")

    # Create external checkpoint
    cp = create_checkpoint(session, checkpoint_file=log_file)
    assert cp["chain_head_hash"] == log2.event_hash
    assert os.path.exists(log_file)

    # Verify against checkpoints (intact)
    ver_res = verify_against_checkpoints(session, checkpoint_file=log_file)
    assert ver_res["anchored_integrity"] is True
    assert len(ver_res["mismatched_checkpoints"]) == 0

    # Simulate attacker rewriting the database chain from block 1 forward
    log1.actor = "malicious_insider"
    log1.event_hash = "rewritten_hash_1234567890abcdef1234567890abcdef1234567890abcdef12345678"
    log2.prev_hash = log1.event_hash
    log2.event_hash = "rewritten_hash_9876543210fedcba9876543210fedcba9876543210fedcba98765432"
    session.commit()

    # External checkpoint verification MUST detect the rewrite
    tamper_res = verify_against_checkpoints(session, checkpoint_file=log_file)
    assert tamper_res["anchored_integrity"] is False
    assert len(tamper_res["mismatched_checkpoints"]) > 0

