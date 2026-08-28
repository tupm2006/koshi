from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.entities import Project, ProjectMember, ProjectRoleEnum, Task, TaskStatusEnum, User
from app.schemas.project import (
    ProjectCreate,
    ProjectOut,
    ProjectMemberAdd,
    ProjectMemberOut,
    ProjectMemberUpdate,
)
from app.security import get_current_user, get_membership, require_member, require_project_pm

router = APIRouter(prefix="/projects", tags=["Projects"])

ACTIVE_STATUSES = [TaskStatusEnum.TODO, TaskStatusEnum.IN_PROGRESS, TaskStatusEnum.BLOCKED]


def _to_project_out(db: Session, project: Project, role: ProjectRoleEnum | None) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description or "",
        owner_id=project.owner_id,
        created_at=project.created_at,
        my_role=role,
        member_count=db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count(),
    )


@router.get("", response_model=List[ProjectOut])
def list_my_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    The personal dashboard feed: only projects the caller is a member of.

    Previously this returned every project in the database to any authenticated
    user. Membership is now the filter.
    """
    memberships = (
        db.query(ProjectMember)
        .filter(ProjectMember.user_id == current_user.id)
        .order_by(ProjectMember.project_id.desc())
        .all()
    )
    out = []
    for m in memberships:
        if m.project is not None:
            out.append(_to_project_out(db, m.project, m.role))
    return out


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    req: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Any authenticated user may create a project, and becomes its PM."""
    project = Project(name=req.name, description=req.description, owner_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)

    membership = ProjectMember(
        project_id=project.id, user_id=current_user.id, role=ProjectRoleEnum.PM
    )
    db.add(membership)
    db.commit()

    return _to_project_out(db, project, ProjectRoleEnum.PM)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = require_member(db, project_id, current_user)
    project = db.query(Project).filter(Project.id == project_id).first()
    return _to_project_out(db, project, membership.role)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_pm(db, project_id, current_user)
    project = db.query(Project).filter(Project.id == project_id).first()
    db.delete(project)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Membership & per-project role assignment
# ---------------------------------------------------------------------------


def _member_out(db: Session, m: ProjectMember) -> ProjectMemberOut:
    active = (
        db.query(Task)
        .filter(Task.assignee_id == m.user_id, Task.project_id == m.project_id)
        .filter(Task.status.in_(ACTIVE_STATUSES))
        .all()
    )
    return ProjectMemberOut(
        user_id=m.user_id,
        project_id=m.project_id,
        role=m.role,
        full_name=m.user.full_name,
        email=m.user.email,
        skills=m.user.skills or "",
        avatar_url=m.user.avatar_url,
        active_tasks_count=len(active),
        wip_points=sum(t.complexity_points for t in active),
    )


@router.get("/{project_id}/members", response_model=List[ProjectMemberOut])
def list_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Any member may see the roster; only a PM may change it."""
    require_member(db, project_id, current_user)
    members = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.id.asc())
        .all()
    )
    return [_member_out(db, m) for m in members]


@router.post("/{project_id}/members", response_model=ProjectMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: int,
    req: ProjectMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_pm(db, project_id, current_user)

    if req.user_id is None and req.email is None:
        raise HTTPException(status_code=400, detail="Provide either email or user_id")

    query = db.query(User)
    target = (
        query.filter(User.id == req.user_id).first()
        if req.user_id is not None
        else query.filter(User.email == req.email).first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if get_membership(db, project_id, target) is not None:
        raise HTTPException(status_code=400, detail="User is already a member of this project")

    membership = ProjectMember(project_id=project_id, user_id=target.id, role=req.role)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return _member_out(db, membership)


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberOut)
def update_member_role(
    project_id: int,
    user_id: int,
    req: ProjectMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change a member's role within this project. PM only."""
    require_project_pm(db, project_id, current_user)

    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    # Refuse to remove the last PM, which would strand the project with nobody
    # able to administer it.
    if membership.role == ProjectRoleEnum.PM and req.role != ProjectRoleEnum.PM:
        pm_count = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.role == ProjectRoleEnum.PM,
            )
            .count()
        )
        if pm_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot demote the last Project Manager; promote another member first",
            )

    membership.role = req.role
    db.commit()
    db.refresh(membership)
    return _member_out(db, membership)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_pm(db, project_id, current_user)

    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    if membership.role == ProjectRoleEnum.PM:
        pm_count = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.role == ProjectRoleEnum.PM,
            )
            .count()
        )
        if pm_count <= 1:
            raise HTTPException(
                status_code=400, detail="Cannot remove the last Project Manager"
            )

    db.delete(membership)
    db.commit()
    return None
