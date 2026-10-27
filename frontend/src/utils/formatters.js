// Single shared formatter and label mapper for SIH26263 frontend
const ACRONYMS = new Set(["AICTE", "APAAR", "IIT", "NIT", "IIIT", "MIT", "VIT", "SRM", "COEP", "DTU", "B.TECH", "M.TECH", "MBA", "MCA", "NRI", "OCI", "FN", "EOA", "UID", "ID", "RSA", "SHA", "QR", "PDF", "API"]);

export function formatTitleCase(str) {
  if (!str) return "";
  return str
    .split(/\s+/)
    .map((word) => {
      const cleanUpper = word.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
      if (ACRONYMS.has(cleanUpper) || ACRONYMS.has(word.toUpperCase())) {
        return word.toUpperCase();
      }
      if (word.length <= 3 && word === word.toUpperCase() && /^[A-Z]+$/.test(word)) {
        return word.toUpperCase();
      }
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(" ");
}

export const ROLE_LABELS = {
  aicte_admin: "AICTE Administrator",
  institute_admin: "Institute Administrator",
  verifier: "Public Verifier",
};

export const STATUS_LABELS = {
  draft: "Draft",
  pushed: "Pushed to AICTE",
  awaiting_review: "Awaiting Review",
  under_review: "Under Review",
  approved: "Approved",
  rejected: "Rejected",
  returned: "Returned for Revision",
  active: "Active",
  graduated: "Graduated",
  withdrawn: "Withdrawn",
  open: "Open",
  reviewed: "Reviewed",
  needs_review: "Needs Review",
  cleared: "Cleared",
  blocked: "Blocked",
  confirmed: "Confirmed",
  critical: "Critical Alert",
  pending: "Pending",
  verified: "Verified",
  correction_requested: "Correction Requested",
  unresponsive: "Unresponsive",
  queued: "Queued",
  sent: "Sent",
  sent_test_mode: "Sent (Test Mode)",
  failed: "Failed",
  no_email: "No Email on File",
  running: "In Progress",
  completed: "Completed",
};

export const CHECK_LABELS = {
  apaar_format: "APAAR ID Format",
  honeytoken_scan: "Honeytoken Canary Scan",
  exact_duplicate: "Exact Duplicate Enrollment",
  fuzzy_duplicate: "Suspected Identity Duplicate",
  self_verification: "Student Self-Verification",
  geographic_plausibility: "Geographic Plausibility",
  lifecycle_plausibility: "Lifecycle Plausibility",
  field_consistency: "Field & Category Consistency",
  capacity_check: "Approved Intake Capacity",
  closure_check: "Closed Programme Check",
};

export function getRoleLabel(role) {
  return ROLE_LABELS[role] || (role ? role.replace(/_/g, " ") : "");
}

export function getStatusLabel(status) {
  return STATUS_LABELS[status?.toLowerCase()] || (status ? status.replace(/_/g, " ") : "");
}

export function getCheckLabel(checkKey) {
  return CHECK_LABELS[checkKey] || (checkKey ? checkKey.replace(/_/g, " ") : "");
}

