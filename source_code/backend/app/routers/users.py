from typing import List
from fastapi import APIRouter, HTTPException, Depends, status, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import User, Task, ProjectMember, RoleEnum, ProjectMemberRoleEnum
from app.schemas.auth import UserOut, UserUpdate
from app.schemas.stats import UserWithWIPOut
from app.security import get_current_user
from app.services.uploads import save_upload, delete_upload, get_upload_path

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
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only update your own profile."
        )
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.skills is not None:
        user.skills = payload.skills.strip()
        
    db.commit()
    db.refresh(user)
    return user

@router.post("/me/avatar", response_model=UserOut)
async def upload_user_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stored_name, content_type, size_bytes = await save_upload(file)

    if current_user.avatar_file:
        delete_upload(current_user.avatar_file)

    current_user.avatar_file = stored_name
    current_user.avatar_url = f"/api/users/{current_user.id}/avatar?v={stored_name[:8]}"
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/{user_id}/avatar")
def get_user_avatar(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.avatar_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")

    file_path = get_upload_path(user.avatar_file)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar file missing on disk")

    media_type = "application/octet-stream"
    if user.avatar_file.endswith(".png"):
        media_type = "image/png"
    elif user.avatar_file.endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
    elif user.avatar_file.endswith(".webp"):
        media_type = "image/webp"

    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=86400",
    }
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers=headers
    )
