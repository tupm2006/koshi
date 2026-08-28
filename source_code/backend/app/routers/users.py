from typing import List
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import User, Task, ProjectMember, RoleEnum, ProjectMemberRoleEnum
from app.schemas.auth import UserOut, UserUpdate
from app.schemas.stats import UserWithWIPOut
from app.security import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

def enrich_user_wip(user: User, db: Session) -> dict:
    active_tasks = db.query(Task).filter(
        Task.assignee_id == user.id,
        Task.status.in_(["TODO", "IN_PROGRESS", "BLOCKED"])
    ).all()
    
    total_pts = sum(t.complexity_points for t in active_tasks)
    skills_list = [s.strip() for s in user.skills.split(",") if s.strip()] if user.skills else []
    
    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "avatar_url": user.avatar_url,
        "active_tasks_count": len(active_tasks),
        "total_complexity_points": total_pts,
        "is_overloaded": total_pts > 8,
        "skills": skills_list
    }

@router.get("", response_model=List[UserWithWIPOut])
def get_collaborating_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Retrieve all users sharing at least one project with the requesting user
    shared_projects = db.query(ProjectMember.project_id).filter(
        ProjectMember.user_id == current_user.id
    ).subquery()
    
    collaborator_ids = db.query(ProjectMember.user_id).filter(
        ProjectMember.project_id.in_(shared_projects)
    ).distinct().all()
    
    user_ids = [uid[0] for uid in collaborator_ids] if collaborator_ids else [current_user.id]
    users = db.query(User).filter(User.id.in_(user_ids)).order_by(User.id.asc()).all()
    return [enrich_user_wip(u, db) for u in users]

@router.get("/search", response_model=List[UserOut])
def search_users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    search_pattern = f"%{q.strip()}%"
    users = db.query(User).filter(
        (User.email.ilike(search_pattern)) | (User.full_name.ilike(search_pattern))
    ).limit(10).all()
    return users

@router.patch("/{user_id}", response_model=UserOut)
def update_user_profile(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    is_pm = (current_user.role == RoleEnum.PM) or (hasattr(current_user.role, 'value') and current_user.role.value == "PM")
    if current_user.id != user_id and not is_pm:
        raise HTTPException(status_code=403, detail="Not authorized to update other users' profile")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.skills is not None:
        user.skills = payload.skills
    if payload.role is not None and is_pm:
        user.role = payload.role
        
    db.commit()
    db.refresh(user)
    return user
