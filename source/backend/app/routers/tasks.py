import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.entities import (
    Sprint, TaskEvent,
    Attachment, Comment, CommentKindEnum, ProjectMember, Task, TaskAssignee,
    TaskStatusEnum, User,
)
from app.schemas.auth import UserOut
from app.schemas.task import (
    AttachmentOut, TaskCreate, TaskUpdate, TaskOut, CommentCreate, CommentOut,
    TaskEventOut,
)
from app.security import (
    get_current_user, get_membership, require_member, require_project_pm,
)
from app.models.entities import NotificationKindEnum
from app.services.mentions import parse_mention_ids
from app.services.notify import notify
from app.services.uploads import path_for, save_upload
from app.utils.time import utcnow

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _task_out(task: Task) -> TaskOut:
    """
    Shape a Task for the wire.

    Needed because `assignees` is a list of TaskAssignee join rows, and the
    contract promises a list of users — returning the ORM object directly would
    serialise the join table.
    """
    return TaskOut(
        id=task.id,
        key=task.key,
        project_id=task.project_id,
        sprint_id=task.sprint_id,
        # The join rows carry the users; the contract promises the users.
        assignees=[
            UserOut.model_validate(a.user, from_attributes=True)
            for a in task.assignees
            if a.user is not None
        ],
        title=task.title,
        description=task.description or "",
        status=task.status,
        priority=task.priority,
        complexity_points=task.complexity_points,
        due_date=task.due_date,
        blocking_reason=task.blocking_reason,
        completed_at=task.completed_at,
        dependencies=task.dependencies,
        acceptance_criteria=task.acceptance_criteria,
        created_at=task.created_at,
        updated_at=task.updated_at,
        comments=[_comment_out(c) for c in task.comments],
    )


def _resolve_mentions(db: Session, comment: Comment) -> list:
    """
    Turn the ids in the body into users.

    Order follows the text. A mention of somebody since removed from the project
    simply does not resolve — the token stays in the content and the client
    falls back to the name captured at write time.
    """
    ids = parse_mention_ids(comment.content)
    if not ids:
        return []
    found = {u.id: u for u in db.query(User).filter(User.id.in_(ids))}
    return [
        UserOut.model_validate(found[i], from_attributes=True) for i in ids if i in found
    ]


def _comment_out(comment: Comment, db: Session | None = None) -> CommentOut:
    out = CommentOut(
        id=comment.id,
        task_id=comment.task_id,
        author_id=comment.author_id,
        author=UserOut.model_validate(comment.author, from_attributes=True) if comment.author else None,
        content=comment.content,
        kind=comment.kind,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
    )
    if db is not None:
        out.mentions = _resolve_mentions(db, comment)
    out.attachments = [
        AttachmentOut(
            id=a.id,
            filename=a.filename,
            content_type=a.content_type,
            size_bytes=a.size_bytes,
            url=f"/api/tasks/attachments/{a.id}",
        )
        for a in comment.attachments
    ]
    return out


