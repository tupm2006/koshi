from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.entities import TaskStatusEnum, TaskPriorityEnum, CommentKindEnum
from app.schemas.auth import UserOut

class AttachmentOut(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    # Where to fetch the bytes. Membership is re-checked on that route — a URL
    # is not a capability.
    url: str = ""

    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    # EVIDENCE is written when a task moves to DONE. Clients may set it, and
    # nothing is enforced by it — it changes how the entry is labelled, not
    # what it can do.
    kind: CommentKindEnum = CommentKindEnum.COMMENT

class CommentOut(CommentBase):
    id: int
    task_id: int
    author_id: int
    author: Optional[UserOut] = None
    kind: CommentKindEnum = CommentKindEnum.COMMENT
    attachments: List[AttachmentOut] = []
    created_at: datetime

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = ""
    status: Optional[TaskStatusEnum] = TaskStatusEnum.TODO
    priority: Optional[TaskPriorityEnum] = TaskPriorityEnum.MEDIUM
    complexity_points: Optional[int] = Field(default=2, ge=1, le=8)
    due_date: Optional[datetime] = None
    blocking_reason: Optional[str] = None
    # Integer task ids, matching Task.id. Previously List[str], which could
    # never match an int primary key — the server-side graph was unresolvable.
    dependencies: Optional[List[int]] = []
    acceptance_criteria: Optional[List[str]] = []

class TaskCreate(TaskBase):
    project_id: int
    sprint_id: Optional[int] = None
    # Plural. Every id must belong to the project (checked server-side) — you
    # cannot assign work to somebody who cannot see it.
    assignee_ids: Optional[List[int]] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    # F-08: the same bounds as TaskCreate. Previously unbounded on update, so a
    # value rejected at creation could be introduced by a subsequent PATCH.
    complexity_points: Optional[int] = Field(default=None, ge=1, le=8)
    due_date: Optional[datetime] = None
    blocking_reason: Optional[str] = None
    sprint_id: Optional[int] = None
    # None means "leave alone"; [] means "unassign everybody". The distinction
    # matters — a PATCH that touches only the title must not clear assignees.
    assignee_ids: Optional[List[int]] = None
    dependencies: Optional[List[int]] = None
    acceptance_criteria: Optional[List[str]] = None

class TaskOut(BaseModel):
    id: int
    # Human-facing label. The canonical identifier is `id`; this exists so
    # clients never have to synthesise "TSK-n" themselves and drift from us.
    key: str = ""
    project_id: int
    sprint_id: Optional[int] = None
    assignees: List[UserOut] = []
    title: str
    description: str
    status: TaskStatusEnum
    priority: TaskPriorityEnum
    complexity_points: int
    due_date: Optional[datetime] = None
    blocking_reason: Optional[str] = None
    dependencies: List[int]
    acceptance_criteria: List[str]
    created_at: datetime
    updated_at: datetime
    comments: Optional[List[CommentOut]] = []

    class Config:
        from_attributes = True
