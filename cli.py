"""
CLI commands for SIH26263:
1. Load official reference datasets (aicte_institutes, aicte_courses, aicte_closures, institutes_reference)
2. Create/manage users with hashed passwords
3. Reset database tables and initialize hash-chain genesis block
"""
import sys
import os
import argparse
import hashlib
import pandas as pd
from sqlalchemy.orm import Session
from models.database import engine, Base, SessionLocal
from models.models import (
    Institute, InstituteProgram, User, AuditLog, Checkpoint, HoneytokenID
)
from security.hash_chain import GENESIS_HASH, log_event
from security.honeytokens import seed_honeytokens
from services.formatters import format_title_case

def hash_password(password: str) -> str:
    """Hash password with SHA-256 + salt."""
    salt = "sih26263_secure_salt_"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def reset_db():
    """Drop and recreate all tables cleanly."""
    print("Resetting database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Initialize fresh genesis block in audit log
    db = SessionLocal()
    genesis = AuditLog(
        record_type="System",
        record_id="0",
        event_type="GENESIS",
        event_hash=GENESIS_HASH,
        prev_hash="0" * 64,
        timestamp=pd.Timestamp.now("UTC").isoformat(),
        actor="system_init"
    )
    db.add(genesis)
    db.commit()

    # Seed system honeytokens (security canaries)
    seed_honeytokens(db, count=10)
    db.close()
    print("Database reset complete. Audit log initialized with Genesis block. Honeytokens generated.")

def load_reference_data():
    """Load AICTE reference CSVs."""
    db = SessionLocal()
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    # 1. aicte_institutes.csv
    inst_csv = os.path.join(data_dir, "aicte_institutes.csv")
    if os.path.exists(inst_csv):
        print(f"Loading {inst_csv}...")
        df_inst = pd.read_csv(inst_csv)
        for _, row in df_inst.iterrows():
            code = str(row.get("aicte_permanent_id") or row.get("aicte_code") or "").strip()
            name = str(row.get("name") or row.get("institution_name") or "").strip()
            if not code or not name:
                continue
            existing = db.query(Institute).filter(Institute.aicte_code == code).first()
            if not existing:
                inst = Institute(
                    aicte_code=code,
                    name=name,
                    state=str(row.get("state") or "").strip() or None,
                    district=str(row.get("district") or "").strip() or None,
                    type=str(row.get("type") or "Approved").strip() or None,
                    approval_status="Approved"
                )
                db.add(inst)
        db.commit()

    # 2. aicte_courses.csv
    courses_csv = os.path.join(data_dir, "aicte_courses.csv")
    if os.path.exists(courses_csv):
        print(f"Loading {courses_csv}...")
        df_courses = pd.read_csv(courses_csv)
        for _, row in df_courses.iterrows():
            inst_code = str(row.get("aicte_permanent_id") or "").strip()
            prog_name = str(row.get("course") or row.get("program") or "").strip()
            intake_raw = row.get("intake_current") or row.get("approved_intake") or 60
            try:
                intake = int(float(intake_raw))
            except (ValueError, TypeError):
                intake = 60

            if inst_code and prog_name:
                inst = db.query(Institute).filter(Institute.aicte_code == inst_code).first()
                if inst:
                    existing_prog = db.query(InstituteProgram).filter(
                        InstituteProgram.institute_id == inst.id,
                        InstituteProgram.program.ilike(prog_name.strip())
                    ).first()
                    if not existing_prog:
                        db.add(InstituteProgram(
                            institute_id=inst.id,
                            program=prog_name.strip(),
                            approved_intake=intake
                        ))
        db.commit()

    inst_count = db.query(Institute).count()
    prog_count = db.query(InstituteProgram).count()
    db.close()
    print(f"Reference data loaded: {inst_count} institutions, {prog_count} approved programmes.")

def list_institutes():
    """List loaded institutes with their ID, AICTE code, and name."""
    db = SessionLocal()
    institutes = db.query(Institute).order_by(Institute.id.asc()).all()
    if not institutes:
        print("No institutes found in database. Run 'python cli.py load-reference-data' first.")
        db.close()
        return

    print("\nLoaded Institutions:")
    print(f"{'ID':<6} {'AICTE Code':<16} {'Institution Name'}")
    print("-" * 70)
    for inst in institutes:
        name_clean = format_title_case(inst.name)
        print(f"{inst.id:<6} {inst.aicte_code:<16} {name_clean}")
    print(f"\nTotal: {len(institutes)} institution(s)\n")
    db.close()

def create_user(email: str, password: str, role: str, institute_id: int | None = None, full_name: str | None = None):
    db = SessionLocal()
    existing = db.query(User).filter(User.email.ilike(email.strip())).first()
    if existing:
        print(f"Error: User with email {email} already exists.")
        db.close()
        return

    pwd_hash = hash_password(password)
    user = User(
        email=email.strip().lower(),
        password_hash=pwd_hash,
        role=role,
        institute_id=institute_id,
        full_name=full_name or format_title_case(email.split('@')[0])
    )
    db.add(user)
    db.commit()
    print(f"Created user: {user.email} (Role: {user.role}, Institute ID: {user.institute_id})")
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SIH26263 Platform CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("reset-db", help="Reset DB & recreate fresh tables and Genesis block")
    subparsers.add_parser("load-reference-data", help="Load official AICTE approval and reference CSVs")
    subparsers.add_parser("list-institutes", help="List all loaded institutions with their IDs and names")

    user_parser = subparsers.add_parser("create-user", help="Create a platform user account")
    user_parser.add_argument("--email", required=True, help="User email address")
    user_parser.add_argument("--password", required=True, help="User password")
    user_parser.add_argument("--role", required=True, choices=["aicte_admin", "institute_admin", "verifier"], help="Account role")
    user_parser.add_argument("--institute-id", type=int, default=None, help="Institute ID (for institute_admin)")
    user_parser.add_argument("--name", type=str, default=None, help="Full name")

    args = parser.parse_args()

    if args.command == "reset-db":
        reset_db()
    elif args.command == "load-reference-data":
        load_reference_data()
    elif args.command == "list-institutes":
        list_institutes()
    elif args.command == "create-user":
        create_user(args.email, args.password, args.role, args.institute_id, args.name)
    else:
        parser.print_help()
