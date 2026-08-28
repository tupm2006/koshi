from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.auth import UserOut

class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    pass

class CommentOut(CommentBase):
    id: int
    task_id: int
    author_id: int
    author: Optional[UserOut] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = ""
    status: Optional[str] = "TODO"
    priority: Optional[str] = "MEDIUM"
    complexity_points: Optional[int] = Field(default=2, ge=1, le=8)
    due_date: Optional[datetime] = None
    blocking_reason: Optional[str] = None
    dependencies: Optional[List[str]] = []
    acceptance_criteria: Optional[List[str]] = []

class TaskCreate(TaskBase):
    project_id: int = 1
    sprint_id: Optional[int] = None
    assignee_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    complexity_points: Optional[int] = None
    due_date: Optional[datetime] = None
    blocking_reason: Optional[str] = None
    assignee_id: Optional[int] = None
    sprint_id: Optional[int] = None
    dependencies: Optional[List[str]] = None
    acceptance_criteria: Optional[List[str]] = None

class PriorityRequestCreate(BaseModel):
    requested_priority: str
    reason: Optional[str] = ""

class TaskOut(BaseModel):
    id: int
    project_id: int
    sprint_id: Optional[int] = None
    assignee_id: Optional[int] = None
    assignee: Optional[UserOut] = None
    title: str
    description: str
    status: str
    priority: str
    requested_priority: Optional[str] = None
    priority_request_reason: Optional[str] = None
    priority_requested_by_id: Optional[int] = None
    complexity_points: int
    due_date: Optional[datetime] = None
    is_overdue: bool = False
    slip_days: int = 0
    blocking_reason: Optional[str] = None
    dependencies: List[str] = []
    acceptance_criteria: List[str] = []
    created_at: datetime
    updated_at: datetime
    comments: Optional[List[CommentOut]] = []

    class Config:
        from_attributes = True

class TaskCycleStatusOut(BaseModel):
    id: int
    status: str
    updated_at: datetime
