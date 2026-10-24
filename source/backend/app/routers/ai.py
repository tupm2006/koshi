from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Task, TaskAssignee, User, Project, ProjectMember, TaskStatusEnum, Sprint
from app.schemas.ai import (
    SprintRetroResponse,
    MeetingNotesRequest, MeetingMinutesResponse,
    AssignmentRecommendRequest, AssignmentRecommendResponse, AssignmentRecommendation,
    WeeklySummaryResponse, AIDecomposeRequest, AIDecomposeResponse, DecomposedSubtask
)
from app.services.ai_service import AIService, answer_language
from app.utils.time import utcnow
from app.security import get_current_user, require_member

async def _answer_in_ui_language(request: Request) -> None:
    """Async on purpose: a sync dependency runs in a worker thread, where the
    contextvar would be set in a copy of the context the endpoint never sees."""
    lang = (request.headers.get("accept-language") or "").split(",")[0].strip().lower()[:2]
    answer_language.set(lang if lang in ("en", "vi") else None)


router = APIRouter(prefix="/ai", tags=["AI Services"], dependencies=[Depends(_answer_in_ui_language)])

@router.post("/weekly-summary", response_model=WeeklySummaryResponse)
async def generate_weekly_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mandated Feature A: Weekly project progress summary based on task/sprint data.
    """
    require_member(db, project_id, current_user)
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    if not tasks:
        # Provide sample context if empty
        task_payload = [
            {"id": "TSK-1", "title": "Setup repository & architecture", "status": "DONE", "priority": "HIGH", "assignee": current_user.full_name},
            {"id": "TSK-2", "title": "Implement core backend API", "status": "IN_PROGRESS", "priority": "CRITICAL", "assignee": current_user.full_name},
            {"id": "TSK-3", "title": "Fix database migration lock", "status": "BLOCKED", "priority": "HIGH", "assignee": current_user.full_name, "blocking_reason": "Waiting for schema lock resolution"}
        ]
    else:
        task_payload = [
            {
                "id": f"TSK-{t.id}",
                "title": t.title,
                "status": t.status.value,
                "priority": t.priority.value,
                "assignee": ", ".join(a.user.full_name for a in t.assignees if a.user) or "Unassigned",
                "blocking_reason": t.blocking_reason,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "complexity": t.complexity_points
            }
            for t in tasks
        ]

    summary_text = await AIService.generate_weekly_summary(task_payload)
    return WeeklySummaryResponse(project_id=project_id, summary=summary_text)

@router.post("/meeting-minutes", response_model=MeetingMinutesResponse)
async def extract_meeting_minutes(
    req: MeetingNotesRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Mandated Feature B: Meeting minutes & action item generator from raw meeting transcripts.
    """
    if not req.notes.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting notes cannot be empty"
        )
        
    result = await AIService.extract_meeting_minutes(req.notes)
    return MeetingMinutesResponse(
        status="success",
        main_topics=result.get("main_topics", []),
        action_items=result.get("action_items", []),
        key_decisions=result.get("key_decisions", [])
    )

