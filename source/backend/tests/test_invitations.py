"""
Membership invitations.

The security claim under test is narrow and absolute: a PENDING row grants
nothing. Adding somebody to a project used to be a unilateral act — the PM typed
an email and that person was in. Now it is a request, and until it is answered
the invited user must not be able to read the project, its tasks, its roster or
its statistics, and must not even be able to tell that it exists.

Most of this file is that one claim, checked against every project-scoped
surface, because a single endpoint that resolved the raw row instead of the
effective membership would silently undo it.
"""
from fastapi.testclient import TestClient


def _me(client, headers):
    return client.get("/api/auth/me", headers=headers).json()


# ---------------------------------------------------------------------------
# A pending invitation grants nothing
# ---------------------------------------------------------------------------

def test_adding_a_member_creates_a_pending_invitation(
    client: TestClient, project_with_pending_invite, pm_auth_headers
):
    project_id, user_id = project_with_pending_invite
    roster = client.get(f"/api/projects/{project_id}/members", headers=pm_auth_headers).json()

    invited = next(m for m in roster if m["user_id"] == user_id)
    assert invited["status"] == "PENDING"


def test_pending_invitation_does_not_reveal_the_project(
    client: TestClient, project_with_pending_invite, member_auth_headers
):
    project_id, _ = project_with_pending_invite
    res = client.get(f"/api/projects/{project_id}", headers=member_auth_headers)
    # 404, not 403 — the same non-disclosure a total stranger gets.
    assert res.status_code == 404


def test_pending_invitation_does_not_appear_in_the_dashboard(
    client: TestClient, project_with_pending_invite, member_auth_headers
):
    # Listing it would put a project on the dashboard that cannot be opened.
    project_id, _ = project_with_pending_invite
    projects = client.get("/api/projects", headers=member_auth_headers).json()
    assert all(p["id"] != project_id for p in projects)


def test_pending_invitation_grants_no_access_to_any_project_surface(
    client: TestClient, project_with_pending_invite, member_auth_headers
):
    project_id, _ = project_with_pending_invite
    h = member_auth_headers

    checks = [
        ("GET", f"/api/projects/{project_id}"),
        ("GET", f"/api/projects/{project_id}/members"),
        ("GET", f"/api/tasks?project_id={project_id}"),
        ("GET", f"/api/sprints?project_id={project_id}"),
        ("GET", f"/api/stats/workload?project_id={project_id}"),
        ("GET", f"/api/stats/delayed-tasks?project_id={project_id}"),
    ]
    for method, path in checks:
        res = client.request(method, path, headers=h)
        assert res.status_code == 404, f"{method} {path} returned {res.status_code}"

    # And no writes either.
    created = client.post(
        "/api/tasks",
        json={"project_id": project_id, "title": "Should not exist", "priority": "LOW"},
        headers=h,
    )
    assert created.status_code == 404

    summary = client.post(f"/api/ai/weekly-summary?project_id={project_id}", headers=h)
    assert summary.status_code == 404


def test_a_pending_invitation_does_not_count_towards_member_count(
    client: TestClient, project_with_pending_invite, pm_auth_headers
):
    # member_count drives the offline write policy (INV-15). An unanswered
    # invitation must not make a personal project look shared and flip it to
    # read-only while disconnected.
    project_id, _ = project_with_pending_invite
    project = client.get(f"/api/projects/{project_id}", headers=pm_auth_headers).json()
    assert project["member_count"] == 1


# ---------------------------------------------------------------------------
# Seeing and answering an invitation
# ---------------------------------------------------------------------------

def test_the_invited_user_sees_the_invitation_with_context(
    client: TestClient, project_with_pending_invite, member_auth_headers
):
    project_id, _ = project_with_pending_invite
    invites = client.get("/api/projects/invitations/pending", headers=member_auth_headers).json()

    invite = next(i for i in invites if i["project_id"] == project_id)
    # They cannot read the project, so the invitation has to carry enough to
    # decide on: what it is, and who asked.
    assert invite["project_name"] == "Pending Invite Project"
    assert invite["role"] == "MEMBER"
    assert invite["invited_by_name"]


def test_nobody_else_sees_that_invitation(
    client: TestClient, project_with_pending_invite, pm_auth_headers
):
    project_id, _ = project_with_pending_invite
    invites = client.get("/api/projects/invitations/pending", headers=pm_auth_headers).json()
    assert all(i["project_id"] != project_id for i in invites)


