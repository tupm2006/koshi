---
description: Run a feature through the full Koshi software factory (requirements → design → tests → code → review → release check)
argument-hint: <feature description>
---

Build this feature through the factory: **$ARGUMENTS**

Run the stations in order with the Agent tool, passing each station's output to the next.
Do not skip a station and do not merge two into one agent — the separation is the control.

1. `requirements-analyst` — FR ids + acceptance criteria in D1/D5/D8.
2. `architect` — impact plan with D6 zones. **If any 🔴 item: stop here and ask me.**
3. `test-engineer` — failing tests (unit + integration). Show me the red output.
4. `implementer` — make them green.
5. `test-engineer` again — mutation check of the new tests.
6. `reviewer` — must return PASS. On findings, loop back to step 4 (at most twice, then ask me).
7. `release-engineer` — all gates + local production stack + smoke test + metrics.

Finish with: requirement ids, files changed, test counts before/after, reviewer verdict,
gate table. Commit only when every gate is green; never push unless I said so.
