"""Task history (migration 0009) and the AI sprint retrospective."""
from datetime import timedelta
import httpx
from app.config import settings
from app.utils.time import utcnow


def _task(client, h, pid, **kw):
    r = client.post("/api/tasks", json={"project_id": pid, "title": "Viết API", **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_history_records_each_changed_field_with_actor(client, pm_auth_headers, member_auth_headers, project_with_member):
    pid, member_id = project_with_member
    t = _task(client, pm_auth_headers, pid)
    client.patch(f"/api/tasks/{t['id']}", json={"priority": "HIGH", "title": "Viết API v2"}, headers=member_auth_headers)
    client.patch(f"/api/tasks/{t['id']}", json={"title": "Viết API v2"}, headers=member_auth_headers)  # no-op
    client.post(f"/api/tasks/{t['id']}/cycle-status", headers=pm_auth_headers)
    client.patch(f"/api/tasks/{t['id']}", json={"assignee_ids": [member_id]}, headers=pm_auth_headers)
    h = client.get(f"/api/tasks/{t['id']}/history", headers=pm_auth_headers).json()
    fields = [(e["field"], e["old_value"], e["new_value"]) for e in reversed(h)]
    assert fields[0] == ("created", None, "Viết API")
    assert ("priority", "MEDIUM", "HIGH") in fields
    assert ("title", "Viết API", "Viết API v2") in fields
    assert ("status", "TODO", "IN_PROGRESS") in fields
    assert ("assignees", None, "Test Member") in fields
    assert len([f for f in fields if f[0] == "title"]) == 1  # the no-op PATCH recorded nothing
    by = {e["field"]: e["actor"]["full_name"] for e in h}
    assert by["priority"] == "Test Member" and by["status"] == "Test PM"


def test_history_is_member_only(client, pm_auth_headers, member_auth_headers):
    p = client.post("/api/projects", json={"name": "Private"}, headers=pm_auth_headers).json()
    t = _task(client, pm_auth_headers, p["id"])
    assert client.get(f"/api/tasks/{t['id']}/history", headers=member_auth_headers).status_code == 404


def _sprint_with_work(client, h, pid):
    now = utcnow()
    s = client.post("/api/sprints", json={"project_id": pid, "name": "S", "goal": "g",
        "start_date": (now - timedelta(days=5)).isoformat(), "end_date": (now + timedelta(days=5)).isoformat(),
        "is_active": False}, headers=h).json()
    _task(client, h, pid, sprint_id=s["id"], complexity_points=3, status="DONE")
    _task(client, h, pid, sprint_id=s["id"], complexity_points=5, status="BLOCKED", blocking_reason="chờ API")
    client.post(f"/api/sprints/{s['id']}/start", headers=h)
    return s


def test_retro_without_a_model_is_built_from_the_sprint_data(client, pm_auth_headers, project_with_member, monkeypatch):
    pid, _ = project_with_member
    s = _sprint_with_work(client, pm_auth_headers, pid)
    monkeypatch.setattr(settings, "AI_API_KEY", "")

    async def down(self, url, **kw):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(httpx.AsyncClient, "post", down)
    r = client.post(f"/api/ai/sprint-retro?sprint_id={s['id']}", headers=pm_auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert any("3/8" in x for x in body["went_well"])
    assert any("chờ API" in x for x in body["to_improve"])
    assert body["action_items"]


def test_retro_uses_the_model_and_sends_it_the_numbers(client, pm_auth_headers, project_with_member, monkeypatch):
    pid, _ = project_with_member
    s = _sprint_with_work(client, pm_auth_headers, pid)
    sent = {}

    class R:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": '{"went_well":["a"],"to_improve":["b"],"action_items":["c"]}'}}]}

    async def fake(self, url, **kw):
        sent.update(kw["json"])
        return R()
    monkeypatch.setattr(settings, "AI_API_KEY", "k")
    monkeypatch.setattr(httpx.AsyncClient, "post", fake)
    r = client.post(f"/api/ai/sprint-retro?sprint_id={s['id']}", headers=pm_auth_headers).json()
    assert r["went_well"] == ["a"] and r["action_items"] == ["c"]
    assert '"committed_points": 8' in sent["messages"][1]["content"]


def test_retro_for_outsider_is_404(client, pm_auth_headers, member_auth_headers):
    p = client.post("/api/projects", json={"name": "Private2"}, headers=pm_auth_headers).json()
    s = _sprint_with_work(client, pm_auth_headers, p["id"])
    assert client.post(f"/api/ai/sprint-retro?sprint_id={s['id']}", headers=member_auth_headers).status_code == 404
