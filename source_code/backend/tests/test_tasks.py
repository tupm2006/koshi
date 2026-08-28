import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

def test_task_lifecycle_and_comments(client: TestClient, pm_auth_headers: dict):
    # 1. Create a project
    proj_res = client.post("/api/projects", json={
        "name": "Audit Verification Project",
        "description": "Integration testing verification project"
    }, headers=pm_auth_headers)
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 2. Create a Sprint
    now = datetime.utcnow()
    sprint_res = client.post("/api/sprints", json={
        "project_id": project_id,
        "name": "Sprint 101: Verification",
        "goal": "Verify all endpoints",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=14)).isoformat()
    }, headers=pm_auth_headers)
    assert sprint_res.status_code == 201
    sprint_id = sprint_res.json()["id"]

    # 3. Create a Task
    task_payload = {
        "project_id": project_id,
        "sprint_id": sprint_id,
        "title": "Build FastAPI Test Suite",
        "description": "Ensure 100% test pass rate",
        "priority": "CRITICAL",
        "complexity_points": 3,
        "due_date": (now + timedelta(days=3)).isoformat(),
        "dependencies": ["TSK-1"],
        "acceptance_criteria": ["All tests green"]
    }
    task_res = client.post("/api/tasks", json=task_payload, headers=pm_auth_headers)
    assert task_res.status_code == 201
    task_data = task_res.json()
    task_id = task_data["id"]
    assert task_data["status"] == "TODO"
    assert task_data["priority"] == "CRITICAL"

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

    # 7. Check Sprint Stats
    stats_res = client.get(f"/api/sprints/{sprint_id}/stats", headers=pm_auth_headers)
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert stats_data["total_tasks"] == 1
    assert stats_data["blocked_tasks"] == 1
