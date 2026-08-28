from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.entities import ProjectRoleEnum


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = ""


class ProjectCreate(ProjectBase):
    pass


class ProjectOut(ProjectBase):
    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    # The *calling* user's role in this project. Populated per-request, so the
    # same project yields different values for different callers.
    my_role: Optional[ProjectRoleEnum] = None
    member_count: int = 0

    class Config:
        from_attributes = True


class ProjectMemberOut(BaseModel):
    user_id: int
    project_id: int
    role: ProjectRoleEnum
    full_name: str
    email: str
    skills: str
    avatar_url: Optional[str] = None
    active_tasks_count: int = 0
    wip_points: int = 0

    class Config:
        from_attributes = True


class ProjectMemberAdd(BaseModel):
    """Invite by email (the id is rarely known to the UI) or by explicit user id."""
    email: Optional[EmailStr] = None
    user_id: Optional[int] = None
    role: ProjectRoleEnum = ProjectRoleEnum.MEMBER


class ProjectMemberUpdate(BaseModel):
    role: ProjectRoleEnum
