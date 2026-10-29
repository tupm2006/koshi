#!/usr/bin/env python3
"""
Claude Code hook entry point. Reads the hook event on stdin, applies policy.py,
answers on stdout in the hook JSON protocol. Wired in .claude/settings.json.

    PreToolUse  Edit|Write|MultiEdit|NotebookEdit  → check_edit
    PreToolUse  Bash                               → check_bash
    Stop                                           → check_completion (D5 §4)

A crash here must not silently disable the guard, so any exception becomes a
"deny"/"block" with the error as the reason.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import policy  # noqa: E402

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _git(*args: str) -> list[str]:
    out = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, check=False).stdout
    return [line for line in out.splitlines() if line.strip()]


def _tracked(path: str) -> bool:
    return bool(_git("ls-files", "--error-unmatch", path))


def _changed() -> list[str]:
    """Everything this session has touched and not yet pushed: working tree + unpushed commits."""
    paths = set(_git("diff", "--name-only", "HEAD"))
    paths |= set(_git("ls-files", "--others", "--exclude-standard"))
    upstream = _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream:
        paths |= set(_git("diff", "--name-only", f"{upstream[0]}...HEAD"))
    return sorted(paths)


def _pre_tool(event: dict) -> dict:
    tool = event.get("tool_name", "")
    data = event.get("tool_input", {}) or {}
    if tool == "Bash":
        decision = policy.check_bash(data.get("command", ""))
    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = policy.normalise(data.get("file_path") or data.get("notebook_path", ""), ROOT)
        content = data.get("content") or data.get("new_string") or ""
        content += "".join(e.get("new_string", "") for e in data.get("edits", []) or [])
        decision = policy.check_edit(path, content, _tracked)
    else:
        return {}
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if decision.action in ("deny", "ask"):
        out["hookSpecificOutput"]["permissionDecision"] = decision.action
        out["hookSpecificOutput"]["permissionDecisionReason"] = decision.reason
    elif decision.reminders:
        out["hookSpecificOutput"]["additionalContext"] = " ".join(decision.reminders)
    return out


def _stop(event: dict) -> dict:
    if event.get("stop_hook_active"):
        return {}  # already sent back once; do not loop forever
    reason = policy.check_completion(_changed())
    return {"decision": "block", "reason": f"Definition of Done not met: {reason}"} if reason else {}


def main() -> None:
    try:
        event = json.load(sys.stdin)
        name = event.get("hook_event_name")
        out = _pre_tool(event) if name == "PreToolUse" else _stop(event) if name == "Stop" else {}
    except Exception as exc:  # fail closed
        out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                      "permissionDecisionReason": f"guard.py failed: {exc}"}}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
