"""
@mentions and threaded replies.

Two claims worth holding onto:

* **You can only tag people who can read the thread.** A mention of an outsider
  is a notification nobody receives, and it confirms a user id exists to
  somebody outside the project.
* **Replies are one level deep, always.** The flattening is enforced here rather
  than trusted to the UI, because the schema cannot express "the parent must not
  itself have a parent".
"""
from fastapi.testclient import TestClient

from app.services.mentions import parse_mention_ids


def _me(client, headers):
    return client.get("/api/auth/me", headers=headers).json()


def _task(client, headers, project_id, **over):
    res = client.post(
        "/api/tasks",
        json={"project_id": project_id, "title": "A task", "priority": "MEDIUM", **over},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _post(client, headers, task_id, content, **over):
    return client.post(
        f"/api/tasks/{task_id}/comments", json={"content": content, **over}, headers=headers
    )


# ---------------------------------------------------------------------------
# The token format
# ---------------------------------------------------------------------------

def test_the_parser_reads_ids_in_order_without_duplicates():
    assert parse_mention_ids("hi @[Ada](3) and @[Bob](7), @[Ada](3) again") == [3, 7]


def test_a_bare_at_sign_is_not_a_mention():
    # Typing "@ada" is ordinary text. Guessing at it would tag the wrong person
    # whenever two people share a first name.
    assert parse_mention_ids("ping @ada about this") == []
    assert parse_mention_ids("email me at a@b.com") == []


def test_a_malformed_token_is_ignored():
    assert parse_mention_ids("@[Ada] (3)") == []
    assert parse_mention_ids("@[Ada](notanumber)") == []


# ---------------------------------------------------------------------------
# Mentions
# ---------------------------------------------------------------------------

def test_a_member_can_be_mentioned(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)

    res = _post(client, pm_auth_headers, task["id"], f"@[Grace]({member_id}) please look")
    assert res.status_code == 201, res.text
    assert [u["id"] for u in res.json()["mentions"]] == [member_id]


def test_the_mention_resolves_to_the_persons_current_name(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    # The label in the text is what it looked like when written; the id is what
    # it means. A rename must not leave the thread lying.
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[Old Name]({member_id}) hello")

    client.patch(f"/api/users/{member_id}", json={"full_name": "Renamed Person"},
                 headers=member_auth_headers)

    thread = client.get(f"/api/tasks/{task['id']}/comments", headers=pm_auth_headers).json()
    assert thread[0]["mentions"][0]["full_name"] == "Renamed Person"
    # The raw text still carries the original label, for anyone reading it plain.
    assert "Old Name" in thread[0]["content"]


def test_you_cannot_mention_somebody_outside_the_project(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)

    res = _post(client, pm_auth_headers, task["id"], "@[Nobody](99999) hi")
    assert res.status_code == 400


def test_you_cannot_mention_somebody_merely_invited(
    client: TestClient, pm_auth_headers, project_with_pending_invite
):
    # They cannot open the project, so they cannot read what they were tagged in.
    project_id, invited_id = project_with_pending_invite
    task = _task(client, pm_auth_headers, project_id)

    res = _post(client, pm_auth_headers, task["id"], f"@[Invited]({invited_id}) hi")
    assert res.status_code == 400


def test_a_comment_with_no_mentions_reports_none(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)

    assert _post(client, pm_auth_headers, task["id"], "just a note").json()["mentions"] == []


# ---------------------------------------------------------------------------
# Replies
# ---------------------------------------------------------------------------

def test_a_reply_points_at_its_parent(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    parent = _post(client, pm_auth_headers, task["id"], "Original").json()

    reply = _post(client, member_auth_headers, task["id"], "Replying", parent_id=parent["id"])
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == parent["id"]


def test_a_top_level_comment_has_no_parent(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    assert _post(client, pm_auth_headers, task["id"], "Original").json()["parent_id"] is None


def test_replying_to_a_reply_flattens_to_the_same_parent(client: TestClient, pm_auth_headers, project_with_member):
    # One level, always. Re-parenting rather than refusing: the user was offered
    # a Reply button and should not be told off for using it.
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    parent = _post(client, pm_auth_headers, task["id"], "Original").json()
    reply = _post(client, pm_auth_headers, task["id"], "First reply", parent_id=parent["id"]).json()

    nested = _post(client, pm_auth_headers, task["id"], "Reply to the reply", parent_id=reply["id"])

    assert nested.json()["parent_id"] == parent["id"]


def test_you_cannot_reply_across_tasks(client: TestClient, pm_auth_headers, project_with_member):
    # The reply would appear under a thread its author never saw.
    project_id, _ = project_with_member
    task_a = _task(client, pm_auth_headers, project_id, title="A")
    task_b = _task(client, pm_auth_headers, project_id, title="B")
    parent = _post(client, pm_auth_headers, task_a["id"], "On A").json()

    res = _post(client, pm_auth_headers, task_b["id"], "Wrong thread", parent_id=parent["id"])
    assert res.status_code == 404


def test_you_cannot_reply_to_a_comment_in_another_project(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    project_id, _ = project_with_member
    mine = _task(client, pm_auth_headers, project_id)

    other = client.post("/api/projects", json={"name": "Elsewhere"}, headers=member_auth_headers).json()
    their_task = _task(client, member_auth_headers, other["id"])
    theirs = _post(client, member_auth_headers, their_task["id"], "Private").json()

    res = _post(client, pm_auth_headers, mine["id"], "Leaking", parent_id=theirs["id"])
    assert res.status_code == 404


def test_replying_to_something_that_does_not_exist(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)

    assert _post(client, pm_auth_headers, task["id"], "x", parent_id=99999).status_code == 404


def test_the_thread_returns_parents_and_replies_together(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    parent = _post(client, pm_auth_headers, task["id"], "Original").json()
    _post(client, pm_auth_headers, task["id"], "A reply", parent_id=parent["id"])

    thread = client.get(f"/api/tasks/{task['id']}/comments", headers=pm_auth_headers).json()

    # Flat list, oldest first — the client nests it. The server does not send a
    # tree, so pagination later needs no reshaping.
    assert [c["content"] for c in thread] == ["Original", "A reply"]
    assert thread[1]["parent_id"] == parent["id"]


def test_deleting_a_task_takes_its_replies_with_it(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    parent = _post(client, pm_auth_headers, task["id"], "Original").json()
    _post(client, pm_auth_headers, task["id"], "A reply", parent_id=parent["id"])

    assert client.delete(f"/api/tasks/{task['id']}", headers=pm_auth_headers).status_code == 204
    assert client.get(f"/api/tasks/{task['id']}/comments", headers=pm_auth_headers).status_code == 404


def test_a_non_member_cannot_reply(client: TestClient, pm_auth_headers, member_auth_headers):
    proj = client.post("/api/projects", json={"name": "Private"}, headers=pm_auth_headers).json()
    task = _task(client, pm_auth_headers, proj["id"])
    parent = _post(client, pm_auth_headers, task["id"], "Original").json()

    res = _post(client, member_auth_headers, task["id"], "Intruding", parent_id=parent["id"])
    assert res.status_code == 404
