import enum
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.time import utcnow

def _coerce_task_id(value) -> "int | None":
    """Accept 12, "12" or a legacy "TSK-12"; anything else is dropped."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.upper().startswith("TSK-"):
            text = text[4:]
        try:
            return int(text)
        except ValueError:
            return None
    return None


class ProjectRoleEnum(str, enum.Enum):
    """A user's role *within a single project*. There is no global role."""
    PM = "PM"
    MEMBER = "MEMBER"

class TaskStatusEnum(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DONE = "DONE"

class TaskPriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth accounts
    full_name = Column(String(100), nullable=False)
    google_id = Column(String(255), unique=True, index=True, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    skills = Column(String(255), default="frontend,backend,general")  # Comma-separated
    created_at = Column(DateTime, default=utcnow)

    assigned_tasks = relationship("Task", back_populates="assignee")
    comments = relationship("Comment", back_populates="author")
    owned_projects = relationship("Project", back_populates="owner")
    memberships = relationship(
        "ProjectMember",
        back_populates="user",
        cascade="all, delete-orphan",
        # Disambiguate: ProjectMember now has two FKs to users (user_id and
        # invited_by_id), so the join condition must be stated.
        foreign_keys="ProjectMember.user_id",
    )

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    
    owner = relationship("User", back_populates="owned_projects")
    sprints = relationship("Sprint", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")

class MembershipStatusEnum(str, enum.Enum):
    """
    Whether a membership has been accepted by the person it names.

    A PM adding someone to a project is an *invitation*, not a fact about that
    person. PENDING rows grant nothing: `require_member` refuses them, so an
    invited user cannot read the project — not even its existence — until they
    accept. Modelling this as a column on ProjectMember rather than a separate
    Invitation table keeps the authorisation root single: there is still exactly
    one row to consult, and exactly one place that decides what it means.
    """
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class ProjectMember(Base):
    """
    Join entity carrying a user's role in one project.

    This is the authorisation root: every project-scoped endpoint resolves the
    caller's ProjectMember row and refuses the request when there is none.
    A user with no row for a project cannot see or touch it at all.
    """
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(ProjectRoleEnum), default=ProjectRoleEnum.MEMBER, nullable=False)
    status = Column(
        Enum(MembershipStatusEnum),
        default=MembershipStatusEnum.ACCEPTED,
        nullable=False,
    )
    invited_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="memberships", foreign_keys=[user_id])
    invited_by = relationship("User", foreign_keys=[invited_by_id])

    @property
    def is_active(self) -> bool:
        """Only an accepted membership confers access."""
        return self.status == MembershipStatusEnum.ACCEPTED


class Sprint(Base):
    __tablename__ = "sprints"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    goal = Column(String(255), default="")
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    
    project = relationship("Project", back_populates="sprints")
    tasks = relationship("Task", back_populates="sprint")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(TaskStatusEnum), default=TaskStatusEnum.TODO, nullable=False)
    priority = Column(Enum(TaskPriorityEnum), default=TaskPriorityEnum.MEDIUM, nullable=False)
    complexity_points = Column(Integer, default=2)  # 1=S, 2=M, 3=L, 5=XL
    due_date = Column(DateTime, nullable=True)
    blocking_reason = Column(String(255), nullable=True)
    dependencies_json = Column(Text, default="[]")  # JSON list of task IDs
    acceptance_criteria_json = Column(Text, default="[]")  # JSON list of strings
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    project = relationship("Project", back_populates="tasks")
    sprint = relationship("Sprint", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")

    @property
    def key(self) -> str:
        """Display label, e.g. "TSK-12". Derived — never stored."""
        return f"TSK-{self.id}"

    @property
    def dependencies(self):
        """
        Integer ids of prerequisite tasks.

        Legacy rows may hold "TSK-n" strings from before the ids were unified,
        so those are coerced on read rather than left to poison the graph.
        """
        try:
            raw = json.loads(self.dependencies_json or "[]")
        except Exception:
            return []
        out = []
        for item in raw if isinstance(raw, list) else []:
            coerced = _coerce_task_id(item)
            if coerced is not None:
                out.append(coerced)
        return out

    @dependencies.setter
    def dependencies(self, value):
        if not isinstance(value, list):
            self.dependencies_json = json.dumps([])
            return
        cleaned = [c for c in (_coerce_task_id(v) for v in value) if c is not None]
        self.dependencies_json = json.dumps(cleaned)

    @property
    def acceptance_criteria(self):
        try:
            return json.loads(self.acceptance_criteria_json or "[]")
        except Exception:
            return []

    @acceptance_criteria.setter
    def acceptance_criteria(self, value):
        self.acceptance_criteria_json = json.dumps(value if isinstance(value, list) else [])

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")
