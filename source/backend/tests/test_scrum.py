"""
Scrum: sprint lifecycle, backlog planning, burndown and velocity (DEC-028).
"""
from datetime import timedelta
from fastapi.testclient import TestClient
from app.utils.time import utcnow


def _sprint(client, headers, project_id, name="S1", days=10, active=False):
    now = utcnow()
    res = client.post("/api/sprints", json={
        "project_id": project_id, "name": name, "goal": "g",
        "start_date": (now - timedelta(days=1)).isoformat(),
        "end_date": (now + timedelta(days=days)).isoformat(),
        "is_active": active,
    }, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def _task(client, headers, project_id, sprint_id=None, points=3, **kw):
    res = client.post("/api/tasks", json={
        "project_id": project_id, "title": kw.pop("title", "t"),
        "complexity_points": points, "sprint_id": sprint_id, **kw,
    }, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def test_new_sprint_is_planned_and_start_records_commitment(client: TestClient, pm_auth_headers, project_with_member):
    pid, _ = project_with_member
    s = _sprint(client, pm_auth_headers, pid)
    assert s["state"] == "PLANNED"
    _task(client, pm_auth_headers, pid, s["id"], points=3)
    _task(client, pm_auth_headers, pid, s["id"], points=5)
    started = client.post(f"/api/sprints/{s['id']}/start", headers=pm_auth_headers)
    assert started.status_code == 200
    assert started.json()["state"] == "ACTIVE"
    assert started.json()["committed_points"] == 8


def test_only_one_active_sprint_per_project(client, pm_auth_headers, project_with_member):
    pid, _ = project_with_member
    a = _sprint(client, pm_auth_headers, pid, "A")
    b = _sprint(client, pm_auth_headers, pid, "B")
    assert client.post(f"/api/sprints/{a['id']}/start", headers=pm_auth_headers).status_code == 200
    assert client.post(f"/api/sprints/{b['id']}/start", headers=pm_auth_headers).status_code == 409


def test_member_cannot_run_the_lifecycle(client, pm_auth_headers, member_auth_headers, project_with_member):
    pid, _ = project_with_member
    s = _sprint(client, pm_auth_headers, pid)
    for path in ("start", "complete"):
        res = client.post(f"/api/sprints/{s['id']}/{path}", json={}, headers=member_auth_headers)
        assert res.status_code == 403
    # but members can read
    assert client.get(f"/api/sprints/{s['id']}/burndown", headers=member_auth_headers).status_code == 200


def test_complete_moves_unfinished_work_and_keeps_done(client, pm_auth_headers, project_with_member):
    pid, _ = project_with_member
    s = _sprint(client, pm_auth_headers, pid, "S1")
    nxt = _sprint(client, pm_auth_headers, pid, "S2")
    done = _task(client, pm_auth_headers, pid, s["id"], points=2, status="DONE")
    open_ = _task(client, pm_auth_headers, pid, s["id"], points=3)
    client.post(f"/api/sprints/{s['id']}/start", headers=pm_auth_headers)
    res = client.post(f"/api/sprints/{s['id']}/complete", json={"move_unfinished_to": nxt["id"]}, headers=pm_auth_headers)
    assert res.status_code == 200 and res.json()["state"] == "COMPLETED"
    assert client.get(f"/api/tasks/{open_['id']}", headers=pm_auth_headers).json()["sprint_id"] == nxt["id"]
    assert client.get(f"/api/tasks/{done['id']}", headers=pm_auth_headers).json()["sprint_id"] == s["id"]
    vel = client.get(f"/api/sprints/velocity/history?project_id={pid}", headers=pm_auth_headers).json()
    assert vel == [{"sprint_id": s["id"], "sprint_name": "S1", "committed_points": 5, "completed_points": 2}]
    # A completed sprint accepts no new work and cannot restart.
    assert client.post(f"/api/sprints/{s['id']}/start", headers=pm_auth_headers).status_code == 400
    r = client.post("/api/tasks", json={"project_id": pid, "title": "late", "sprint_id": s["id"]}, headers=pm_auth_headers)
    assert r.status_code == 400


def test_complete_without_target_returns_work_to_backlog(client, pm_auth_headers, project_with_member):
    pid, _ = project_with_member
    s = _sprint(client, pm_auth_headers, pid)
    t = _task(client, pm_auth_headers, pid, s["id"])
    client.post(f"/api/sprints/{s['id']}/complete", json={}, headers=pm_auth_headers)
    assert client.get(f"/api/tasks/{t['id']}", headers=pm_auth_headers).json()["sprint_id"] is None


def test_task_cannot_be_planned_into_another_projects_sprint(client, pm_auth_headers, project_with_member):
    """Before 0008 sprint_id was stored unchecked — a cross-project write (F-48)."""
    pid, _ = project_with_member
    other = client.post("/api/projects", json={"name": "Other"}, headers=pm_auth_headers).json()
    foreign = _sprint(client, pm_auth_headers, other["id"])
    r = client.post("/api/tasks", json={"project_id": pid, "title": "x", "sprint_id": foreign["id"]}, headers=pm_auth_headers)
    assert r.status_code == 400
    t = _task(client, pm_auth_headers, pid)
    r = client.patch(f"/api/tasks/{t['id']}", json={"sprint_id": foreign["id"]}, headers=pm_auth_headers)
    assert r.status_code == 400


def test_completed_at_follows_status(client, pm_auth_headers, project_with_member):
    pid, _ = project_with_member
    t = _task(client, pm_auth_headers, pid)
    assert t["completed_at"] is None
    d = client.patch(f"/api/tasks/{t['id']}", json={"status": "DONE"}, headers=pm_auth_headers).json()
    assert d["completed_at"] is not None
    # cycle DONE -> TODO clears it
    c = client.post(f"/api/tasks/{t['id']}/cycle-status", headers=pm_auth_headers).json()
    assert c["status"] == "TODO" and c["completed_at"] is None


def test_burndown_counts_done_points(client, pm_auth_headers, project_with_member):
    pid, _ = project_with_member
    s = _sprint(client, pm_auth_headers, pid, days=4)
    _task(client, pm_auth_headers, pid, s["id"], points=3, status="DONE")
    _task(client, pm_auth_headers, pid, s["id"], points=5)
    b = client.get(f"/api/sprints/{s['id']}/burndown", headers=pm_auth_headers).json()
    assert b["total_points"] == 8
    assert b["days"][0]["ideal"] == 8
    assert b["days"][-1]["ideal"] == 0
    today = [d for d in b["days"] if d["remaining"] is not None][-1]
    assert today["remaining"] == 5
    assert b["days"][-1]["remaining"] is None  # future


def test_delete_sprint_returns_tasks_to_backlog(client, pm_auth_headers, project_with_member):
    pid, _ = project_with_member
    s = _sprint(client, pm_auth_headers, pid)
    t = _task(client, pm_auth_headers, pid, s["id"])
    assert client.delete(f"/api/sprints/{s['id']}", headers=pm_auth_headers).status_code == 204
    assert client.get(f"/api/tasks/{t['id']}", headers=pm_auth_headers).json()["sprint_id"] is None


def test_outsider_gets_404_on_sprint_reads(client, pm_auth_headers, member_auth_headers):
    p = client.post("/api/projects", json={"name": "Private"}, headers=pm_auth_headers).json()
    s = _sprint(client, pm_auth_headers, p["id"])
    assert client.get(f"/api/sprints/{s['id']}/burndown", headers=member_auth_headers).status_code == 404
    assert client.get(f"/api/sprints/velocity/history?project_id={p['id']}", headers=member_auth_headers).status_code == 404
