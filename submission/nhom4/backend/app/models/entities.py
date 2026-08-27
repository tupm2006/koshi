import enum
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class RoleEnum(str, enum.Enum):
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
    role = Column(Enum(RoleEnum), default=RoleEnum.MEMBER, nullable=False)
    skills = Column(String(255), default="frontend,backend,general")  # Comma-separated
    created_at = Column(DateTime, default=datetime.utcnow)
    
    assigned_tasks = relationship("Task", back_populates="assignee")
    comments = relationship("Comment", back_populates="author")
    owned_projects = relationship("Project", back_populates="owner")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="owned_projects")
    sprints = relationship("Sprint", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

class Sprint(Base):
    __tablename__ = "sprints"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    goal = Column(String(255), default="")
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")
    sprint = relationship("Sprint", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")

    @property
    def dependencies(self):
        try:
            return json.loads(self.dependencies_json or "[]")
        except Exception:
            return []

    @dependencies.setter
    def dependencies(self, value):
        self.dependencies_json = json.dumps(value if isinstance(value, list) else [])

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
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")
