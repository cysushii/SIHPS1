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

    # 2. Add students to batch (or verify already attached on creation)
    db = SessionLocal()
    st = db.query(Student).filter(Student.institute_id == 1).first()
    db.close()
    assert st is not None

    add_res = client.post(f"/batches/{batch_id}/students", json={
        "student_ids": [st.id]
    }, headers=auth_headers)
    assert add_res.status_code == 200
    assert add_res.json()["added"] >= 0

    # 3. Generate verification tokens
    gen_res = client.post(f"/batches/{batch_id}/verification/generate", headers=auth_headers)
    assert gen_res.status_code == 200
    assert gen_res.json()["generated_count"] >= 1
    token = gen_res.json()["tokens"][0]["token"]

    # 4. Public Student self-verify lookup
    verify_lookup = client.get(f"/verify/token/{token}")
    assert verify_lookup.status_code == 200
    assert "student" in verify_lookup.json()
    assert verify_lookup.json()["student"]["name"] == st.name

    # 5. Public Student confirm
    confirm_res = client.post(f"/verify/token/{token}/confirm")
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "verified"

    # 6. Push Batch
    push_res = client.post(f"/batches/{batch_id}/push", headers=auth_headers)
    assert push_res.status_code == 200
    assert push_res.json()["status"] == "pushed"

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

