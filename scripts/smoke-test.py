#!/usr/bin/env python3
"""
End-to-end smoke test against a RUNNING, seeded instance (scripts/seed-demo.py).
Exercises every feature area through the public API, including the AI
endpoints, and checks permissions from the outside.

    python3 scripts/smoke-test.py [base-url]

Exit code is the number of failed checks. AI checks pass on any tier; whether a
real LLM answered is printed, and is visible in the backend log ("AI DEGRADED"
means the deterministic fallback was used).
"""
import json, os, sys, time, urllib.request, urllib.error

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8090").rstrip("/") + "/api"
PW = os.environ.get("SEED_PASSWORD", "Koshi@2026")
fails = 0


def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read(); return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return e.code, json.loads(raw)
        except Exception: return e.code, raw


def check(name, cond, detail=""):
    global fails
    print(("  ok    " if cond else "  FAIL  ") + name + ("" if cond else f"  -- {detail}"))
    if not cond: fails += 1


def login(slug):
    s, b = call("POST", "/auth/login", body={"email": f"{slug}@koshi.dev", "password": PW})
    assert s == 200, f"login {slug}: {s} {b}"
    return b["access_token"]


print(f"Smoke test {BASE}")
an, binh, dung = login("huynh"), login("tu"), login("don")

print("auth")
s, _ = call("POST", "/auth/login", body={"email": "huynh@koshi.dev", "password": "wrong"})
check("wrong password -> 401", s == 401, s)
s, me = call("GET", "/auth/me", an)
check("me has no global role", s == 200 and "role" not in me, me)
s, _ = call("GET", "/auth/me")
check("no token -> 401", s == 401, s)

print("projects & roles")
s, ps = call("GET", "/projects", an)
byname = {p["name"]: p for p in ps}
mob, web = byname["Koshi Mobile App"], byname["Website Bán Hàng Q4"]
check("PM role on own project", mob["my_role"] == "PM", mob)
s, ps_b = call("GET", "/projects", binh)
roles_b = {p["name"]: p["my_role"] for p in ps_b}
check("tu is MEMBER on Mobile, PM on personal", roles_b.get("Koshi Mobile App") == "MEMBER" and roles_b.get("Việc cá nhân của Tú") == "PM", roles_b)
personal = [p for p in ps_b if p["name"] == "Việc cá nhân của Tú"][0]
s, _ = call("GET", f"/projects/{personal['id']}", an)
check("outsider -> 404 on personal project", s == 404, s)
s, _ = call("PATCH", f"/projects/{mob['id']}/members/{me['id']}", binh, {"role": "MEMBER"})
check("member cannot change roles -> 403", s == 403, s)
s, mem = call("GET", f"/projects/{mob['id']}/members", binh)
check("members list (3)", s == 200 and len(mem) == 3, len(mem) if isinstance(mem, list) else mem)

print("tasks")
s, tasks = call("GET", f"/tasks?project_id={mob['id']}", an)
check("list tasks", s == 200 and len(tasks) >= 18, len(tasks))
s, t = call("POST", "/tasks", binh, {"project_id": mob["id"], "title": "Smoke test task", "complexity_points": 2})
check("member creates task", s == 201 and t["key"] == f"TSK-{t['id']}", t)
seq = []
for _ in range(4):
    s, t2 = call("POST", f"/tasks/{t['id']}/cycle-status", binh); seq.append(t2["status"])
check("status cycle TODO→IN_PROGRESS→BLOCKED→DONE→TODO", seq == ["IN_PROGRESS", "BLOCKED", "DONE", "TODO"], seq)
s, _ = call("PATCH", f"/tasks/{t['id']}", binh, {"dependencies": [999999]})
check("unknown dependency -> 400", s == 400, s)
s, _ = call("PATCH", f"/tasks/{t['id']}", binh, {"assignee_ids": [99999]})
check("assign non-member -> 400", s == 400, s)
s, _ = call("GET", f"/tasks/{t['id']}", dung)
check("member reads task", s == 200, s)
s, c = call("POST", f"/tasks/{t['id']}/comments", binh, {"content": "comment from smoke test"})
check("comment", s == 201, c)
s, _ = call("POST", f"/tasks/{t['id']}/comments", binh, {"content": "reply", "parent_id": c["id"]})
check("reply", s == 201, s)
s, _ = call("DELETE", f"/tasks/{t['id']}", binh)
check("delete task", s == 204, s)

