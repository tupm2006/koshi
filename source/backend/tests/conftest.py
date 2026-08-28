import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///./data/test_koshi.db"
# The Google OAuth test exercises the unverified-token path, which is opt-in.
os.environ["ALLOW_UNVERIFIED_GOOGLE_TOKENS"] = "true"

from app.database import Base, get_db
from app.main import app, seed_initial_data
from app.security import create_access_token

TEST_DATABASE_URL = "sqlite:///./data/test_koshi.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./data/test_koshi.db"):
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
