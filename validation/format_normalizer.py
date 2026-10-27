import os
import pandas as pd
from rapidfuzz import process, fuzz

DEFAULT_REF_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "institutes_reference.csv")
DEFAULT_AICTE_INST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "aicte_institutes.csv")

COMMON_ABBREVIATIONS = {
    r"\binst\b\.?": "institute",
    r"\btech\b\.?": "technology",
    r"\bsci\b\.?": "science",
    r"\bengg\b\.?": "engineering",
    r"\buniv\b\.?": "university",
    r"\bmgmt\b\.?": "management",
    r"&": "and",
}

def clean_institute_name(name: str) -> str:
    """Expands common educational abbreviations for better fuzzy matching and lowercases."""
    text = name.strip()
    import re
    for pattern, repl in COMMON_ABBREVIATIONS.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    # clean extra punctuation and spaces
    text = re.sub(r"[,\.-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()

class FormatNormalizer:
    def __init__(self, reference_csv_path: str = DEFAULT_REF_PATH):
        self.reference_csv_path = reference_csv_path
        self._reference_names = []
        self._clean_reference_names = []
        self._reference_df = None
        self._load_reference()

    def _load_reference(self):
        if os.path.exists(self.reference_csv_path):
            self._reference_df = pd.read_csv(self.reference_csv_path)
            col = "institute_name" if "institute_name" in self._reference_df.columns else ("name" if "name" in self._reference_df.columns else None)
            if col:
                self._reference_names = self._reference_df[col].dropna().astype(str).tolist()
                self._clean_reference_names = [clean_institute_name(n) for n in self._reference_names]
        else:
            self._reference_names = []
            self._clean_reference_names = []
            self._reference_df = pd.DataFrame()

    def match_institute_name(self, name: str, threshold: float = 85.0) -> dict:
        """
        Matches an institute name against reference AISHE/AICTE list using RapidFuzz token_sort_ratio.
        Returns:
            {
                "original": name,
                "matched_name": matched or None,
                "score": float,
                "is_match": bool,
                "details": row_dict or None
            }
        """
        if not name or not self._reference_names:
            return {
                "original": name,
                "matched_name": None,
                "score": 0.0,
                "is_match": False,
                "details": None,
            }

        cleaned_query = clean_institute_name(name)

        result = process.extractOne(
            query=cleaned_query,
            choices=self._clean_reference_names,
            scorer=fuzz.token_sort_ratio
        )

        if result:
            _, score, idx = result
            best_match = self._reference_names[idx]
            if score >= threshold:
                row_details = self._reference_df.iloc[idx].to_dict() if self._reference_df is not None else None
                return {
                    "original": name,
                    "matched_name": best_match,
                    "score": round(float(score), 2),
                    "is_match": True,
                    "details": row_details,
                }
            else:
                return {
                    "original": name,
                    "matched_name": best_match,
                    "score": round(float(score), 2),
                    "is_match": False,
                    "details": None,
                }

        return {
            "original": name,
            "matched_name": None,
            "score": 0.0,
            "is_match": False,
            "details": None,
        }

    def match_aicte_institutes(self, aicte_csv_path: str = DEFAULT_AICTE_INST_PATH, threshold: float = 80.0) -> list[dict]:
        """
        Fuzzy-match joins aicte_institutes.csv against the larger reference roster (institutes_reference.csv).
        Returns a list of match results for each AICTE institute.
        """
        if not os.path.exists(aicte_csv_path):
            return []

        aicte_df = pd.read_csv(aicte_csv_path)
        join_results = []

        for _, row in aicte_df.iterrows():
            inst_name = str(row.get("name", "")).strip()
            match_res = self.match_institute_name(inst_name, threshold=threshold)
            join_results.append({
                "aicte_permanent_id": str(row.get("aicte_permanent_id", "")),
                "aicte_name": inst_name,
                "aicte_state": str(row.get("state", "")),
                "matched_reference_name": match_res["matched_name"],
                "score": match_res["score"],
                "is_match": match_res["is_match"],
                "reference_details": match_res["details"]
            })

        return join_results

# Global singleton helper
normalizer = FormatNormalizer()

def normalize_institute_name(name: str, threshold: float = 85.0) -> dict:
    return normalizer.match_institute_name(name, threshold=threshold)

def match_aicte_institutes_to_reference(aicte_csv_path: str = DEFAULT_AICTE_INST_PATH, threshold: float = 80.0) -> list[dict]:
    return normalizer.match_aicte_institutes(aicte_csv_path=aicte_csv_path, threshold=threshold)
