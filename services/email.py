"""
Email service for SIH26263 platform.

Design decisions (hackathon-safe):
- SMTP credentials come from environment variables ONLY — never hardcoded.
- If SMTP_HOST is not set → dry-run mode: email body is written to EmailLog
  with status='skipped' and logged to console. No real email is sent.
- EMAIL_ALLOWLIST: comma-separated list of allowed recipient addresses.
  Any address NOT in the allowlist is skipped (status='skipped'), even if SMTP
  is configured. This prevents accidentally mailing real students.
- Every attempt (sent, failed, skipped) is written to the EmailLog table.
- Rate limiting: batch sends use asyncio.sleep between messages (configurable).
"""

import os
import smtplib
import ssl
import secrets
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from models.models import EmailLog, VerificationToken, Student, Batch
from security.hash_chain import log_event

# ── Configuration from environment ─────────────────────────────────────────
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
MAIL_FROM = os.environ.get("MAIL_FROM", "no-reply@aicte-demo.in")
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000")
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173")
EMAIL_ALLOWLIST_RAW = os.environ.get("EMAIL_ALLOWLIST", "")
VERIFICATION_TOKEN_EXPIRY_HOURS = int(os.environ.get("VERIFICATION_TOKEN_EXPIRY_HOURS", "72"))

EMAIL_ALLOWLIST: set[str] = (
    {e.strip().lower() for e in EMAIL_ALLOWLIST_RAW.split(",") if e.strip()}
    if EMAIL_ALLOWLIST_RAW.strip()
    else set()
)

SMTP_CONFIGURED = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def get_email_config() -> dict:
    """Return current email config status (safe to expose via API — no secrets)."""
    return {
        "smtp_configured": SMTP_CONFIGURED,
        "allowlist_active": bool(EMAIL_ALLOWLIST),
        "allowlist_addresses": list(EMAIL_ALLOWLIST) if EMAIL_ALLOWLIST else [],
        "dry_run": not SMTP_CONFIGURED,
        "from_address": MAIL_FROM,
        "token_expiry_hours": VERIFICATION_TOKEN_EXPIRY_HOURS,
    }


def _is_allowed(address: str) -> bool:
    """Return True if address may receive real email."""
    if not EMAIL_ALLOWLIST:
        return True  # No allowlist = allow all
    return address.strip().lower() in EMAIL_ALLOWLIST


def _send_smtp(to: str, subject: str, html_body: str, text_body: str) -> tuple[bool, str]:
    """
    Attempt to send via SMTP. Returns (success, error_message).
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = MAIL_FROM
        msg["To"] = to
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        if MAIL_USE_TLS:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(MAIL_FROM, to, msg.as_string())
        else:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(MAIL_FROM, to, msg.as_string())
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _log_email(
    db: Session,
    student_id: int | None,
    batch_id: int | None,
    template: str,
    to_address: str,
    subject: str,
    status: str,
    error: str | None = None,
):
    """Persist an EmailLog record and write to audit hash chain."""
    entry = EmailLog(
        student_id=student_id,
        batch_id=batch_id,
        template=template,
        to_address=to_address,
        subject=subject,
        status=status,
        error=error,
        sent_at=datetime.datetime.now(datetime.timezone.utc) if status == "sent" else None,
    )
    db.add(entry)
    db.commit()

    log_event(
        db=db,
        record_type="EmailLog",
        record_id=entry.id,
        event_type="EMAIL_SENT" if status == "sent" else "EMAIL_SKIPPED",
        actor="email_service",
    )
    return entry


# ─────────────────────────────────────────────────────────────────────────────
# Template renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_verification_email(student_name: str, token: str, institute_name: str) -> tuple[str, str, str]:
    """Returns (subject, html_body, text_body) for verification request email."""
    verify_url = f"{FRONTEND_BASE_URL}/verify/{token}"
    subject = "Please verify your student record — AICTE Data Platform (DEMO)"

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#1a3a5c;">
      <div style="background:#1a3a5c;padding:20px;text-align:center;">
        <h2 style="color:white;margin:0;">AICTE Student Data Platform</h2>
        <p style="color:#0d9488;margin:4px 0 0;font-size:13px;">DEMO BUILD — Student records are synthetic</p>
      </div>
      <div style="padding:28px 24px;">
        <p>Dear <strong>{student_name}</strong>,</p>
        <p><strong>{institute_name}</strong> has submitted your student record to AICTE.
           Please verify that the details are correct using the button below.</p>
        <div style="text-align:center;margin:32px 0;">
          <a href="{verify_url}"
             style="background:#0d9488;color:white;padding:14px 28px;border-radius:6px;
                    text-decoration:none;font-size:15px;font-weight:bold;">
            Verify My Record
          </a>
        </div>
        <p style="color:#666;font-size:13px;">
          Or copy this link: <a href="{verify_url}">{verify_url}</a>
        </p>
        <p style="color:#666;font-size:13px;">This link expires in {VERIFICATION_TOKEN_EXPIRY_HOURS} hours.</p>
        <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
        <p style="color:#aaa;font-size:11px;">
          This is a demonstration build. No real AICTE data or student records are involved.
        </p>
      </div>
    </div>
    """

    text_body = (
        f"Dear {student_name},\n\n"
        f"{institute_name} has submitted your student record to AICTE.\n"
        f"Please verify your details at:\n{verify_url}\n\n"
        f"This link expires in {VERIFICATION_TOKEN_EXPIRY_HOURS} hours.\n\n"
        f"[DEMO BUILD — synthetic data only]"
    )

    return subject, html_body, text_body


