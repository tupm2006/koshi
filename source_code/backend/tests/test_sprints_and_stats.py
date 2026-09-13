import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

def test_sprint_creation_listing_and_rbac(client: TestClient, project_with_member, pm_auth_headers: dict, member_auth_headers: dict):
    project_id, member_id = project_with_member
    now = datetime.utcnow()

    # 1. PM can create a sprint
    sprint_payload = {
        "project_id": project_id,
        "name": "Sprint 1: Core Foundation",
        "goal": "Deliver MVP architecture",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=14)).isoformat(),
        "is_active": True,
    }
    create_res = client.post("/api/sprints", json=sprint_payload, headers=pm_auth_headers)
    assert create_res.status_code == 201
    sprint_data = create_res.json()
    assert sprint_data["name"] == "Sprint 1: Core Foundation"
    sprint_id = sprint_data["id"]

    # 2. Member cannot create a sprint
    member_sprint_res = client.post("/api/sprints", json={
        "project_id": project_id,
        "name": "Sprint Member Attempt",
        "goal": "Should fail",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=14)).isoformat(),
    }, headers=member_auth_headers)
    assert member_sprint_res.status_code == 403

    # 3. List sprints for project
    list_res = client.get(f"/api/sprints?project_id={project_id}", headers=member_auth_headers)
    assert list_res.status_code == 200
    sprints = list_res.json()
    assert len(sprints) >= 1
    assert any(s["id"] == sprint_id for s in sprints)

    # 4. Sprint stats
    stats_res = client.get(f"/api/sprints/{sprint_id}/stats", headers=member_auth_headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["sprint_id"] == sprint_id
    assert stats["total_tasks"] == 0
    assert stats["completion_rate_pct"] == 0.0

    # 5. Non-member cannot list sprints or get stats
    non_member_reg = client.post("/api/auth/register", json={
        "email": "outsider_sprint@example.com",
        "password": "password123",
        "full_name": "Outsider User",
    })
    outsider_headers = {"Authorization": f"Bearer {non_member_reg.json()['access_token']}"}

    forbidden_list = client.get(f"/api/sprints?project_id={project_id}", headers=outsider_headers)
    assert forbidden_list.status_code == 403

    forbidden_stats = client.get(f"/api/sprints/{sprint_id}/stats", headers=outsider_headers)
    assert forbidden_stats.status_code == 403

def test_delayed_tasks_sla_calculation(client: TestClient, project_with_member, pm_auth_headers: dict, member_auth_headers: dict):
    project_id, member_id = project_with_member
    now = datetime.utcnow()

    # 1. Create a delayed task (due 5 days ago)
    past_due = now - timedelta(days=5)
    overdue_task_res = client.post("/api/tasks", json={
        "project_id": project_id,
        "title": "Overdue Backend Task",
        "description": "Task past due date",
        "priority": "HIGH",
        "complexity_points": 5,
        "due_date": past_due.isoformat(),
        "assignee_id": member_id,
        "documents": ["spec_v1.pdf"]
    }, headers=pm_auth_headers)
    assert overdue_task_res.status_code == 201
    overdue_task = overdue_task_res.json()
    assert overdue_task["is_overdue"] is True
    assert overdue_task["slip_days"] >= 5
    assert overdue_task["documents"] == ["spec_v1.pdf"]

    # 2. Create on-time task (due in 5 days)
    future_due = now + timedelta(days=5)
    ontime_task_res = client.post("/api/tasks", json={
        "project_id": project_id,
        "title": "Future Task",
        "priority": "LOW",
        "due_date": future_due.isoformat(),
    }, headers=pm_auth_headers)
    assert ontime_task_res.status_code == 201
    assert ontime_task_res.json()["is_overdue"] is False
    assert ontime_task_res.json()["slip_days"] == 0

    # 3. Fetch delayed tasks from stats endpoint
    delayed_res = client.get(f"/api/v1/stats/delayed-tasks?project_id={project_id}", headers=pm_auth_headers)
    assert delayed_res.status_code == 200
    delayed_tasks = delayed_res.json()
    assert len(delayed_tasks) >= 1

    matched = next((d for d in delayed_tasks if d["task_id"] == overdue_task["id"]), None)
    assert matched is not None
    assert matched["days_overdue"] == (now - past_due).days
    assert matched["days_overdue"] >= 5

    # 4. Resolve overdue task to DONE -> should no longer appear in delayed-tasks
    done_res = client.put(f"/api/tasks/{overdue_task['id']}", json={
        "status": "DONE"
    }, headers=pm_auth_headers)
    assert done_res.status_code == 200
    assert done_res.json()["is_overdue"] is False

    delayed_res_after = client.get(f"/api/v1/stats/delayed-tasks?project_id={project_id}", headers=pm_auth_headers)
    assert delayed_res_after.status_code == 200
    assert not any(d["task_id"] == overdue_task["id"] for d in delayed_res_after.json())

def test_priority_proposal_and_approval_flow(client: TestClient, project_with_member, pm_auth_headers: dict, member_auth_headers: dict):
    project_id, member_id = project_with_member

    # 1. PM creates task with LOW priority
    task_res = client.post("/api/tasks", json={
        "project_id": project_id,
        "title": "Security Audit Hardening",
        "description": "Fix potential auth vulnerabilities",
        "priority": "LOW",
        "complexity_points": 3,
        "assignee_id": member_id,
        "documents": ["architecture_review.md"]
    }, headers=pm_auth_headers)
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]
    assert task_res.json()["priority"] == "LOW"

    # 2. Member attempts direct priority escalation -> 403 Forbidden
    direct_escalate = client.put(f"/api/tasks/{task_id}", json={
        "priority": "CRITICAL"
    }, headers=member_auth_headers)
    assert direct_escalate.status_code == 403

    # 3. Member submits priority change request / proposal
    req_res = client.post(f"/api/v1/tasks/{task_id}/request-priority", json={
        "requested_priority": "CRITICAL",
        "reason": "Vulnerability discovered in staging environment"
    }, headers=member_auth_headers)
    assert req_res.status_code == 200
    req_data = req_res.json()
    assert req_data["priority"] == "LOW"  # Not changed yet
    assert req_data["requested_priority"] == "CRITICAL"
    assert req_data["priority_request_reason"] == "Vulnerability discovered in staging environment"
    assert req_data["priority_requested_by_id"] == member_id

    # 4. Member attempts to approve priority change -> 403 Forbidden
    member_approve = client.post(f"/api/v1/tasks/{task_id}/approve-priority", headers=member_auth_headers)
    assert member_approve.status_code == 403

    # 5. Non-member cannot approve priority change -> 403 Forbidden
    outsider_reg = client.post("/api/auth/register", json={
        "email": "outsider_prio@example.com",
        "password": "password123",
        "full_name": "Outsider Prio",
    })
    outsider_headers = {"Authorization": f"Bearer {outsider_reg.json()['access_token']}"}
    outsider_approve = client.post(f"/api/v1/tasks/{task_id}/approve-priority", headers=outsider_headers)
    assert outsider_approve.status_code == 403

    # 6. PM approves priority change
    pm_approve = client.post(f"/api/v1/tasks/{task_id}/approve-priority", headers=pm_auth_headers)
    assert pm_approve.status_code == 200
    approved_data = pm_approve.json()
    assert approved_data["priority"] == "CRITICAL"
    assert approved_data["requested_priority"] is None
    assert approved_data["priority_request_reason"] is None
    assert approved_data["priority_requested_by_id"] is None

