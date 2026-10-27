import pytest
from security.doc_signer import sign_document, verify_document, get_public_key_pem

def test_sign_and_verify_document_exact_schema():
    signed = sign_document(
        student_id=101,
        apaar_id="241234567890",
        name="Aarav Sharma",
        institute="IIT Bombay",
        program="B.Tech Computer Science"
    )

    doc = signed["document"]
    # Verify exact schema: name, apaar_id, institute, program, issued_date
    assert "name" in doc
    assert "apaar_id" in doc
    assert "institute" in doc
    assert "program" in doc
    assert "issued_date" in doc
    assert "signature" in signed
    assert "hash" in signed
    assert "qr_code_base64" in signed
    assert "verification_url" in signed

    # 1. Genuine verification MUST pass
    assert verify_document(doc, signed["signature"]) is True

    # 2. Judge Live Demo: Altering even ONE single character MUST cause verification to FAIL
    tampered_doc_char = dict(doc)
    tampered_doc_char["name"] = "Aarav Sharma." # Added single period
    assert verify_document(tampered_doc_char, signed["signature"]) is False

    tampered_doc_year = dict(doc)
    tampered_doc_year["issued_date"] = "2026-10-28" # Changed single day
    assert verify_document(tampered_doc_year, signed["signature"]) is False

def test_public_key_format():
    pem = get_public_key_pem()
    assert pem.startswith("-----BEGIN PUBLIC KEY-----")
    assert pem.strip().endswith("-----END PUBLIC KEY-----")
