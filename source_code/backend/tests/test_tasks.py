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
    assert task_data["is_overdue"] is False
    assert task_data["slip_days"] == 0

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

def test_overdue_task_sla_calculation(client: TestClient, pm_auth_headers: dict):
    now = datetime.utcnow()
    # Task with due_date in the past (3 days ago)
    overdue_payload = {
        "project_id": 1,
        "title": "Overdue Security Remediation",
        "description": "Task that missed its SLA",
        "priority": "HIGH",
        "status": "IN_PROGRESS",
        "due_date": (now - timedelta(days=3)).isoformat()
    }
    create_res = client.post("/api/tasks", json=overdue_payload, headers=pm_auth_headers)
    assert create_res.status_code == 201
    task = create_res.json()
    assert task["is_overdue"] is True
    assert task["slip_days"] >= 3

def test_priority_governance_workflow_and_rbac(client: TestClient, pm_auth_headers: dict, member_auth_headers: dict):
    # 1. Create a task by PM
    task_res = client.post("/api/tasks", json={
        "project_id": 1,
        "title": "Refactor Database Indexing",
        "priority": "MEDIUM"
    }, headers=pm_auth_headers)
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]

    # 2. Member tries direct priority update -> Must return 403 Forbidden
    direct_res = client.patch(f"/api/tasks/{task_id}", json={
        "priority": "CRITICAL"
    }, headers=member_auth_headers)
    assert direct_res.status_code == 403
    assert "Members cannot directly change priority" in direct_res.json()["detail"]

    # 3. Member submits a priority change proposal -> Must succeed with 200 OK
    proposal_res = client.post(f"/api/tasks/{task_id}/request-priority", json={
        "requested_priority": "CRITICAL",
        "reason": "Production database latency spike under load"
    }, headers=member_auth_headers)
    assert proposal_res.status_code == 200
    p_data = proposal_res.json()
    assert p_data["priority"] == "MEDIUM"
    assert p_data["requested_priority"] == "CRITICAL"
    assert p_data["priority_request_reason"] == "Production database latency spike under load"

    # 4. Member tries to approve proposal -> Must return 403 Forbidden
    approve_unauth = client.post(f"/api/tasks/{task_id}/approve-priority", headers=member_auth_headers)
    assert approve_unauth.status_code == 403

    # 5. PM approves priority proposal -> Must succeed and promote priority
    approve_res = client.post(f"/api/tasks/{task_id}/approve-priority", headers=pm_auth_headers)
    assert approve_res.status_code == 200
    app_data = approve_res.json()
    assert app_data["priority"] == "CRITICAL"
    assert app_data["requested_priority"] is None
    assert app_data["priority_request_reason"] is None

    # 6. Member submits another request for LOW priority
    client.post(f"/api/tasks/{task_id}/request-priority", json={
        "requested_priority": "LOW",
        "reason": "Downgrading priority"
    }, headers=member_auth_headers)

    # 7. PM rejects the request -> Priority remains CRITICAL
    reject_res = client.post(f"/api/tasks/{task_id}/reject-priority", headers=pm_auth_headers)
    assert reject_res.status_code == 200
    rej_data = reject_res.json()
    assert rej_data["priority"] == "CRITICAL"
    assert rej_data["requested_priority"] is None
