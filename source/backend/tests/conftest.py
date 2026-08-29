import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Which database the suite runs against.
#
# SQLite by default, so `pytest` works in a bare checkout with no server. Set
# TEST_DATABASE_URL to run the same suite against the engine that actually
# ships:
#
#   TEST_DATABASE_URL='mysql+pymysql://root:pw@127.0.0.1:3307/koshi_test?charset=utf8mb4' pytest
#
# This gap is real and worth naming: F-47 — foreign keys never enforced —
# survived four migrations precisely because the tests ran on a different
# engine from production. Run against MySQL before anything that touches the
# schema, constraints or a dialect-specific migration.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "sqlite:///./data/test_koshi.db"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
# The Google OAuth test exercises the unverified-token path, which is opt-in.
os.environ["ALLOW_UNVERIFIED_GOOGLE_TOKENS"] = "true"

from app.database import Base, get_db, enforce_foreign_keys
from app.main import app, seed_initial_data
from app.security import create_access_token

IS_SQLITE = TEST_DATABASE_URL.startswith("sqlite")
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
)
# The tests must run against the same constraint enforcement as the app, or a
# cascade that only works in production is a cascade nobody has ever verified.
# InnoDB does this itself, so it is a SQLite-only correction.
if IS_SQLITE:
    enforce_foreign_keys(test_engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if IS_SQLITE and os.path.exists("./data/test_koshi.db"):
        try:
            os.remove("./data/test_koshi.db")
        except Exception:
            pass

@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def pm_auth_headers(client):
    # Register / login test PM
    reg_payload = {
        "email": "test_pm@example.com",
        "password": "password123",
        "full_name": "Test PM",
        "skills": "architecture,python"
    }
    client.post("/api/auth/register", json=reg_payload)
    login_res = client.post("/api/auth/login", json={"email": "test_pm@example.com", "password": "password123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def member_auth_headers(client):
    reg_payload = {
        "email": "test_member@example.com",
        "password": "password123",
        "full_name": "Test Member",
        "skills": "svelte,css"
    }
    client.post("/api/auth/register", json=reg_payload)
    login_res = client.post("/api/auth/login", json={"email": "test_member@example.com", "password": "password123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def project_with_member(client, pm_auth_headers, member_auth_headers):
    """
    A project owned by the PM fixture, with the member fixture added as MEMBER.

    Returns (project_id, member_user_id). Roles here are project-scoped: the
    same accounts may hold different roles in a different project.
    """
    proj = client.post(
        "/api/projects",
        json={"name": "Fixture Project", "description": "for tests"},
        headers=pm_auth_headers,
    )
    assert proj.status_code == 201
    project_id = proj.json()["id"]

    me = client.get("/api/auth/me", headers=member_auth_headers).json()
    add = client.post(
        f"/api/projects/{project_id}/members",
        json={"email": me["email"], "role": "MEMBER"},
        headers=pm_auth_headers,
    )
    assert add.status_code == 201, add.text
    # Adding somebody creates a PENDING invitation, which grants nothing. Most
    # tests want an established member, so accept it here. Tests about the
    # invitation flow itself use `project_with_pending_invite` instead.
    assert add.json()["status"] == "PENDING", add.text
    accepted = client.post(
        f"/api/projects/{project_id}/invitation/accept",
        headers=member_auth_headers,
    )
    assert accepted.status_code == 200, accepted.text
    return project_id, me["id"]


@pytest.fixture
def project_with_pending_invite(client, pm_auth_headers, member_auth_headers):
    """A project whose second user has been invited but has NOT answered."""
    proj = client.post(
        "/api/projects",
        json={"name": "Pending Invite Project", "description": "invite flow"},
        headers=pm_auth_headers,
    )
    assert proj.status_code == 201, proj.text
    project_id = proj.json()["id"]

    me = client.get("/api/auth/me", headers=member_auth_headers).json()
    add = client.post(
        f"/api/projects/{project_id}/members",
        json={"email": me["email"], "role": "MEMBER"},
        headers=pm_auth_headers,
    )
    assert add.status_code == 201, add.text
    return project_id, me["id"]