def test_priority_proposal_rejection_flow(client: TestClient, project_with_member, pm_auth_headers: dict, member_auth_headers: dict):
    project_id, member_id = project_with_member

    # 1. PM creates task with MEDIUM priority
    task_res = client.post("/api/tasks", json={
        "project_id": project_id,
        "title": "Refactor Button Styles",
        "priority": "MEDIUM",
        "complexity_points": 1,
        "assignee_id": member_id,
    }, headers=pm_auth_headers)
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]

    # 2. Member requests HIGH priority
    req_res = client.post(f"/api/v1/tasks/{task_id}/request-priority", json={
        "requested_priority": "HIGH",
        "reason": "Designer requested quick turnaround"
    }, headers=member_auth_headers)
    assert req_res.status_code == 200
    assert req_res.json()["requested_priority"] == "HIGH"

    # 3. Member attempts to reject -> 403 Forbidden
    member_reject = client.post(f"/api/v1/tasks/{task_id}/reject-priority", headers=member_auth_headers)
    assert member_reject.status_code == 403

    # 4. PM rejects request
    pm_reject = client.post(f"/api/v1/tasks/{task_id}/reject-priority", headers=pm_auth_headers)
    assert pm_reject.status_code == 200
    rejected_data = pm_reject.json()
    assert rejected_data["priority"] == "MEDIUM"
    assert rejected_data["requested_priority"] is None
    assert rejected_data["priority_request_reason"] is None
    assert rejected_data["priority_requested_by_id"] is None

def test_task_documents_mutation_flow(client: TestClient, project_with_member, pm_auth_headers: dict):
    project_id, member_id = project_with_member

    # 1. Create task with initial documents
    init_docs = ["https://drive.google.com/doc1", "spec.pdf"]
    task_res = client.post("/api/tasks", json={
        "project_id": project_id,
        "title": "Task with Documents",
        "priority": "MEDIUM",
        "documents": init_docs,
    }, headers=pm_auth_headers)
    assert task_res.status_code == 201
    task = task_res.json()
    assert task["documents"] == init_docs
    task_id = task["id"]

    # 2. Update task with appended document
    updated_docs = init_docs + ["figma_link.url"]
    update_res = client.put(f"/api/tasks/{task_id}", json={
        "documents": updated_docs
    }, headers=pm_auth_headers)
    assert update_res.status_code == 200
    assert update_res.json()["documents"] == updated_docs

    # 3. Verify fetched task retains documents
    get_res = client.get(f"/api/tasks/{task_id}", headers=pm_auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["documents"] == updated_docs
