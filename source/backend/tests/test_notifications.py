"""
The notification feed.

Three claims carry this file:

* **You are never notified about your own action.** It is the single rule that
  decides whether a feed is worth opening, and it applies to mentioning
  yourself and to replying to yourself.
* **One notification per person per event.** Somebody both mentioned in a reply
  and the author of its parent gets one entry, of the more specific kind.
* **A feed does not outlive access.** Membership is re-checked on read, because
  somebody can be removed from a project after the notification was written and
  the entry carries the project's name and a task title.

The kinds are deliberately more general than "mention" — the entity is an event
addressed to a person, so later kinds need no schema change. `test_the_shape_is_
reusable` pins that.
"""
from fastapi.testclient import TestClient

from app.models.entities import NotificationKindEnum


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
    res = client.post(
        f"/api/tasks/{task_id}/comments", json={"content": content, **over}, headers=headers
    )
    assert res.status_code == 201, res.text
    return res.json()


def _feed(client, headers, **params):
    return client.get("/api/notifications", params=params, headers=headers).json()


def _count(client, headers):
    return client.get("/api/notifications/unread-count", headers=headers).json()["unread"]


# ---------------------------------------------------------------------------
# Being notified
# ---------------------------------------------------------------------------

def test_a_mention_notifies_the_person_tagged(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[Grace]({member_id}) please look")

    feed = _feed(client, member_auth_headers)
    assert len(feed) == 1
    assert feed[0]["kind"] == "MENTION"
    assert feed[0]["actor"]["id"] == _me(client, pm_auth_headers)["id"]


def test_a_reply_notifies_the_parents_author(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    parent = _post(client, pm_auth_headers, task["id"], "Original")

    _post(client, member_auth_headers, task["id"], "Replying", parent_id=parent["id"])

    feed = _feed(client, pm_auth_headers)
    assert [n["kind"] for n in feed] == ["REPLY"]


def test_the_entry_carries_enough_to_read_without_another_request(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id, title="Ship the parser")
    _post(client, pm_auth_headers, task["id"], f"@[Grace]({member_id}) urgent")

    n = _feed(client, member_auth_headers)[0]
    assert n["task_title"] == "Ship the parser"
    assert n["task_key"] == task["key"]
    assert n["project_name"]
    assert "urgent" in n["excerpt"]


def test_there_is_no_message_string(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    # Wording belongs to the client, which knows the reader's locale. English
    # prose stored here could never be re-translated or corrected.
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[Grace]({member_id}) hi")

    assert "message" not in _feed(client, member_auth_headers)[0]


# ---------------------------------------------------------------------------
# Not being notified
# ---------------------------------------------------------------------------

def test_mentioning_yourself_notifies_nobody(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    pm_id = _me(client, pm_auth_headers)["id"]
    task = _task(client, pm_auth_headers, project_id)

    _post(client, pm_auth_headers, task["id"], f"note to self @[Me]({pm_id})")

    assert _feed(client, pm_auth_headers) == []


def test_replying_to_yourself_notifies_nobody(client: TestClient, pm_auth_headers, project_with_member):
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    parent = _post(client, pm_auth_headers, task["id"], "Original")

    _post(client, pm_auth_headers, task["id"], "Following up", parent_id=parent["id"])

    assert _feed(client, pm_auth_headers) == []


def test_a_plain_comment_notifies_nobody(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    # Notifying every member of every comment is how a feed becomes something
    # people mute.
    project_id, _ = project_with_member
    task = _task(client, pm_auth_headers, project_id)

    _post(client, pm_auth_headers, task["id"], "just a note")

    assert _feed(client, member_auth_headers) == []


def test_mentioned_in_a_reply_to_your_own_comment_is_one_entry(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    # Both a MENTION and a REPLY apply. The more specific one wins; two entries
    # for one event is how a feed stops being trusted.
    project_id, _ = project_with_member
    pm_id = _me(client, pm_auth_headers)["id"]
    task = _task(client, pm_auth_headers, project_id)
    parent = _post(client, pm_auth_headers, task["id"], "Original")

    _post(client, member_auth_headers, task["id"], f"@[Pat]({pm_id}) yes", parent_id=parent["id"])

    feed = _feed(client, pm_auth_headers)
    assert len(feed) == 1
    assert feed[0]["kind"] == "MENTION"


def test_being_mentioned_twice_in_one_comment_is_one_entry(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)

    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) and again @[G]({member_id})")

    assert len(_feed(client, member_auth_headers)) == 1


# ---------------------------------------------------------------------------
# Reading and read-tracking
# ---------------------------------------------------------------------------

def test_the_badge_counts_unread_only(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) one")
    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) two")

    assert _count(client, member_auth_headers) == 2

    first = _feed(client, member_auth_headers)[0]
    client.post(f"/api/notifications/{first['id']}/read", headers=member_auth_headers)

    assert _count(client, member_auth_headers) == 1


def test_unread_only_filters_the_feed(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) one")
    n = _feed(client, member_auth_headers)[0]
    client.post(f"/api/notifications/{n['id']}/read", headers=member_auth_headers)

    assert _feed(client, member_auth_headers, unread_only=True) == []
    assert len(_feed(client, member_auth_headers)) == 1


def test_marking_read_is_idempotent(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    # Re-reading must not move the timestamp, or "when did they first see this"
    # stops being answerable.
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) hi")
    n = _feed(client, member_auth_headers)[0]

    first = client.post(f"/api/notifications/{n['id']}/read", headers=member_auth_headers).json()
    second = client.post(f"/api/notifications/{n['id']}/read", headers=member_auth_headers).json()

    assert first["read_at"] == second["read_at"]


def test_read_all_clears_the_badge(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    for i in range(3):
        _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) {i}")

    assert client.post("/api/notifications/read-all", headers=member_auth_headers).status_code == 204
    assert _count(client, member_auth_headers) == 0


def test_newest_first(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) older")
    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) newer")

    assert "newer" in _feed(client, member_auth_headers)[0]["excerpt"]


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------

def test_you_only_see_your_own_feed(client: TestClient, pm_auth_headers, member_auth_headers, project_with_member):
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) hi")

    assert _feed(client, pm_auth_headers) == []


def test_you_cannot_mark_somebody_elses_as_read(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    # 404, not 403: the reply must not confirm the notification exists.
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) hi")
    theirs = _feed(client, member_auth_headers)[0]

    res = client.post(f"/api/notifications/{theirs['id']}/read", headers=pm_auth_headers)
    assert res.status_code == 404


def test_an_anonymous_request_is_refused(client: TestClient):
    assert client.get("/api/notifications").status_code == 401
    assert client.get("/api/notifications/unread-count").status_code == 401


def test_losing_access_to_a_project_hides_its_notifications(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    # The entry carries the project name and a task title, so a feed that
    # outlived membership would be a slow leak.
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) hi")
    assert len(_feed(client, member_auth_headers)) == 1

    client.delete(f"/api/projects/{project_id}/members/{member_id}", headers=pm_auth_headers)

    assert _feed(client, member_auth_headers) == []
    assert _count(client, member_auth_headers) == 0


def test_deleting_the_task_removes_its_notifications(
    client: TestClient, pm_auth_headers, member_auth_headers, project_with_member
):
    # Cascade rather than filtering on read: an entry pointing at nothing is not
    # something to keep and then have to hide.
    project_id, member_id = project_with_member
    task = _task(client, pm_auth_headers, project_id)
    _post(client, pm_auth_headers, task["id"], f"@[G]({member_id}) hi")

    client.delete(f"/api/tasks/{task['id']}", headers=pm_auth_headers)

    assert _feed(client, member_auth_headers) == []


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------

def test_the_shape_is_reusable_for_kinds_that_do_not_exist_yet():
    # The entity describes an event addressed to a person, not a mention. These
    # kinds are declared now so the columns are judged against them; adding one
    # needs no migration.
    kinds = {k.value for k in NotificationKindEnum}
    assert {"MENTION", "REPLY", "TASK_ASSIGNED", "PROJECT_INVITED", "TASK_DUE_SOON"} <= kinds


def test_a_notification_needs_no_actor(client: TestClient, db_session, pm_auth_headers):
    # A due-date reminder has no author. Nullable actor_id means no fake user is
    # invented to satisfy a foreign key.
    from app.models.entities import Notification

    # Ask the API who we are rather than guessing at the fixture's email.
    me_id = _me(client, pm_auth_headers)["id"]
    n = Notification(user_id=me_id, kind=NotificationKindEnum.TASK_DUE_SOON, actor_id=None)
    db_session.add(n)
    db_session.commit()

    feed = _feed(client, pm_auth_headers)
    assert any(x["kind"] == "TASK_DUE_SOON" and x["actor"] is None for x in feed)
