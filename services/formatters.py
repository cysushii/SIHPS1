"""
Core formatting and display label maps for SIH26263.
Ensures zero snake_case or raw technical identifiers appear on frontend or reports.
"""
import re

ACRONYMS = {"AICTE", "APAAR", "IIT", "NIT", "IIIT", "MIT", "VIT", "SRM", "COEP", "DTU", "B.TECH", "M.TECH", "MBA", "MCA", "BBA", "BCA", "NRI", "OCI", "FN", "EOA", "UID", "ID", "RSA", "SHA", "QR", "PDF", "API"}

ROLE_LABELS = {
    "aicte_admin": "AICTE Administrator",
    "institute_admin": "Institute Administrator",
    "verifier": "Public Verifier",
}

STATUS_LABELS = {
    "draft": "Draft",
    "pushed": "Pushed to AICTE",
    "awaiting_review": "Awaiting Review",
    "under_review": "Under Review",
    "approved": "Approved",
    "rejected": "Rejected",
    "returned": "Returned for Revision",
    "active": "Active",
    "graduated": "Graduated",
    "withdrawn": "Withdrawn",
    "open": "Open",
    "reviewed": "Reviewed",
    "needs_review": "Needs Review",
    "cleared": "Cleared",
    "blocked": "Blocked",
    "confirmed": "Confirmed",
    "critical": "Critical Alert",
    "pending": "Pending",
    "verified": "Verified",
    "correction_requested": "Correction Requested",
    "unresponsive": "Unresponsive",
    "queued": "Queued",
    "sent": "Sent",
    "sent_test_mode": "Sent (Test Mode)",
    "failed": "Failed",
    "no_email": "No Email on File",
    "running": "In Progress",
    "completed": "Completed",
}

CHECK_NAMES = {
    "apaar_format": "APAAR ID Format",
    "honeytoken_scan": "Honeytoken Canary Scan",
    "exact_duplicate": "Exact Duplicate Enrollment",
    "fuzzy_duplicate": "Suspected Identity Duplicate",
    "self_verification": "Student Self-Verification",
    "geographic_plausibility": "Geographic Plausibility",
    "lifecycle_plausibility": "Lifecycle Plausibility",
    "field_consistency": "Field & Category Consistency",
    "capacity_check": "Approved Intake Capacity",
    "closure_check": "Closed Programme Check",
}

def format_title_case(name: str | None) -> str:
    """Format stored institute or student names into clean Title Case while preserving key acronyms."""
    if not name:
        return ""
    words = name.strip().split()
    formatted = []
    for w in words:
        clean_upper = re.sub(r'[^A-Za-z0-9]', '', w.upper())
        if clean_upper in ACRONYMS or w.upper() in ACRONYMS:
            formatted.append(w.upper())
        elif len(w) <= 3 and w.isupper() and w.isalpha():
            formatted.append(w.upper())
        else:
            formatted.append(w.capitalize())
    return " ".join(formatted)

def get_role_label(role: str | None) -> str:
    return ROLE_LABELS.get(role or "", (role or "").replace("_", " ").title())

def get_status_label(status: str | None) -> str:
    return STATUS_LABELS.get((status or "").lower(), (status or "").replace("_", " ").title())

def get_check_label(check: str | None) -> str:
    return CHECK_NAMES.get(check or "", (check or "").replace("_", " ").title())

