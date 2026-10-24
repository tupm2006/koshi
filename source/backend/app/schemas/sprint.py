from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SprintBase(BaseModel):
    name: str
    goal: Optional[str] = ""
    start_date: datetime
    end_date: datetime
    is_active: Optional[bool] = True

class SprintCreate(SprintBase):
    project_id: int

class SprintOut(SprintBase):
    id: int
    project_id: int
    # PLANNED | ACTIVE | COMPLETED — derived from is_active/completed_at.
    state: str = "PLANNED"
    completed_at: Optional[datetime] = None
    committed_points: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SprintStatsOut(BaseModel):
    sprint_id: int
    sprint_name: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    todo_tasks: int
    completion_rate_pct: float
    delayed_tasks_count: int


class SprintUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SprintComplete(BaseModel):
    # Where unfinished work goes. None = back to the product backlog.
    move_unfinished_to: Optional[int] = None


class BurndownPoint(BaseModel):
    date: str          # YYYY-MM-DD
    ideal: float
    remaining: Optional[int] = None   # None for days that have not happened yet


class BurndownOut(BaseModel):
    sprint_id: int
    total_points: int
    days: List[BurndownPoint]


class VelocityEntry(BaseModel):
    sprint_id: int
    sprint_name: str
    committed_points: int
    completed_points: int