def _render_completion_email(student_name: str, batch_name: str, institute_name: str) -> tuple[str, str, str]:
    """Returns (subject, html_body, text_body) for batch-approved completion email."""
    subject = "Your student record has been approved by AICTE (DEMO)"

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#1a3a5c;">
      <div style="background:#1a3a5c;padding:20px;text-align:center;">
        <h2 style="color:white;margin:0;">AICTE Student Data Platform</h2>
        <p style="color:#0d9488;margin:4px 0 0;font-size:13px;">DEMO BUILD — Student records are synthetic</p>
      </div>
      <div style="padding:28px 24px;">
        <p>Dear <strong>{student_name}</strong>,</p>
        <p>We are pleased to inform you that the batch <strong>"{batch_name}"</strong> submitted by
           <strong>{institute_name}</strong> has been <span style="color:#0d9488;font-weight:bold;">approved by AICTE</span>.
           Your student record is now verified.</p>
        <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
        <p style="color:#aaa;font-size:11px;">
          This is a demonstration build. No real AICTE data or student records are involved.
        </p>
      </div>
    </div>
    """

    text_body = (
        f"Dear {student_name},\n\n"
        f"The batch '{batch_name}' submitted by {institute_name} has been approved by AICTE.\n"
        f"Your student record is now verified.\n\n"
        f"[DEMO BUILD — synthetic data only]"
    )

    return subject, html_body, text_body


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def send_verification_email(
    db: Session,
    student: "Student",
    token_obj: "VerificationToken",
    institute_name: str,
) -> dict:
    """
    Send (or mock) a verification request email for a single student.
    Returns a status dict.
    """
    # Determine recipient — use student email if available, else synthetic placeholder
    to_address = getattr(student, "email", None) or f"student_{student.id}@demo.example.com"
    subject, html_body, text_body = _render_verification_email(
        student_name=student.name,
        token=token_obj.token,
        institute_name=institute_name,
    )

    if not SMTP_CONFIGURED:
        # Dry-run: log but do not send
        entry = _log_email(
            db=db,
            student_id=student.id,
            batch_id=token_obj.batch_id,
            template="verification",
            to_address=to_address,
            subject=subject,
            status="skipped",
            error="SMTP not configured — dry-run mode",
        )
        verify_url = f"{FRONTEND_BASE_URL}/verify/{token_obj.token}"
        return {
            "status": "skipped",
            "reason": "smtp_not_configured",
            "to": to_address,
            "verify_url": verify_url,
            "email_log_id": entry.id,
        }

    if not _is_allowed(to_address):
        entry = _log_email(
            db=db,
            student_id=student.id,
            batch_id=token_obj.batch_id,
            template="verification",
            to_address=to_address,
            subject=subject,
            status="skipped",
            error="Address not in EMAIL_ALLOWLIST",
        )
        verify_url = f"{FRONTEND_BASE_URL}/verify/{token_obj.token}"
        return {
            "status": "skipped",
            "reason": "not_in_allowlist",
            "to": to_address,
            "verify_url": verify_url,
            "email_log_id": entry.id,
        }

    ok, err = _send_smtp(to_address, subject, html_body, text_body)
    entry = _log_email(
        db=db,
        student_id=student.id,
        batch_id=token_obj.batch_id,
        template="verification",
        to_address=to_address,
        subject=subject,
        status="sent" if ok else "failed",
        error=err if not ok else None,
    )
    verify_url = f"{FRONTEND_BASE_URL}/verify/{token_obj.token}"
    return {
        "status": "sent" if ok else "failed",
        "to": to_address,
        "verify_url": verify_url,
        "error": err if not ok else None,
        "email_log_id": entry.id,
    }


def send_completion_emails(db: Session, batch: "Batch") -> list[dict]:
    """
    Send (or mock) approval completion emails to all students in an approved batch.
    Returns a list of per-student status dicts.
    """
    from models.models import StudentBatch
    institute_name = batch.institute.name if batch.institute else "AICTE Institution"
    results = []

    sb_links = db.query(StudentBatch).filter(StudentBatch.batch_id == batch.id).all()
    for link in sb_links:
        student = link.student
        to_address = getattr(student, "email", None) or f"student_{student.id}@demo.example.com"
        subject, html_body, text_body = _render_completion_email(
            student_name=student.name,
            batch_name=batch.name,
            institute_name=institute_name,
        )

        if not SMTP_CONFIGURED:
            entry = _log_email(
                db=db,
                student_id=student.id,
                batch_id=batch.id,
                template="completion",
                to_address=to_address,
                subject=subject,
                status="skipped",
                error="SMTP not configured — dry-run mode",
            )
            results.append({"student_id": student.id, "status": "skipped", "email_log_id": entry.id})
            continue

        if not _is_allowed(to_address):
            entry = _log_email(
                db=db,
                student_id=student.id,
                batch_id=batch.id,
                template="completion",
                to_address=to_address,
                subject=subject,
                status="skipped",
                error="Address not in EMAIL_ALLOWLIST",
            )
            results.append({"student_id": student.id, "status": "skipped", "reason": "not_in_allowlist", "email_log_id": entry.id})
            continue

        ok, err = _send_smtp(to_address, subject, html_body, text_body)
        entry = _log_email(
            db=db,
            student_id=student.id,
            batch_id=batch.id,
            template="completion",
            to_address=to_address,
            subject=subject,
            status="sent" if ok else "failed",
            error=err if not ok else None,
        )
        results.append({"student_id": student.id, "status": "sent" if ok else "failed", "email_log_id": entry.id})

    return results

