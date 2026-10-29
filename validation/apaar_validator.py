import os
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
    Validates format integrity of APAAR ID.
    APAAR ID is exactly 12 numeric digits.
    """
    if not isinstance(apaar_id, str):
        return False, "APAAR ID must be a string."

    clean_id = apaar_id.strip()

    if len(clean_id) != 12:
        return False, f"APAAR ID must be exactly 12 digits, got length {len(clean_id)}."

    if not clean_id.isdigit():
        return False, "APAAR ID must contain only numeric digits."

    return True, "Valid APAAR ID format."


def check_geographic_consistency(apaar_id: str, institute_id: int, db) -> dict:
    """
    [SIH Differentiator Layer - Proprietary APAAR Structural Analysis]
    Extracts the state/district code segment from the APAAR ID (digits 3-6: index 2 to 6).
    Compares against the institute's official state and district in the database.
    Pure evaluation: NEVER hard-rejects, only a soft consistency signal.
    """
    from models.models import Institute

    note_text = "mismatch is a soft signal, not a rejection — contributes to trust score, student may have relocated"

    if not isinstance(apaar_id, str) or len(apaar_id.strip()) != 12 or not apaar_id.strip().isdigit():
        return {
            "match": False,
            "embedded_location": "Invalid APAAR format",
            "institute_location": "Unknown",
            "note": note_text,
        }

    clean_id = apaar_id.strip()
    geo_code = clean_id[2:6]  # digits 3-6 (0-indexed 2..6)

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

    inst = db.query(Institute).filter(Institute.id == institute_id).first() if db is not None else None
    if not inst:
        return {
            "match": False,
            "embedded_location": embedded_location,
            "institute_location": "Institute not found",
            "note": note_text,
        }

    inst_state = (inst.state or "").strip()
    inst_dist = (inst.district or "").strip()
    institute_location = (
        f"{inst_dist}, {inst_state}" if inst_dist and inst_state
        else (inst_state or inst_dist or "Unknown")
    )

    match = bool(embedded_state and inst_state and embedded_state.lower() == inst_state.lower())

    return {
        "match": match,
        "embedded_location": embedded_location,
        "institute_location": institute_location,
        "note": note_text,
    }


def check_lifecycle_plausibility(apaar_id: str, admission_year: int) -> dict:
    """
    [SIH Differentiator Layer - Proprietary APAAR Structural Analysis]
    Extracts year prefix (first 2 digits), converts to full 4-digit registration year.
    Calculates gap = admission_year - apaar_registration_year:
    - Implausible: gap < 0 or gap > 25
    - Needs Review: gap < 8
    - Plausible: 8 <= gap <= 25
    """
    if not isinstance(apaar_id, str) or len(apaar_id.strip()) < 2 or not apaar_id.strip()[:2].isdigit():
        return {
            "plausible": False,
            "gap_years": 0,
            "severity": "implausible",
            "reason": "Invalid or missing APAAR ID year prefix.",
        }

    year_prefix = int(apaar_id.strip()[:2])
    reg_year = 2000 + year_prefix if year_prefix <= 30 else 1900 + year_prefix

    try:
        gap = int(admission_year) - reg_year
    except (TypeError, ValueError):
        return {
            "plausible": False,
            "gap_years": 0,
            "severity": "implausible",
            "reason": f"Invalid admission year: {admission_year}.",
        }

    if gap < 0:
        return {
            "plausible": False,
            "gap_years": gap,
            "severity": "implausible",
            "reason": f"APAAR registered in {reg_year}, after claimed admission year {admission_year} (gap: {gap} yrs).",
        }
    elif gap > 25:
        return {
            "plausible": False,
            "gap_years": gap,
            "severity": "implausible",
            "reason": f"Unreasonably long gap of {gap} years between APAAR registration ({reg_year}) and admission ({admission_year}).",
        }
    elif gap < 8:
        return {
            "plausible": False,
            "gap_years": gap,
            "severity": "needs_review",
            "reason": f"Short schooling-to-higher-ed lifecycle gap of {gap} years ({reg_year} to {admission_year}). Typically requires review.",
        }
    else:
        return {
            "plausible": True,
            "gap_years": gap,
            "severity": "none",
            "reason": f"Lifecycle timeline plausible ({gap} years from registration {reg_year} to admission {admission_year}).",
        }
