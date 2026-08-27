from pydantic import BaseModel
from typing import List, Optional

class MemberWorkloadOut(BaseModel):
    user_id: int
    full_name: str
    email: str
    role: str
    skills: List[str]
    active_tasks_count: int
    total_complexity_points: int
    is_overloaded: bool

class DelayedTaskOut(BaseModel):
    task_id: int
    title: str
    status: str
    priority: str
    due_date: str
    days_overdue: int
    assignee_name: str
