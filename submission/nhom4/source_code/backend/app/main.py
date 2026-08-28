from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.entities import (
    User,
    Project,
    ProjectMember,
    ProjectMemberRoleEnum,
    Sprint,
    Task,
    RoleEnum,
    TaskStatusEnum,
    TaskPriorityEnum,
)
from app.security import get_password_hash
from app.routers import auth, users, projects, sprints, tasks, stats, ai

def seed_initial_data():
    db = SessionLocal()
    try:
        # Create default PM and Member if no users exist
        if db.query(User).count() == 0:
            pm_user = User(
                email="pm@tupm.qzz.io",
                hashed_password=get_password_hash("koshi123"),
                full_name="Phạm Minh Tú (PM)",
                role=RoleEnum.PM,
                skills="management,architecture,python,fastapi,vue"
            )
            member_user = User(
                email="dev@tupm.qzz.io",
                hashed_password=get_password_hash("koshi123"),
                full_name="Dev Member",
                role=RoleEnum.MEMBER,
                skills="frontend,vue,tailwind,typescript"
            )
            db.add(pm_user)
            db.add(member_user)
            db.commit()
            db.refresh(pm_user)
            db.refresh(member_user)
            
            # Create default Project
            default_proj = Project(
                name="Koshi Project Management Engine",
                description="Core high-velocity local-first project management system with Vue 3 and FastAPI.",
                owner_id=pm_user.id
            )
            db.add(default_proj)
            db.commit()
            db.refresh(default_proj)

            # Assign project members
            db.add(ProjectMember(project_id=default_proj.id, user_id=pm_user.id, role=ProjectMemberRoleEnum.OWNER))
            db.add(ProjectMember(project_id=default_proj.id, user_id=member_user.id, role=ProjectMemberRoleEnum.MEMBER))
            db.commit()
            
            # Create default Sprint
            now = datetime.utcnow()
            default_sprint = Sprint(
                project_id=default_proj.id,
                name="Sprint 1: Core Architecture & AI Integration",
                goal="Deliver full-stack project tracking with FastAPI, SQLite, and 3 AI services.",
                start_date=now,
                end_date=now + timedelta(days=14),
                is_active=True
            )
            db.add(default_sprint)
            db.commit()
            db.refresh(default_sprint)
            
            # Create sample tasks
            sample_tasks = [
                Task(
                    project_id=default_proj.id,
                    sprint_id=default_sprint.id,
                    assignee_id=pm_user.id,
                    title="Implement FastAPI backend with SQLAlchemy & SQLite",
                    description="Build complete REST APIs for auth, tasks, sprints, workload stats, and AI.",
                    status=TaskStatusEnum.DONE,
                    priority=TaskPriorityEnum.HIGH,
                    complexity_points=3,
                    due_date=now + timedelta(days=2)
                ),
                Task(
                    project_id=default_proj.id,
                    sprint_id=default_sprint.id,
                    assignee_id=member_user.id,
                    title="Integrate Vue 3 Composition API with JWT Bearer Token API sync",
                    description="Connect frontend task store with backend authentication and CRUD endpoints.",
                    status=TaskStatusEnum.IN_PROGRESS,
                    priority=TaskPriorityEnum.CRITICAL,
                    complexity_points=3,
                    due_date=now + timedelta(days=4)
                ),
                Task(
                    project_id=default_proj.id,
                    sprint_id=default_sprint.id,
                    assignee_id=pm_user.id,
                    title="Develop AI Workflow Endpoints (Summary, Minutes, Assignment)",
                    description="Implement OpenAI API cascade with local Ollama fallback and deterministic safety.",
                    status=TaskStatusEnum.IN_PROGRESS,
                    priority=TaskPriorityEnum.HIGH,
                    complexity_points=3,
                    due_date=now + timedelta(days=5)
                ),
                Task(
                    project_id=default_proj.id,
                    sprint_id=default_sprint.id,
                    assignee_id=member_user.id,
                    title="Design Interactive Kanban Board View in Frontend",
                    description="Provide board view alongside table view with drag-to-status capabilities.",
                    status=TaskStatusEnum.TODO,
                    priority=TaskPriorityEnum.MEDIUM,
                    complexity_points=2,
                    due_date=now + timedelta(days=7)
                ),
                Task(
                    project_id=default_proj.id,
                    sprint_id=default_sprint.id,
                    assignee_id=member_user.id,
                    title="Deploy multi-container setup with Docker Compose on umi",
                    description="Orchestrate frontend and backend containers behind Caddy reverse proxy.",
                    status=TaskStatusEnum.BLOCKED,
                    priority=TaskPriorityEnum.HIGH,
                    complexity_points=2,
                    due_date=now + timedelta(days=1),
                    blocking_reason="Waiting for backend image build and test validation."
                )
            ]
            for st in sample_tasks:
                db.add(st)
            db.commit()
    finally:
        db.close()

def migrate_database():
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            if columns:
                if "google_id" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR(255)"))
                if "avatar_url" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)"))
            # Ensure project_members table exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS project_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL DEFAULT 'MEMBER' CHECK (role IN ('OWNER', 'PM', 'MEMBER', 'VIEWER')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_id, user_id)
                )
            """))
    except Exception as e:
        print("Migration notice:", e)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    migrate_database()
    Base.metadata.create_all(bind=engine)
    seed_initial_data()
    yield
    # Teardown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers on both /api and /api/v1 for full API specification compatibility
for prefix in ["/api", "/api/v1"]:
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(projects.router, prefix=prefix)
    app.include_router(sprints.router, prefix=prefix)
    app.include_router(tasks.router, prefix=prefix)
    app.include_router(stats.router, prefix=prefix)
    app.include_router(ai.router, prefix=prefix)

@app.get("/api/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }
