"""
Creating notifications.

One module, so every kind is delivered the same way and the rules that make a
feed bearable live in one place rather than at each call site:

* **Never notify somebody about their own action.** Being told what you just did
  is noise, and it is the single rule that decides whether the feed is worth
  opening at all.
* **At most one notification per person per event.** Somebody who is both
  mentioned in a reply *and* the parent's author gets one entry, not two — the
  more specific kind wins.
* **Only people who can still see the thing.** Membership is re-checked when the
  notification is created; it is checked again on read, because a person can be
  removed from a project between the two.

Nothing here raises. A notification is a courtesy on top of an action that has
already succeeded — failing the comment because its notification could not be
written would be the tail wagging the dog.
"""
import logging
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.entities import (
    MembershipStatusEnum, Notification, NotificationKindEnum, ProjectMember,
)

logger = logging.getLogger(__name__)


def _active_member_ids(db: Session, project_id: int, user_ids: Iterable[int]) -> set[int]:
    wanted = set(user_ids)
    if not wanted:
        return set()
    return {
        m.user_id
        for m in db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id.in_(wanted),
            ProjectMember.status == MembershipStatusEnum.ACCEPTED,
        )
    }


def notify(
    db: Session,
    *,
    recipients: Iterable[int],
    kind: NotificationKindEnum,
    actor_id: Optional[int],
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    comment_id: Optional[int] = None,
    skip_user_ids: Iterable[int] = (),
) -> list[Notification]:
    """
    Create notifications, dropping the ones that should not exist.

    `skip_user_ids` is for callers delivering several kinds for one event: pass
    the recipients already served by a more specific kind so nobody is told
    twice about the same thing.

    Does not commit — the caller owns the transaction, so a notification and the
    thing it describes land together or not at all.
    """
    try:
        targets = set(recipients)
        # The rule that matters most.
        if actor_id is not None:
            targets.discard(actor_id)
        targets -= set(skip_user_ids)

        if project_id is not None:
            targets &= _active_member_ids(db, project_id, targets)

        created = []
        for uid in sorted(targets):
            n = Notification(
                user_id=uid,
                kind=kind,
                actor_id=actor_id,
                project_id=project_id,
                task_id=task_id,
                comment_id=comment_id,
            )
            db.add(n)
            created.append(n)
        return created
    except Exception:  # pragma: no cover - defensive
        logger.warning("Could not create %s notifications", kind, exc_info=True)
        return []
