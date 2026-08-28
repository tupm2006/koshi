# KOSHI (輿)

> Local-first, keyboard-driven project management for small software teams.
> Vue 3 + Pinia · FastAPI + SQLAlchemy · deterministic state machine · topological DAG critical path · schema-constrained AI.

**Live:** https://koshi.tupm.qzz.io

---

## What it is

Koshi optimises for two things most trackers do badly: **mutation velocity** (every state change is
local and instant, the network never blocks the UI) and **trustworthy AI output** (every AI endpoint
is validated against a Pydantic schema and degrades to a deterministic generator rather than
failing).

It deliberately trades breadth for those two properties. Multi-tenant orgs, real-time collaboration,
attachments, and time tracking are out of scope — see [D1 §2](./documentation/D1-requirements.md).

## Repository layout

```
source/
  frontend/     Vue 3 SPA — Vite root
  backend/      FastAPI service
documentation/  D1–D8: the navigation layer (start here)
scripts/        packaging helpers
submission/     frozen coursework snapshot — do not edit
```

## Quick start

**Frontend**
```bash
pnpm install
pnpm run dev            # http://localhost:5173, proxies /api → :8000
pnpm run build          # vue-tsc -b && vite build → dist/
```

**Backend**
```bash
cd source/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data                      # required — DATABASE_URL points at ./data/
uvicorn app.main:app --reload --port 8000
pytest -q                          # 6 tests
```

On first run with an empty database the app seeds a PM (`pm@tupm.qzz.io` / `koshi123`), a member, a
project, a sprint, and five sample tasks. **Disable this before any real deployment** — see
[D6 RISK-11](./documentation/D6-risks-delegation-policies.md).

**Docker**
```bash
docker compose build && docker compose up -d
```

## Documentation

All project documentation lives in [`documentation/`](./documentation/README.md) as eight numbered
documents. Read them in order; each answers one question.

| | | |
|:--|:--|:--|
| [D1](./documentation/D1-requirements.md) | Requirements | what must be achieved |
| [D2](./documentation/D2-module-map.md) | Module Map | where things live |
| [D3](./documentation/D3-architecture.md) | Architecture | how components interact |
| [D4](./documentation/D4-api-and-data-contracts.md) | API & Data Contracts | boundaries that must not break |
| [D5](./documentation/D5-tests-and-acceptance.md) | Tests & Acceptance | what correctness means |
| [D6](./documentation/D6-risks-delegation-policies.md) | Risks & Delegation | limits of AI autonomy |
| [D7](./documentation/D7-development-book.md) | Development Book | what was tried and why |
| [D8](./documentation/D8-rtm.md) | RTM | requirement → code → test |

**This README is a summary, not a specification.** Where it differs from D1–D8, D1–D8 are correct.

## Core behaviour

**Status cycle** — the system's central invariant:
```
TODO → IN_PROGRESS → BLOCKED → DONE → (wraps to TODO)
```
Implemented in both `taskStore.ts` and `routers/tasks.py`; changing it requires changing both
([D4 §3.1](./documentation/D4-api-and-data-contracts.md)).

**Keyboard model** — the authoritative list is `source/frontend/lib/keyboard.ts`:

| Key | Action | | Key | Action |
|:--|:--|:--|:--|:--|
| `b` | toggle Table ⇄ Kanban | | `n` | create task |
| `h` `j` `k` `l` | navigate (2D in Kanban) | | `i` | inline title edit |
| `H` `L` | shift task across columns | | `Enter` | open task inspector |
| `Space` | cycle status | | `d` | delete task |
| `1`–`4` | set priority | | `/` | focus search |
| `a` `g` `v` | decomposer · git diff · DAG | | `t` `?` | theme · help |
| `Esc` | dismiss anything (capture phase) | | | |

**AI cascade** — every AI endpoint falls through three tiers and never 5xxs on model
unavailability:
```
Tier 1  OpenAI-compatible API (10s)  →  Tier 2  Ollama (4s)  →  Tier 3  deterministic generator
```
Tier 3 output is currently indistinguishable from real model output to the caller
([D6 RISK-12](./documentation/D6-risks-delegation-policies.md)).

## Project status

The backend HTTP surface is smoke-tested end to end (6/6 passing). **The frontend has no automated
tests**, including the DAG engine — the most intricate logic in the repository. Overall: 33% of
requirements automated, 26% unverified. Full breakdown in [D8 §5](./documentation/D8-rtm.md).

Known defects are catalogued in [D7 Part II](./documentation/D7-development-book.md) and risk-rated
in [D6 §4](./documentation/D6-risks-delegation-policies.md). Four are critical and should be
addressed before any production use: unverified Google ID tokens, a hardcoded JWT secret, absent
project-scoped authorisation, and inconsistent task identity across layers.

## Contributors

- **Lead Architect & Developer** — Phạm Minh Tú (`tupm`)
- Phạm Văn Huynh
- Đàm Đức Đôn

MIT License.
