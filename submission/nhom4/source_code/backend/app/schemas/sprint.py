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
