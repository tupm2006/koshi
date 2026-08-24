from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.entities import User, Project, Sprint, Task, RoleEnum, TaskStatusEnum, TaskPriorityEnum
from app.security import get_password_hash
from app.routers import auth, projects, sprints, tasks, stats, ai

def seed_initial_data():
    db = SessionLocal()
    try:
        # Create default PM and Member if no users exist
        if db.query(User).count() == 0:
            pm_user = User(
                email="pm@felixsu.qzz.io",
                hashed_password=get_password_hash("koshi123"),
                full_name="Felix Su (PM)",
                role=RoleEnum.PM,
                skills="management,system_architecture,python,fastapi,svelte"
            )
            member_user = User(
                email="dev@felixsu.qzz.io",
                hashed_password=get_password_hash("koshi123"),
                full_name="Dev Member",
                role=RoleEnum.MEMBER,
                skills="frontend,svelte,tailwind,javascript"
            )
            db.add(pm_user)
            db.add(member_user)
            db.commit()
            db.refresh(pm_user)
            db.refresh(member_user)
            
            # Create default Project
            default_proj = Project(
                name="Koshi Project Management Engine",
                description="Core high-velocity local-first project management system with Svelte 5 and FastAPI.",
                owner_id=pm_user.id
            )
            db.add(default_proj)
            db.commit()
            db.refresh(default_proj)
            
            # Create default Sprint
            now = datetime.utcnow()
            default_sprint = Sprint(
                project_id=default_proj.id,
                name="Sprint 1: Core Architecture & AI Integration",
                goal="Deliver full-stack project tracking with FastAPI, SQLite, and 3 mandated AI endpoints.",
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
                    title="Develop 3 Mandated AI Endpoints (Summary, Minutes, Assignment)",
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
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
