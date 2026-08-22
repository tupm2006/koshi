from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.entities import User, Task, TaskStatusEnum
from app.schemas.stats import MemberWorkloadOut, DelayedTaskOut
from app.security import get_current_user

router = APIRouter(prefix="/stats", tags=["Statistics & Workload"])

@router.get("/workload", response_model=List[MemberWorkloadOut])
def get_member_workloads(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).all()
    results = []
    
    for u in users:
        active_tasks = db.query(Task).filter(
            Task.assignee_id == u.id,
            Task.status.in_([TaskStatusEnum.TODO, TaskStatusEnum.IN_PROGRESS, TaskStatusEnum.BLOCKED])
        ).all()
        
        points = sum(t.complexity_points for t in active_tasks)
        skills_list = [s.strip() for s in (u.skills or "").split(",") if s.strip()]
        
        # Overloaded heuristic threshold: > 10 complexity points or > 5 active tasks
        is_overloaded = points > 10 or len(active_tasks) > 5
        
        results.append(MemberWorkloadOut(
            user_id=u.id,
            full_name=u.full_name,
            email=u.email,
            role=u.role.value,
            skills=skills_list,
            active_tasks_count=len(active_tasks),
            total_complexity_points=points,
            is_overloaded=is_overloaded
        ))
        
    return results

@router.get("/delayed-tasks", response_model=List[DelayedTaskOut])
def get_delayed_tasks(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    now = datetime.utcnow()
    tasks = db.query(Task).filter(
        Task.project_id == project_id,
        Task.status != TaskStatusEnum.DONE,
        Task.due_date.isnot(None),
        Task.due_date < now
    ).all()
    
    results = []
    for t in tasks:
        days_overdue = (now - t.due_date).days if t.due_date else 0
        assignee_name = t.assignee.full_name if t.assignee else "Unassigned"
        results.append(DelayedTaskOut(
            task_id=t.id,
            title=t.title,
            status=t.status.value,
            priority=t.priority.value,
            due_date=t.due_date.isoformat() if t.due_date else "",
            days_overdue=days_overdue,
            assignee_name=assignee_name
        ))
        
    return results