def test_accepting_grants_access_and_returns_the_project(
    client: TestClient, project_with_pending_invite, member_auth_headers
):
    project_id, _ = project_with_pending_invite

    res = client.post(f"/api/projects/{project_id}/invitation/accept", headers=member_auth_headers)
    assert res.status_code == 200
    assert res.json()["my_role"] == "MEMBER"

    # Now everything that was 404 works.
    assert client.get(f"/api/projects/{project_id}", headers=member_auth_headers).status_code == 200
    assert client.get(f"/api/tasks?project_id={project_id}", headers=member_auth_headers).status_code == 200
    projects = client.get("/api/projects", headers=member_auth_headers).json()
    assert any(p["id"] == project_id for p in projects)


def test_accepting_clears_the_pending_list(
    client: TestClient, project_with_pending_invite, member_auth_headers
):
    project_id, _ = project_with_pending_invite
    client.post(f"/api/projects/{project_id}/invitation/accept", headers=member_auth_headers)

    invites = client.get("/api/projects/invitations/pending", headers=member_auth_headers).json()
    assert all(i["project_id"] != project_id for i in invites)


def test_declining_leaves_no_access(
    client: TestClient, project_with_pending_invite, member_auth_headers
):
    project_id, _ = project_with_pending_invite

    res = client.post(f"/api/projects/{project_id}/invitation/decline", headers=member_auth_headers)
    assert res.status_code == 204

    assert client.get(f"/api/projects/{project_id}", headers=member_auth_headers).status_code == 404
    invites = client.get("/api/projects/invitations/pending", headers=member_auth_headers).json()
    assert all(i["project_id"] != project_id for i in invites)


def test_the_pm_can_see_that_it_was_declined(
    client: TestClient, project_with_pending_invite, member_auth_headers, pm_auth_headers
):
    # The row is kept rather than deleted, so a declined invitation is an answer
    # the PM can see instead of an invitation that silently vanished.
    project_id, user_id = project_with_pending_invite
    client.post(f"/api/projects/{project_id}/invitation/decline", headers=member_auth_headers)

    roster = client.get(f"/api/projects/{project_id}/members", headers=pm_auth_headers).json()
    row = next(m for m in roster if m["user_id"] == user_id)
    assert row["status"] == "DECLINED"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_an_invitation_cannot_be_answered_twice(
    client: TestClient, project_with_pending_invite, member_auth_headers
):
    project_id, _ = project_with_pending_invite
    client.post(f"/api/projects/{project_id}/invitation/accept", headers=member_auth_headers)

    again = client.post(f"/api/projects/{project_id}/invitation/accept", headers=member_auth_headers)
    assert again.status_code == 409


def test_a_stranger_answering_an_invitation_gets_404(
    client: TestClient, pm_auth_headers, member_auth_headers
):
    # Not 403: replying must not confirm that the project exists either.
    proj = client.post("/api/projects", json={"name": "Private"}, headers=pm_auth_headers).json()
    res = client.post(f"/api/projects/{proj['id']}/invitation/accept", headers=member_auth_headers)
    assert res.status_code == 404


def test_inviting_the_same_person_twice_is_refused(
    client: TestClient, project_with_pending_invite, pm_auth_headers, member_auth_headers
):
    project_id, _ = project_with_pending_invite
    me = _me(client, member_auth_headers)

    again = client.post(
        f"/api/projects/{project_id}/members",
        json={"email": me["email"], "role": "MEMBER"},
        headers=pm_auth_headers,
    )
    assert again.status_code == 400


def test_someone_who_declined_can_be_invited_again(
    client: TestClient, project_with_pending_invite, pm_auth_headers, member_auth_headers
):
    # Otherwise one mis-click would lock a person out of a project permanently.
    project_id, _ = project_with_pending_invite
    me = _me(client, member_auth_headers)
    client.post(f"/api/projects/{project_id}/invitation/decline", headers=member_auth_headers)

    again = client.post(
        f"/api/projects/{project_id}/members",
        json={"email": me["email"], "role": "PM"},
        headers=pm_auth_headers,
    )
    assert again.status_code == 201
    assert again.json()["status"] == "PENDING"
    assert again.json()["role"] == "PM"

    accepted = client.post(
        f"/api/projects/{project_id}/invitation/accept", headers=member_auth_headers
    )
    assert accepted.status_code == 200
    assert accepted.json()["my_role"] == "PM"


def test_only_a_pm_can_invite(
    client: TestClient, project_with_member, member_auth_headers
):
    project_id, _ = project_with_member
    res = client.post(
        f"/api/projects/{project_id}/members",
        json={"email": "someone@koshi-local.dev", "role": "MEMBER"},
        headers=member_auth_headers,
    )
    # 403: they are a member, so the project's existence is not a secret from
    # them — they simply lack the authority.
    assert res.status_code == 403
