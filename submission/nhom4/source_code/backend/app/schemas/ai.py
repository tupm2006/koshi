from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class MeetingNotesRequest(BaseModel):
    notes: str

class ActionItemOut(BaseModel):
    title: str
    assignee_name: Optional[str] = "Unassigned"
    priority: Optional[str] = "MEDIUM"
    deadline: Optional[str] = "Next Sprint"

class MeetingMinutesResponse(BaseModel):
    status: str = "success"
    main_topics: List[str]
    action_items: List[ActionItemOut]
    key_decisions: List[str]

class AssignmentRecommendRequest(BaseModel):
    title: str
    description: Optional[str] = ""

class AssignmentRecommendation(BaseModel):
    recommended_user_id: Optional[int] = None
    recommended_name: str
    rationale: str
    risk_assessment: Optional[str] = None

class AssignmentRecommendResponse(BaseModel):
    status: str = "success"
    recommendation: AssignmentRecommendation

class WeeklySummaryResponse(BaseModel):
    status: str = "success"
    project_id: int
    summary: str

class DecomposedSubtask(BaseModel):
    title: str
    description: str
    priority: str
    complexity: str
    acceptanceCriteria: List[str]
    dependsOnTitles: Optional[List[str]] = []

class AIDecomposeRequest(BaseModel):
    goal: str

class AIDecomposeResponse(BaseModel):
    status: str = "success"
    goal: str
    rationale: str
    subtasks: List[DecomposedSubtask]
