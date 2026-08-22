import pytest
from fastapi.testclient import TestClient

def test_register_and_login_flow(client: TestClient):
    # 1. Register new user
    reg_data = {
        "email": "auditor@felixsu.qzz.io",
        "password": "securepassword123",
        "full_name": "Audit Inspector",
        "role": "PM",
        "skills": "security,audit,python"
    }
    res = client.post("/api/auth/register", json=reg_data)
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "auditor@felixsu.qzz.io"
    assert data["user"]["role"] == "PM"

    # 2. Prevent duplicate email registration
    res_dup = client.post("/api/auth/register", json=reg_data)
    assert res_dup.status_code == 400

    # 3. Login with credentials
    login_res = client.post("/api/auth/login", json={
        "email": "auditor@felixsu.qzz.io",
        "password": "securepassword123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token

    # 4. Fetch authenticated profile /api/auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "auditor@felixsu.qzz.io"
    assert me_data["full_name"] == "Audit Inspector"

def test_unauthenticated_request_rejected(client: TestClient):
    res = client.get("/api/auth/me")
    assert res.status_code == 401
