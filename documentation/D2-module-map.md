# D2 — Module Map

**Purpose:** answer "where does X live?" in one lookup, so an agent never greps blindly.
**Last verified against code:** 2026-08-28

---

## 1. Repository layout

```
koshi/
├── source/                      ← ALL executable code lives here
│   ├── frontend/                ← Vue 3 SPA (Vite root)
│   │   ├── index.html           ← HTML entry; inline pre-paint theme script
│   │   ├── main.ts              ← Vue + Pinia bootstrap
│   │   ├── App.vue              ← Root shell, layout, capture-phase Escape handler
│   │   ├── app.css              ← Tailwind v4 entry + global surface rules
│   │   ├── components/          ← 14 presentational / modal components
│   │   ├── lib/                 ← Pure, framework-free algorithms
│   │   ├── stores/              ← Pinia state
│   │   ├── services/            ← Backend HTTP client
│   │   └── types/               ← Shared TypeScript contracts
│   └── backend/                 ← FastAPI service
│       ├── app/
│       │   ├── main.py          ← App factory, router mounting, seed data, /health
│       │   ├── config.py        ← Pydantic Settings (env-driven)
│       │   ├── database.py      ← Engine, SessionLocal, Base, get_db
│       │   ├── security.py      ← Hashing, JWT, auth dependencies
│       │   ├── models/          ← SQLAlchemy ORM entities
│       │   ├── schemas/         ← Pydantic request/response contracts
│       │   ├── routers/         ← HTTP endpoints, one module per resource
│       │   └── services/        ← AI cascade
│       ├── db/schema.sql        ← Reference DDL (⚠ not the source of truth — see D4 §2.1)
│       ├── tests/               ← pytest suite
│       ├── init_db.py           ← Standalone DB bootstrap
│       └── requirements.txt
├── documentation/               ← ALL documentation lives here (this folder)
├── scripts/                     ← Packaging / report generation helpers
├── submission/                  ← Frozen coursework snapshot — DO NOT EDIT (D6 §3)
├── vite.config.ts               ← root='source/frontend', outDir='../../dist'
├── tsconfig.json                ← includes source/frontend/**
├── package.json                 ← Frontend scripts & deps
├── Dockerfile                   ← Frontend build → nginx
├── docker-compose.yml           ← Two services; backend context = ./source/backend
└── nginx.conf                   ← SPA fallback + /api proxy
```

## 2. Frontend module index

### 2.1 Algorithms — `source/frontend/lib/` (pure, no Vue imports, easiest to test)

| File | Exports | Responsibility | Requirements |
|:--|:--|:--|:--|
| `dagSorter.ts` | `topologicalSort(tasks)`, `computeCriticalPath(tasks)` | Kahn's algorithm with deterministic tie-breaking; memoised longest-weighted-path search over non-`DONE` tasks. | FR-GRAPH-01…05 |
| `keyboard.ts` | keydown dispatcher | Single global `switch` mapping keys → store actions. **The one authoritative list of key bindings.** | FR-INT-01…13 |
| `gitParser.ts` | `parseGitDiff(diff, tasks)` | Regex extraction of `close/fix/resolve #ID`; scans added lines for TODO/FIXME, empty catch blocks, hardcoded secrets, `: any`. | FR-AI-05 |
| `aiDecomposer.ts` | client-side goal heuristics | Tier-1 (<5 ms) local decomposition before any network call. | FR-AI-04 |

### 2.2 State — `source/frontend/stores/`

| File | Responsibility | Notes |
|:--|:--|:--|
| `taskStore.ts` | **The system's centre of gravity (~515 lines).** Holds `tasks`, selection indices (`selectedIndex`, `kanbanColIndex`, `kanbanRowIndex`), edit/detail target IDs, filter object, `currentUser`, `isBackendConnected`. Owns every mutation, IndexedDB read/write (`koshi_tasks_v1`), and the `INITIAL_TASKS` seed. | Changes here have the widest blast radius in the repo — see D8. |
| `themeStore.ts` | Dark/light state; injects a temporary `* { transition: none !important }` element during class swap to guarantee 0 ms snapping. | NFR-02, NFR-05 |

### 2.3 Transport — `source/frontend/services/api.ts`

Single `ApiClient` class. Holds the JWT, sets `Authorization: Bearer`, unwraps `detail` from error
bodies, treats 204 as `null`. Method groups: auth, tasks, AI workflows, stats.

> ⚠️ `ApiClient.analyzeGitDiff()` does **not** call the backend and does **not** use
> `lib/gitParser.ts`. It fabricates a result inline. See D7 / DEC-006.

### 2.4 Types — `source/frontend/types/task.ts`

The frontend's contract surface: `TaskStatus`, `TaskPriority`, `Complexity`, `Task`, `TaskFilter`,
`DecomposedTaskResult`, `GitDiffAnalysisResult`, `DAGNode`. **`Task.id` is `string` here.**

### 2.5 Components — `source/frontend/components/`

