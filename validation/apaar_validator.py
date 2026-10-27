import os
import re
import pandas as pd

DEFAULT_STATE_DISTRICT_CODES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "state_district_codes.csv"
)

# Cache mapping table in-memory
_CODE_TO_LOCATION: dict[str, dict[str, str]] = {}

def _get_location_mapping() -> dict[str, dict[str, str]]:
    global _CODE_TO_LOCATION
    if not _CODE_TO_LOCATION and os.path.exists(DEFAULT_STATE_DISTRICT_CODES_PATH):
        try:
            df = pd.read_csv(DEFAULT_STATE_DISTRICT_CODES_PATH, dtype=str)
            for _, row in df.iterrows():
                st_code = str(row.get("state_code", "")).strip().zfill(2)
                dist_code = str(row.get("district_code", "")).strip().zfill(2)
                key = f"{st_code}{dist_code}"
                _CODE_TO_LOCATION[key] = {
                    "state": str(row.get("state_name", "")).strip(),
                    "district": str(row.get("district_name", "")).strip(),
                }
        except Exception:
            pass
    return _CODE_TO_LOCATION

def validate_apaar_format(apaar_id: str) -> tuple[bool, str]:
    """
    Validates structural integrity of APAAR ID.
    APAAR ID is a 12-digit number:
    - Exactly 12 digits
    - Numeric only
    - First 2 digits form a plausible year (00-30 representing 2000-2030)
    - No obviously invalid patterns (all same digit, strictly sequential digits)
    """
    if not isinstance(apaar_id, str):
        return False, "APAAR ID must be a string."

    clean_id = apaar_id.strip()

    if len(clean_id) != 12:
        return False, f"APAAR ID must be exactly 12 digits, got length {len(clean_id)}."

    if not clean_id.isdigit():
        return False, "APAAR ID must contain only numeric digits."

    # First 2 digits represent registration year: 00-30 (2000 to 2030)
    year_prefix = int(clean_id[:2])
    if year_prefix > 30:
        return False, f"Invalid registration year prefix '{clean_id[:2]}'. Expected '00'-'30' (years 2000-2030)."

    # Reject all same digit (e.g. '111111111111', '000000000000')
    if len(set(clean_id)) == 1:
        return False, "APAAR ID cannot consist of identical digits."

    # Reject obvious sequential sequences (e.g. '012345678901', '123456789012', '987654321098')
    sequential_asc = "01234567890123456789"
    sequential_desc = "98765432109876543210"
    if clean_id in sequential_asc or clean_id in sequential_desc:
        return False, "APAAR ID cannot be a sequential series of digits."

    return True, "Valid APAAR ID structure."

def check_geographic_consistency(apaar_id: str, institute_id: int, db) -> dict:
    """
    [SIH Differentiator Layer - Proprietary APAAR Structural Analysis]
    NOTE: This is NOT a standard AICTE-mandated check — this is our custom validation
    layer built upon APAAR's documented ID structure to evaluate geographic alignment.
    
    Extracts the state/district code segment from the APAAR ID (digits 3-6: index 2 to 6).
    Compares against the institute's official state and district in the database.
    
    Pure evaluation: NEVER hard-rejects, only returns a soft consistency signal for
    risk assessment and trust scoring (students may legitimately relocate).
    """
    from models.models import Institute

    note_text = "mismatch is a soft signal, not a rejection — contributes to trust score, student may have relocated"

    if not isinstance(apaar_id, str) or len(apaar_id.strip()) != 12 or not apaar_id.strip().isdigit():
        return {
            "match": False,
            "embedded_location": "Invalid APAAR format",
            "institute_location": "Unknown",
            "note": note_text
        }

    clean_id = apaar_id.strip()
    geo_code = clean_id[2:6] # Digits 3-6 (0-indexed 2..6)

    # Lookup mapping
    loc_map = _get_location_mapping()
    loc_entry = loc_map.get(geo_code)

    if loc_entry:
        embedded_state = loc_entry["state"]
        embedded_dist = loc_entry["district"]
        embedded_location = f"{embedded_dist}, {embedded_state}"
    else:
        embedded_state = ""
        embedded_dist = ""
        embedded_location = f"Code {geo_code} (Unmapped)"

    # Lookup institute location
    inst = db.query(Institute).filter(Institute.id == institute_id).first() if db is not None else None
    if not inst:
        return {
            "match": False,
            "embedded_location": embedded_location,
            "institute_location": "Institute not found",
            "note": note_text
        }

    inst_state = (inst.state or "").strip()
    inst_dist = (inst.district or "").strip()
    institute_location = f"{inst_dist}, {inst_state}" if inst_dist and inst_state else (inst_state or inst_dist or "Unknown")

    # Match check: match if state aligns
    match = False
    if embedded_state and inst_state:
        if embedded_state.lower() == inst_state.lower():
            match = True

    return {
        "match": match,
        "embedded_location": embedded_location,
        "institute_location": institute_location,
        "note": note_text
    }

