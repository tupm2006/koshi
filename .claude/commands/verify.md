---
description: Run every Koshi verification gate and report a pass/fail table
---

Run, from the repository root, and report each as a row (gate, command, result, counts):

1. `cd source/backend && .venv/bin/pytest -q`
2. `pnpm test`
3. `pnpm run build`
4. `source/backend/.venv/bin/python -m pytest -q .claude/hooks`
5. `git status --short` — anything under `source/` without a matching `documentation/` change is a
   Definition-of-Done failure (D5 §4).

Do not fix anything in this command; only report.
