import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.utils.time import utcnow

def test_task_lifecycle_and_comments(client: TestClient, pm_auth_headers: dict):
    # 1. Create a project
    proj_res = client.post("/api/projects", json={
        "name": "Audit Verification Project",
        "description": "Integration testing verification project"
    }, headers=pm_auth_headers)
    assert proj_res.status_code == 201
    assert proj_res.json()["my_role"] == "PM"   # creator is PM of this project
    project_id = proj_res.json()["id"]

    # 2. Create a Sprint
    now = utcnow()
    sprint_res = client.post("/api/sprints", json={
        "project_id": project_id,
        "name": "Sprint 101: Verification",
        "goal": "Verify all endpoints",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=14)).isoformat()
    }, headers=pm_auth_headers)
    assert sprint_res.status_code == 201
    sprint_id = sprint_res.json()["id"]

    # 3. Create a prerequisite, then a Task that genuinely depends on it.
    #    Dependencies are integer task ids: before F-01 was fixed this field was
    #    List[str] against an int primary key, so it could never resolve.
    prereq = client.post("/api/tasks", json={
        "project_id": project_id,
        "title": "Prerequisite",
    }, headers=pm_auth_headers)
    assert prereq.status_code == 201
    prereq_id = prereq.json()["id"]
    assert prereq.json()["key"] == f"TSK-{prereq_id}"

    task_payload = {
        "project_id": project_id,
        "sprint_id": sprint_id,
        "title": "Build FastAPI Test Suite",
        "description": "Ensure 100% test pass rate",
        "priority": "CRITICAL",
        "complexity_points": 3,
        "due_date": (now + timedelta(days=3)).isoformat(),
        "dependencies": [prereq_id],
        "acceptance_criteria": ["All tests green"]
    }
    task_res = client.post("/api/tasks", json=task_payload, headers=pm_auth_headers)
    assert task_res.status_code == 201
    task_data = task_res.json()
    task_id = task_data["id"]
    assert task_data["status"] == "TODO"
    assert task_data["priority"] == "CRITICAL"
    # The dependency round-trips as a resolvable id, not an opaque string.
    assert task_data["dependencies"] == [prereq_id]

    # 4. Cycle status: TODO -> IN_PROGRESS -> BLOCKED -> DONE
    cycle1 = client.post(f"/api/tasks/{task_id}/cycle-status", headers=pm_auth_headers)
    assert cycle1.status_code == 200
    assert cycle1.json()["status"] == "IN_PROGRESS"

    cycle2 = client.post(f"/api/tasks/{task_id}/cycle-status", headers=pm_auth_headers)
    assert cycle2.status_code == 200
    assert cycle2.json()["status"] == "BLOCKED"

    # 5. Add Comment
    comment_res = client.post(f"/api/tasks/{task_id}/comments", json={
        "content": "Blocking issue identified in schema."
    }, headers=pm_auth_headers)
    assert comment_res.status_code == 201
    assert comment_res.json()["content"] == "Blocking issue identified in schema."

    # 6. Fetch task details and verify comment
    get_task_res = client.get(f"/api/tasks/{task_id}", headers=pm_auth_headers)
    assert get_task_res.status_code == 200
    assert len(get_task_res.json()["comments"]) == 1

    # 7. Check Sprint Stats (only the second task is in the sprint)
    stats_res = client.get(f"/api/sprints/{sprint_id}/stats", headers=pm_auth_headers)
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert stats_data["total_tasks"] == 1
    assert stats_data["blocked_tasks"] == 1


def test_dependencies_must_resolve_within_the_project(client: TestClient, pm_auth_headers: dict):
    """Unresolvable dependency ids are refused rather than silently stored."""
    proj = client.post("/api/projects", json={"name": "Dep Validation"}, headers=pm_auth_headers).json()

    ghost = client.post("/api/tasks", json={
        "project_id": proj["id"],
        "title": "Depends on nothing real",
        "dependencies": [999999],
    }, headers=pm_auth_headers)
    assert ghost.status_code == 400
    assert "Unknown dependency" in ghost.json()["detail"]


def test_task_cannot_depend_on_itself(client: TestClient, pm_auth_headers: dict):
    proj = client.post("/api/projects", json={"name": "Self Dep"}, headers=pm_auth_headers).json()
    task = client.post("/api/tasks", json={
        "project_id": proj["id"], "title": "Ouroboros",
    }, headers=pm_auth_headers).json()

    res = client.patch(f"/api/tasks/{task['id']}",
                       json={"dependencies": [task["id"]]}, headers=pm_auth_headers)
    assert res.status_code == 400
    assert "cannot depend on itself" in res.json()["detail"]


def test_dependency_cannot_cross_projects(client: TestClient, pm_auth_headers: dict):
    a = client.post("/api/projects", json={"name": "Proj A"}, headers=pm_auth_headers).json()
    b = client.post("/api/projects", json={"name": "Proj B"}, headers=pm_auth_headers).json()

    in_a = client.post("/api/tasks", json={"project_id": a["id"], "title": "In A"},
                       headers=pm_auth_headers).json()

    res = client.post("/api/tasks", json={
        "project_id": b["id"], "title": "In B", "dependencies": [in_a["id"]],
    }, headers=pm_auth_headers)
    assert res.status_code == 400


def test_complexity_points_bounded_on_update(client: TestClient, pm_auth_headers: dict):
    """F-08: the bound applied on create was missing on update."""
    proj = client.post("/api/projects", json={"name": "Bounds"}, headers=pm_auth_headers).json()
    task = client.post("/api/tasks", json={"project_id": proj["id"], "title": "T"},
                       headers=pm_auth_headers).json()

    assert client.patch(f"/api/tasks/{task['id']}", json={"complexity_points": 99},
                        headers=pm_auth_headers).status_code == 422
    assert client.patch(f"/api/tasks/{task['id']}", json={"complexity_points": 0},
                        headers=pm_auth_headers).status_code == 422
    assert client.patch(f"/api/tasks/{task['id']}", json={"complexity_points": 5},
                        headers=pm_auth_headers).status_code == 200
