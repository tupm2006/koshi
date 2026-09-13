from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.entities import User, Task, TaskStatusEnum, ProjectMember
from app.schemas.stats import MemberWorkloadOut, DelayedTaskOut
from app.security import get_current_user, verify_project_membership

router = APIRouter(prefix="/stats", tags=["Statistics & Workload"])

@router.get("/workload", response_model=List[MemberWorkloadOut])
def get_member_workloads(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if project_id is not None:
        verify_project_membership(project_id, current_user.id, db)
        members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
        users = [m.user for m in members if m.user is not None]
        role_by_user = {m.user_id: m.role.value if hasattr(m.role, 'value') else str(m.role) for m in members}
    else:
        users = db.query(User).all()
        role_by_user = {}

    results = []
    for u in users:
        task_query = db.query(Task).filter(
            Task.assignee_id == u.id,
            Task.status.in_([TaskStatusEnum.TODO, TaskStatusEnum.IN_PROGRESS, TaskStatusEnum.BLOCKED])
        )
        if project_id is not None:
            task_query = task_query.filter(Task.project_id == project_id)
        active_tasks = task_query.all()
        
        points = sum(t.complexity_points for t in active_tasks)
        skills_list = [s.strip() for s in (u.skills or "").split(",") if s.strip()]
        
        # Overloaded heuristic threshold: > 10 complexity points or > 5 active tasks
        is_overloaded = points > 10 or len(active_tasks) > 5
        role_str = role_by_user.get(u.id, u.role.value if hasattr(u.role, 'value') else str(u.role))
        
        results.append(MemberWorkloadOut(
            user_id=u.id,
            full_name=u.full_name,
            email=u.email,
            role=role_str,
            skills=skills_list,
            active_tasks_count=len(active_tasks),
            total_complexity_points=points,
            is_overloaded=is_overloaded
        ))
        
    return results

@router.get("/delayed-tasks", response_model=List[DelayedTaskOut])
def get_delayed_tasks(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_project_membership(project_id, current_user.id, db)
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
