from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.entities import ProjectRoleEnum


class UserRegister(BaseModel):
    """
    Registration carries no role.

    Roles are per-project (see ProjectMember); a fresh account simply has no
    memberships until it creates a project or is invited to one.
    """
    email: EmailStr
    password: str
    full_name: str
    skills: Optional[str] = "general"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str


class UserUpdate(BaseModel):
    """Self-service profile edit. Roles are not settable here."""
    skills: Optional[str] = None
    full_name: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    skills: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserWithWIPOut(UserOut):
    active_tasks_count: int = 0
    wip_points: int = 0


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenPayload(BaseModel):
    sub: str
