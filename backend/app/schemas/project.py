from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = ""

class ProjectCreate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    id: int
    owner_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