| Component | Trigger | Responsibility |
|:--|:--|:--|
| `TaskTable.vue` | view `TABLE` | High-density rows; permanent `border-l-2` to prevent traversal jitter; mobile swipe gestures. |
| `KanbanBoard.vue` | view `KANBAN` (`b`) | 4 status columns; `ring-inset` selection. |
| `TaskDetailModal.vue` | `Enter` | Full inspector: description, criteria, dependencies, comments. Largest component (~478 lines). |
| `CreateTaskModal.vue` | `n` | Task creation form. |
| `TaskContextMenu.vue` | right-click | Per-task action menu. |
| `AIDecomposerModal.vue` | `a` | FR-AI-04 goal decomposition. |
| `GitDiffModal.vue` | `g` | FR-AI-05 diff analysis. |
| `DAGVisualizerModal.vue` | `v` | FR-GRAPH-05 dependency graph. |
| `WeeklySummaryModal.vue` | AI menu | FR-AI-01. |
| `MeetingMinutesModal.vue` | AI menu | FR-AI-02. |
| `WorkloadAssignModal.vue` | AI menu | FR-AI-03 / FR-AI-07. |
| `AuthModal.vue` | unauthenticated | Login / register / Google. |
| `ShortcutsHelpModal.vue` | `?` | Key reference. |
| `MobileBottomNav.vue` | narrow viewport | FR-INT-14. |

## 3. Backend module index

### 3.1 Routers — `source/backend/app/routers/` (all mounted under `/api`)

| File | Prefix | Endpoints |
|:--|:--|:--|
| `auth.py` | `/auth` | `POST /register`, `POST /login`, `POST /google`, `GET /me` |
| `users.py` | `/users` | `GET ""` (with WIP points), `PATCH /{user_id}` (**PM only**) |
| `projects.py` | `/projects` | `GET ""`, `POST ""`, `GET /{project_id}` |
| `sprints.py` | `/sprints` | `GET ""`, `POST ""`, `GET /{sprint_id}/stats` |
| `tasks.py` | `/tasks` | `GET ""`, `POST ""`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`, `POST /{id}/cycle-status`, `POST /{id}/comments` |
| `stats.py` | `/stats` | `GET /workload`, `GET /delayed-tasks` |
| `ai.py` | `/ai` | `POST /weekly-summary`, `POST /meeting-minutes`, `POST /recommend-assignment`, `POST /decompose` |
| *(`main.py`)* | — | `GET /api/health` |

### 3.2 Core modules

| File | Responsibility | Key detail |
|:--|:--|:--|
| `main.py` | Lifespan hook runs `create_all` + `seed_initial_data()`; mounts routers; permissive CORS. | Seeds 2 users, 1 project, 1 sprint, 5 tasks **only when the users table is empty**. |
| `config.py` | `Settings` from env / `.env`. | Ships an insecure default `JWT_SECRET` — D6 §4 RISK-02. |
| `security.py` | `verify_password`, `get_password_hash` (bcrypt, 72-byte truncation), `create_access_token`, `get_current_user`, `get_current_pm_user`, `require_role(role)`. | `require_role` is a dependency **factory**; call it — `Depends(require_role(RoleEnum.PM))`. |
| `models/entities.py` | `User`, `Project`, `Sprint`, `Task`, `Comment` + `RoleEnum`, `TaskStatusEnum`, `TaskPriorityEnum`. | `Task.dependencies` / `.acceptance_criteria` are **Python properties** over `*_json` TEXT columns — not real relations, so they are not queryable in SQL. |
| `services/ai_service.py` | `AIService` — the three-tier cascade and every prompt. | All prompts are Vietnamese. Tier-3 branches on substring matches in the prompt text. |

### 3.3 Where the AI tiers actually live

```
routers/ai.py  ──calls──▶  AIService.<feature>()  ──calls──▶  AIService._call_llm()
                                                                    │
                                        Tier 1 ── OpenAI-compatible HTTP (10 s) ──┐ on any failure
                                        Tier 2 ── Ollama local HTTP     (4 s)  ──┤ fall through
                                        Tier 3 ── _deterministic_fallback()     ◀┘ always succeeds
```
`POST /ai/decompose` bypasses this entirely — it never enters `AIService`.

## 4. Task-to-location lookup

| If you need to change… | Go to |
|:--|:--|
| a keyboard shortcut | `source/frontend/lib/keyboard.ts` (**and** `ShortcutsHelpModal.vue`, `README.md`) |
| what a status change does | `taskStore.ts` (client) **and** `routers/tasks.py::cycle_task_status` (server) |
| critical-path weighting | `lib/dagSorter.ts::computeCriticalPath` |
| an API request/response shape | `app/schemas/*.py` **and** `source/frontend/services/api.ts` |
| a DB column | `app/models/entities.py` (truth) **and** `db/schema.sql` (reference copy) |
| an AI prompt | `app/services/ai_service.py` only |
| offline behaviour | `taskStore.ts` IndexedDB block |
| build paths | `vite.config.ts`, `tsconfig.json`, `Dockerfile`, `docker-compose.yml` |

## 5. Files that are NOT what they look like

| File | Reality |
|:--|:--|
| `svelte.config.js` | Dead. Koshi is Vue 3; this is residue from a Svelte prototype. Nothing imports it. |
| `source/backend/db/schema.sql` | Reference documentation only. Tables are created from the ORM, and the two disagree (D4 §2.1). |
| `source/backend/app/data/koshi.db` | A committed SQLite binary. Not used by tests (they write `data/test_koshi.db`). |
| `submission/` | A frozen duplicate of the whole project for coursework. Editing it has no effect on the app. |
| `tsconfig.tsbuildinfo` | Build cache, committed by accident. |
| `pnpm-lock.yaml` + `package-lock.json` | Both present. Ambiguous package manager — D7 / DEC-007. |
