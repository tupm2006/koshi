"""
Alembic migration integrity (D7 / DEC-011).

These tests protect the upgrade path for an already-deployed database, which is
the case that cannot be recovered by deleting the file and starting again.
"""
import sqlite3
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command


def _alembic_cfg(db_path):
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(root, "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def _cols(db_path, table):
    con = sqlite3.connect(db_path)
    try:
        return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
    finally:
        con.close()


def _tables(db_path):
    con = sqlite3.connect(db_path)
    try:
        return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()


def test_single_head(tmp_path):
    """A branched history would make `upgrade head` ambiguous."""
    script = ScriptDirectory.from_config(_alembic_cfg(tmp_path / "x.db"))
    assert len(script.get_heads()) == 1, "migration history has branched"


def test_fresh_upgrade_produces_current_schema(tmp_path):
    db = tmp_path / "fresh.db"
    command.upgrade(_alembic_cfg(db), "head")

    assert "project_members" in _tables(db)
    # The global role column must be gone — authority lives on ProjectMember.
    assert "role" not in _cols(db, "users")
    assert set(_cols(db, "project_members")) >= {"project_id", "user_id", "role"}


def test_legacy_database_upgrades_and_backfills_roles(tmp_path):
    """
    The migration that matters: an existing pre-roles database with real rows.

    Backfill contract (see the migration docstring): everyone keeps the access
    they had, project owners and former global PMs become PMs.
    """
    db = tmp_path / "legacy.db"
    cfg = _alembic_cfg(db)
    command.upgrade(cfg, "0001_initial_schema")

    con = sqlite3.connect(db)
    con.executescript("""
        INSERT INTO users (id,email,full_name,role,skills) VALUES
          (1,'boss@x.io','Boss','PM','mgmt'),
          (2,'dev@x.io','Dev','MEMBER','vue'),
          (3,'ops@x.io','Ops','MEMBER','k8s');
        INSERT INTO projects (id,name,owner_id) VALUES (1,'Apollo',2),(2,'Orphan',NULL);
    """)
    con.commit()
    con.close()

    command.upgrade(cfg, "head")

    con = sqlite3.connect(db)
    try:
        roles = {(p, u): r for p, u, r in con.execute(
            "SELECT project_id, user_id, role FROM project_members"
        )}
    finally:
        con.close()

    # Nobody loses access they previously had.
    assert len(roles) == 6, "every user should be a member of every project"

    assert roles[(1, 2)] == "PM"      # owner of Apollo
    assert roles[(1, 1)] == "PM"      # former global PM
    assert roles[(1, 3)] == "MEMBER"

    # An ownerless project still gets a PM, so it is never unadministered.
    assert roles[(2, 1)] == "PM"
    assert "role" not in _cols(db, "users")


def test_ownerless_project_with_no_global_pm_still_gets_a_pm(tmp_path):
    db = tmp_path / "nopm.db"
    cfg = _alembic_cfg(db)
    command.upgrade(cfg, "0001_initial_schema")

    con = sqlite3.connect(db)
    con.executescript("""
        INSERT INTO users (id,email,full_name,role,skills) VALUES
          (7,'a@x.io','A','MEMBER','x'),
          (9,'b@x.io','B','MEMBER','y');
        INSERT INTO projects (id,name,owner_id) VALUES (1,'Stranded',NULL);
    """)
    con.commit()
    con.close()

    command.upgrade(cfg, "head")

    con = sqlite3.connect(db)
    try:
        pms = [u for (u,) in con.execute(
            "SELECT user_id FROM project_members WHERE project_id=1 AND role='PM'"
        )]
    finally:
        con.close()

    assert pms == [7], "lowest-id user should be promoted as the fallback PM"


def test_downgrade_restores_global_role(tmp_path):
    db = tmp_path / "down.db"
    cfg = _alembic_cfg(db)
    command.upgrade(cfg, "0001_initial_schema")

    con = sqlite3.connect(db)
    con.executescript("""
        INSERT INTO users (id,email,full_name,role,skills) VALUES
          (1,'boss@x.io','Boss','PM','mgmt'),
          (2,'dev@x.io','Dev','MEMBER','vue');
        INSERT INTO projects (id,name,owner_id) VALUES (1,'Apollo',2);
    """)
    con.commit()
    con.close()

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0001_initial_schema")

    assert "project_members" not in _tables(db)
    assert "role" in _cols(db, "users")

    con = sqlite3.connect(db)
    try:
        roles = dict(con.execute("SELECT id, role FROM users"))
    finally:
        con.close()

    # Both were PMs of Apollo after backfill, so both come back as global PMs.
    assert roles[1] == "PM"
    assert roles[2] == "PM"
