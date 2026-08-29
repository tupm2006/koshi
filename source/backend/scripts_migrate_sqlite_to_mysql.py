"""
Copy an existing SQLite database into MySQL.

    python -m scripts_migrate_sqlite_to_mysql \
        --source sqlite:///./data/koshi.db \
        --target 'mysql+pymysql://koshi:pw@127.0.0.1:3306/koshi?charset=utf8mb4'

Row-by-row through SQLAlchemy rather than a SQL dump, because the two dialects
disagree about quoting, booleans and datetimes, and a dump that *almost* imports
is worse than one that refuses.

**The target must already be at head.** This copies data; Alembic owns the
schema. Running it against an empty database would only produce a schema-shaped
hole, so it checks and refuses.

Tables are copied parents-first and identity columns are preserved, so every
foreign key still resolves and no id in a bookmark, a URL or an uploaded file's
row goes stale.
"""
import argparse
import sys

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.database import Base
import app.models.entities  # noqa: F401  — registers the tables on Base

#: Parents before children. Derived by hand rather than sorted, because the
#: order is a fact about the schema that a reader should be able to check.
ORDER = [
    "users", "projects", "project_members", "sprints", "tasks",
    "task_assignees", "comments", "attachments", "notifications",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="SQLite URL to read from")
    ap.add_argument("--target", required=True, help="MySQL URL to write to")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation")
    args = ap.parse_args()

    src = create_engine(args.source)
    dst = create_engine(args.target)

    src_tables = set(inspect(src).get_table_names())
    dst_tables = set(inspect(dst).get_table_names())

    missing = [t for t in ORDER if t in src_tables and t not in dst_tables]
    if missing:
        print(f"Target is missing tables: {missing}", file=sys.stderr)
        print("Run `alembic upgrade head` against the target first.", file=sys.stderr)
        return 1

    # Refuse to merge into a database that already holds rows: this preserves
    # ids, so a second run would collide, and a partial merge is far harder to
    # unpick than a fresh import.
    with Session(dst) as check:
        for table in ORDER:
            if table in dst_tables and check.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar():
                print(f"Target table '{table}' is not empty — refusing.", file=sys.stderr)
                print("Drop and re-migrate the target, or use a fresh database.", file=sys.stderr)
                return 1

    counts = {}
    with Session(src) as s_in, Session(dst) as s_out:
        # FK checks off for the copy: parents-first ordering makes it correct,
        # but a self-referencing row (a reply whose parent comes later in the
        # same table) would still trip on the way in.
        s_out.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for name in ORDER:
            if name not in src_tables:
                continue
            table = Base.metadata.tables[name]
            rows = [dict(r._mapping) for r in s_in.execute(select(table))]
            if rows:
                s_out.execute(table.insert(), rows)
            counts[name] = len(rows)
            print(f"  {name}: {len(rows)}")
        s_out.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        s_out.commit()

    # Prove it landed rather than trusting the insert.
    with Session(dst) as verify:
        for name, expected in counts.items():
            actual = verify.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar()
            if actual != expected:
                print(f"MISMATCH in {name}: copied {expected}, found {actual}", file=sys.stderr)
                return 1

    print(f"\nCopied {sum(counts.values())} rows. Verified.")
    print("Uploaded files live on disk, not in the database — keep the data volume.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
