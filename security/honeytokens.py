import random
import datetime
from sqlalchemy.orm import Session
from models.models import HoneytokenID, FlaggedRecord
from security.hash_chain import log_event

"""
Honeytoken APAAR IDs (security/honeytokens.py)

Real-World Concept / Innovation:
Borrowed from cybersecurity and intrusion-detection systems (honeytokens / canary tokens).
In standard cybersecurity, honeytokens are fake credentials, email addresses, or database
records placed to detect unauthorized access or data leakage without legitimate traffic.

In this platform, we apply honeytokens to academic data provenance and fraud detection:
we generate syntactically authentic APAAR IDs following all official structural rules
(12 digits, valid year, valid state/district codes) that are reserved and NEVER issued
to any real student or authorized system. If an institution attempts to upload or claim
one of these IDs, it is near-certain evidence of data provenance fraud (e.g., test-dataset
leakage, automated scraping, credential fabrication, or malicious manipulation).
"""

def generate_honeytokens(count: int = 10) -> list[str]:
    """
    Generates `count` structurally valid APAAR-format IDs (12 digits, valid year 24,
    valid state code 99/unassigned district, and random sequence).
    Reserved and never assigned to real or synthetic students.
    """
    tokens = []
    # Use year prefix '24' and reserved test region code '9999'
    base_prefix = "249999"
    for i in range(count):
        # 6 random trailing digits
        seq = f"{random.randint(100000, 999999)}"
        tokens.append(f"{base_prefix}{seq}")
    return tokens

def seed_honeytokens(db: Session, count: int = 10) -> list[HoneytokenID]:
    """
    Seeds `count` honeytoken APAAR IDs into the HoneytokenID table if empty.
    """
    existing_count = db.query(HoneytokenID).count()
    if existing_count >= count:
        return db.query(HoneytokenID).all()

    needed = count - existing_count
    tokens = generate_honeytokens(needed)
    seeded = []
    for token in tokens:
        # Check duplicate
        if not db.query(HoneytokenID).filter(HoneytokenID.apaar_id == token).first():
            entry = HoneytokenID(apaar_id=token, triggered=False)
            db.add(entry)
            seeded.append(entry)
    db.commit()
    return db.query(HoneytokenID).all()

def check_honeytoken(apaar_id: str, db: Session, actor: str = "system") -> dict:
    """
    Checks if an uploaded apaar_id matches a reserved honeytoken canary.
    If matched:
    - Marks triggered=True and records triggered_at timestamp
    - Generates FlaggedRecord with flag_reason="honeytoken_triggered" and severity="critical"
      (our HIGHEST severity — near-certain evidence of data misuse, not a soft plausibility signal)
    - Records tamper-evident audit event via log_event()
    """
    if not apaar_id:
        return {"is_honeytoken": False, "severity": None}

    clean_id = str(apaar_id).strip()
    token_entry = db.query(HoneytokenID).filter(HoneytokenID.apaar_id == clean_id).first()

    if not token_entry:
        return {"is_honeytoken": False, "severity": None}

    # Honeytoken canary tripped!
    token_entry.triggered = True
    token_entry.triggered_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    # Create high-priority critical FlaggedRecord
    flag = FlaggedRecord(
        record_type="Honeytoken",
        record_id=clean_id,
        flag_reason="honeytoken_triggered",
        severity="critical",
        status="open"
    )
    db.add(flag)
    db.commit()

    # Log into hash chain audit trail
    log_event(
        db=db,
        record_type="Honeytoken",
        record_id=token_entry.id,
        event_type="FLAGGED",
        actor=actor
    )

    return {
        "is_honeytoken": True,
        "severity": "critical",
        "reason": "Honeytoken canary triggered: reserved unassigned APAAR ID detected in upload."
    }

