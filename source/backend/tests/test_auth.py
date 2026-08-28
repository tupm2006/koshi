import pytest
from fastapi.testclient import TestClient

def test_register_and_login_flow(client: TestClient):
    # 1. Register new user
    reg_data = {
        "email": "auditor@tupm.qzz.io",
        "password": "securepassword123",
        "full_name": "Audit Inspector",
        "skills": "security,audit,python"
    }
    res = client.post("/api/auth/register", json=reg_data)
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "auditor@tupm.qzz.io"
    # Registration grants no role; roles are per-project (see test_projects_and_roles.py).
    assert "role" not in data["user"]

    # 2. Prevent duplicate email registration
    res_dup = client.post("/api/auth/register", json=reg_data)
    assert res_dup.status_code == 400

    # 3. Login with credentials
    login_res = client.post("/api/auth/login", json={
        "email": "auditor@tupm.qzz.io",
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
    assert me_data["email"] == "auditor@tupm.qzz.io"
    assert me_data["full_name"] == "Audit Inspector"

def test_unauthenticated_request_rejected(client: TestClient):
    res = client.get("/api/auth/me")
    assert res.status_code == 401

import json
import base64

def test_google_oauth_and_user_management_flow(client: TestClient):
    # 1. Simulate Google ID token
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({
        "sub": "google-user-123456",
        "email": "google.dev@tupm.qzz.io",
        "name": "Google Developer",
        "picture": "https://lh3.googleusercontent.com/a/default-user"
    }).encode()).decode().rstrip("=")
    dummy_jwt = f"{header}.{payload}.signature"

    google_res = client.post("/api/auth/google", json={"credential": dummy_jwt})
    assert google_res.status_code == 200
    auth_data = google_res.json()
    assert "access_token" in auth_data
    assert auth_data["user"]["email"] == "google.dev@tupm.qzz.io"
    assert auth_data["user"]["avatar_url"] == "https://lh3.googleusercontent.com/a/default-user"
    user_id = auth_data["user"]["id"]
    token = auth_data["access_token"]

    # 2. Query all users (Authenticated)
    users_res = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert users_res.status_code == 200
    user_list = users_res.json()
    assert any(u["email"] == "google.dev@tupm.qzz.io" for u in user_list)

    # 3. The Google-authenticated user can edit their own profile.
    patch_res = client.patch(
        f"/api/users/{user_id}",
        json={"skills": "golang,kubernetes,vue"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["skills"] == "golang,kubernetes,vue"


def test_unverified_google_token_rejected_when_flag_disabled(client: TestClient, monkeypatch):
    """
    With ALLOW_UNVERIFIED_GOOGLE_TOKENS off, a token whose signature cannot be
    verified must be refused rather than trusted (D6 RISK-01).
    """
    from app.config import settings
    monkeypatch.setattr(settings, "ALLOW_UNVERIFIED_GOOGLE_TOKENS", False)

    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({
        "sub": "attacker-1",
        "email": "victim@tupm.qzz.io",
        "name": "Victim",
    }).encode()).decode().rstrip("=")
    forged = f"{header}.{payload}.not-a-real-signature"

    res = client.post("/api/auth/google", json={"credential": forged})
    assert res.status_code == 401
    assert "could not be verified" in res.json()["detail"]
