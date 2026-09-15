from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.entities import ProjectMemberRoleEnum
from app.schemas.auth import UserOut

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = ""

class ProjectCreate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    id: int
    owner_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProjectMemberAdd(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[ProjectMemberRoleEnum] = ProjectMemberRoleEnum.MEMBER

class ProjectMemberUpdate(BaseModel):
    role: ProjectMemberRoleEnum

class ProjectMemberOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: ProjectMemberRoleEnum
    created_at: Optional[datetime] = None
    user: Optional[UserOut] = None

    class Config:
        from_attributes = True
