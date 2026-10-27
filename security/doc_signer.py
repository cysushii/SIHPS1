import io
import base64
import json
from datetime import datetime, timezone
import qrcode
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

# Generate RSA-2048 keypair on module startup
_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
_public_key = _private_key.public_key()

def get_public_key_pem() -> str:
    """Returns the public key in PEM format."""
    pem = _public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem.decode("utf-8")

def sign_document(
    student_id: int | str,
    apaar_id: str,
    name: str | None = None,
    institute: str | None = None,
    program: str | None = None,
    issued_date: str | None = None,
    db = None
) -> dict:
    """
    Builds a certificate dict {name, apaar_id, institute, program, issued_date},
    SHA-256 hashes it, signs the hash with the RSA private key,
    and returns {document, hash, signature, qr_code_base64, verification_url}.

    If name/institute/program are omitted and db is supplied, looks up student record.
    """
    if (name is None or institute is None or program is None) and db is not None:
        from models.models import Student
        std = db.query(Student).filter(
            (Student.id == student_id) | (Student.apaar_id == str(apaar_id))
        ).first()
        if std:
            name = name or std.name
            program = program or std.program
            institute = institute or (std.institute.name if std.institute else "AICTE Institution")

    name = name or "Student Name"
    institute = institute or "AICTE Approved Institution"
    program = program or "Degree Program"

    if issued_date is None:
        issued_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    document = {
        "name": str(name),
        "apaar_id": str(apaar_id),
        "institute": str(institute),
        "program": str(program),
        "issued_date": str(issued_date),
    }

    # Deterministic JSON canonical representation for hashing
    doc_json = json.dumps(document, sort_keys=True)
    doc_hash = hashes.Hash(hashes.SHA256())
    doc_hash.update(doc_json.encode("utf-8"))
    digest = doc_hash.finalize()

    # Sign digest with RSA private key (PKCS1v15 padding + SHA-256)
    signature_bytes = _private_key.sign(
        digest,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    sig_b64 = base64.b64encode(signature_bytes).decode("utf-8")
    hash_hex = digest.hex()

    # Generate QR Code encoding verification link: /verify/document/{apaar_id}
    verification_url = f"/verify/document/{apaar_id}"
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(verification_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "document": document,
        "hash": hash_hex,
        "signature": sig_b64,
        "qr_code_base64": qr_b64,
        "verification_url": verification_url,
    }

def verify_document(document: dict, signature: str) -> bool:
    """
    Recomputes document SHA-256 hash and verifies the RSA signature using the public key.
    Returns True if authentic; False if tampered or invalid.
    """
    try:
        doc_json = json.dumps(document, sort_keys=True)
        doc_hash = hashes.Hash(hashes.SHA256())
        doc_hash.update(doc_json.encode("utf-8"))
        digest = doc_hash.finalize()

        sig_bytes = base64.b64decode(signature.encode("utf-8"))

        _public_key.verify(
            sig_bytes,
            digest,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False
