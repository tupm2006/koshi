from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.entities import NotificationKindEnum
from app.schemas.auth import UserOut


class NotificationOut(BaseModel):
    """
    One feed entry.

    Carries a denormalised `project_name` / `task_key` / `task_title` / `excerpt`
    so the client can render a readable line without fetching the project and
    task behind every row — and, more importantly, so an entry still reads
    correctly for somebody who has since lost access to the project it came from.

    There is no message string. Wording belongs to the client, which knows the
    reader's locale; English prose stored here would have to be re-translated on
    every read and could never be corrected retroactively.
    """
    id: int
    kind: NotificationKindEnum
    actor: Optional[UserOut] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    task_id: Optional[int] = None
    task_key: Optional[str] = None
    task_title: Optional[str] = None
    comment_id: Optional[int] = None
    #: A short slice of the comment, so the feed says what it is about. Mention
    #: tokens are left as written; the client renders them.
    excerpt: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UnreadCountOut(BaseModel):
    unread: int
