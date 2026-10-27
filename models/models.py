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
    type = Column(String(100), nullable=True) # e.g. Central, State, Private, Deemed
    approval_status = Column(String(50), default="Approved")

    programs = relationship("InstituteProgram", back_populates="institute", cascade="all, delete-orphan")
    students = relationship("Student", back_populates="institute")
    trust_scores = relationship("TrustScoreHistory", back_populates="institute")

class InstituteProgram(Base):
    __tablename__ = "institute_programs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False)
    program = Column(String(100), nullable=False) # e.g. B.Tech Computer Science
    approved_intake = Column(Integer, nullable=False, default=60)

    institute = relationship("Institute", back_populates="programs")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    apaar_id = Column(String(12), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False)
    program = Column(String(100), nullable=False)
    enrollment_year = Column(Integer, nullable=False)
    status = Column(String(50), default="Active") # Active, Graduated, Withdrawn
    dob = Column(String(20), nullable=True) # YYYY-MM-DD or DD/MM/YYYY for dedup
    address = Column(String(255), nullable=True) # For graph fraud analysis
    email = Column(String(255), nullable=True) # Student email for verification emails

    institute = relationship("Institute", back_populates="students")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_type = Column(String(50), nullable=False)
    record_id = Column(String(50), nullable=False)
    event_type = Column(String(50), nullable=False) # CREATE, UPDATE, DELETE, VERIFY, FLAGGED, REVIEWED
    event_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=False)
    timestamp = Column(String(40), nullable=False) # ISO timestamp
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
    record_type = Column(String(50), nullable=False) # Student, Institute, Cluster
    record_id = Column(String(50), nullable=False)
    flag_reason = Column(String(255), nullable=False)
    severity = Column(String(50), default="needs_review") # needs_review, high, confirmed, critical
    status = Column(String(50), default="open") # open, reviewed
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

class HoneytokenID(Base):
    """
    Intrusion detection / canary token table for reserved APAAR IDs.
    Any appearance of these IDs in real uploads is definitive proof of data misuse.
    """
    __tablename__ = "honeytoken_ids"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    apaar_id = Column(String(12), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    triggered = Column(Boolean, default=False)
    triggered_at = Column(DateTime, nullable=True)

class Checkpoint(Base):
    """
    Query-convenience replica for external hash-chain anchoring.
    The primary source of truth is /data/checkpoints.log.
    """
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(String(40), nullable=False)
    chain_head_hash = Column(String(64), nullable=False)


class Batch(Base):
    """
    Represents a submission batch that an institute creates, populates with
    students, then pushes to AICTE for review.
    Lifecycle: draft -> pushed -> under_review -> approved | rejected
    """
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="draft")  # draft|pushed|under_review|approved|rejected
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    pushed_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reject_reason = Column(Text, nullable=True)
    report_pdf_path = Column(String(512), nullable=True)
    report_signed = Column(Boolean, default=False)

    institute = relationship("Institute", backref="batches")
    students = relationship("StudentBatch", back_populates="batch", cascade="all, delete-orphan")
    verification_tokens = relationship("VerificationToken", back_populates="batch", cascade="all, delete-orphan")


class StudentBatch(Base):
    """Many-to-many link between students and batches."""
    __tablename__ = "student_batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    batch = relationship("Batch", back_populates="students")
    student = relationship("Student", backref="batch_links")


class VerificationToken(Base):
    """
    Per-student self-verification token sent (or shown in demo UI) after batch creation.
    Student uses this token to confirm or correct their record via /verify/token/{token}.
    Single-use, configurable expiry.
    """
    __tablename__ = "verification_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token = Column(String(64), unique=True, index=True, nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    expires_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")  # pending|verified|unresponsive
    responded_at = Column(DateTime, nullable=True)
    corrections = Column(JSON, nullable=True)  # student-submitted corrections as JSON

    student = relationship("Student", backref="verification_tokens")
    batch = relationship("Batch", back_populates="verification_tokens")


class EmailLog(Base):
    """
    Audit log for every email send attempt (real or mocked/dry-run).
    """
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    template = Column(String(50), nullable=False)  # verification|completion
    to_address = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    status = Column(String(20), default="queued")  # queued|sent|failed|skipped
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    sent_at = Column(DateTime, nullable=True)
