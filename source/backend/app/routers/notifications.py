from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import MembershipStatusEnum, Notification, ProjectMember, User
from app.schemas.auth import UserOut
from app.schemas.notification import NotificationOut, UnreadCountOut
from app.security import get_current_user
from app.utils.time import utcnow

router = APIRouter(prefix="/notifications", tags=["Notifications"])

#: Enough to fill a page; the feed is a recent history, not an archive.
MAX_LIMIT = 100
EXCERPT_CHARS = 140


def _visible(db: Session, n: Notification, user: User) -> bool:
    """
    Should this entry still be shown?

    Membership is re-checked on read, not only when the notification was
    created: somebody can be removed from a project in between, and a feed that
    kept showing them a project's task titles would be a slow leak.
    """
    if n.project_id is None:
        return True
    membership = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == n.project_id,
            ProjectMember.user_id == user.id,
            ProjectMember.status == MembershipStatusEnum.ACCEPTED,
        )
        .first()
    )
    return membership is not None


def _out(n: Notification) -> NotificationOut:
    excerpt = None
    if n.comment is not None:
        text = (n.comment.content or "").strip()
        excerpt = text[:EXCERPT_CHARS] + ("…" if len(text) > EXCERPT_CHARS else "")

    return NotificationOut(
        id=n.id,
        kind=n.kind,
        actor=UserOut.model_validate(n.actor, from_attributes=True) if n.actor else None,
        project_id=n.project_id,
        project_name=n.project.name if n.project else None,
        task_id=n.task_id,
        task_key=n.task.key if n.task else None,
        task_title=n.task.title if n.task else None,
        comment_id=n.comment_id,
        excerpt=excerpt,
        read_at=n.read_at,
        created_at=n.created_at,
    )


@router.get("", response_model=List[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=MAX_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Newest first — a feed is read from the top."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))

    rows = query.order_by(Notification.id.desc()).limit(limit).all()
    return [_out(n) for n in rows if _visible(db, n, current_user)]


@router.get("/unread-count", response_model=UnreadCountOut)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The badge.

    Counted with the same visibility rule as the list, so the badge can never
    promise entries the feed will not show.
    """
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .order_by(Notification.id.desc())
        .limit(MAX_LIMIT)
        .all()
    )
    return UnreadCountOut(unread=sum(1 for n in rows if _visible(db, n, current_user)))


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    # 404 for somebody else's notification: the reply must not confirm it exists.
    if n is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Idempotent. Re-reading must not move the timestamp, or "when did they
    # first see this" stops being answerable.
    if n.read_at is None:
        n.read_at = utcnow()
        db.commit()
        db.refresh(n)
    return _out(n)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = utcnow()
    (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .update({Notification.read_at: now}, synchronize_session=False)
    )
    db.commit()
    return None
