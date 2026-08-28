import pytest
import json
import base64
from fastapi.testclient import TestClient

def test_register_and_login_flow(client: TestClient):
    # 1. Register new user with only full_name, email, password
    reg_data = {
        "email": "auditor@tupm.qzz.io",
        "password": "securepassword123",
        "full_name": "Audit Inspector"
    }
    res = client.post("/api/auth/register", json=reg_data)
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "auditor@tupm.qzz.io"

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

    # 2. Query user search API (/api/users/search and /api/v1/users/search)
    search_res = client.get("/api/v1/users/search?q=google", headers={"Authorization": f"Bearer {token}"})
    assert search_res.status_code == 200
    search_list = search_res.json()
    assert len(search_list) >= 1
    assert search_list[0]["email"] == "google.dev@tupm.qzz.io"

    # 3. Test Project creation & auto-owner assignment
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "OAuth Test Workspace", "description": "Testing project membership"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # 4. Verify project members list
    members_res = client.get(f"/api/v1/projects/{proj_id}/members", headers={"Authorization": f"Bearer {token}"})
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 1
    assert members[0]["user_id"] == user_id
    assert members[0]["role"] == "OWNER"

    # 5. Add second member to project
    # Login as seed PM
    pm_login = client.post("/api/auth/login", json={"email": "pm@tupm.qzz.io", "password": "koshi123"})
    pm_token = pm_login.json()["access_token"]
    pm_id = pm_login.json()["user"]["id"]

    add_mem_res = client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"user_id": pm_id, "role": "PM"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert add_mem_res.status_code == 201
    assert add_mem_res.json()["role"] == "PM"
