"""Time helpers."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Naive UTC 'now'.

    `datetime.utcnow()` is deprecated, but the database columns are naive and
    are compared against naive values throughout, so returning an aware datetime
    here would break those comparisons. This keeps the existing semantics while
    dropping the deprecation.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