@router.post("/recommend-assignment", response_model=AssignmentRecommendResponse)
async def recommend_assignment(
    req: AssignmentRecommendRequest,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mandated Feature C: Skill- and workload-based task assignment recommendation engine.
    """
    require_member(db, project_id, current_user)

    # Candidates are the members of *this* project, not every user in the system.
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    # Accepted members only: an invitee cannot be assigned (the task router
    # refuses it), so recommending one is a suggestion that cannot be applied.
    users = [m.user for m in members if m.user is not None and m.is_active]
    workload_payload = []

    for u in users:
        active_tasks = db.query(Task).filter(
            Task.assignees.any(TaskAssignee.user_id == u.id),
            Task.project_id == project_id,
            Task.status.in_([TaskStatusEnum.TODO, TaskStatusEnum.IN_PROGRESS, TaskStatusEnum.BLOCKED])
        ).all()
        points = sum(t.complexity_points for t in active_tasks)
        skills_list = [s.strip() for s in (u.skills or "").split(",") if s.strip()]
        
        workload_payload.append({
            "user_id": u.id,
            "name": u.full_name,
            "skills": skills_list,
            "active_tasks_count": len(active_tasks),
            "total_complexity_points": points
        })
        
    res = await AIService.recommend_task_assignment(req.title, req.description or "", workload_payload)
    
    rec_obj = AssignmentRecommendation(
        recommended_user_id=res.get("recommended_user_id", users[0].id if users else None),
        recommended_name=res.get("recommended_name", users[0].full_name if users else "Team Member"),
        rationale=res.get("rationale", "Thành viên có kỹ năng phù hợp và khối lượng công việc hiện tại tối ưu."),
        risk_assessment=res.get("risk_assessment", "Khối lượng công việc an toàn, không có nguy cơ trễ hạn.")
    )
    return AssignmentRecommendResponse(status="success", recommendation=rec_obj)

@router.post("/decompose", response_model=AIDecomposeResponse)
async def decompose_goal(
    req: AIDecomposeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Deterministic subtask breakdown with DAG dependencies.
    """
    goal = req.goal.strip()
    if not goal:
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    generated = await AIService.decompose_goal(goal)
    if generated is not None:
        return AIDecomposeResponse(
            status="success", goal=goal, rationale=generated["rationale"],
            subtasks=[DecomposedSubtask(**t) for t in generated["subtasks"]],
        )

    # Deterministic template: no model reachable, or its answer was unusable.
    subtasks = [
        DecomposedSubtask(
            title=f"Phân tích yêu cầu & thiết kế kiến trúc: {goal[:30]}",
            description="Lập tài liệu đặc tả và thiết kế schema dữ liệu tương ứng.",
            priority="HIGH",
            complexity="M",
            acceptance_criteria=["Có tài liệu SRS/URD", "Được phê duyệt bởi PM"],
            depends_on_titles=[]
        ),
        DecomposedSubtask(
            title=f"Phát triển backend & API endpoints: {goal[:30]}",
            description="Hiện thực hóa các REST endpoint và xử lý logic nghiệp vụ.",
            priority="CRITICAL",
            complexity="L",
            acceptance_criteria=["Unit test pass > 90%", "Tích hợp database đầy đủ"],
            depends_on_titles=[f"Phân tích yêu cầu & thiết kế kiến trúc: {goal[:30]}"]
        ),
        DecomposedSubtask(
            title=f"Xây dựng giao diện người dùng & tích hợp: {goal[:30]}",
            description="Kết nối giao diện với API backend, xử lý trạng thái tải và lỗi.",
            priority="HIGH",
            complexity="M",
            acceptance_criteria=["Giao diện phản hồi <50ms", "Tương thích responsive mobile/desktop"],
            depends_on_titles=[f"Phát triển backend & API endpoints: {goal[:30]}"]
        )
    ]
    return AIDecomposeResponse(
        status="success",
        goal=goal,
        rationale=f"Đã phân tích mục tiêu '{goal}' thành 3 nhiệm vụ tuần tự với quan hệ phụ thuộc DAG.",
        subtasks=subtasks
    )


@router.post("/sprint-retro", response_model=SprintRetroResponse)
async def sprint_retro(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Feature E: AI retrospective for a sprint, grounded in its own numbers."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    require_member(db, sprint.project_id, current_user)

    tasks = db.query(Task).filter(Task.sprint_id == sprint.id).all()
    done = [t for t in tasks if t.status == TaskStatusEnum.DONE]
    now = utcnow()
    end = sprint.completed_at or now
    total = sum(t.complexity_points or 0 for t in tasks)
    stats = {
        "sprint": sprint.name,
        "goal": sprint.goal,
        "state": sprint.state,
        "committed_points": sprint.committed_points if sprint.committed_points is not None else total,
        "completed_points": sum(t.complexity_points or 0 for t in done),
        "added_points": max(total - (sprint.committed_points or total), 0) if sprint.state == "ACTIVE" else 0,
        "done_count": len(done),
        "done": [t.title for t in done][:15],
        "not_done": [f"{t.title} ({t.status.value})" for t in tasks if t.status != TaskStatusEnum.DONE][:15],
        "blocked": [f"{t.title}: {t.blocking_reason or 'không rõ lý do'}" for t in tasks if t.status == TaskStatusEnum.BLOCKED],
        "overdue": len([t for t in tasks if t.status != TaskStatusEnum.DONE and t.due_date and t.due_date < end]),
        "members": sorted({a.user.full_name for t in tasks for a in t.assignees if a.user}),
    }
    out = await AIService.sprint_retrospective(stats)
    return SprintRetroResponse(sprint_id=sprint.id, **out)
