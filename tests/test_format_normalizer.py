import pytest
from validation.format_normalizer import normalize_institute_name

def test_exact_match():
    res = normalize_institute_name("Indian Institute of Technology Bombay")
    assert res["is_match"] is True
    assert res["matched_name"] == "Indian Institute of Technology Bombay"
    assert res["score"] == 100.0

def test_fuzzy_variation():
    # Abbreviations & re-ordered words
    res = normalize_institute_name("SRM Inst. of Science & Tech", threshold=80.0)
    assert res["is_match"] is True
    assert "SRM Institute of Science and Technology" in res["matched_name"]

def test_unmatched_low_score():
    res = normalize_institute_name("Completely Non Existent Academy of Mars", threshold=85.0)
    assert res["is_match"] is False

