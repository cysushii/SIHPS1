import pytest
from fastapi.testclient import TestClient
from main import app
from api.rbac import create_access_token

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_public_key_endpoint():
    response = client.get("/verify/public-key")
    assert response.status_code == 200
    assert "public_key_pem" in response.json()

def test_rbac_protection():
    # Attempt to access AICTE admin endpoint without token
    response = client.get("/dashboard/trust-scores")
    assert response.status_code == 401

    # Attempt with institute_admin token (forbidden)
    inst_token = create_access_token({"sub": "inst_user", "role": "institute_admin", "institute_id": 1})
    response = client.get("/dashboard/trust-scores", headers={"Authorization": f"Bearer {inst_token}"})
    assert response.status_code == 403

    # Access with aicte_admin token (authorized)
    aicte_token = create_access_token({"sub": "aicte_user", "role": "aicte_admin"})
    response = client.get("/dashboard/trust-scores", headers={"Authorization": f"Bearer {aicte_token}"})
    assert response.status_code == 200
    assert "institutes" in response.json()

def test_audit_verify_chain_api():
    aicte_token = create_access_token({"sub": "aicte_user", "role": "aicte_admin"})
    response = client.get("/audit/verify-chain", headers={"Authorization": f"Bearer {aicte_token}"})
    assert response.status_code == 200
    assert response.json()["is_valid"] is True

