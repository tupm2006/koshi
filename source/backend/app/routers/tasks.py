from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.entities import Task, Comment, TaskStatusEnum, User
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut, CommentCreate, CommentOut
from app.security import get_current_user, require_member, require_project_pm
from app.utils.time import utcnow

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.get("", response_model=List[TaskOut])
def list_tasks(
    project_id: int,
    sprint_id: Optional[int] = None,
    status: Optional[TaskStatusEnum] = None,
    assignee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_member(db, project_id, current_user)
    query = db.query(Task).filter(Task.project_id == project_id)
    if sprint_id is not None:
        query = query.filter(Task.sprint_id == sprint_id)
    if status is not None:
        query = query.filter(Task.status == status)
    if assignee_id is not None:
        query = query.filter(Task.assignee_id == assignee_id)
    return query.order_by(Task.id.desc()).all()

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(req: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_member(db, req.project_id, current_user)
    _validate_dependencies(db, req.project_id, req.dependencies)
    task = Task(
        project_id=req.project_id,
        sprint_id=req.sprint_id,
        assignee_id=req.assignee_id,
        title=req.title,
        description=req.description or "",
        status=req.status or TaskStatusEnum.TODO,
        priority=req.priority,
        complexity_points=req.complexity_points or 2,
        due_date=req.due_date,
        blocking_reason=req.blocking_reason
    )
    if req.dependencies:
        task.dependencies = req.dependencies
    if req.acceptance_criteria:
        task.acceptance_criteria = req.acceptance_criteria
        
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def _validate_dependencies(db: Session, project_id: int, dep_ids, exclude_id: int | None = None) -> None:
    """
    Reject dependency ids that do not resolve to a task in the same project.

    Silently storing unresolvable ids is what made the server-side graph useless
    before the ids were unified (F-01); refusing them keeps it honest.
    """
    if not dep_ids:
        return
    unique = set(dep_ids)
    if exclude_id is not None and exclude_id in unique:
        raise HTTPException(status_code=400, detail="A task cannot depend on itself")

    found = {
        t.id for t in db.query(Task.id)
        .filter(Task.id.in_(unique), Task.project_id == project_id)
        .all()
    }
    missing = sorted(unique - found)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown dependency task id(s) for this project: {missing}",
        )


def _get_task_for_member(db: Session, task_id: int, user: User) -> Task:
    """Load a task and assert the caller is a member of its project."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    require_member(db, task.project_id, user)
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = _get_task_for_member(db, task_id, current_user)
    return task

@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, req: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = _get_task_for_member(db, task_id, current_user)
    
    update_data = req.model_dump(exclude_unset=True)
    
    if "dependencies" in update_data:
        deps = update_data.pop("dependencies")
        _validate_dependencies(db, task.project_id, deps, exclude_id=task.id)
        task.dependencies = deps
    if "acceptance_criteria" in update_data:
        task.acceptance_criteria = update_data.pop("acceptance_criteria")
        
    for k, v in update_data.items():
        setattr(task, k, v)
        
    task.updated_at = utcnow()
    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = _get_task_for_member(db, task_id, current_user)
    db.delete(task)
    db.commit()
    return None

@router.post("/{task_id}/cycle-status", response_model=TaskOut)
def cycle_task_status(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = _get_task_for_member(db, task_id, current_user)
        
    cycle = [TaskStatusEnum.TODO, TaskStatusEnum.IN_PROGRESS, TaskStatusEnum.BLOCKED, TaskStatusEnum.DONE]
    current_idx = cycle.index(task.status)
    task.status = cycle[(current_idx + 1) % len(cycle)]
    task.updated_at = utcnow()
    
    db.commit()
    db.refresh(task)
    return task

@router.post("/{task_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(task_id: int, req: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    comment = Comment(
        task_id=task_id,
        author_id=current_user.id,
        content=req.content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