print("scrum")
s, sprints = call("GET", f"/sprints?project_id={mob['id']}", binh)
states = sorted(x["state"] for x in sprints)
check("4 sprints: 2 completed, 1 active, 1 planned", states == ["ACTIVE", "COMPLETED", "COMPLETED", "PLANNED"], states)
active = [x for x in sprints if x["state"] == "ACTIVE"][0]
planned = [x for x in sprints if x["state"] == "PLANNED"][0]
s, v = call("GET", f"/sprints/velocity/history?project_id={mob['id']}", binh)
check("velocity S1 16→11, S2 15→15", [(x["committed_points"], x["completed_points"]) for x in v] == [(16, 11), (15, 15)], v)
s, b = call("GET", f"/sprints/{active['id']}/burndown", binh)
rem = [d["remaining"] for d in b["days"] if d["remaining"] is not None]
check("burndown active sprint has history", s == 200 and b["total_points"] == 23 and rem[-1] == 16, (b.get("total_points"), rem))
s, _ = call("POST", f"/sprints/{planned['id']}/start", an)
check("second active sprint -> 409", s == 409, s)
s, _ = call("POST", f"/sprints/{planned['id']}/start", binh)
check("member cannot start sprint -> 403", s == 403, s)
s, _ = call("POST", "/tasks", an, {"project_id": web["id"], "title": "x", "sprint_id": active["id"]})
check("task into another project's sprint -> 400", s == 400, s)

print("stats & notifications")
s, w = call("GET", f"/stats/workload?project_id={mob['id']}", an)
check("workload", s == 200 and len(w) >= 3, w)
s, d = call("GET", f"/stats/delayed-tasks?project_id={web['id']}", an)
check("delayed tasks (web has overdue)", s == 200 and len(d) >= 1, d)
s, n = call("GET", "/notifications", binh)
check("tu has notifications (mention/assign)", s == 200 and len(n) >= 1, n)

print("AI (Groq)")
tiers = {}
t0 = time.time(); s, r = call("POST", f"/ai/weekly-summary?project_id={mob['id']}", an)
check("weekly summary", s == 200 and len(r.get("summary", "")) > 50, r); tiers["summary"] = (time.time() - t0, r.get("summary", "")[:160])
t0 = time.time(); s, r = call("POST", "/ai/meeting-minutes", an, {"notes": "Họp sprint 3: Cường làm hàng đợi offline xong trước thứ 6, Dung test sau đó. Quyết định dùng outbox pattern. Bình làm badge trạng thái."})
check("meeting minutes", s == 200 and isinstance(r.get("action_items"), list), r); tiers["minutes"] = (time.time() - t0, json.dumps(r, ensure_ascii=False)[:200])
t0 = time.time(); s, r = call("POST", f"/ai/recommend-assignment?project_id={mob['id']}", an, {"title": "Màn hình cài đặt thông báo", "description": "Giao diện Vue cho cài đặt push"})
check("assignment recommendation", s == 200 and r.get("recommendation", {}).get("recommended_name"), r); tiers["assign"] = (time.time() - t0, json.dumps(r, ensure_ascii=False)[:200])
t0 = time.time(); s, r = call("POST", "/ai/decompose", an, {"goal": "Thêm thanh toán MoMo vào website"})
check("decompose", s == 200, r); tiers["decompose"] = (time.time() - t0, json.dumps(r, ensure_ascii=False)[:200])
for k, (dt, sample) in tiers.items():
    print(f"    {k:9s} {dt:5.1f}s  {sample}")

print(f"\n{fails} failed")
sys.exit(fails)
