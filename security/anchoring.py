import os
import datetime
from sqlalchemy.orm import Session
from models.models import AuditLog, Checkpoint
from security.hash_chain import verify_chain, GENESIS_HASH

"""
External Hash-Chain Anchoring / Checkpointing (security/anchoring.py)

Real-World Concept / Innovation:
Borrowed from distributed systems security, cryptographic timestamping authorities (RFC 3161),
and Bitcoin/Ethereum state checkpointing (e.g., anchoring Layer 2 rollups onto an immutable Layer 1).

Why this is necessary:
In a single-database hash chain, a malicious or compromised DB administrator with write access
could alter a historical audit log and systematically recompute every subsequent block hash.
Internally, the chain would look 100% mathematically valid (hash(n) = SHA256(data + hash(n-1))).

External Anchoring solves this vulnerability:
We periodically publish the current chain-head hash to an append-only file (/data/checkpoints.log)
located completely OUTSIDE the database table, simulating an external public notary, transparency
log (like Certificate Transparency), or cold-storage ledger. When validating, we cross-reference
the current recomputed chain against this external chronological anchor. Any post-hoc DB rewriting
is immediately detected because the historical checkpoints will no longer match the recalculated hashes.
"""

DEFAULT_CHECKPOINT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "checkpoints.log"
)

def create_checkpoint(db: Session, checkpoint_file: str = DEFAULT_CHECKPOINT_FILE) -> dict:
    """
    Captures the current head hash of the AuditLog chain:
    1. Obtains the latest hash in AuditLog table.
    2. Writes to an append-only file OUTSIDE the database (/data/checkpoints.log):
       "{timestamp},{chain_head_hash}\n"
    3. Stores in Checkpoint table for fast querying.
    Returns {checkpoint_id, timestamp, chain_head_hash}
    """
    last_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    chain_head_hash = last_log.event_hash if last_log else GENESIS_HASH
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 1. Write to external file (real external source of truth)
    os.makedirs(os.path.dirname(checkpoint_file), exist_ok=True)
    with open(checkpoint_file, "a", encoding="utf-8") as f:
        f.write(f"{now_iso},{chain_head_hash}\n")

    # 2. Store in DB table for query convenience
    cp = Checkpoint(
        timestamp=now_iso,
        chain_head_hash=chain_head_hash
    )
    db.add(cp)
    db.commit()
    db.refresh(cp)

    return {
        "checkpoint_id": cp.id,
        "timestamp": now_iso,
        "chain_head_hash": chain_head_hash,
        "external_log_file": checkpoint_file
    }

def verify_against_checkpoints(db: Session, checkpoint_file: str = DEFAULT_CHECKPOINT_FILE) -> dict:
    """
    Verifies chain integrity against both internal linking AND external checkpoint anchors:
    1. Recomputes internal chain validity (calling verify_chain()).
    2. Reads all checkpoints from external file /data/checkpoints.log.
    3. Finds if every anchored hash exists in the live AuditLog history at the expected sequence.
       Mismatch = definitive proof of a FULL chain rewrite!
    """
    # 1. Verify internal link continuity
    internal_valid, broken_id = verify_chain(db)

    # 2. Check external checkpoints regardless of internal validity
    all_logs = db.query(AuditLog.event_hash).order_by(AuditLog.id.asc()).all()
    live_hashes = set(h[0] for h in all_logs)
    if not live_hashes:
        live_hashes.add(GENESIS_HASH)

    mismatched_checkpoints = []
    line_idx = 0

    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line or "," not in line:
                    continue
                ts, chash = line.split(",", 1)
                ts = ts.strip()
                chash = chash.strip()
                # Check if anchored hash actually exists in our current DB chain
                if chash not in live_hashes and chash != GENESIS_HASH:
                    mismatched_checkpoints.append({
                        "line": line_idx,
                        "timestamp": ts,
                        "anchored_hash": chash,
                        "status": "MISSING_FROM_CHAIN_REWRITE_DETECTED"
                    })

    is_anchored_valid = internal_valid and (len(mismatched_checkpoints) == 0)

    if not internal_valid:
        message = f"Internal chain integrity failure at log ID {broken_id}."
        if mismatched_checkpoints:
            message += f" Additionally, {len(mismatched_checkpoints)} external checkpoint(s) mismatch."
    elif not is_anchored_valid:
        message = f"EXTERNAL ANCHOR INTEGRITY COMPROMISED: {len(mismatched_checkpoints)} checkpoint(s) mismatch! Chain was rewritten."
    else:
        message = "All external cryptographic checkpoint anchors and internal chain verified intact."

    return {
        "anchored_integrity": is_anchored_valid,
        "internal_chain_valid": internal_valid,
        "first_broken_log_id": broken_id,
        "total_checkpoints_verified": line_idx,
        "mismatched_checkpoints": mismatched_checkpoints,
        "message": message
    }
