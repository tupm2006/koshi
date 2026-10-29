"""
D6 as code: the delegation map an agent is held to, not merely asked to read.

Pure functions only — no I/O except the optional `tracked` lookup — so the
whole policy is unit-tested in test_policy.py without a running agent.

Decisions mirror Claude Code's PreToolUse vocabulary:
    "deny"  — never, whoever asks (P9 secrets, P10 frozen/generated trees, P12)
    "ask"   — D6 🔴 RED: a human approves this specific action
    "allow" — GREEN/YELLOW; YELLOW returns a reminder to report and update docs
"""
from __future__ import annotations

import fnmatch
import re
import shlex
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional


@dataclass
class Decision:
    action: str                 # deny | ask | allow
    reason: str = ""
    reminders: list[str] = field(default_factory=list)


# ---- File edits --------------------------------------------------------------

# Never edited by an agent (D6 P9, P10, §3).
DENY_PATHS = [
    (".env", "P9: secrets live in a gitignored .env; an agent never reads or writes it"),
    ("*/.env", "P9: secrets live in a gitignored .env; an agent never reads or writes it"),
    (".env.*", "P9: secrets live in a gitignored .env; an agent never reads or writes it"),
    ("submission/*", "D6 §3: submission/ is a frozen coursework snapshot"),
    ("node_modules/*", "P10: generated tree"),
    ("*/node_modules/*", "P10: generated tree"),
    ("dist/*", "P10: build output"),
    ("*/.venv/*", "P10: virtualenv"),
]
ALLOWED_ENV_TEMPLATES = {".env.example", "source/backend/.env.example"}

# D6 §1 RED — the file itself is a security or contract boundary.
RED_PATHS = [
    ("source/backend/app/security.py", "auth/JWT/hashing logic"),
    ("source/backend/app/routers/auth.py", "auth logic"),
    ("source/backend/app/models/entities.py", "D4 contract: database columns"),
    ("source/backend/app/schemas/*", "D4 contract: request/response shapes"),
    ("source/frontend/types/task.ts", "D4 contract C4: bump the IndexedDB key if this changes"),
    ("source/backend/app/services/uploads.py", "upload allowlist (stored-XSS boundary)"),
    ("source/backend/app/config.py", "secrets and CORS defaults"),
    ("scripts/deploy.sh", "deployment overwrites a live host"),
    ("docker-compose.prod-local.yml", "production posture"),
    (".github/workflows/*", "CI is the merge gate"),
    (".claude/*", "the agent's own guardrails"),
]

YELLOW_PATHS = [
    ("source/frontend/stores/taskStore.ts", "widest blast radius; keep INV-02/03 and the status cycle identical to tasks.py"),
    ("source/frontend/lib/keyboard.ts", "binding change ⇒ update ShortcutsHelpModal.vue, README.md, D1 §3.1"),
    ("source/frontend/lib/dagSorter.ts", "covered by dagSorter.test.ts; F-24 is pinned deliberately"),
    ("source/backend/app/routers/*", "never remove require_member / require_project_pm; a shape change is RED"),
    ("source/frontend/lib/translations.ts", "every key in both locales"),
    ("source/backend/app/services/ai_service.py", "prompt wording can change fallback routing"),
    ("source/frontend/components/LandingPage.vue", "P14: no invented testimonials or metrics"),
    ("Dockerfile", "path-coupled; run pnpm run build afterwards"),
    ("vite.config.ts", "path-coupled; run pnpm run build afterwards"),
    ("nginx.conf", "path-coupled"),
]

MIGRATIONS = "source/backend/migrations/versions/"

