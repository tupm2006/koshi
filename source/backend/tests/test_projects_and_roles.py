"""
Per-project roles and project-scoped authorisation.

Covers D1 FR-AUTH-04/06/07 and closes D5 GAP-02 (negative authorisation cases)
and D6 RISK-03 (cross-project access).
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Registration no longer carries a role
# ---------------------------------------------------------------------------

def test_registration_accepts_no_role_and_grants_none(client: TestClient):
    res = client.post("/api/auth/register", json={
        "email": "roleless@example.com",
        "password": "password123",
        "full_name": "Roleless User",
    })
    assert res.status_code == 201
    user = res.json()["user"]

    # The account exists but carries no role field at all.
    assert "role" not in user

    # And it starts with no projects, so it has no authority anywhere.
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    projects = client.get("/api/projects", headers=headers)
    assert projects.status_code == 200
    assert projects.json() == []


def test_registration_ignores_a_submitted_role(client: TestClient):
    """A client cannot escalate by posting a role field; it is not in the schema."""
    res = client.post("/api/auth/register", json={
        "email": "sneaky@example.com",
        "password": "password123",
        "full_name": "Sneaky User",
        "role": "PM",
    })
    assert res.status_code == 201
    assert "role" not in res.json()["user"]


# ---------------------------------------------------------------------------
# Project creation grants PM of that project only
# ---------------------------------------------------------------------------

def test_creator_becomes_pm_of_their_own_project(client: TestClient, pm_auth_headers: dict):
    res = client.post("/api/projects", json={"name": "Alpha"}, headers=pm_auth_headers)
    assert res.status_code == 201
    body = res.json()
    assert body["my_role"] == "PM"
    assert body["member_count"] == 1


def test_dashboard_lists_only_my_projects(client: TestClient, pm_auth_headers: dict, member_auth_headers: dict):
    client.post("/api/projects", json={"name": "PM Only Project"}, headers=pm_auth_headers)

    mine = client.get("/api/projects", headers=member_auth_headers)
    assert mine.status_code == 200
    assert all(p["name"] != "PM Only Project" for p in mine.json())


# ---------------------------------------------------------------------------
# Role assignment is per-project and PM-gated  (closes GAP-02)
# ---------------------------------------------------------------------------

def test_pm_can_assign_and_change_roles(client: TestClient, pm_auth_headers: dict, project_with_member):
    project_id, member_id = project_with_member

    members = client.get(f"/api/projects/{project_id}/members", headers=pm_auth_headers)
    assert members.status_code == 200
    roles = {m["user_id"]: m["role"] for m in members.json()}
    assert roles[member_id] == "MEMBER"

    promote = client.patch(
        f"/api/projects/{project_id}/members/{member_id}",
        json={"role": "PM"},
        headers=pm_auth_headers,
    )
    assert promote.status_code == 200
    assert promote.json()["role"] == "PM"


def test_member_cannot_change_roles(client: TestClient, member_auth_headers: dict, project_with_member):
    """The negative authorisation case that previously had no coverage."""
    project_id, member_id = project_with_member

    res = client.patch(
        f"/api/projects/{project_id}/members/{member_id}",
        json={"role": "PM"},
        headers=member_auth_headers,
    )
    assert res.status_code == 403


def test_member_cannot_add_or_remove_members(client: TestClient, member_auth_headers: dict, project_with_member):
    project_id, member_id = project_with_member

    add = client.post(
        f"/api/projects/{project_id}/members",
        json={"email": "someone@example.com", "role": "MEMBER"},
        headers=member_auth_headers,
    )
    assert add.status_code == 403

    remove = client.delete(
        f"/api/projects/{project_id}/members/{member_id}", headers=member_auth_headers
    )
    assert remove.status_code == 403


def test_member_cannot_create_sprints(client: TestClient, member_auth_headers: dict, project_with_member):
    from datetime import datetime, timedelta
    project_id, _ = project_with_member
    now = datetime.utcnow()

    res = client.post("/api/sprints", json={
        "project_id": project_id,
        "name": "Unauthorised Sprint",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=7)).isoformat(),
    }, headers=member_auth_headers)
    assert res.status_code == 403


def test_cannot_demote_the_last_pm(client: TestClient, pm_auth_headers: dict):
    proj = client.post("/api/projects", json={"name": "Solo"}, headers=pm_auth_headers)
    project_id = proj.json()["id"]
    me = client.get("/api/auth/me", headers=pm_auth_headers).json()

    res = client.patch(
        f"/api/projects/{project_id}/members/{me['id']}",
        json={"role": "MEMBER"},
        headers=pm_auth_headers,
    )
    assert res.status_code == 400
    assert "last Project Manager" in res.json()["detail"]


def test_roles_are_independent_across_projects(client: TestClient, pm_auth_headers: dict, member_auth_headers: dict):
    """The same user is MEMBER in one project and PM in another."""
    me = client.get("/api/auth/me", headers=member_auth_headers).json()

    shared = client.post("/api/projects", json={"name": "Shared"}, headers=pm_auth_headers).json()
    client.post(
        f"/api/projects/{shared['id']}/members",
        json={"email": me["email"], "role": "MEMBER"},
        headers=pm_auth_headers,
    )

    own = client.post("/api/projects", json={"name": "My Own"}, headers=member_auth_headers).json()

    assert own["my_role"] == "PM"
    fetched_shared = client.get(f"/api/projects/{shared['id']}", headers=member_auth_headers).json()
    assert fetched_shared["my_role"] == "MEMBER"


# ---------------------------------------------------------------------------
# Cross-project isolation  (closes RISK-03)
# ---------------------------------------------------------------------------

def test_non_member_cannot_read_project(client: TestClient, pm_auth_headers: dict, member_auth_headers: dict):
    proj = client.post("/api/projects", json={"name": "Private"}, headers=pm_auth_headers).json()

    res = client.get(f"/api/projects/{proj['id']}", headers=member_auth_headers)
    # 404 rather than 403: existence itself is not disclosed to outsiders.
    assert res.status_code == 404


def test_non_member_cannot_list_or_create_tasks(client: TestClient, pm_auth_headers: dict, member_auth_headers: dict):
    proj = client.post("/api/projects", json={"name": "Sealed"}, headers=pm_auth_headers).json()

    listing = client.get(f"/api/tasks?project_id={proj['id']}", headers=member_auth_headers)
    assert listing.status_code == 404

    creating = client.post("/api/tasks", json={
        "project_id": proj["id"],
        "title": "Injected task",
    }, headers=member_auth_headers)
    assert creating.status_code == 404


def test_non_member_cannot_mutate_a_task_by_id(client: TestClient, pm_auth_headers: dict, member_auth_headers: dict):
    proj = client.post("/api/projects", json={"name": "Guarded"}, headers=pm_auth_headers).json()
    task = client.post("/api/tasks", json={
        "project_id": proj["id"],
        "title": "PM's task",
    }, headers=pm_auth_headers).json()

    assert client.get(f"/api/tasks/{task['id']}", headers=member_auth_headers).status_code == 404
    assert client.patch(f"/api/tasks/{task['id']}", json={"title": "hijacked"},
                        headers=member_auth_headers).status_code == 404
    assert client.post(f"/api/tasks/{task['id']}/cycle-status",
                       headers=member_auth_headers).status_code == 404
    assert client.delete(f"/api/tasks/{task['id']}", headers=member_auth_headers).status_code == 404

    # And the task is genuinely untouched.
    still_there = client.get(f"/api/tasks/{task['id']}", headers=pm_auth_headers)
    assert still_there.status_code == 200
    assert still_there.json()["title"] == "PM's task"


def test_non_member_cannot_reach_ai_or_stats(client: TestClient, pm_auth_headers: dict, member_auth_headers: dict):
    proj = client.post("/api/projects", json={"name": "Confidential"}, headers=pm_auth_headers).json()
    pid = proj["id"]

    assert client.post(f"/api/ai/weekly-summary?project_id={pid}",
                       headers=member_auth_headers).status_code == 404
    assert client.get(f"/api/stats/workload?project_id={pid}",
                      headers=member_auth_headers).status_code == 404
    assert client.get(f"/api/stats/delayed-tasks?project_id={pid}",
                      headers=member_auth_headers).status_code == 404


# ---------------------------------------------------------------------------
# Profile editing is self-service only
# ---------------------------------------------------------------------------

def test_user_can_edit_own_profile(client: TestClient, member_auth_headers: dict):
    me = client.get("/api/auth/me", headers=member_auth_headers).json()
    res = client.patch(f"/api/users/{me['id']}", json={"skills": "rust,wasm"},
                       headers=member_auth_headers)
    assert res.status_code == 200
    assert res.json()["skills"] == "rust,wasm"


def test_user_cannot_edit_another_profile(client: TestClient, pm_auth_headers: dict, member_auth_headers: dict):
    other = client.get("/api/auth/me", headers=pm_auth_headers).json()
    res = client.patch(f"/api/users/{other['id']}", json={"skills": "hacked"},
                       headers=member_auth_headers)
    assert res.status_code == 403
