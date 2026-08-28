"""
Alembic environment for Koshi.

The database URL and target metadata are taken from the application itself
(`app.config.settings` / `app.database.Base`) rather than being duplicated in
`alembic.ini`, so migrations always target whatever the app is configured to use.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.config import settings
from app.database import Base
# Importing the entities registers every table on Base.metadata; without this
# autogenerate would see an empty model and propose dropping everything.
from app.models import entities  # noqa: F401

config = context.config

# Fall back to the application's configured database, but let an explicit
# override win — that is what lets the test-suite (and `alembic -x`) point a
# migration run at a scratch database.
DATABASE_URL = config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL
config.set_main_option("sqlalchemy.url", DATABASE_URL)
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # SQLite cannot ALTER most columns in place; batch mode rebuilds the
        # table transparently instead.
        render_as_batch=IS_SQLITE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=IS_SQLITE,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
