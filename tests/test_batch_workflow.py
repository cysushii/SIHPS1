import pytest
from fastapi.testclient import TestClient
from main import app
from models.database import SessionLocal
from models.models import Batch, Student, VerificationToken, Institute

client = TestClient(app)

@pytest.fixture
def auth_headers():
    token_resp = client.post("/auth/token", json={
        "username": "test_inst_admin",
        "role": "institute_admin",
        "institute_id": 1
    })
    token = token_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def aicte_headers():
    token_resp = client.post("/auth/token", json={
        "username": "test_aicte_admin",
        "role": "aicte_admin"
    })
    token = token_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_batch_lifecycle_and_verification(auth_headers, aicte_headers):
    # 1. Create Batch
    create_res = client.post("/batches", json={
        "name": "Integration Test Batch 2024",
        "institute_id": 1
    }, headers=auth_headers)
    assert create_res.status_code == 200
    batch_id = create_res.json()["batch_id"]

    # 2. Ensure at least one student exists for testing
    db = SessionLocal()
    st = db.query(Student).filter(Student.institute_id == 1).first()
    if not st:
        st = Student(
            apaar_id="999988887771",
            name="Workflow Test Student",
            institute_id=1,
            program="Computer Engineering",
            enrollment_year=2021,
            email="test.student@example.com"
        )
        db.add(st)
        db.commit()
        db.refresh(st)
    db.close()
    assert st is not None

    add_res = client.post(f"/batches/{batch_id}/students", json={
        "student_ids": [st.id]
    }, headers=auth_headers)
    assert add_res.status_code == 200
    assert add_res.json()["added"] >= 0

    # 3. Create a verification token directly using hashed token
    import secrets
    from services.email import hash_token
    import datetime

    raw_token = secrets.token_urlsafe(32)
    token_digest = hash_token(raw_token)
    db = SessionLocal()
    vt = VerificationToken(
        student_id=st.id,
        batch_id=batch_id,
        token_hash=token_digest,
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
        status="pending"
    )
    db.add(vt)
    db.commit()
    db.close()
    token = raw_token

    # 4. Public Student self-verify lookup
    verify_lookup = client.get(f"/verify/token/{token}")
    assert verify_lookup.status_code == 200
    data = verify_lookup.json()
    assert data["student_name"] == st.name

    # 5. Public Student confirm
    confirm_res = client.post(f"/verify/token/{token}/confirm")
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "verified"

    # 6. Push Batch
    push_res = client.post(f"/batches/{batch_id}/push", headers=auth_headers)
    assert push_res.status_code == 200
    assert push_res.json()["status"] == "pushed"

    # AICTE Run verification record creation to clear gate
    from models.models import VerificationRun, StudentVerificationResult
    db = SessionLocal()
    vrun = VerificationRun(
        batch_id=batch_id,
        status="completed",
        summary={"cleared": 1, "needs_review": 0, "blocked": 0}
    )
    db.add(vrun)
    db.commit()
    db.refresh(vrun)

    svr = StudentVerificationResult(
        run_id=vrun.id,
        student_id=st.id,
        verdict="cleared",
        checks={}
    )
    db.add(svr)
    db.commit()
    db.close()

    # 7. AICTE Approve batch -> triggers signed PDF report
    approve_res = client.post(f"/aicte/batches/{batch_id}/approve", headers=aicte_headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"
    assert approve_res.json()["report_signed"] is True

    # 8. Download PDF Report
    report_res = client.get(f"/batches/{batch_id}/report", headers=auth_headers)
    assert report_res.status_code == 200
    assert report_res.headers["content-type"] == "application/pdf"
    assert len(report_res.content) > 1000  # valid PDF binary

