import json
import re
from typing import List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Task, TaskDependency, Comment, User, TaskStatusEnum, ProjectMemberRoleEnum, RoleEnum
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskOut,
    TaskCycleStatusOut,
    PriorityRequestCreate,
    CommentCreate,
    CommentOut
)
from app.security import get_current_user, verify_project_membership

router = APIRouter(prefix="/tasks", tags=["Tasks"])

def compute_task_out(task: Task) -> dict:
    now = datetime.utcnow()
    is_overdue = False
    slip_days = 0
    
    status_str = task.status.value if hasattr(task.status, 'value') else str(task.status)
    if task.due_date and status_str != "DONE":
        if task.due_date < now:
            is_overdue = True
            slip_days = max(0, int((now - task.due_date).total_seconds() // 86400))

    deps = []
    if task.dependencies_json:
        try:
            deps = json.loads(task.dependencies_json)
        except Exception:
            deps = []

    criteria = []
    if task.acceptance_criteria_json:
        try:
            criteria = json.loads(task.acceptance_criteria_json)
        except Exception:
            criteria = []

    priority_str = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)

    return {
        "id": task.id,
        "project_id": task.project_id,
        "sprint_id": task.sprint_id,
        "assignee_id": task.assignee_id,
        "assignee": task.assignee,
        "title": task.title,
        "description": task.description or "",
        "status": status_str,
        "priority": priority_str,
        "requested_priority": task.requested_priority,
        "priority_request_reason": task.priority_request_reason,
        "priority_requested_by_id": task.priority_requested_by_id,
        "complexity_points": task.complexity_points,
        "due_date": task.due_date,
        "is_overdue": is_overdue,
        "slip_days": slip_days,
        "blocking_reason": task.blocking_reason,
        "dependencies": deps,
        "acceptance_criteria": criteria,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "comments": task.comments or []
    }

def sync_dependencies(task_id: int, dep_ids: List[int], db: Session):
    db.query(TaskDependency).filter(TaskDependency.task_id == task_id).delete()
    for dep_id in dep_ids:
        if dep_id != task_id:
            db.add(TaskDependency(task_id=task_id, depends_on_id=dep_id))
    db.commit()

@router.get("", response_model=List[TaskOut])
def list_tasks(
    project_id: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_project_membership(project_id, current_user.id, db)
    tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.id.asc()).all()
    return [compute_task_out(t) for t in tasks]

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_project_membership(payload.project_id, current_user.id, db)
    task = Task(
        project_id=payload.project_id,
        sprint_id=payload.sprint_id,
        assignee_id=payload.assignee_id,
        title=payload.title,
        description=payload.description or "",
        status=payload.status or "TODO",
        priority=payload.priority or "MEDIUM",
        complexity_points=payload.complexity_points or 2,
        due_date=payload.due_date,
        blocking_reason=payload.blocking_reason,
        dependencies_json=json.dumps(payload.dependencies or []),
        acceptance_criteria_json=json.dumps(payload.acceptance_criteria or [])
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    if payload.dependencies:
        raw_ids = [int(re.sub(r'\D', '', str(d))) for d in payload.dependencies if re.sub(r'\D', '', str(d))]
        sync_dependencies(task.id, raw_ids, db)

    return compute_task_out(task)

@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    verify_project_membership(task.project_id, current_user.id, db)
    return compute_task_out(task)

@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    role = verify_project_membership(task.project_id, current_user.id, db)
    update_data = payload.model_dump(exclude_unset=True) if hasattr(payload, 'model_dump') else payload.dict(exclude_unset=True)

    # Priority Mutation Governance: Only PM or OWNER can directly alter priority
    if "priority" in update_data and update_data["priority"] is not None:
        current_priority = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
        if update_data["priority"] != current_priority:
            role_str = role.value if hasattr(role, 'value') else str(role)
            user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
            if role_str not in ["PM", "OWNER"] and user_role_str not in ["PM", "OWNER"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Members cannot directly change priority. Please submit a priority proposal."
                )

    if "dependencies" in update_data and update_data["dependencies"] is not None:
        deps = update_data.pop("dependencies")
        task.dependencies_json = json.dumps(deps)
        raw_ids = [int(re.sub(r'\D', '', str(d))) for d in deps if re.sub(r'\D', '', str(d))]
        sync_dependencies(task.id, raw_ids, db)

    if "acceptance_criteria" in update_data and update_data["acceptance_criteria"] is not None:
        task.acceptance_criteria_json = json.dumps(update_data.pop("acceptance_criteria"))

    for field, value in update_data.items():
        setattr(task, field, value)

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return compute_task_out(task)

@router.post("/{task_id}/request-priority", response_model=TaskOut)
def request_priority_change(
    task_id: int,
    payload: PriorityRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    verify_project_membership(task.project_id, current_user.id, db)

    task.requested_priority = payload.requested_priority
    task.priority_request_reason = payload.reason or ""
    task.priority_requested_by_id = current_user.id
    task.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(task)
    return compute_task_out(task)

@router.post("/{task_id}/approve-priority", response_model=TaskOut)
def approve_priority_change(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    role = verify_project_membership(task.project_id, current_user.id, db)
    role_str = role.value if hasattr(role, 'value') else str(role)
    user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if role_str not in ["PM", "OWNER"] and user_role_str not in ["PM", "OWNER"]:
        raise HTTPException(status_code=403, detail="Only PM or Owner can approve priority changes.")

    if task.requested_priority:
        task.priority = task.requested_priority
        task.requested_priority = None
        task.priority_request_reason = None
        task.priority_requested_by_id = None
        task.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(task)

    return compute_task_out(task)

@router.post("/{task_id}/reject-priority", response_model=TaskOut)
def reject_priority_change(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    role = verify_project_membership(task.project_id, current_user.id, db)
    role_str = role.value if hasattr(role, 'value') else str(role)
    user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if role_str not in ["PM", "OWNER"] and user_role_str not in ["PM", "OWNER"]:
        raise HTTPException(status_code=403, detail="Only PM or Owner can reject priority changes.")

    task.requested_priority = None
    task.priority_request_reason = None
    task.priority_requested_by_id = None
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return compute_task_out(task)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    verify_project_membership(task.project_id, current_user.id, db)

    db.query(TaskDependency).filter((TaskDependency.task_id == task_id) | (TaskDependency.depends_on_id == task_id)).delete()

    sibling_tasks = db.query(Task).filter(Task.project_id == task.project_id).all()
    for sibling in sibling_tasks:
        if sibling.id == task_id:
            continue
        deps = sibling.dependencies
        if task_id in deps or str(task_id) in deps:
            sibling.dependencies = [d for d in deps if d != task_id and str(d) != str(task_id)]

    db.delete(task)
    db.commit()
    return None

@router.post("/{task_id}/cycle-status", response_model=TaskCycleStatusOut)
def cycle_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    verify_project_membership(task.project_id, current_user.id, db)

    status_str = task.status.value if hasattr(task.status, 'value') else str(task.status)
    cycle = ["TODO", "IN_PROGRESS", "BLOCKED", "DONE"]
    current_idx = cycle.index(status_str) if status_str in cycle else 0
    next_status = cycle[(current_idx + 1) % len(cycle)]
    
    task.status = next_status
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return {"id": task.id, "status": next_status, "updated_at": task.updated_at}

@router.post("/{task_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    task_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    verify_project_membership(task.project_id, current_user.id, db)

    comment = Comment(task_id=task_id, author_id=current_user.id, content=payload.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