# Content that must never be written into the tree (P9, F-01).
SECRET_PATTERNS = [
    (re.compile(r"gsk_[A-Za-z0-9]{20,}"), "a Groq API key"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{30,}"), "a Google API key"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), "an OpenAI-style API key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    (re.compile(r"koshi_super_secret_jwt_key_2026_academic_spec"), "the leaked JWT secret (F-01)"),
]


def _match(path: str, patterns: Iterable[tuple[str, str]]) -> Optional[str]:
    for pattern, why in patterns:
        if fnmatch.fnmatch(path, pattern):
            return why
    return None


def normalise(path: str, repo_root: str) -> str:
    root = repo_root.rstrip("/") + "/"
    return path[len(root):] if path.startswith(root) else path.lstrip("./")


def check_edit(path: str, content: str = "", tracked: Callable[[str], bool] = lambda p: False) -> Decision:
    """`path` is repo-relative. `tracked(path)` says whether git already has the file."""
    for pattern, label in SECRET_PATTERNS:
        if pattern.search(content or ""):
            return Decision("deny", f"P9: the new content contains {label}. Read it from the environment instead.")

    if path not in ALLOWED_ENV_TEMPLATES:
        why = _match(path, DENY_PATHS)
        if why:
            return Decision("deny", why)

    if path.startswith(MIGRATIONS) and path.endswith(".py") and tracked(path):
        return Decision("deny", "P12: an applied Alembic revision is immutable — add a new revision instead")

    why = _match(path, RED_PATHS)
    if why:
        return Decision("ask", f"D6 RED zone ({why}). A human must approve this edit.")

    why = _match(path, YELLOW_PATHS)
    if why:
        return Decision("allow", reminders=[f"YELLOW {path}: {why}. Report it and update the D-docs in the same commit."])
    return Decision("allow")


# ---- Shell commands ----------------------------------------------------------

def _words(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\b", re.S)


def check_bash(command: str) -> Decision:
    # A heredoc body is data being written, not a command being run — prose
    # that mentions "git push" must not trip the push rule.
    words = _words(_HEREDOC.sub("<<HEREDOC", command))
    text = " ".join(words)

    if re.search(r"(^|[\s/])\.env(\s|$)", " " + text + " ") and re.search(r"\b(cat|less|more|head|tail|grep|sed|awk|cp|scp|curl)\b", text):
        return Decision("deny", "P9: do not print or copy .env; refer to variables by name")
    if re.search(r"git\s+push\b.*(--force\b|--force-with-lease\b|\s-f\b)", text):
        return Decision("deny", "Force-push rewrites shared history (D6 RED); never by an agent")
    if re.search(r"git\s+(reset\s+--hard|clean\s+-[a-z]*f|branch\s+-D)", text):
        return Decision("ask", "Destroys uncommitted or branch work; a human confirms")
    if re.search(r"\brm\s+-[a-z]*r[a-z]*f?\b.*(\s/|\s~|\s\.\s*$|\s\*)", text + " "):
        return Decision("deny", "Recursive delete of a root, home or wildcard path")
    if re.search(r"(^|\s)(\./)?scripts/deploy\.sh\b", text):
        return Decision("ask", "Deploying overwrites a live host (D6 RED, F-37); human-initiated only")
    if re.search(r"\btar\s[^|]*\|\s*ssh\s", text):
        return Decision("deny", "F-37: the tar|ssh deploy shipped .env to production; use scripts/deploy.sh")
    if re.search(r"git\s+push\b", text):
        return Decision("ask", "Publishing commits needs an explicit instruction (D6 RED)")
    if re.search(r"alembic\s+downgrade\b", text):
        return Decision("ask", "A downgrade can drop columns and data")
    if re.search(r"docker\s+(volume\s+rm|compose\b.*\bdown\b.*-v)", text):
        return Decision("ask", "Removing a volume deletes the database and every upload")
    return Decision("allow")


# ---- Completion gate -----------------------------------------------------------

def check_completion(changed: list[str]) -> Optional[str]:
    """
    The Definition of Done (D5 §4) as a gate on the agent's Stop.
    Returns a reason to keep working, or None when the change set is complete.
    """
    code = [p for p in changed if p.startswith("source/") and not p.endswith((".md",))]
    if not code:
        return None
    problems = []
    docs = [p for p in changed if p.startswith("documentation/") or p in ("CLAUDE.md", "README.md")]
    if not docs:
        problems.append("source/ changed but no D1–D8 document did (\"keep docs in the same commit\")")
    backend = [p for p in code if p.startswith("source/backend/app/")]
    backend_tests = [p for p in changed if p.startswith("source/backend/tests/")]
    if backend and not backend_tests:
        problems.append("backend code changed without a test change — add or extend a test (D5 §4)")
    frontend = [p for p in code if p.startswith("source/frontend/") and p.endswith((".ts", ".vue")) and ".test." not in p]
    frontend_tests = [p for p in changed if ".test." in p]
    if frontend and not frontend_tests:
        problems.append("frontend code changed without a test change — add or extend a test (D5 §4)")
    if any(p.startswith("source/backend/app/models/") for p in changed) and not any(p.startswith(MIGRATIONS) for p in changed):
        problems.append("an ORM model changed without a new Alembic revision")
    return "; ".join(problems) or None
