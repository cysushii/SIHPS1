import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.models import AuditLog

GENESIS_HASH = "0" * 64

def compute_hash(event_data: dict, prev_hash: str) -> str:
    """Computes SHA256(json.dumps(event_data, sort_keys=True) + prev_hash)"""
    serialized = json.dumps(event_data, sort_keys=True)
    payload = f"{serialized}{prev_hash}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def log_event(db: Session, record_type: str, record_id: str | int, event_type: str, actor: str) -> AuditLog:
    """
    Appends an immutable tamper-evident event to the AuditLog hash chain.
    1. Builds event_data = {record_type, record_id, event_type, actor, timestamp}
    2. Gets the hash of the LAST entry in AuditLog table (or "0"*64 if empty)
    3. Computes new_hash = SHA256(json.dumps(event_data) + prev_hash)
    4. Inserts new AuditLog row with event_hash and prev_hash
    """
    # Fetch the latest log to establish chaining
    last_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    prev_hash = last_log.event_hash if last_log else GENESIS_HASH

    now_iso = datetime.now(timezone.utc).isoformat()
    event_data = {
        "record_type": str(record_type),
        "record_id": str(record_id),
        "event_type": str(event_type),
        "actor": str(actor),
        "timestamp": now_iso,
    }

    new_hash = compute_hash(event_data, prev_hash)

    log_entry = AuditLog(
        record_type=str(record_type),
        record_id=str(record_id),
        event_type=str(event_type),
        event_hash=new_hash,
        prev_hash=prev_hash,
        timestamp=now_iso,
        actor=str(actor),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    # Checkpoint every 20 audit log entries
    if log_entry.id % 20 == 0:
        try:
            from security.anchoring import create_checkpoint
            create_checkpoint(db)
        except Exception:
            pass

    return log_entry

def verify_chain(db: Session) -> tuple[bool, int | None]:
    """
    Walks the entire AuditLog table in order, recomputes each hash from stored data + prev_hash,
    and returns (is_valid: bool, first_broken_index: int | None).
    """
    logs = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    if not logs:
        return True, None

    expected_prev = GENESIS_HASH
    for log in logs:
        # Re-check that stored prev_hash matches what previous block produced
        if log.prev_hash != expected_prev:
            return False, log.id

        event_data = {
            "record_type": log.record_type,
            "record_id": log.record_id,
            "event_type": log.event_type,
            "actor": log.actor,
            "timestamp": log.timestamp,
        }
        recomputed_hash = compute_hash(event_data, log.prev_hash)
        if recomputed_hash != log.event_hash:
            return False, log.id

        expected_prev = log.event_hash

    return True, None

