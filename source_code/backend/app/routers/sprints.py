from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.entities import Sprint, Task, TaskStatusEnum, User, ProjectMemberRoleEnum
from app.schemas.sprint import SprintCreate, SprintOut, SprintStatsOut
from app.security import get_current_user, verify_project_membership

router = APIRouter(prefix="/sprints", tags=["Sprints"])

@router.get("", response_model=List[SprintOut])
def list_sprints(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_project_membership(project_id, current_user.id, db)
    return db.query(Sprint).filter(Sprint.project_id == project_id).all()

@router.post("", response_model=SprintOut, status_code=status.HTTP_201_CREATED)
def create_sprint(req: SprintCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_project_membership(req.project_id, current_user.id, db, allowed_roles=[ProjectMemberRoleEnum.OWNER, ProjectMemberRoleEnum.PM])
    sprint = Sprint(
        project_id=req.project_id,
        name=req.name,
        goal=req.goal,
        start_date=req.start_date,
        end_date=req.end_date,
        is_active=req.is_active
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint

@router.get("/{sprint_id}/stats", response_model=SprintStatsOut)
def get_sprint_stats(sprint_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
        
    verify_project_membership(sprint.project_id, current_user.id, db)
    tasks = db.query(Task).filter(Task.sprint_id == sprint_id).all()
    total = len(tasks)
    done = len([t for t in tasks if t.status == TaskStatusEnum.DONE])
    in_prog = len([t for t in tasks if t.status == TaskStatusEnum.IN_PROGRESS])
    blocked = len([t for t in tasks if t.status == TaskStatusEnum.BLOCKED])
    todo = len([t for t in tasks if t.status == TaskStatusEnum.TODO])
    
    now = datetime.utcnow()
    delayed = len([
        t for t in tasks 
        if t.status != TaskStatusEnum.DONE and t.due_date and t.due_date < now
    ])
    
    completion_rate = (done / total * 100.0) if total > 0 else 0.0

    return SprintStatsOut(
        sprint_id=sprint.id,
        sprint_name=sprint.name,
        total_tasks=total,
        completed_tasks=done,
        in_progress_tasks=in_prog,
        blocked_tasks=blocked,
        todo_tasks=todo,
        completion_rate_pct=round(completion_rate, 1),
        delayed_tasks_count=delayed
    )
