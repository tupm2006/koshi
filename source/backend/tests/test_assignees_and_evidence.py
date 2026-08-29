"""
Multiple assignees, comments, and completion evidence.

Two security claims carry most of this file:

* **You cannot assign work to somebody who is not in the project.** A task
  assigned to an outsider is a task nobody receives, and it would leak the
  existence of a user id into a project they cannot see.
* **Attachments are not public.** Knowing the URL is not permission; membership
  is re-checked on every fetch, and the id is a small integer anyone could
  guess.

The upload tests use real bytes through the real route rather than mocking the
storage layer — the whole point of that layer is what it does with a file, and a
mock would assert only that the mock was called.
"""
import io

from fastapi.testclient import TestClient

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _me(client, headers):
    return client.get("/api/auth/me", headers=headers).json()


def _task(client, headers, project_id, **over):
    payload = {"project_id": project_id, "title": "A task", "priority": "MEDIUM", **over}
    res = client.post("/api/tasks", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Multiple assignees
# ---------------------------------------------------------------------------

def test_a_task_can_have_two_assignees(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    pm_id = _me(client, pm_auth_headers)["id"]

    task = _task(client, pm_auth_headers, project_id, assignee_ids=[pm_id, member_id])

    assert sorted(a["id"] for a in task["assignees"]) == sorted([pm_id, member_id])


def test_a_task_can_have_none(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    assert _task(client, pm_auth_headers, project_id)["assignees"] == []


def test_duplicate_ids_collapse(client: TestClient, pm_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id, assignee_ids=[member_id, member_id])
    assert len(task["assignees"]) == 1


def test_cannot_assign_somebody_outside_the_project(client: TestClient, pm_auth_headers, project_with_member):
    # Otherwise the task is delivered to nobody, and a user id is confirmed to
    # exist for a project that person cannot open.
    project_id, _ = project_with_member
    res = client.post(
        "/api/tasks",
        json={"project_id": project_id, "title": "x", "priority": "LOW", "assignee_ids": [99_999]},
        headers=pm_auth_headers,
    )
    assert res.status_code == 400


def test_cannot_assign_somebody_who_has_only_been_invited(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_pending_invite
):
    # A pending invitation grants no access, so assigning to it produces work
    # its owner cannot see (DEC-022).
    project_id, invited_id = project_with_pending_invite
    res = client.post(
        "/api/tasks",
        json={"project_id": project_id, "title": "x", "priority": "LOW", "assignee_ids": [invited_id]},
        headers=pm_auth_headers,
    )
    assert res.status_code == 400


def test_patching_replaces_the_whole_set(client: TestClient, pm_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    pm_id = _me(client, pm_auth_headers)["id"]
    task = _task(client, pm_auth_headers, project_id, assignee_ids=[pm_id, member_id])

    res = client.patch(f"/api/tasks/{task['id']}", json={"assignee_ids": [member_id]}, headers=pm_auth_headers)

    assert [a["id"] for a in res.json()["assignees"]] == [member_id]


def test_an_empty_list_unassigns_everybody(client: TestClient, pm_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id, assignee_ids=[member_id])

    res = client.patch(f"/api/tasks/{task['id']}", json={"assignee_ids": []}, headers=pm_auth_headers)

    assert res.json()["assignees"] == []


def test_a_patch_that_omits_assignees_leaves_them_alone(client: TestClient, pm_auth_headers, project_with_member):
    # The None-vs-[] distinction. Renaming a task must not silently unassign it.
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id, assignee_ids=[member_id])

    res = client.patch(f"/api/tasks/{task['id']}", json={"title": "Renamed"}, headers=pm_auth_headers)

    assert [a["id"] for a in res.json()["assignees"]] == [member_id]


def test_filtering_by_assignee_finds_shared_tasks(client: TestClient, pm_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    pm_id = _me(client, pm_auth_headers)["id"]
    shared = _task(client, pm_auth_headers, project_id, title="Shared", assignee_ids=[pm_id, member_id])
    _task(client, pm_auth_headers, project_id, title="PM only", assignee_ids=[pm_id])

    res = client.get(f"/api/tasks?project_id={project_id}&assignee_id={member_id}", headers=pm_auth_headers)

    ids = [t["id"] for t in res.json()]
    assert ids == [shared["id"]]


def test_workload_counts_a_shared_task_for_both_people(client: TestClient, pm_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    pm_id = _me(client, pm_auth_headers)["id"]
    _task(client, pm_auth_headers, project_id, assignee_ids=[pm_id, member_id])

    workloads = client.get(f"/api/stats/workload?project_id={project_id}", headers=pm_auth_headers).json()

    by_id = {w["user_id"]: w for w in workloads}
    assert by_id[pm_id]["active_tasks_count"] == 1
    assert by_id[member_id]["active_tasks_count"] == 1


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def test_a_member_can_comment_and_read_the_thread(client: TestClient, member_auth_headers, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)

    posted = client.post(
        f"/api/tasks/{task['id']}/comments",
        json={"content": "Started on this"},
        headers=member_auth_headers,
    )
    assert posted.status_code == 201
    assert posted.json()["kind"] == "COMMENT"

    thread = client.get(f"/api/tasks/{task['id']}/comments", headers=pm_auth_headers).json()
    assert [c["content"] for c in thread] == ["Started on this"]
    assert thread[0]["author"]["full_name"]


def test_a_non_member_cannot_comment(client: TestClient, pm_auth_headers, member_auth_headers):
    # F-40: this route checked only that the task existed, so any authenticated
    # user could post into any project. Dormant only because no UI called it.
    proj = client.post("/api/projects", json={"name": "Private"}, headers=pm_auth_headers).json()
    task = _task(client, pm_auth_headers, proj["id"])

    res = client.post(
        f"/api/tasks/{task['id']}/comments",
        json={"content": "I should not be here"},
        headers=member_auth_headers,
    )
    assert res.status_code == 404


def test_a_non_member_cannot_read_the_thread(client: TestClient, pm_auth_headers, member_auth_headers):
    proj = client.post("/api/projects", json={"name": "Private"}, headers=pm_auth_headers).json()
    task = _task(client, pm_auth_headers, proj["id"])

    res = client.get(f"/api/tasks/{task['id']}/comments", headers=member_auth_headers)
    assert res.status_code == 404


def test_an_empty_comment_is_refused(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)

    res = client.post(f"/api/tasks/{task['id']}/comments", json={"content": "   "}, headers=pm_auth_headers)
    assert res.status_code == 400


def test_evidence_is_marked_as_such(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)

    res = client.post(
        f"/api/tasks/{task['id']}/comments",
        json={"content": "Deployed and verified", "kind": "EVIDENCE"},
        headers=pm_auth_headers,
    )
    assert res.json()["kind"] == "EVIDENCE"


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

def _comment(client, headers, task_id, kind="EVIDENCE"):
    return client.post(
        f"/api/tasks/{task_id}/comments",
        json={"content": "Proof", "kind": kind},
        headers=headers,
    ).json()


def _upload(client, headers, comment_id, name="shot.png", data=PNG, ctype="image/png"):
    return client.post(
        f"/api/tasks/comments/{comment_id}/attachments",
        files={"file": (name, io.BytesIO(data), ctype)},
        headers=headers,
    )


def test_an_image_can_be_attached_and_fetched_back(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    comment = _comment(client, pm_auth_headers, task["id"])

    res = _upload(client, pm_auth_headers, comment["id"])
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["filename"] == "shot.png"
    assert body["size_bytes"] == len(PNG)

    fetched = client.get(body["url"].replace("/api", "/api"), headers=pm_auth_headers)
    assert fetched.status_code == 200
    assert fetched.content == PNG
    # Never let a browser re-interpret an upload as HTML on this origin.
    assert fetched.headers["x-content-type-options"] == "nosniff"


def test_the_attachment_appears_on_the_comment(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    comment = _comment(client, pm_auth_headers, task["id"])
    _upload(client, pm_auth_headers, comment["id"])

    thread = client.get(f"/api/tasks/{task['id']}/comments", headers=pm_auth_headers).json()
    assert len(thread[0]["attachments"]) == 1
    assert thread[0]["attachments"][0]["url"].endswith(str(thread[0]["attachments"][0]["id"]))


def test_a_non_member_cannot_download_an_attachment(client: TestClient, pm_auth_headers, member_auth_headers):
    # Knowing the URL is not permission.
    proj = client.post("/api/projects", json={"name": "Private"}, headers=pm_auth_headers).json()
    task = _task(client, pm_auth_headers, proj["id"])
    comment = _comment(client, pm_auth_headers, task["id"])
    url = _upload(client, pm_auth_headers, comment["id"]).json()["url"]

    assert client.get(url, headers=member_auth_headers).status_code == 404


def test_an_anonymous_request_cannot_download_an_attachment(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    comment = _comment(client, pm_auth_headers, task["id"])
    url = _upload(client, pm_auth_headers, comment["id"]).json()["url"]

    assert client.get(url).status_code == 401


def test_a_non_member_cannot_upload(client: TestClient, pm_auth_headers, member_auth_headers):
    # Membership is checked before any byte is written — an outsider must not be
    # able to fill the disk of a project they cannot see.
    proj = client.post("/api/projects", json={"name": "Private"}, headers=pm_auth_headers).json()
    task = _task(client, pm_auth_headers, proj["id"])
    comment = _comment(client, pm_auth_headers, task["id"])

    assert _upload(client, member_auth_headers, comment["id"]).status_code == 404


def test_you_cannot_staple_a_file_onto_somebody_elses_comment(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    comment = _comment(client, pm_auth_headers, task["id"])

    # A member of the project, but not the author of this entry.
    assert _upload(client, member_auth_headers, comment["id"]).status_code == 403


def test_an_executable_is_refused(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    comment = _comment(client, pm_auth_headers, task["id"])

    res = _upload(client, pm_auth_headers, comment["id"], name="evil.sh",
                  data=b"#!/bin/sh\nrm -rf /", ctype="application/x-sh")
    assert res.status_code == 400


def test_html_is_refused_even_disguised_by_extension(client: TestClient, pm_auth_headers, project_with_member):
    # An allowlist, not a blocklist: the type is what decides, and text/html is
    # simply not on it.
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    comment = _comment(client, pm_auth_headers, task["id"])

    res = _upload(client, pm_auth_headers, comment["id"], name="shot.png",
                  data=b"<script>alert(1)</script>", ctype="text/html")
    assert res.status_code == 400


def test_the_stored_name_is_never_the_clients(client: TestClient, pm_auth_headers, project_with_member):
    # Path traversal is impossible because the client's name is never used to
    # build a path — it is kept only as a label.
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    comment = _comment(client, pm_auth_headers, task["id"])

    res = _upload(client, pm_auth_headers, comment["id"], name="../../../../etc/passwd.png")
    assert res.status_code == 201
    assert "/" not in res.json()["filename"]
    assert res.json()["filename"] == "passwd.png"


def test_an_empty_file_is_refused(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    comment = _comment(client, pm_auth_headers, task["id"])

    assert _upload(client, pm_auth_headers, comment["id"], data=b"").status_code == 400


def test_a_file_over_the_limit_is_refused(client: TestClient, pm_auth_headers, project_with_member, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 1024)

    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    comment = _comment(client, pm_auth_headers, task["id"])

    res = _upload(client, pm_auth_headers, comment["id"], data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 4096)
    assert res.status_code == 413


def test_an_oversize_upload_leaves_no_file_behind(client: TestClient, pm_auth_headers, project_with_member, monkeypatch):
    import os
    from app.config import settings
    from app.services.uploads import upload_dir

    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 1024)
    before = set(os.listdir(upload_dir()))

    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    comment = _comment(client, pm_auth_headers, task["id"])
    _upload(client, pm_auth_headers, comment["id"], data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 4096)

    assert set(os.listdir(upload_dir())) == before


# ---------------------------------------------------------------------------
# Profile avatars
# ---------------------------------------------------------------------------

def _put_avatar(client, headers, data=PNG, ctype="image/png", name="face.png"):
    return client.post(
        "/api/users/me/avatar",
        files={"file": (name, io.BytesIO(data), ctype)},
        headers=headers,
    )


def test_uploading_an_avatar_sets_it_on_the_profile(client: TestClient, pm_auth_headers):
    res = _put_avatar(client, pm_auth_headers)
    assert res.status_code == 200, res.text
    assert res.json()["avatar_url"].startswith("/api/users/")


def test_you_can_fetch_your_own_avatar(client: TestClient, pm_auth_headers):
    url = _put_avatar(client, pm_auth_headers).json()["avatar_url"]
    fetched = client.get(url, headers=pm_auth_headers)

    assert fetched.status_code == 200
    assert fetched.content == PNG
    assert fetched.headers["x-content-type-options"] == "nosniff"


def test_a_teammate_can_see_your_avatar(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    # Faces are rendered on task cards, so people who share a project must be
    # able to load each other's.
    url = _put_avatar(client, pm_auth_headers).json()["avatar_url"]
    assert client.get(url, headers=member_auth_headers).status_code == 200


def test_a_stranger_cannot(client: TestClient, pm_auth_headers, member_auth_headers):
    # 404, not 403: the reply must not confirm the account exists.
    url = _put_avatar(client, pm_auth_headers).json()["avatar_url"]
    assert client.get(url, headers=member_auth_headers).status_code == 404


def test_an_anonymous_request_cannot(client: TestClient, pm_auth_headers):
    url = _put_avatar(client, pm_auth_headers).json()["avatar_url"]
    assert client.get(url).status_code == 401


def test_a_video_is_refused_as_an_avatar(client: TestClient, pm_auth_headers):
    # Attachments allow video; avatars deliberately do not — a profile picture
    # is re-fetched on every board that renders a card.
    res = _put_avatar(client, pm_auth_headers, data=b"\x00" * 128,
                      ctype="video/mp4", name="clip.mp4")
    assert res.status_code == 400


def test_an_oversized_avatar_is_refused(client: TestClient, pm_auth_headers):
    from app.routers.users import AVATAR_MAX_BYTES
    res = _put_avatar(client, pm_auth_headers, data=b"\x89PNG\r\n\x1a\n" + b"\x00" * (AVATAR_MAX_BYTES + 1))
    assert res.status_code == 413


def test_replacing_an_avatar_removes_the_old_file(client: TestClient, pm_auth_headers):
    import os
    from app.services.uploads import upload_dir

    _put_avatar(client, pm_auth_headers)
    after_first = set(os.listdir(upload_dir()))
    _put_avatar(client, pm_auth_headers, data=PNG + b"\x01")
    after_second = set(os.listdir(upload_dir()))

    # One replaced the other rather than accumulating.
    assert len(after_second) == len(after_first)


def test_removing_an_avatar_clears_the_profile(client: TestClient, pm_auth_headers):
    _put_avatar(client, pm_auth_headers)
    res = client.delete("/api/users/me/avatar", headers=pm_auth_headers)

    assert res.status_code == 200
    assert res.json()["avatar_url"] is None


def test_there_is_no_way_to_set_somebody_elses_avatar(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    # The route takes no user id, so this is structural rather than a check that
    # could be forgotten. Asserted so a future signature change is noticed.
    _, member_id = project_with_member
    res = client.post(
        f"/api/users/{member_id}/avatar",
        files={"file": ("face.png", io.BytesIO(PNG), "image/png")},
        headers=pm_auth_headers,
    )
    assert res.status_code in (404, 405)
