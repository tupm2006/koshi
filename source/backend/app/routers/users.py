import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.entities import (
    ProjectMember, Task, TaskAssignee, TaskStatusEnum, User,
)
from app.schemas.auth import UserOut, UserWithWIPOut, UserUpdate
from app.security import get_current_user
from app.services.uploads import AVATAR_TYPES, path_for, save_upload

router = APIRouter(prefix="/users", tags=["Users Management"])

@router.get("", response_model=List[UserWithWIPOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    users = db.query(User).order_by(User.id.asc()).all()
    results = []

    for u in users:
        active_tasks = db.query(Task).filter(
            Task.assignees.any(TaskAssignee.user_id == u.id),
            Task.status.in_([TaskStatusEnum.TODO, TaskStatusEnum.IN_PROGRESS, TaskStatusEnum.BLOCKED])
        ).all()

        wip_pts = sum(t.complexity_points for t in active_tasks)
        
        user_out = UserWithWIPOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            google_id=u.google_id,
            avatar_url=u.avatar_url,
            skills=u.skills or "general",
            created_at=u.created_at,
            active_tasks_count=len(active_tasks),
            wip_points=wip_pts
        )
        results.append(user_out)

    return results

@router.patch("/{user_id}", response_model=UserOut)
def update_user_profile(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Self-service profile edit.

    Roles are no longer editable here: they live on ProjectMember and are changed
    via PATCH /projects/{project_id}/members/{user_id} by a PM of that project.
    """
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only edit your own profile"
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    if payload.skills is not None:
        target_user.skills = payload.skills
    if payload.full_name is not None:
        target_user.full_name = payload.full_name

    db.commit()
    db.refresh(target_user)
    return target_user


# ---------------------------------------------------------------------------
# Avatars
# ---------------------------------------------------------------------------
#
# Stored in the same directory as attachments and through the same streaming
# writer, so there is one place that decides what a stored file may be. Avatars
# narrow it further: images only, and a smaller ceiling, because a profile
# picture is re-fetched on every board that renders a card.

AVATAR_MAX_BYTES = 2 * 1024 * 1024


def _shares_a_project(db: Session, a: User, b_id: int) -> bool:
    """Do these two people have any project in common?"""
    mine = {m.project_id for m in db.query(ProjectMember).filter(
        ProjectMember.user_id == a.id) if m.is_active}
    if not mine:
        return False
    return db.query(ProjectMember).filter(
        ProjectMember.user_id == b_id,
        ProjectMember.project_id.in_(mine),
    ).first() is not None


@router.post("/me/avatar", response_model=UserOut)
async def upload_my_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Replace the caller's profile picture.

    Only ever the caller's own — there is no user_id parameter, so no request
    can aim this at somebody else's profile.
    """
    # Read the outgoing name BEFORE overwriting it: reading it back after the
    # commit returns the new one, and the old file is then never removed.
    previous_file = current_user.avatar_file

    stored_name, _content_type, _size = await save_upload(
        file, allowed=AVATAR_TYPES, max_bytes=AVATAR_MAX_BYTES
    )

    current_user.avatar_url = f"/api/users/{current_user.id}/avatar?v={stored_name[:8]}"
    current_user.avatar_file = stored_name
    db.commit()
    db.refresh(current_user)

    # Best effort, after the commit: the new picture is already saved, so
    # failing to unlink the old one must not fail the request. That leaves a
    # stray file, which is recoverable; failing here would lose the upload.
    if previous_file and previous_file != stored_name:
        try:
            os.remove(path_for(previous_file))
        except OSError:
            pass

    return current_user


@router.delete("/me/avatar", response_model=UserOut)
def remove_my_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stored = current_user.avatar_file
    current_user.avatar_url = None
    current_user.avatar_file = None
    db.commit()
    db.refresh(current_user)

    if stored:
        try:
            os.remove(path_for(stored))
        except OSError:
            pass
    return current_user


@router.get("/{user_id}/avatar")
def get_avatar(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Serve a profile picture.

    Visible to yourself and to anyone you share a project with — the two cases
    where the app actually renders a face. Anyone else gets 404 rather than 403:
    the reply must not confirm that an account exists.
    """
    if user_id != current_user.id and not _shares_a_project(db, current_user, user_id):
        raise HTTPException(status_code=404, detail="Not found")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.avatar_file:
        raise HTTPException(status_code=404, detail="No avatar")

    path = path_for(user.avatar_file)
    if not os.path.exists(path):
        raise HTTPException(status_code=410, detail="Avatar file is no longer stored")

    return FileResponse(
        path,
        media_type=_avatar_media_type(user.avatar_file),
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src \'none\'; sandbox",
            # Content is immutable per stored_name, and the URL carries a
            # version segment, so a long cache is safe and saves a request per
            # card render.
            "Cache-Control": "private, max-age=86400",
        },
    )


def _avatar_media_type(stored_name: str) -> str:
    ext = os.path.splitext(stored_name)[1].lower()
    for ctype, extension in AVATAR_TYPES.items():
        if extension == ext:
            return ctype
    # Unreachable for anything save_upload wrote; refuse rather than guess.
    raise HTTPException(status_code=500, detail="Unknown avatar type")
