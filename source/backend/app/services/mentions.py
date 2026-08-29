"""
Parsing and validating @mentions inside comment text.

**Storage shape.** A mention is written into the comment body as
`@[Display Name](userId)`. The id is what the mention *means*; the name is only
what it looked like when it was written.

That matters because people get renamed. Storing the name alone would leave
stale text nobody could correct; storing the id alone would make the raw comment
unreadable. Keeping both, with the id authoritative, lets a client render the
person's *current* name and fall back to the captured one when it cannot resolve
the id (a former member, say).

**No mentions table.** The tokens in the body are the single source of truth.
A parallel table would have to be kept in step with an editable text field, and
two records of the same fact is how they drift. If "notify me when mentioned"
is ever wanted, derive it from these tokens rather than duplicating them.
"""
import re
from typing import List, Set

#: `@[Ada Lovelace](12)`. The name may contain anything except a closing
#: bracket, which keeps the pattern unambiguous without escaping rules.
MENTION_RE = re.compile(r"@\[([^\]]{1,100})\]\((\d{1,10})\)")


def parse_mention_ids(content: str) -> List[int]:
    """User ids mentioned in the text, in order, without duplicates."""
    seen: Set[int] = set()
    out: List[int] = []
    for _label, raw_id in MENTION_RE.findall(content or ""):
        try:
            uid = int(raw_id)
        except ValueError:  # pragma: no cover - the pattern only matches digits
            continue
        if uid not in seen:
            seen.add(uid)
            out.append(uid)
    return out