def _set_assignees(db: Session, task: Task, user_ids: list[int]) -> None:
    """
    Replace a task's assignees.

    Every id must be an accepted member of the task's project. Assigning work to
    somebody who cannot open the project produces a task nobody receives, and
    `get_membership` already excludes people who were merely invited.
    """
    wanted = list(dict.fromkeys(user_ids))  # de-duplicate, keep order

    if wanted:
        members = {
            m.user_id
            for m in db.query(ProjectMember).filter(
                ProjectMember.project_id == task.project_id,
                ProjectMember.user_id.in_(wanted),
            )
            if m.is_active
        }
        outsiders = [uid for uid in wanted if uid not in members]
        if outsiders:
            raise HTTPException(
                status_code=400,
                detail=f"Not accepted members of this project: {outsiders}",
            )

    task.assignees.clear()
    db.flush()
    for uid in wanted:
        db.add(TaskAssignee(task_id=task.id, user_id=uid))

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
        query = query.filter(
            Task.assignees.any(TaskAssignee.user_id == assignee_id)
        )
    return [_task_out(t) for t in query.order_by(Task.id.desc()).all()]

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(req: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_member(db, req.project_id, current_user)
    _validate_dependencies(db, req.project_id, req.dependencies)
    _validate_sprint(db, req.project_id, req.sprint_id)
    task = Task(
        project_id=req.project_id,
        sprint_id=req.sprint_id,
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
        
    _stamp_completion(task)
    db.add(task)
    db.flush()
    if req.assignee_ids:
        _set_assignees(db, task, req.assignee_ids)
    db.add(TaskEvent(task_id=task.id, actor_id=current_user.id, field="created", new_value=task.title))
    db.commit()
    db.refresh(task)
    return _task_out(task)

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


def _validate_sprint(db: Session, project_id: int, sprint_id) -> None:
    """A task may only be planned into a sprint of its own project."""
    if sprint_id is None:
        return
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if sprint is None or sprint.project_id != project_id:
        raise HTTPException(status_code=400, detail="Unknown sprint for this project")
    if sprint.completed_at is not None:
        raise HTTPException(status_code=400, detail="Cannot add work to a completed sprint")


def _stamp_completion(task: Task) -> None:
    """Keep completed_at in step with status; burndown depends on it."""
    if task.status == TaskStatusEnum.DONE:
        if task.completed_at is None:
            task.completed_at = utcnow()
    else:
        task.completed_at = None



# --- history (migration 0009) ----------------------------------------------

_TRACKED = ("title", "status", "priority", "complexity_points", "due_date", "blocking_reason", "sprint_id", "description")


def _display(db: Session, field: str, value) -> "str | None":
    if value is None or value == "":
        return None
    if field == "sprint_id":
        sp = db.query(Sprint).filter(Sprint.id == value).first()
        return sp.name if sp else f"#{value}"
    if field == "due_date":
        return value.date().isoformat() if hasattr(value, "date") else str(value)[:10]
    if hasattr(value, "value"):
        return str(value.value)
    text = str(value)
    return text if len(text) <= 300 else text[:297] + "..."


def _snapshot(db: Session, task: Task) -> dict:
    snap = {f: _display(db, f, getattr(task, f)) for f in _TRACKED}
    snap["assignees"] = ", ".join(sorted(a.user.full_name for a in task.assignees if a.user)) or None
    return snap


def _record_changes(db: Session, task: Task, before: dict, actor: User) -> None:
    after = _snapshot(db, task)
    for field, old in before.items():
        new = after.get(field)
        if old != new:
            db.add(TaskEvent(task_id=task.id, actor_id=actor.id, field=field, old_value=old, new_value=new))


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
    return _task_out(task)

@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, req: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = _get_task_for_member(db, task_id, current_user)
    before = _snapshot(db, task)

    update_data = req.model_dump(exclude_unset=True)
    
    if "dependencies" in update_data:
        deps = update_data.pop("dependencies")
        _validate_dependencies(db, task.project_id, deps, exclude_id=task.id)
        task.dependencies = deps
    if "acceptance_criteria" in update_data:
        task.acceptance_criteria = update_data.pop("acceptance_criteria")
    if "assignee_ids" in update_data:
        # exclude_unset means this key is present only when the client sent it,
        # so [] genuinely means "unassign everybody" and an untouched PATCH
        # leaves the roster alone.
        _set_assignees(db, task, update_data.pop("assignee_ids") or [])

    if "sprint_id" in update_data:
        _validate_sprint(db, task.project_id, update_data["sprint_id"])

    for k, v in update_data.items():
        setattr(task, k, v)
    _stamp_completion(task)

    task.updated_at = utcnow()
    db.flush()
    db.refresh(task)
    _record_changes(db, task, before, current_user)
    db.commit()
    db.refresh(task)
    return _task_out(task)

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
    old_status = task.status.value
    task.status = cycle[(current_idx + 1) % len(cycle)]
    _stamp_completion(task)
    task.updated_at = utcnow()
    db.add(TaskEvent(task_id=task.id, actor_id=current_user.id, field="status", old_value=old_status, new_value=task.status.value))

    db.commit()
    db.refresh(task)
    return _task_out(task)

@router.get("/{task_id}/history", response_model=List[TaskEventOut])
def task_history(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _get_task_for_member(db, task_id, current_user)
    return db.query(TaskEvent).filter(TaskEvent.task_id == task_id).order_by(TaskEvent.id.desc()).limit(200).all()


@router.get("/{task_id}/comments", response_model=List[CommentOut])
def list_comments(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Oldest first — a thread reads forwards."""
    task = _get_task_for_member(db, task_id, current_user)
    comments = (
        db.query(Comment)
        .filter(Comment.task_id == task.id)
        .order_by(Comment.id.asc())
        .all()
    )
    return [_comment_out(c, db) for c in comments]


@router.post("/{task_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(task_id: int, req: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # F-40: this route used to check only that the task existed, so any
    # authenticated user could post to any task in any project they had never
    # been invited to. Dormant only because no UI called it.
    task = _get_task_for_member(db, task_id, current_user)

    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="A comment cannot be empty")

    # You may only tag people who can actually read the thread. Otherwise a
    # mention is a notification nobody receives, and it confirms that a user id
    # exists to somebody outside the project.
    mentioned = parse_mention_ids(content)
    if mentioned:
        members = {
            m.user_id
            for m in db.query(ProjectMember).filter(
                ProjectMember.project_id == task.project_id,
                ProjectMember.user_id.in_(mentioned),
            )
            if m.is_active
        }
        strangers = [uid for uid in mentioned if uid not in members]
        if strangers:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mention people who are not in this project: {strangers}",
            )

    parent_id = None
    if req.parent_id is not None:
        parent = db.query(Comment).filter(Comment.id == req.parent_id).first()
        # Same task, or the reply would appear under a thread its author never
        # saw — and would leak text across projects.
        if parent is None or parent.task_id != task.id:
            raise HTTPException(status_code=404, detail="Reply target not found on this task")
        # Flatten: replying to a reply attaches to its parent. One level keeps
        # the thread readable in a narrow panel, and re-parenting is kinder than
        # refusing a button the user was legitimately offered.
        parent_id = parent.parent_id or parent.id

    comment = Comment(
        task_id=task.id,
        author_id=current_user.id,
        content=content,
        kind=req.kind,
        parent_id=parent_id,
    )
    db.add(comment)
    db.flush()  # the notifications need comment.id

    # A mention is more specific than "somebody replied", so it wins when one
    # person is both. `notify` drops the author either way — being told what you
    # just did is noise.
    notify(
        db,
        recipients=mentioned,
        kind=NotificationKindEnum.MENTION,
        actor_id=current_user.id,
        project_id=task.project_id,
        task_id=task.id,
        comment_id=comment.id,
    )
    if parent_id is not None:
        parent_author = db.query(Comment).filter(Comment.id == parent_id).first()
        if parent_author is not None:
            notify(
                db,
                recipients=[parent_author.author_id],
                kind=NotificationKindEnum.REPLY,
                actor_id=current_user.id,
                project_id=task.project_id,
                task_id=task.id,
                comment_id=comment.id,
                skip_user_ids=mentioned,
            )

    # One commit: the comment and its notifications land together, so the feed
    # can never reference something that was rolled back.
    db.commit()
    db.refresh(comment)
    return _comment_out(comment, db)


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

@router.post(
    "/comments/{comment_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    comment_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Attach a file to a comment.

    Membership is checked before a single byte is written — an outsider must not
    be able to fill the disk of a project they cannot see.
    """
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    task = _get_task_for_member(db, comment.task_id, current_user)

    # Only the author may add to their own entry. Otherwise anybody in the
    # project could staple files onto somebody else's evidence.
    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You can only attach files to your own comment"
        )

    stored_name, content_type, size = await save_upload(file)

    attachment = Attachment(
        comment_id=comment.id,
        uploader_id=current_user.id,
        filename=os.path.basename(file.filename or "upload"),
        stored_name=stored_name,
        content_type=content_type,
        size_bytes=size,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return AttachmentOut(
        id=attachment.id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        url=f"/api/tasks/attachments/{attachment.id}",
    )


@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Serve an attachment's bytes.

    Membership is re-checked on every fetch: knowing the URL is not permission,
    and the id is a small integer that anybody could guess.
    """
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    comment = attachment.comment
    if comment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    _get_task_for_member(db, comment.task_id, current_user)

    path = path_for(attachment.stored_name)
    if not os.path.exists(path):
        # The row outlived the file. Say so rather than raising a 500.
        raise HTTPException(status_code=410, detail="Attachment file is no longer stored")

    return FileResponse(
        path,
        # Our allowlisted type, never one echoed from the upload.
        media_type=attachment.content_type,
        filename=attachment.filename,
        headers={
            # Stop a browser from re-interpreting an "image" as HTML and running
            # script on this origin.
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )
