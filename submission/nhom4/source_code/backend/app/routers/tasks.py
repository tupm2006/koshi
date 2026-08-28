import json
import re
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Task, TaskDependency, Comment, User, TaskStatusEnum, ProjectMemberRoleEnum
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut, TaskCycleStatusOut, CommentCreate, CommentOut
from app.security import get_current_user, verify_project_membership

router = APIRouter(prefix="/tasks", tags=["Tasks"])

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
    return db.query(Task).filter(Task.project_id == project_id).order_by(Task.id.asc()).all()

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
        status=payload.status or TaskStatusEnum.TODO,
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

    # Sync relational dependencies table
    if payload.dependencies:
        raw_ids = [int(re.sub(r'\D', '', str(d))) for d in payload.dependencies if re.sub(r'\D', '', str(d))]
        sync_dependencies(task.id, raw_ids, db)

    return task

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
    return task

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
    verify_project_membership(task.project_id, current_user.id, db)

    update_data = payload.model_dump(exclude_unset=True) if hasattr(payload, 'model_dump') else payload.dict(exclude_unset=True)
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
    return task

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

    # Clean up relational dependency records
    db.query(TaskDependency).filter((TaskDependency.task_id == task_id) | (TaskDependency.depends_on_id == task_id)).delete()

    # Clean up any sibling task referencing the deleted task ID in its dependencies_json
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

    cycle = [TaskStatusEnum.TODO, TaskStatusEnum.IN_PROGRESS, TaskStatusEnum.BLOCKED, TaskStatusEnum.DONE]
    current_idx = cycle.index(task.status) if task.status in cycle else 0
    next_status = cycle[(current_idx + 1) % len(cycle)]

    task.status = next_status
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    return {"id": task.id, "status": task.status, "updated_at": task.updated_at}

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

    comment = Comment(
        task_id=task_id,
        author_id=current_user.id,
        content=payload.content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
