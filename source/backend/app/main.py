from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.entities import (
    User, Project, ProjectMember, Sprint, Task,
    ProjectRoleEnum, TaskStatusEnum, TaskPriorityEnum,
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
                skills="management,architecture,python,fastapi,vue"
            )
            member_user = User(
                email="dev@tupm.qzz.io",
                hashed_password=get_password_hash("koshi123"),
                full_name="Dev Member",
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

            # Roles are granted per-project: the creator is PM here, the other
            # user is an ordinary member of this same project.
            db.add(ProjectMember(project_id=default_proj.id, user_id=pm_user.id, role=ProjectRoleEnum.PM))
            db.add(ProjectMember(project_id=default_proj.id, user_id=member_user.id, role=ProjectRoleEnum.MEMBER))
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

def _check_production_safety() -> None:
    """
    Refuse to start with development defaults outside development.

    These settings are convenient locally and dangerous in production, so the
    check fails loudly at boot rather than silently exposing the deployment.
    """
    if settings.ENVIRONMENT.lower() in ("development", "dev", "test", "testing"):
        return

    problems = []
    if settings.JWT_SECRET == settings.DEV_JWT_SECRET:
        problems.append("JWT_SECRET is still the development default; set a strong unique value.")
    if settings.ALLOW_UNVERIFIED_GOOGLE_TOKENS:
        problems.append("ALLOW_UNVERIFIED_GOOGLE_TOKENS is enabled; this permits forged sessions.")
    if settings.CORS_ORIGINS.strip() == "*":
        problems.append("CORS_ORIGINS is '*'; pin it to the deployed frontend origin(s).")
    if settings.SEED_DEMO_DATA:
        problems.append("SEED_DEMO_DATA is enabled; this creates accounts with known passwords.")

    if problems:
        raise RuntimeError(
            "Refusing to start with insecure configuration in ENVIRONMENT="
            f"{settings.ENVIRONMENT}:\n  - " + "\n  - ".join(problems)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    _check_production_safety()
    Base.metadata.create_all(bind=engine)
    if settings.SEED_DEMO_DATA:
        seed_initial_data()
    yield
    # Teardown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # Credentialed requests cannot use a wildcard origin; browsers reject the
    # combination. Only send credentials when the origins are pinned.
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(projects.router, prefix=settings.API_V1_PREFIX)
app.include_router(sprints.router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX)
app.include_router(stats.router, prefix=settings.API_V1_PREFIX)
app.include_router(ai.router, prefix=settings.API_V1_PREFIX)

@app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }
