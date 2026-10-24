from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from app.database import get_db
from app.models.entities import Sprint, Task, TaskStatusEnum, User
from app.schemas.sprint import (
    SprintCreate, SprintOut, SprintStatsOut, SprintUpdate, SprintComplete,
    BurndownOut, BurndownPoint, VelocityEntry,
)
from app.security import get_current_user, require_member, require_project_pm
from app.utils.time import utcnow

router = APIRouter(prefix="/sprints", tags=["Sprints"])

@router.get("", response_model=List[SprintOut])
def list_sprints(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_member(db, project_id, current_user)
    return db.query(Sprint).filter(Sprint.project_id == project_id).all()

@router.post("", response_model=SprintOut, status_code=status.HTTP_201_CREATED)
def create_sprint(req: SprintCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Planning is a PM activity; ordinary members may read sprints but not create them.
    require_project_pm(db, req.project_id, current_user)
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
    require_member(db, sprint.project_id, current_user)

    tasks = db.query(Task).filter(Task.sprint_id == sprint_id).all()
    total = len(tasks)
    done = len([t for t in tasks if t.status == TaskStatusEnum.DONE])
    in_prog = len([t for t in tasks if t.status == TaskStatusEnum.IN_PROGRESS])
    blocked = len([t for t in tasks if t.status == TaskStatusEnum.BLOCKED])
    todo = len([t for t in tasks if t.status == TaskStatusEnum.TODO])
    
    now = utcnow()
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


# ---------------------------------------------------------------------------
# Scrum lifecycle (DEC-028). PLANNED -> ACTIVE -> COMPLETED, one ACTIVE sprint
# per project. Every transition is a PM action; members read.
# ---------------------------------------------------------------------------

def _get_sprint(db: Session, sprint_id: int) -> Sprint:
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return sprint


def _points(tasks) -> int:
    return sum(t.complexity_points or 0 for t in tasks)


@router.patch("/{sprint_id}", response_model=SprintOut)
def update_sprint(sprint_id: int, req: SprintUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sprint = _get_sprint(db, sprint_id)
    require_project_pm(db, sprint.project_id, current_user)
    if sprint.completed_at is not None:
        raise HTTPException(status_code=400, detail="A completed sprint cannot be edited")
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(sprint, k, v)
    if sprint.end_date < sprint.start_date:
        raise HTTPException(status_code=400, detail="end_date is before start_date")
    db.commit()
    db.refresh(sprint)
    return sprint


@router.post("/{sprint_id}/start", response_model=SprintOut)
def start_sprint(sprint_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sprint = _get_sprint(db, sprint_id)
    require_project_pm(db, sprint.project_id, current_user)
    if sprint.completed_at is not None:
        raise HTTPException(status_code=400, detail="A completed sprint cannot be restarted")
    other = db.query(Sprint).filter(
        Sprint.project_id == sprint.project_id,
        Sprint.id != sprint.id,
        Sprint.is_active == True,  # noqa: E712
        Sprint.completed_at.is_(None),
    ).first()
    if other:
        raise HTTPException(status_code=409, detail=f"Sprint '{other.name}' is already active; complete it first")
    sprint.is_active = True
    # The commitment is what was in the sprint when it started; adding work
    # later is scope creep, and velocity should show it rather than hide it.
    sprint.committed_points = _points(db.query(Task).filter(Task.sprint_id == sprint.id).all())
    db.commit()
    db.refresh(sprint)
    return sprint


@router.post("/{sprint_id}/complete", response_model=SprintOut)
def complete_sprint(sprint_id: int, req: SprintComplete, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sprint = _get_sprint(db, sprint_id)
    require_project_pm(db, sprint.project_id, current_user)
    if sprint.completed_at is not None:
        raise HTTPException(status_code=400, detail="Sprint is already completed")
    target = None
    if req.move_unfinished_to is not None:
        target = _get_sprint(db, req.move_unfinished_to)
        # Same project only — otherwise this moves tasks into a project the
        # caller may not even belong to.
        if target.project_id != sprint.project_id or target.id == sprint.id or target.completed_at is not None:
            raise HTTPException(status_code=400, detail="Invalid target sprint")
    for t in db.query(Task).filter(Task.sprint_id == sprint.id, Task.status != TaskStatusEnum.DONE).all():
        t.sprint_id = target.id if target else None
        t.updated_at = utcnow()
    if sprint.committed_points is None:
        sprint.committed_points = 0
    sprint.is_active = False
    sprint.completed_at = utcnow()
    db.commit()
    db.refresh(sprint)
    return sprint


@router.delete("/{sprint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sprint(sprint_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sprint = _get_sprint(db, sprint_id)
    require_project_pm(db, sprint.project_id, current_user)
    # Deleting a sprint never deletes work: its tasks return to the backlog.
    for t in db.query(Task).filter(Task.sprint_id == sprint.id).all():
        t.sprint_id = None
    db.delete(sprint)
    db.commit()
    return None


@router.get("/{sprint_id}/burndown", response_model=BurndownOut)
def sprint_burndown(sprint_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sprint = _get_sprint(db, sprint_id)
    require_member(db, sprint.project_id, current_user)
    tasks = db.query(Task).filter(Task.sprint_id == sprint.id).all()
    total = _points(tasks)
    start = sprint.start_date.date()
    end = max(sprint.end_date.date(), start)
    today = (sprint.completed_at or utcnow()).date()
    n = (end - start).days
    days = []
    for i in range(n + 1):
        d = start + timedelta(days=i)
        ideal = round(total - total * (i / n), 1) if n else 0.0
        remaining = None
        if d <= today:
            remaining = total - sum(
                t.complexity_points or 0 for t in tasks
                if t.status == TaskStatusEnum.DONE and t.completed_at and t.completed_at.date() <= d
            )
        days.append(BurndownPoint(date=d.isoformat(), ideal=ideal, remaining=remaining))
    return BurndownOut(sprint_id=sprint.id, total_points=total, days=days)


@router.get("/velocity/history", response_model=List[VelocityEntry])
def velocity(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_member(db, project_id, current_user)
    sprints = db.query(Sprint).filter(
        Sprint.project_id == project_id, Sprint.completed_at.isnot(None)
    ).order_by(Sprint.completed_at).all()
    out = []
    for s in sprints:
        done = db.query(Task).filter(Task.sprint_id == s.id, Task.status == TaskStatusEnum.DONE).all()
        out.append(VelocityEntry(
            sprint_id=s.id, sprint_name=s.name,
            committed_points=s.committed_points or 0, completed_points=_points(done),
        ))
    return out
