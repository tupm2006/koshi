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
    created_at: datetime

    class Config:
        from_attributes = True

class ProjectMemberAdd(BaseModel):
    user_id: int
    role: Optional[ProjectMemberRoleEnum] = ProjectMemberRoleEnum.MEMBER

class ProjectMemberUpdate(BaseModel):
    role: ProjectMemberRoleEnum

class ProjectMemberOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: ProjectMemberRoleEnum
    created_at: datetime
    user: Optional[UserOut] = None

    class Config:
        from_attributes = True
