import pytest
from fastapi.testclient import TestClient
from main import app
from api.rbac import create_access_token

client = TestClient(app)

def test_dashboard_duplicates_endpoint():
    token = create_access_token({"sub": "aicte_admin", "role": "aicte_admin"})
    response = client.get("/dashboard/duplicates", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "total_duplicates" in data
    assert "grouped_by_severity" in data
    assert "confirmed" in data["grouped_by_severity"]
    assert "needs_review" in data["grouped_by_severity"]

def test_security_checkpoints_endpoints():
    token = create_access_token({"sub": "aicte_admin", "role": "aicte_admin"})
    
    # 1. Trigger checkpoint
    cp_res = client.post("/security/checkpoint", headers={"Authorization": f"Bearer {token}"})
    assert cp_res.status_code == 200
    assert cp_res.json()["status"] == "CHECKPOINT_CREATED"

    # 2. Verify anchored chain
    ver_res = client.get("/security/verify-anchored", headers={"Authorization": f"Bearer {token}"})
    assert ver_res.status_code == 200
    assert "anchored_integrity" in ver_res.json()

def test_security_honeytokens_status_endpoint():
    token = create_access_token({"sub": "aicte_admin", "role": "aicte_admin"})
    response = client.get("/security/honeytokens/status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "total_honeytokens" in data
    assert "triggered_count" in data
    assert data["total_honeytokens"] >= 10

