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
pnpm test               # vitest run — 122 tests
pnpm run build          # vue-tsc -b && vite build → dist/
```

**Backend**
```bash
cd source/backend
cp .env.example .env               # then set JWT_SECRET (openssl rand -hex 32)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
alembic upgrade head               # build/update the schema
pytest -q                          # 38 tests
```

On first run with an empty database the app seeds two accounts (`pm@tupm.qzz.io` and
`dev@tupm.qzz.io`, both `koshi123`), a project with one PM and one MEMBER, a sprint, and five
sample tasks. Seeding is controlled by `SEED_DEMO_DATA` and the server **refuses to start** with it
enabled outside development.

**Docker**
```bash
JWT_SECRET="$(openssl rand -hex 32)" docker compose build && docker compose up -d
```

`JWT_SECRET` is required — the compose file no longer ships a default, and outside development the
API refuses to start with development defaults in force (dev JWT secret, `CORS_ORIGINS=*`, demo
seeding, or unverified Google tokens).

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

## Screens

An unauthenticated visitor gets a **marketing landing page** — hero, features, how-it-works,
pricing, FAQ — with a small sign-in control in the top-right and a language picker (English /
Tiếng Việt). There is no signed-out board: authentication is required before any project data
loads. Signing in opens the **board**; signing out returns to the landing page. A dedicated
**profile page** owns account details, project memberships and sign-out.

**Offline.** A *personal* project (one member) stays fully editable with the backend unreachable.
A *shared* project goes read-only while disconnected — there is no reconciliation, so two members
editing offline would overwrite each other.

## Accounts, projects and roles

Sign-up asks for name, email, password and optional skills — **no role**. A new account has no
authority anywhere until it creates a project or is added to one.

Roles are **per project**, not per user. Create a project and you are its PM; a PM can add members
by email and set each member's role in that project. The same account can be PM of one project and
MEMBER of another at the same time.

| | PM | MEMBER |
|:--|:--:|:--:|
| Read the project and its tasks | ✓ | ✓ |
| Create, edit, delete tasks | ✓ | ✓ |
| Add / remove members, change roles | ✓ | — |
| Create sprints | ✓ | — |
| Delete the project | ✓ | — |

A project always keeps at least one PM. Non-members get a `404` — not a `403` — so project
existence is never disclosed. The server enforces all of this independently of the UI.

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

The backend is covered end to end (38/38), with authorisation the best-tested area. The frontend
has 122 tests over the DAG engine, both stores, and the four highest-risk components — every suite
mutation-verified. Overall: 69% of requirements automated, 8% unverified. Full breakdown in
[D8 §5](./documentation/D8-rtm.md).

Known defects are catalogued in [D7 Part II](./documentation/D7-development-book.md) and risk-rated
in [D6 §4](./documentation/D6-risks-delegation-policies.md). Still open and worth knowing about:

- **Task identity is inconsistent across layers** — the ORM uses integer ids, the frontend uses
  `TSK-n` strings, and `dependencies` is `List[str]`, so the server-side dependency graph cannot
  resolve. [D4 VIOLATION-01](./documentation/D4-api-and-data-contracts.md).
- **Rotate `JWT_SECRET` on any deployment that predates 2026-08-28.** The old default was published
  in this repo; tokens signed with it remain forgeable. Runbook:
  [D6 §7.1](./documentation/D6-risks-delegation-policies.md).
- **The board interaction layer is untested** (D5 GAP-12) — `lib/keyboard.ts` and the
  table/kanban/detail components, which is all fourteen FR-INT requirements.
- **Landing-page pricing figures are placeholders** and must be replaced before publishing
  (D6 RISK-18).

## Contributors

- **Lead Architect & Developer** — Phạm Minh Tú (`tupm`)
- Phạm Văn Huynh
- Đàm Đức Đôn

MIT License.
