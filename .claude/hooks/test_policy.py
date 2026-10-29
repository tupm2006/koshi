"""Unit tests for the agent guardrails (policy.py) and an end-to-end test of guard.py's protocol."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import policy  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


# ---- edits -------------------------------------------------------------------

@pytest.mark.parametrize("path", [".env", "source/backend/.env", ".env.production", "submission/README.md",
                                  "node_modules/x/index.js", "dist/index.html", "source/backend/.venv/lib/x.py"])
def test_forbidden_paths_are_denied(path):
    assert policy.check_edit(path).action == "deny"


def test_env_templates_are_editable():
    assert policy.check_edit(".env.example").action == "allow"


@pytest.mark.parametrize("path", ["source/backend/app/security.py", "source/backend/app/routers/auth.py",
                                  "source/backend/app/models/entities.py", "source/frontend/types/task.ts",
                                  "source/backend/app/services/uploads.py", "scripts/deploy.sh",
                                  ".claude/settings.json", ".github/workflows/test.yml"])
def test_red_zone_needs_a_human(path):
    assert policy.check_edit(path).action == "ask"


def test_applied_migration_is_immutable_but_a_new_one_is_fine():
    applied = "source/backend/migrations/versions/0001_initial_schema.py"
    new = "source/backend/migrations/versions/0010_next.py"
    assert policy.check_edit(applied, tracked=lambda p: p == applied).action == "deny"
    assert policy.check_edit(new, tracked=lambda p: p == applied).action == "allow"


def test_yellow_zone_is_allowed_with_a_reminder():
    d = policy.check_edit("source/frontend/stores/taskStore.ts")
    assert d.action == "allow" and "status cycle" in d.reminders[0]


def test_green_zone_is_silent():
    d = policy.check_edit("documentation/D7-development-book.md")
    assert d.action == "allow" and not d.reminders


@pytest.mark.parametrize("secret", ["gsk_" + "a" * 40, "AIza" + "b" * 35, "sk-" + "c" * 40,
                                    "-----BEGIN RSA PRIVATE KEY-----",
                                    "koshi_super_secret_jwt_key_2026_academic_spec"])
def test_secrets_are_never_written_anywhere(secret):
    assert policy.check_edit("documentation/notes.md", f"key = '{secret}'").action == "deny"


# ---- shell -------------------------------------------------------------------

@pytest.mark.parametrize("cmd", ["git push --force", "git push -f origin main", "git push --force-with-lease",
                                 "cat .env", "grep JWT source/backend/.env", "rm -rf /", "rm -rf ~",
                                 "tar czf - . | ssh umi 'tar xzf -'"])
def test_dangerous_commands_are_denied(cmd):
    assert policy.check_bash(cmd).action == "deny"


@pytest.mark.parametrize("cmd", ["git push", "./scripts/deploy.sh umi", "git reset --hard HEAD~1",
                                 "alembic downgrade -1", "docker volume rm koshi-data",
                                 "docker compose down -v"])
def test_irreversible_commands_need_a_human(cmd):
    assert policy.check_bash(cmd).action == "ask"


@pytest.mark.parametrize("cmd", ["pytest -q", "pnpm test", "git status", "git commit -m 'x'",
                                 "cat .env.example", "alembic upgrade head", "rm -rf dist/assets"])
def test_routine_commands_pass(cmd):
    assert policy.check_bash(cmd).action == "allow"


def test_heredoc_prose_is_not_a_command():
    cmd = "cat >> notes.md <<'EOF'\nThe old tar|ssh deploy; never git push --force.\nEOF\nwc -l notes.md"
    assert policy.check_bash(cmd).action == "allow"


def test_a_later_commands_flag_is_not_a_push_flag():
    d = policy.check_bash("git push -q; pdftotext -f 3 -l 8 x.pdf -")
    assert d.action == "ask"  # the push itself still needs a human, but it is not a force-push


def test_command_after_a_heredoc_is_still_checked():
    assert policy.check_bash("cat > x <<EOF\nhi\nEOF\ngit push --force").action == "deny"


# ---- definition of done -------------------------------------------------------

def test_docs_only_change_is_complete():
    assert policy.check_completion(["documentation/D1-requirements.md"]) is None


def test_code_without_docs_or_tests_is_sent_back():
    reason = policy.check_completion(["source/backend/app/routers/tasks.py"])
    assert "no D1–D8 document" in reason and "without a test" in reason


def test_complete_backend_change_passes():
    assert policy.check_completion(["source/backend/app/routers/tasks.py",
                                    "source/backend/tests/test_tasks.py",
                                    "documentation/D8-rtm.md"]) is None


def test_model_change_needs_a_migration():
    reason = policy.check_completion(["source/backend/app/models/entities.py",
                                      "source/backend/tests/test_x.py", "documentation/D4.md"])
    assert "Alembic" in reason


def test_frontend_change_needs_a_frontend_test():
    reason = policy.check_completion(["source/frontend/lib/urgency.ts", "documentation/D5.md"])
    assert "frontend code changed without a test" in reason


# ---- guard.py, end to end -------------------------------------------------------

def _run(event):
    out = subprocess.run([sys.executable, os.path.join(HERE, "guard.py")], input=json.dumps(event),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def test_guard_denies_force_push_in_protocol_shape():
    out = _run({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git push -f"}})
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_guard_blocks_a_secret_inside_an_edit():
    out = _run({"hook_event_name": "PreToolUse", "tool_name": "Edit",
                "tool_input": {"file_path": "README.md", "old_string": "a", "new_string": "gsk_" + "x" * 40}})
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_guard_fails_closed_on_garbage():
    out = subprocess.run([sys.executable, os.path.join(HERE, "guard.py")], input="not json",
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_stop_does_not_loop():
    assert _run({"hook_event_name": "Stop", "stop_hook_active": True}) == {}