def check_lifecycle_plausibility(apaar_id: str, admission_year: int) -> dict:
    """
    [SIH Differentiator Layer - Proprietary APAAR Structural Analysis]
    NOTE: This is NOT a standard AICTE-mandated check — this is our custom validation
    layer built upon APAAR's documented ID structure to evaluate student lifecycle plausibility.

    Extracts year prefix (first 2 digits), converts to full 4-digit registration year (e.g. '21' -> 2021).
    Calculates gap = admission_year - apaar_registration_year:
    - Implausible: gap < 0 (APAAR registered after claimed higher-ed admission) or gap > 25 (unreasonably long)
    - Needs Review: gap < 8 (short gap for schooling-to-higher-ed progression)
    - Plausible: 8 <= gap <= 25

    Pure evaluation: does not perform DB writes.
    """
    if not isinstance(apaar_id, str) or len(apaar_id.strip()) < 2 or not apaar_id.strip()[:2].isdigit():
        return {
            "plausible": False,
            "gap_years": 0,
            "severity": "implausible",
            "reason": "Invalid or missing APAAR ID year prefix."
        }

    year_prefix = int(apaar_id.strip()[:2])
    # Prefix 00-30 represents 2000-2030; otherwise 1900s
    reg_year = 2000 + year_prefix if year_prefix <= 30 else 1900 + year_prefix
    gap = admission_year - reg_year

    if gap < 0:
        return {
            "plausible": False,
            "gap_years": gap,
            "severity": "implausible",
            "reason": f"APAAR registered in {reg_year}, after claimed admission year {admission_year} (gap: {gap} yrs)."
        }
    elif gap > 25:
        return {
            "plausible": False,
            "gap_years": gap,
            "severity": "implausible",
            "reason": f"Unreasonably long gap of {gap} years between APAAR registration ({reg_year}) and admission ({admission_year})."
        }
    elif gap < 8:
        return {
            "plausible": False,
            "gap_years": gap,
            "severity": "needs_review",
            "reason": f"Short schooling-to-higher-ed lifecycle gap of {gap} years ({reg_year} to {admission_year}). Typically requires review."
        }
    else:
        return {
            "plausible": True,
            "gap_years": gap,
            "severity": "none",
            "reason": f"Lifecycle timeline plausible ({gap} years from registration {reg_year} to admission {admission_year})."
        }

    note_text = "mismatch is a soft signal, not a rejection — contributes to trust score, student may have relocated"

    if not isinstance(apaar_id, str) or len(apaar_id.strip()) != 12 or not apaar_id.strip().isdigit():
        return {
            "match": False,
            "embedded_location": "Invalid APAAR format",
            "institute_location": "Unknown",
            "note": note_text
        }

    clean_id = apaar_id.strip()
    geo_code = clean_id[2:6] # Digits 3-6 (0-indexed 2..6)

    # Lookup mapping
    loc_map = _get_location_mapping()
    loc_entry = loc_map.get(geo_code)

    if loc_entry:
        embedded_state = loc_entry["state"]
        embedded_dist = loc_entry["district"]
        embedded_location = f"{embedded_dist}, {embedded_state}"
    else:
        embedded_state = ""
        embedded_dist = ""
        embedded_location = f"Code {geo_code} (Unmapped)"

    # Lookup institute location
    inst = db.query(Institute).filter(Institute.id == institute_id).first() if db is not None else None
    if not inst:
        return {
            "match": False,
            "embedded_location": embedded_location,
            "institute_location": "Institute not found",
            "note": note_text
        }

    inst_state = (inst.state or "").strip()
    inst_dist = (inst.district or "").strip()
    institute_location = f"{inst_dist}, {inst_state}" if inst_dist and inst_state else (inst_state or inst_dist or "Unknown")

    # Match check: match if state aligns
    match = False
    if embedded_state and inst_state:
        if embedded_state.lower() == inst_state.lower():
            match = True

    return {
        "match": match,
        "embedded_location": embedded_location,
        "institute_location": institute_location,
        "note": note_text
    }

def check_lifecycle_plausibility(apaar_id: str, admission_year: int) -> dict:
    """
    [SIH Differentiator Layer - Proprietary APAAR Structural Analysis]
    NOTE: This is NOT a standard AICTE-mandated check — this is our custom validation
    layer built upon APAAR's documented ID structure to evaluate student lifecycle plausibility.

    Extracts year prefix (first 2 digits), converts to full 4-digit registration year (e.g. '21' -> 2021).
    Calculates gap = admission_year - apaar_registration_year:
    - Implausible: gap < 0 (APAAR registered after claimed higher-ed admission) or gap > 25 (unreasonably long)
    - Needs Review: gap < 8 (short gap for schooling-to-higher-ed progression)
    - Plausible: 8 <= gap <= 25

    Pure evaluation: does not perform DB writes.
    """
    if not isinstance(apaar_id, str) or len(apaar_id.strip()) < 2 or not apaar_id.strip()[:2].isdigit():
        return {
            "plausible": False,
            "gap_years": 0,
            "severity": "implausible",
            "reason": "Invalid or missing APAAR ID year prefix."
        }

    year_prefix = int(apaar_id.strip()[:2])
    # Prefix 00-30 represents 2000-2030; otherwise 1900s
    reg_year = 2000 + year_prefix if year_prefix <= 30 else 1900 + year_prefix
    gap = admission_year - reg_year

    if gap < 0:
        return {
            "plausible": False,
            "gap_years": gap,
            "severity": "implausible",
            "reason": f"APAAR registered in {reg_year}, after claimed admission year {admission_year} (gap: {gap} yrs)."
        }
    elif gap > 25:
        return {
            "plausible": False,
            "gap_years": gap,
            "severity": "implausible",
            "reason": f"Unreasonably long gap of {gap} years between APAAR registration ({reg_year}) and admission ({admission_year})."
        }
    elif gap < 8:
        return {
            "plausible": False,
            "gap_years": gap,
            "severity": "needs_review",
            "reason": f"Short schooling-to-higher-ed lifecycle gap of {gap} years ({reg_year} to {admission_year}). Typically requires review."
        }
    else:
        return {
            "plausible": True,
            "gap_years": gap,
            "severity": "none",
            "reason": f"Lifecycle timeline plausible ({gap} years from registration {reg_year} to admission {admission_year})."
        }

