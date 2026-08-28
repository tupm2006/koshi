from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.entities import User, Task, TaskStatusEnum
from app.schemas.auth import UserOut, UserWithWIPOut, UserUpdate
from app.security import get_current_user

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
            Task.assignee_id == u.id,
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
