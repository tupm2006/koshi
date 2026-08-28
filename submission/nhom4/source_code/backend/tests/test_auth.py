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
    # 1. Test mock token handling in test environment
    dummy_jwt = "mock_google_token_google.dev@tupm.qzz.io"

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

def test_tenant_rbac_cross_project_isolation(client: TestClient):
    # 1. Register User A and create Tenant Project A
    res_a = client.post("/api/auth/register", json={
        "email": "user_a@tenant.qzz.io",
        "password": "password123",
        "full_name": "Tenant A User"
    })
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    proj_a = client.post(
        "/api/projects",
        json={"name": "Tenant A Secret Workspace", "description": "Confidential project data"},
        headers=headers_a
    ).json()
    proj_a_id = proj_a["id"]

    # 2. Register User B (different tenant)
    res_b = client.post("/api/auth/register", json={
        "email": "user_b@tenant.qzz.io",
        "password": "password123",
        "full_name": "Tenant B User"
    })
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User B attempts unauthorized access to Project A -> MUST return 403 Forbidden
    unauthorized_proj = client.get(f"/api/projects/{proj_a_id}", headers=headers_b)
    assert unauthorized_proj.status_code == 403

    unauthorized_tasks = client.get(f"/api/tasks?project_id={proj_a_id}", headers=headers_b)
    assert unauthorized_tasks.status_code == 403

    unauthorized_create_task = client.post(
        "/api/tasks",
        json={"project_id": proj_a_id, "title": "Malicious Injection Task", "priority": "HIGH"},
        headers=headers_b
    )
    assert unauthorized_create_task.status_code == 403
