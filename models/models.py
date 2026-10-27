import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from .database import Base

class Institute(Base):
    __tablename__ = "institutes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    aicte_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    type = Column(String(100), nullable=True) # Central, State, Private, Deemed
    approval_status = Column(String(50), default="Approved")

    programs = relationship("InstituteProgram", back_populates="institute", cascade="all, delete-orphan")
    students = relationship("Student", back_populates="institute")
    trust_scores = relationship("TrustScoreHistory", back_populates="institute")
    users = relationship("User", back_populates="institute")

class InstituteProgram(Base):
    __tablename__ = "institute_programs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False)
    program = Column(String(100), nullable=False) # e.g. B.Tech Computer Science
    approved_intake = Column(Integer, nullable=False, default=60)

    institute = relationship("Institute", back_populates="programs")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False) # aicte_admin, institute_admin, verifier
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=True)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    institute = relationship("Institute", back_populates="users")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    apaar_id = Column(String(12), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False)
    program = Column(String(100), nullable=False)
    enrollment_year = Column(Integer, nullable=False)
    status = Column(String(50), default="Active") # Active, Graduated, Withdrawn
    dob = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    nri_status = Column(String(50), nullable=True) # NRI, OCI, Foreign, General

    institute = relationship("Institute", back_populates="students")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_type = Column(String(50), nullable=False)
    record_id = Column(String(50), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=False)
    timestamp = Column(String(40), nullable=False)
    actor = Column(String(100), nullable=False)

class TrustScoreHistory(Base):
    __tablename__ = "trust_score_histories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False)
    score = Column(Integer, nullable=False)
    computed_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    signal_breakdown = Column(JSON, nullable=False)

    institute = relationship("Institute", back_populates="trust_scores")

class FlaggedRecord(Base):
    __tablename__ = "flagged_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_type = Column(String(50), nullable=False)
    record_id = Column(String(50), nullable=False)
    flag_reason = Column(String(255), nullable=False)
    severity = Column(String(50), default="needs_review")
    status = Column(String(50), default="open") # open, reviewed
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

class HoneytokenID(Base):
    __tablename__ = "honeytoken_ids"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    apaar_id = Column(String(12), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    triggered = Column(Boolean, default=False)
    triggered_at = Column(DateTime, nullable=True)

class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(String(40), nullable=False)
    chain_head_hash = Column(String(64), nullable=False)

class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="draft")  # draft, pushed, under_review, approved, rejected, returned
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    pushed_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reject_reason = Column(Text, nullable=True)
    report_pdf_path = Column(String(512), nullable=True)
    report_signed = Column(Boolean, default=False)

    institute = relationship("Institute", backref="batches")
    students = relationship("StudentBatch", back_populates="batch", cascade="all, delete-orphan")
    verification_tokens = relationship("VerificationToken", back_populates="batch", cascade="all, delete-orphan")
    verification_runs = relationship("VerificationRun", back_populates="batch", cascade="all, delete-orphan")

class StudentBatch(Base):
    __tablename__ = "student_batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    batch = relationship("Batch", back_populates="students")
    student = relationship("Student", backref="batch_links")

class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False) # SHA-256 hash of token
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    expires_at = Column(DateTime, nullable=True)
    status = Column(String(30), default="pending")  # pending, verified, correction_requested, unresponsive
    responded_at = Column(DateTime, nullable=True)
    corrections = Column(JSON, nullable=True)
    correction_status = Column(String(30), nullable=True) # pending_review, accepted, rejected

    student = relationship("Student", backref="verification_tokens")
    batch = relationship("Batch", back_populates="verification_tokens")

class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(30), default="running") # running, completed, error
    summary = Column(JSON, nullable=True) # total, cleared, needs_review, blocked, course_capacities

    batch = relationship("Batch", back_populates="verification_runs")
    student_results = relationship("StudentVerificationResult", back_populates="run", cascade="all, delete-orphan")

class StudentVerificationResult(Base):
    __tablename__ = "student_verification_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("verification_runs.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    verdict = Column(String(30), nullable=False) # cleared, needs_review, blocked
    checks = Column(JSON, nullable=False) # dict of 10 checks with status, evidence, reason
    reviewer_decision = Column(String(50), nullable=True) # accepted, rejected, correction_requested
    reviewer_note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    audit_hash = Column(String(64), nullable=True)

    run = relationship("VerificationRun", back_populates="student_results")
    student = relationship("Student")

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    template = Column(String(50), nullable=False)
    intended_recipient = Column(String(255), nullable=False)
    actual_recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    status = Column(String(20), default="queued") # queued, sent, failed
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    sent_at = Column(DateTime, nullable=True)
