import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Ensure sqlite data directory exists if using relative path
if "sqlite:///" in settings.DATABASE_URL:
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    # Server-side connections go stale; MySQL closes an idle one after
    # `wait_timeout` (8 hours by default) and the pool would then hand out a
    # dead socket. Recycling below that, and checking before use, turns a
    # mysterious "server has gone away" into a transparent reconnect.
    **({} if IS_SQLITE else {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
    }),
)

def enforce_foreign_keys(target_engine: Engine) -> None:
    """
    Make a SQLite engine honour its foreign keys.

    Applied to this module's engine below, and to the test suite's own engine in
    `conftest.py` — a database that enforces constraints only in production is a
    database whose constraints are untested.

    Deliberately NOT registered against the `Engine` class: Alembic builds its
    own engine, and `batch_alter_table` rebuilds a table by copying it and
    dropping the original, which enforcement turns into a failure. Migrations
    disable the pragma explicitly (see `migrations/env.py`); scoping the
    listener keeps those two decisions from fighting.
    """
    @event.listens_for(target_engine, "connect")
    def _set_pragma(dbapi_connection, _record):
        """
        Turn on foreign-key enforcement, per connection.

        SQLite ignores foreign keys unless this pragma is set — it is off by
        default, and off means every `ondelete="CASCADE"` in the migrations was
        decorative (F-47). Deleting a task left its comments, attachments and
        assignment rows behind as orphans; nothing failed, and nothing cleaned
        up either.

        Safe to enable here because every parent→child path that a DELETE
        endpoint can reach also has an ORM cascade, so SQLAlchemy removes the
        children first. The pragma is what makes the *database* agree, which
        matters for rows the ORM does not know to cascade — notifications
        pointing at a deleted task, for one.

        It does not retroactively validate existing rows; it governs operations
        from now on.
        """
        if type(dbapi_connection).__module__.split(".")[0] != "sqlite3":
            return
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


if IS_SQLITE:
    # InnoDB enforces foreign keys itself, so this is a SQLite-only correction.
    enforce_foreign_keys(engine)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
