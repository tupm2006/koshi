from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.entities import User, Task, TaskAssignee, ProjectMember, TaskStatusEnum
from app.schemas.stats import MemberWorkloadOut, DelayedTaskOut
from app.security import get_current_user, require_member
from app.utils.time import utcnow

router = APIRouter(prefix="/stats", tags=["Statistics & Workload"])

@router.get("/workload", response_model=List[MemberWorkloadOut])
def get_member_workloads(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Workload for the members of one project. Requires membership of it."""
    require_member(db, project_id, current_user)

    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    users = [m.user for m in members if m.user is not None]
    role_by_user = {m.user_id: m.role.value for m in members}
    results = []

    for u in users:
        active_tasks = db.query(Task).filter(
            Task.assignees.any(TaskAssignee.user_id == u.id),
            Task.project_id == project_id,
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
            role=role_by_user.get(u.id, "MEMBER"),
            skills=skills_list,
            active_tasks_count=len(active_tasks),
            total_complexity_points=points,
            is_overloaded=is_overloaded
        ))
        
    return results

@router.get("/delayed-tasks", response_model=List[DelayedTaskOut])
def get_delayed_tasks(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_member(db, project_id, current_user)
    now = utcnow()
    tasks = db.query(Task).filter(
        Task.project_id == project_id,
        Task.status != TaskStatusEnum.DONE,
        Task.due_date.isnot(None),
        Task.due_date < now
    ).all()
    
    results = []
    for t in tasks:
        days_overdue = (now - t.due_date).days if t.due_date else 0
        # Several people can own one task now; name them all rather than
        # picking one and implying sole responsibility.
        names = [a.user.full_name for a in t.assignees if a.user]
        assignee_name = ", ".join(names) if names else "Unassigned"
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
