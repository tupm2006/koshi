from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.entities import (
    MembershipStatusEnum, Project, ProjectMember, ProjectRoleEnum, Task,
    TaskStatusEnum, User,
)
from app.schemas.project import (
    InvitationOut,
    ProjectCreate,
    ProjectOut,
    ProjectMemberAdd,
    ProjectMemberOut,
    ProjectMemberUpdate,
)
from app.security import (
    get_current_user, get_membership, get_membership_row, require_member,
    require_project_pm,
)
from app.utils.time import utcnow

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
        # Accepted only. An outstanding invitation must not make a personal
        # project look shared — that would flip it to read-only offline
        # (INV-15) on the strength of somebody who has not replied.
        member_count=db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project.id,
            ProjectMember.status == MembershipStatusEnum.ACCEPTED,
        )
        .count(),
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
        .filter(
            ProjectMember.user_id == current_user.id,
            # Invitations are not projects. They surface separately, at
            # /projects/invitations, so the dashboard never shows something the
            # caller cannot actually open.
            ProjectMember.status == MembershipStatusEnum.ACCEPTED,
        )
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
        project_id=project.id,
        user_id=current_user.id,
        role=ProjectRoleEnum.PM,
        # You do not invite yourself to the project you just created.
        status=MembershipStatusEnum.ACCEPTED,
        responded_at=utcnow(),
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
        status=m.status,
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

    existing = get_membership_row(db, project_id, target)
    if existing is not None:
        if existing.status == MembershipStatusEnum.ACCEPTED:
            raise HTTPException(status_code=400, detail="User is already a member of this project")
        if existing.status == MembershipStatusEnum.PENDING:
            raise HTTPException(status_code=400, detail="This user has already been invited")
        # DECLINED: allow a re-invite. People change their minds, and refusing
        # forever would mean a PM could permanently lock someone out of a
        # project by mis-clicking once.
        existing.role = req.role
        existing.status = MembershipStatusEnum.PENDING
        existing.invited_by_id = current_user.id
        existing.responded_at = None
        db.commit()
        db.refresh(existing)
        return _member_out(db, existing)

    # PENDING, not ACCEPTED: adding somebody to a project is a request, and the
    # row grants nothing until they answer it.
    membership = ProjectMember(
        project_id=project_id,
        user_id=target.id,
        role=req.role,
        status=MembershipStatusEnum.PENDING,
        invited_by_id=current_user.id,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return _member_out(db, membership)


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------
# Mounted before /{project_id} would matter if this path could be read as an id,
# but "invitations" is not an int so FastAPI resolves it correctly either way.

@router.get("/invitations/pending", response_model=List[InvitationOut])
def list_my_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Invitations awaiting this user's answer.

    Returns the project's name and the inviter's — the recipient is not a member
    yet and so cannot look either of them up.
    """
    rows = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.user_id == current_user.id,
            ProjectMember.status == MembershipStatusEnum.PENDING,
        )
        .order_by(ProjectMember.id.desc())
        .all()
    )
    out = []
    for m in rows:
        if m.project is None:
            continue
        out.append(
            InvitationOut(
                project_id=m.project_id,
                project_name=m.project.name,
                project_description=m.project.description or "",
                role=m.role,
                invited_by_name=m.invited_by.full_name if m.invited_by else None,
                invited_at=m.created_at,
            )
        )
    return out


def _respond_to_invitation(
    db: Session, project_id: int, user: User, accept: bool
) -> ProjectMember:
    row = get_membership_row(db, project_id, user)
    # 404 for a stranger, and equally for someone with no invitation: the reply
    # must not reveal that the project exists (same rule as require_member).
    if row is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if row.status != MembershipStatusEnum.PENDING:
        raise HTTPException(
            status_code=409,
            detail="This invitation has already been answered",
        )
    row.status = MembershipStatusEnum.ACCEPTED if accept else MembershipStatusEnum.DECLINED
    row.responded_at = utcnow()
    db.commit()
    db.refresh(row)
    return row


@router.post("/{project_id}/invitation/accept", response_model=ProjectOut)
def accept_invitation(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept, and get the project back so the client can open it immediately."""
    row = _respond_to_invitation(db, project_id, current_user, accept=True)
    return _to_project_out(db, row.project, row.role)


@router.post("/{project_id}/invitation/decline", status_code=status.HTTP_204_NO_CONTENT)
def decline_invitation(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Decline. The row is kept as DECLINED rather than deleted, so the PM can see
    the answer instead of watching the invitation silently disappear.
    """
    _respond_to_invitation(db, project_id, current_user, accept=False)
    return None


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
