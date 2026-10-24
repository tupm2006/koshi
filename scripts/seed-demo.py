#!/usr/bin/env python3
"""
Seed a running Koshi instance with realistic test data — through the public
API, never the database, so every row is one the application itself accepted.
That makes the script a smoke test as well: any endpoint that misbehaves stops
it with the response that did.

    python3 scripts/seed-demo.py                       # http://localhost:8090
    python3 scripts/seed-demo.py http://localhost:8080

Creates three accounts (password from SEED_PASSWORD, default "Koshi@2026"),
three projects — one shared Scrum project, one shared Kanban project, one
personal — with sprints, a product backlog, dependencies, assignees, comments,
@mentions and replies. Idempotent per account: an email that already exists is
logged in instead of re-registered, and a project name the owner already has is
skipped.

These are TEST accounts with a known password. Run it against a local instance,
never against one real people use.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8090").rstrip("/") + "/api"
PASSWORD = os.environ.get("SEED_PASSWORD", "Koshi@2026")
DOMAIN = "koshi.dev"  # .test is rejected by EmailStr


# SEED_LANG=en writes the same data set in English (used for the report's
# screenshots, taken with the UI in English). Translation happens on the way
# out, so the seeding logic below stays written once.
LANG = os.environ.get("SEED_LANG", "vi")
EN = {'API phân trang task': 'Paginated task API',
    'Biểu tượng trạng thái mạng': 'Network status indicator',
    'Chuẩn bị slide thuyết trình đồ án': 'Prepare the project presentation slides',
    'Chưa ước lượng chi tiết — chờ refinement.': 'Not estimated in detail yet — waiting for refinement.',
    'Chế độ tối cho ứng dụng di động': 'Dark mode for the mobile app',
    'Chịu tải 1.000 người dùng': 'Handle 1,000 concurrent users',
    'Chờ VNPay cấp tài khoản sandbox': 'Waiting for VNPay to issue a sandbox account',
    'Danh sách task dạng thẻ': 'Card-style task list',
    'Dự án một người — vẫn sửa được khi mất mạng.': 'A one-person project — still editable offline.',
    'Gia hạn domain cá nhân': 'Renew personal domain',
    'Giải quyết xung đột khi hai người cùng sửa': 'Resolve conflicts when two people edit at once',
    'Giỏ hàng lưu theo phiên': 'Session-persistent shopping cart',
    'Hàng đợi thay đổi khi mất mạng': 'Offline change queue',
    'Học Vue 3 Composition API': 'Learn the Vue 3 Composition API',
    'Kiểm thử E2E luồng đăng nhập': 'E2E tests for the login flow',
    'Kiểm thử tải 1.000 người dùng đồng thời': 'Load test with 1,000 concurrent users',
    'Làm lại website thương mại điện tử trước mùa sale cuối năm.': 'Rebuild the e-commerce site before the year-end sales season.',
    'Lưu task vào SQLite trên máy': 'Store tasks in on-device SQLite',
    'Màn hình đăng nhập email/mật khẩu': 'Email/password sign-in screen',
    'Mình đề xuất dùng bảng outbox. {TAG} xem giúp phần UI hiển thị trạng thái chờ đồng bộ nhé?': 'I suggest an outbox table. {TAG} could you look at how the UI shows pending sync?',
    'Nhắc việc trước hạn 24 giờ': 'Reminder 24 hours before the deadline', "Ok, mình sẽ thêm badge 'đang chờ' trên thẻ.": "OK, I'll add a 'pending' badge on the card.", 'Push notification và nhắc hạn': 'Push notifications and due-date reminders',
    'Sai mật khẩu hiện lỗi rõ ràng': 'A wrong password shows a clear error',
    'Sprint 1 — Giao diện mới': 'Sprint 1 — New storefront',
    'Sprint 1 — Nền tảng': 'Sprint 1 — Foundations',
    'Sprint 2 — Bảng công việc': 'Sprint 2 — Task board',
    'Sprint 2 — Thanh toán': 'Sprint 2 — Payments',
    'Sprint 3 — Hiệu năng': 'Sprint 3 — Performance',
    'Sprint 3 — Đồng bộ ngoại tuyến': 'Sprint 3 — Offline sync',
    'Sprint 4 — Thông báo đẩy': 'Sprint 4 — Push notifications',
    'Sửa lỗi hiển thị giá trên Safari': 'Fix price rendering on Safari',
    'Sửa offline, đồng bộ khi có mạng': 'Edit offline, sync when back online',
    'Test đồng bộ trên mạng chập chờn': 'Test sync on a flaky network',
    'Thiết kế lại trang chủ': 'Redesign the home page',
    'Thiết lập dự án React Native + TypeScript': 'Set up the React Native + TypeScript project',
    'Token lưu an toàn trong Keychain': 'Token stored securely in the Keychain',
    'Trang chính sách đổi trả': 'Returns policy page',
    'Trang chủ và giỏ hàng mới': 'New home page and cart',
    'Tìm kiếm task toàn văn': 'Full-text task search',
    'Tích hợp cổng thanh toán VNPay': 'Integrate the VNPay payment gateway',
    'Tối ưu ảnh sản phẩm (WebP)': 'Optimise product images (WebP)',
    'VNPay chạy được, giá hiển thị đúng': 'VNPay working, prices shown correctly',
    'Việc cá nhân của Tú': "Tú's personal tasks", 'Website Bán Hàng Q4': 'Online Store Q4',
    'Widget màn hình chính': 'Home-screen widget',
    'Xem và sửa task trên điện thoại': 'View and edit tasks on the phone',
    'Đa ngôn ngữ Anh/Việt': 'English/Vietnamese localisation',
    'Đã chuẩn bị kịch bản test với Network Link Conditioner, chỉ chờ build có hàng đợi.': 'Test scenarios with Network Link Conditioner are ready — just waiting for a build with the queue.',
    'Đính kèm ảnh chụp màn hình': 'Screenshot attachments',
    'Đăng ký Firebase Cloud Messaging': 'Register with Firebase Cloud Messaging',
    'Đăng nhập bằng Google': 'Sign in with Google',
    'Đăng nhập, điều hướng và CI chạy được': 'Sign-in, navigation and CI working',
    'Đọc sách Clean Architecture': 'Read Clean Architecture',
    'Ứng dụng di động cho Koshi — quản lý theo Scrum, sprint 2 tuần.': 'The Koshi mobile app — run with Scrum, two-week sprints.'}
_TAG = re.compile(r"@\[[^\]]+\]\(\d+\)")


def _en(value):
    if isinstance(value, dict):
        return {k: _en(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_en(v) for v in value]
    if isinstance(value, str):
        tags = _TAG.findall(value)
        key = _TAG.sub("{TAG}", value)
        if key.startswith("Chờ hàng đợi thay đổi"):
            return value.replace("Chờ hàng đợi thay đổi", "Waiting for the change queue").replace(") xong", ") to land")
        out = EN.get(key, value)
        for t in tags:
            out = out.replace("{TAG}", t, 1)
        return out
    return value


def call(method, path, token=None, body=None, ok=(200, 201, 204)):
    if LANG == "en" and body is not None:
        body = _en(body)
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    # Cloudflare blocks the default Python-urllib agent with a 403.
    req.add_header("User-Agent", "koshi-smoke-test/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, timeout=60) as res:
            raw = res.read()
            status = res.status
    except urllib.error.HTTPError as e:
        raw, status = e.read(), e.code
    if status not in ok:
        raise SystemExit(f"FAILED {method} {path} -> {status}: {raw[:400]!r}")
    return json.loads(raw) if raw else None


def iso(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


PEOPLE = [
    ("huynh", "Phạm Văn Huynh", "management,scrum,architecture,qa"),
    ("tu", "Phạm Minh Tú", "frontend,vue,tailwind,typescript,devops"),
    ("don", "Đàm Đức Đôn", "backend,python,fastapi,mysql,testing"),
]


def account(slug, name, skills):
    email = f"{slug}@{DOMAIN}"
    res = call("POST", "/auth/login", body={"email": email, "password": PASSWORD}, ok=(200, 401))
    if res and "access_token" in res:
        return res["access_token"], res["user"]
    res = call("POST", "/auth/register", body={
        "email": email, "password": PASSWORD, "full_name": name, "skills": skills,
    })
    return res["access_token"], res["user"]


def main():
    print(f"Seeding {BASE}")
    users = {}
    for slug, name, skills in PEOPLE:
        token, user = account(slug, name, skills)
        users[slug] = {"token": token, **user}
        print(f"  account  {user['email']}")
    pm = users["huynh"]["token"]

    existing = {p["name"] for p in call("GET", "/projects", pm)}

    def project(name, desc, members, owner="huynh"):
        tok = users[owner]["token"]
        # Check the OWNER's projects: a project owned by someone else is not
        # in the PM's list, and checking only that list duplicated it.
        shown = _en(name) if LANG == "en" else name
        if shown in existing or shown in {x["name"] for x in call("GET", "/projects", tok)}:
            print(f"  project  {name} (exists, skipped)")
            return None
        p = call("POST", "/projects", tok, {"name": name, "description": desc})
        for slug, role in members:
            call("POST", f"/projects/{p['id']}/members", tok, {"email": users[slug]["email"], "role": role})
            # Invitations grant nothing until accepted — accept as the invitee.
            call("POST", f"/projects/{p['id']}/invitation/accept", users[slug]["token"])
        print(f"  project  {name} (#{p['id']}, {len(members) + 1} members)")
        return p

    def task(pid, tok, title, **kw):
        body = {"project_id": pid, "title": title, **kw}
        return call("POST", "/tasks", tok, body)

    # ------------------------------------------------------------ Scrum project
    p = project(
        "Koshi Mobile App",
        "Ứng dụng di động cho Koshi — quản lý theo Scrum, sprint 2 tuần.",
        [("tu", "MEMBER"), ("don", "MEMBER")],
    )
    if p:
        pid = p["id"]
        uid = {k: v["id"] for k, v in users.items()}
        s1 = call("POST", "/sprints", pm, {"project_id": pid, "name": "Sprint 1 — Nền tảng",
                  "goal": "Đăng nhập, điều hướng và CI chạy được", "start_date": iso(-28), "end_date": iso(-15), "is_active": False})
        s2 = call("POST", "/sprints", pm, {"project_id": pid, "name": "Sprint 2 — Bảng công việc",
                  "goal": "Xem và sửa task trên điện thoại", "start_date": iso(-14), "end_date": iso(-1), "is_active": False})
        s3 = call("POST", "/sprints", pm, {"project_id": pid, "name": "Sprint 3 — Đồng bộ ngoại tuyến",
                  "goal": "Sửa offline, đồng bộ khi có mạng", "start_date": iso(-3), "end_date": iso(10), "is_active": False})
        s4 = call("POST", "/sprints", pm, {"project_id": pid, "name": "Sprint 4 — Thông báo đẩy",
                  "goal": "Push notification và nhắc hạn", "start_date": iso(11), "end_date": iso(24), "is_active": False})

        def done(t):
            call("PATCH", f"/tasks/{t['id']}", pm, {"status": "DONE"})

        # Sprint 1: completed, 1 item carried over.
        a = task(pid, pm, "Thiết lập dự án React Native + TypeScript", sprint_id=s1["id"], complexity_points=3, priority="HIGH", assignee_ids=[uid["tu"]])
        b = task(pid, pm, "Màn hình đăng nhập email/mật khẩu", sprint_id=s1["id"], complexity_points=5, priority="HIGH", assignee_ids=[uid["tu"]], dependencies=[a["id"]],
                 acceptance_criteria=["Sai mật khẩu hiện lỗi rõ ràng", "Token lưu an toàn trong Keychain"])
        c = task(pid, pm, "Pipeline CI build APK", sprint_id=s1["id"], complexity_points=3, priority="MEDIUM", assignee_ids=[uid["tu"]], dependencies=[a["id"]])
        carry = task(pid, pm, "Đăng nhập bằng Google", sprint_id=s1["id"], complexity_points=5, priority="MEDIUM", assignee_ids=[uid["don"]], dependencies=[b["id"]])
        call("POST", f"/sprints/{s1['id']}/start", pm)
        for t in (a, b, c):
            done(t)
        call("POST", f"/sprints/{s1['id']}/complete", pm, {"move_unfinished_to": s2["id"]})

        # Sprint 2: completed fully.
        d = task(pid, pm, "Danh sách task dạng thẻ", sprint_id=s2["id"], complexity_points=5, priority="HIGH", assignee_ids=[uid["tu"]])
        e = task(pid, pm, "API phân trang task", sprint_id=s2["id"], complexity_points=3, priority="HIGH", assignee_ids=[uid["don"]])
        f = task(pid, pm, "Kiểm thử E2E luồng đăng nhập", sprint_id=s2["id"], complexity_points=2, priority="MEDIUM", assignee_ids=[uid["don"]], dependencies=[b["id"]])
        call("POST", f"/sprints/{s2['id']}/start", pm)
        for t in (carry, d, e, f):
            done(t)
        call("POST", f"/sprints/{s2['id']}/complete", pm, {})

        # Sprint 3: active, mixed progress.
        g = task(pid, pm, "Lưu task vào SQLite trên máy", sprint_id=s3["id"], complexity_points=5, priority="CRITICAL", assignee_ids=[uid["don"], uid["tu"]], due_date=iso(4))
        h = task(pid, pm, "Hàng đợi thay đổi khi mất mạng", sprint_id=s3["id"], complexity_points=8, priority="CRITICAL", assignee_ids=[uid["don"]], dependencies=[g["id"]], due_date=iso(7))
        i = task(pid, pm, "Giải quyết xung đột khi hai người cùng sửa", sprint_id=s3["id"], complexity_points=5, priority="HIGH", assignee_ids=[uid["huynh"]], dependencies=[h["id"]], due_date=iso(9))
        j = task(pid, pm, "Biểu tượng trạng thái mạng", sprint_id=s3["id"], complexity_points=2, priority="LOW", assignee_ids=[uid["tu"]])
        k = task(pid, pm, "Test đồng bộ trên mạng chập chờn", sprint_id=s3["id"], complexity_points=3, priority="MEDIUM", assignee_ids=[uid["don"]], dependencies=[h["id"]])
        call("POST", f"/sprints/{s3['id']}/start", pm)
        done(j)
        done(g)
        call("PATCH", f"/tasks/{h['id']}", pm, {"status": "IN_PROGRESS"})
        call("PATCH", f"/tasks/{k['id']}", pm, {"status": "BLOCKED", "blocking_reason": "Chờ hàng đợi thay đổi (TSK-%d) xong" % h["id"]})

        # Sprint 4: planned. Plus a product backlog.
        task(pid, pm, "Đăng ký Firebase Cloud Messaging", sprint_id=s4["id"], complexity_points=3, priority="MEDIUM", assignee_ids=[uid["tu"]])
        task(pid, pm, "Nhắc việc trước hạn 24 giờ", sprint_id=s4["id"], complexity_points=5, priority="MEDIUM")
        for title, pts, prio in [
            ("Chế độ tối cho ứng dụng di động", 2, "LOW"),
            ("Tìm kiếm task toàn văn", 5, "MEDIUM"),
            ("Đính kèm ảnh chụp màn hình", 3, "MEDIUM"),
            ("Widget màn hình chính", 8, "LOW"),
            ("Đa ngôn ngữ Anh/Việt", 3, "HIGH"),
        ]:
            task(pid, pm, title, complexity_points=pts, priority=prio, description="Chưa ước lượng chi tiết — chờ refinement.")

        # Collaboration: comment, @mention, reply.
        tu_tag = f"@[{users['tu']['full_name']}]({uid['tu']})"
        c1 = call("POST", f"/tasks/{h['id']}/comments", users["don"]["token"],
                  {"content": f"Mình đề xuất dùng bảng outbox. {tu_tag} xem giúp phần UI hiển thị trạng thái chờ đồng bộ nhé?"})
        call("POST", f"/tasks/{h['id']}/comments", users["tu"]["token"],
             {"content": "Ok, mình sẽ thêm badge 'đang chờ' trên thẻ.", "parent_id": c1["id"]})
        call("POST", f"/tasks/{k['id']}/comments", users["don"]["token"],
             {"content": "Đã chuẩn bị kịch bản test với Network Link Conditioner, chỉ chờ build có hàng đợi."})

    # ------------------------------------------------------------ Kanban project
    q = project(
        "Website Bán Hàng Q4",
        "Làm lại website thương mại điện tử trước mùa sale cuối năm.",
        [("tu", "MEMBER"), ("don", "MEMBER")],
    )
    if q:
        qid = q["id"]
        uid = {k: v["id"] for k, v in users.items()}
        rows = [
            ("Thiết kế lại trang chủ", "DONE", "HIGH", 3, -10, [uid["tu"]]),
            ("Giỏ hàng lưu theo phiên", "IN_PROGRESS", "CRITICAL", 5, 2, [uid["tu"]]),
            ("Tích hợp cổng thanh toán VNPay", "BLOCKED", "CRITICAL", 8, -1, [uid["huynh"]]),
            ("Tối ưu ảnh sản phẩm (WebP)", "TODO", "MEDIUM", 2, 6, [uid["tu"]]),
            ("Kiểm thử tải 1.000 người dùng đồng thời", "TODO", "HIGH", 5, 12, [uid["don"]]),
            ("Trang chính sách đổi trả", "TODO", "LOW", 1, 15, []),
            ("Sửa lỗi hiển thị giá trên Safari", "IN_PROGRESS", "HIGH", 2, -3, [uid["don"], uid["tu"]]),
        ]
        made = []
        for title, st, prio, pts, due, who in rows:
            extra = {"blocking_reason": "Chờ VNPay cấp tài khoản sandbox"} if st == "BLOCKED" else {}
            made.append(task(qid, pm, title, status=st, priority=prio, complexity_points=pts, due_date=iso(due), assignee_ids=who, **extra))
        call("PATCH", f"/tasks/{made[4]['id']}", pm, {"dependencies": [made[1]["id"], made[2]["id"]]})

    # ------------------------------------------------------------ Kanban → Scrum
    # The app opens a user's newest project first, which is this one, so it gets
    # sprints too — otherwise the Scrum panel greets the tester with nothing.
    # Runs on re-seeds as well, but only while the project has no sprints.
    web_name = _en("Website Bán Hàng Q4") if LANG == "en" else "Website Bán Hàng Q4"
    web = next((x for x in call("GET", "/projects", pm) if x["name"] == web_name), None)
    if web and not call("GET", f"/sprints?project_id={web['id']}", pm):
        wid = web["id"]
        wt = call("GET", f"/tasks?project_id={wid}", pm)
        w1 = call("POST", "/sprints", pm, {"project_id": wid, "name": "Sprint 1 — Giao diện mới",
                  "goal": "Trang chủ và giỏ hàng mới", "start_date": iso(-18), "end_date": iso(-5), "is_active": False})
        w2 = call("POST", "/sprints", pm, {"project_id": wid, "name": "Sprint 2 — Thanh toán",
                  "goal": "VNPay chạy được, giá hiển thị đúng", "start_date": iso(-4), "end_date": iso(9), "is_active": False})
        call("POST", "/sprints", pm, {"project_id": wid, "name": "Sprint 3 — Hiệu năng",
             "goal": "Chịu tải 1.000 người dùng", "start_date": iso(10), "end_date": iso(23), "is_active": False})
        by = {t["title"]: t for t in wt}
        def plan(title, sid):
            title = _en(title) if LANG == "en" else title
            if title in by:
                call("PATCH", f"/tasks/{by[title]['id']}", pm, {"sprint_id": sid})
        plan("Thiết kế lại trang chủ", w1["id"])
        call("POST", f"/sprints/{w1['id']}/start", pm)
        call("POST", f"/sprints/{w1['id']}/complete", pm, {})
        for title in ("Giỏ hàng lưu theo phiên", "Tích hợp cổng thanh toán VNPay", "Sửa lỗi hiển thị giá trên Safari"):
            plan(title, w2["id"])
        call("POST", f"/sprints/{w2['id']}/start", pm)
        print("  scrum    Website Bán Hàng Q4 (3 sprints)")

    # ------------------------------------------------------------ personal
    r = project("Việc cá nhân của Tú", "Dự án một người — vẫn sửa được khi mất mạng.", [], owner="tu")
    if r:
        bt = users["tu"]["token"]
        for title, st in [("Học Vue 3 Composition API", "DONE"), ("Đọc sách Clean Architecture", "IN_PROGRESS"),
                          ("Chuẩn bị slide thuyết trình đồ án", "TODO"), ("Gia hạn domain cá nhân", "TODO")]:
            task(r["id"], bt, title, status=st, complexity_points=2, priority="MEDIUM")

    print("\nDone. Every account's password:", PASSWORD)
    for slug, *_ in PEOPLE:
        print(f"  {slug}@{DOMAIN}")


if __name__ == "__main__":
    main()
