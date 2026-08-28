from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.entities import MembershipStatusEnum, ProjectRoleEnum


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
    # PENDING means invited but not yet accepted — the roster shows them greyed
    # out, and they have no access at all until they respond.
    status: MembershipStatusEnum = MembershipStatusEnum.ACCEPTED
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


class InvitationOut(BaseModel):
    """
    A pending invitation, from the invited user's point of view.

    Deliberately carries the project name and the inviter's name: someone
    deciding whether to accept needs to know what they are joining and who asked,
    and they cannot read the project itself to find out (they are not a member
    yet — that is the whole point).
    """
    project_id: int
    project_name: str
    project_description: str = ""
    role: ProjectRoleEnum
    invited_by_name: Optional[str] = None
    invited_at: Optional[datetime] = None

    class Config:
        from_attributes = True
