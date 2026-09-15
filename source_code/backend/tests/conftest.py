import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///./data/test_koshi.db"
os.environ.setdefault("ALLOW_UNVERIFIED_GOOGLE_TOKENS", "True")

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
    seed_initial_data()
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
def pm_auth_headers(client, db_session):
    # Register / login test PM
    reg_payload = {
        "email": "test_pm@example.com",
        "password": "password123",
        "full_name": "Test PM",
        "role": "PM",
        "skills": "architecture,python"
    }
    client.post("/api/auth/register", json=reg_payload)
    login_res = client.post("/api/auth/login", json={"email": "test_pm@example.com", "password": "password123"})
    token = login_res.json()["access_token"]
    user_id = login_res.json()["user"]["id"]
    from app.models.entities import ProjectMember, ProjectMemberRoleEnum, Project
    if db_session.query(Project).filter(Project.id == 1).first():
        if not db_session.query(ProjectMember).filter(ProjectMember.project_id == 1, ProjectMember.user_id == user_id).first():
            db_session.add(ProjectMember(project_id=1, user_id=user_id, role=ProjectMemberRoleEnum.PM))
            db_session.commit()
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def member_auth_headers(client, db_session):
    reg_payload = {
        "email": "test_member@example.com",
        "password": "password123",
        "full_name": "Test Member",
        "role": "MEMBER",
        "skills": "svelte,css"
    }
    client.post("/api/auth/register", json=reg_payload)
    login_res = client.post("/api/auth/login", json={"email": "test_member@example.com", "password": "password123"})
    token = login_res.json()["access_token"]
    user_id = login_res.json()["user"]["id"]
    from app.models.entities import ProjectMember, ProjectMemberRoleEnum, Project
    if db_session.query(Project).filter(Project.id == 1).first():
        if not db_session.query(ProjectMember).filter(ProjectMember.project_id == 1, ProjectMember.user_id == user_id).first():
            db_session.add(ProjectMember(project_id=1, user_id=user_id, role=ProjectMemberRoleEnum.MEMBER))
            db_session.commit()
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def project_with_member(client, pm_auth_headers, member_auth_headers):
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
        json={"user_id": me["id"], "role": "MEMBER"},
        headers=pm_auth_headers,
    )
    assert add.status_code == 201
    return project_id, me["id"]
