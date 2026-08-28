# D4 — API & Data Contracts

**Purpose:** the boundaries. Everything in this document is load-bearing: other code depends on
these shapes, so changing one without changing every consumer is a defect, not a refactor.
**Last verified against code:** 2026-08-28 (rev 2 — per-project roles)

> **Rule for any agent working in this repo:** if a change alters anything in this document, it is a
> **contract change**. Contract changes require the escalation path in D6 §2. They are never
> "while I was in there" edits.

---

## 1. Contract inventory

| # | Contract | Defined by | Consumed by |
|:--|:--|:--|:--|
| C1 | HTTP REST surface under `/api` | `app/routers/*.py` + `app/schemas/*.py` | `source/frontend/services/api.ts` |
| C2 | Relational schema | `app/models/entities.py` | ORM, all routers, `db/schema.sql` (stale copy) |
| C3 | Frontend domain types | `source/frontend/types/task.ts` | every component + store |
| C4 | IndexedDB persisted shape | keys `koshi_tasks_v2_p{projectId}` / `koshi_tasks_v2_guest` | `taskStore.ts` only |
| C5 | JWT claims | `security.py` | `get_current_user` |
| C8 | Authorisation model — `project_members` | `entities.py::ProjectMember` + `security.py` guards | every project-scoped router |
| C9 | Schema version | `migrations/versions/` (Alembic head) | `main.py::_check_migrations_current` |
| C6 | AI structured outputs | `app/schemas/ai.py` | AI modals |
| C7 | Environment variables | `app/config.py` + `docker-compose.yml` | deployment |

---

## 2. ⚠️ Known contract violations (read before touching anything)

### 2.1 VIOLATION-01 — Task identity is inconsistent across three layers

This is the single most dangerous inconsistency in the codebase.

| Layer | Type of a task ID | Example | Source |
|:--|:--|:--|:--|
| ORM (**runtime truth**) | `Integer` autoincrement | `1` | `entities.py::Task.id` |
| `db/schema.sql` (reference) | `VARCHAR(32)` | `'TSK-1'` | `db/schema.sql` |
| API response `TaskOut.id` | `int` | `1` | `schemas/task.py` |
| API `TaskOut.dependencies` | `List[str]` | `["TSK-1"]` | `schemas/task.py` |
| Frontend `Task.id` | `string` | `'TSK-101'` | `types/task.ts` |
| Frontend seed data | `string` | `'TSK-101'` | `taskStore.ts::INITIAL_TASKS` |
| AI summary payload | `f"TSK-{t.id}"` | `"TSK-1"` | `routers/ai.py` |

**Consequences.** A task's `dependencies` list is `List[str]` while its own `id` is `int`. A server
dependency reference can therefore never match a server task ID. Dependency data round-trips
through the API but the **server-side graph is unresolvable**; only the client's own
locally-seeded string IDs form a working graph. `POST /api/tasks` with
`"dependencies": ["TSK-1"]` is accepted and stored verbatim, and resolves to nothing.

**Do not "fix" this incidentally.** Unifying identity touches C1, C2, C3 and C4 simultaneously and
is tracked as OQ-01 (D1 §5). See D6 §2 — it requires human sign-off.

### 2.2 VIOLATION-02 — API prefix is `/api`, not `/api/v1`

`config.py` sets `API_V1_PREFIX = "/api"` — the constant is misleadingly named, which is likely how
the error propagated. The retired SRS §3.4 documented `/api/v1/...`. **No `/v1` segment exists
anywhere**; Vite's dev proxy and `nginx.conf` both forward `/api`. Recorded here because the wrong
prefix outlived the document that introduced it (D7 / DEC-005).

### 2.3 VIOLATION-03 — `db/schema.sql` is not the schema

**Superseded 2026-08-28.** The schema is now owned by Alembic (`migrations/versions/`), with
`entities.py` as the ORM description that migrations must match. `db/schema.sql` is a stale legacy
artefact that predates `project_members` entirely and is never executed; it is retained only as
historical reference. It diverges from the ORM in at least four ways:

| Aspect | `schema.sql` | ORM (actual) |
|:--|:--|:--|
| `tasks.id` | `VARCHAR(32)` | `Integer` |
| Dependencies | `task_dependencies` join table | `dependencies_json` TEXT column |
| Acceptance criteria | absent | `acceptance_criteria_json` TEXT column |
| `users.skills` | `VARCHAR(500)` | `String(255)` |
| `users.full_name` | `VARCHAR(255)` | `String(100)` |

Treat `entities.py` as truth. `schema.sql` is documentation with a `.sql` extension.

### 2.4 VIOLATION-04 — `analyzeGitDiff` shadows the real parser

`services/api.ts::analyzeGitDiff()` returns a fabricated result built from `+++ b/` line counts and
blindly marks `currentTasks[0]` resolved. The genuine implementation —
`lib/gitParser.ts::parseGitDiff()` — is fully written, handles close-keyword regexes and security
scanning, and returns the complete `GitDiffAnalysisResult` including `architecturalConcerns`. The
stub omits `architecturalConcerns` entirely, so it does not even satisfy C3.

---

## 3. Domain invariants (must hold everywhere)

### 3.1 The status cycle — INVARIANT

```
TODO ──▶ IN_PROGRESS ──▶ BLOCKED ──▶ DONE ──▶ (wraps to TODO)
```
`f(Sᵢ) = S₍ᵢ₊₁₎ mod 4` over the ordered 4-set.

Implemented **twice** and both must stay identical:
- `source/frontend/stores/taskStore.ts` — `STATUS_ORDER`
- `source/backend/app/routers/tasks.py::cycle_task_status` — local `cycle` list

> ⚠️ The order above is asserted by `tests/test_tasks.py` and is authoritative. Three retired
> documents each stated it differently (two as `TODO → IN_PROGRESS → DONE → BLOCKED`); all were
> wrong, and all have been deleted or rewritten. See D7 / DEC-005.

Changing this order breaks: kanban column layout, `Shift+H`/`Shift+L` lateral movement, the
`(col ± 1 + 4) % 4` wrap, and `test_task_lifecycle_and_comments`.

### 3.2 Complexity weights — two incompatible scales, both live

| Context | S | M | L | XL | Location |
|:--|:--|:--|:--|:--|:--|
| Storage / workload points | 1 | 2 | 3 | 5 | `entities.py`, `stats.py`, `routers/ai.py` |
| Critical-path weighting | 1 | 3 | 5 | 8 | `lib/dagSorter.ts::complexityWeight` |

This is intentional (CPM exaggerates large tasks to surface bottlenecks) but undocumented in the
code. Do not "harmonise" them without reading D7 / DEC-002.

`complexity_points` is validated `ge=1, le=8` on create but **unvalidated on update**
(`TaskUpdate.complexity_points` has no `Field` constraint).

### 3.3 Priority weights

| Context | LOW | MEDIUM | HIGH | CRITICAL |
|:--|:--|:--|:--|:--|
| Topological tie-break | 1 | 2 | 3 | 4 |
| Critical-path weighting | 1 | 2 | 5 | 10 |

### 3.4 Other invariants

| ID | Invariant | Enforced where |
|:--|:--|:--|
| INV-01 | Kanban has exactly 4 columns; navigation wraps via `(c ± 1 + 4) % 4`. | `taskStore.ts`, `KanbanBoard.vue` |
| INV-02 | Selection index stays within `[0, N-1]` after any filter or deletion. | `taskStore.ts` |
| INV-03 | IndexedDB write happens **before** any API call. | `taskStore.ts` — see D3 §4.1 |
| INV-12 | Cached tasks are namespaced by project; no key is shared between projects. | `taskStore.ts::tasksKey` |
| INV-04 | A cyclic dependency graph must not drop tasks; cyclic members append after the acyclic prefix. | `dagSorter.ts::topologicalSort` tail block |
| INV-05 | Critical path considers only tasks where `status !== 'DONE'`. | `dagSorter.ts::computeCriticalPath` |
| INV-06 | An AI endpoint never returns 5xx because a model was unreachable. | `ai_service.py::_call_llm` |
| INV-07 | Passwords are truncated to 72 bytes before bcrypt (library limit). | `security.py` |
| INV-08 | A user's authority is always `(user, project)`, never `user` alone. No global role column exists. | `entities.py::ProjectMember` |
| INV-09 | Every project must retain at least one PM. | `routers/projects.py` demote/remove guards |
| INV-10 | Non-membership is reported as `404`, never `403`, so project existence stays undisclosed. | `security.py::require_member` |
| INV-11 | A `(project_id, user_id)` pair is unique — a user holds exactly one role per project. | `uq_project_member` constraint |

---

## 4. HTTP API reference

Base URL: `/api`. All responses JSON. All endpoints except `POST /auth/register`,
`POST /auth/login`, `POST /auth/google` and `GET /health` require `Authorization: Bearer <jwt>`.

### 4.1 Authentication

| Method | Path | Body | Success | Errors |
|:--|:--|:--|:--|:--|
| POST | `/auth/register` | `{email, password, full_name, skills?}` | `201` `Token` | `400` email taken |
| POST | `/auth/login` | `{email, password}` | `200` `Token` | `401` bad credentials |
| POST | `/auth/google` | `{credential}` | `200` `Token` | `401` unverifiable signature · `400` missing email |
| GET | `/auth/me` | — | `200` `UserOut` | `401` |

```jsonc
// Token — note: no `role`. Roles are per-project (see §4.3b).
{ "access_token": "<jwt>", "token_type": "bearer",
  "user": { "id": 1, "email": "...", "full_name": "...", "skills": "a,b,c",
            "avatar_url": null, "created_at": "..." } }
```

> **Registration accepts no role and silently ignores one if posted** — `role` is not in
> `UserRegister`, so Pydantic drops it. A client cannot self-escalate at signup.

### 4.2 Users

| Method | Path | Notes |
|:--|:--|:--|
| GET | `/users` | Returns `UserWithWIPOut[]` — adds `active_tasks_count`, `wip_points`. Used by the member picker. |
| PATCH | `/users/{user_id}` | Body `{skills?, full_name?}`. **Self only** — `403` for any other id. Roles are *not* settable here. |

### 4.3 Projects & sprints

| Method | Path | Role required | Notes |
|:--|:--|:--|:--|
| GET | `/projects` | — | **Only the caller's projects.** Each row carries `my_role` and `member_count`. |
| POST | `/projects` | — | `{name, description?}` → `201`. Any authenticated user may create; the creator becomes **PM** of it. |
| GET | `/projects/{id}` | member | `404` if absent **or** if the caller is not a member. |
| DELETE | `/projects/{id}` | **PM** | `204`. Cascades to members, sprints, tasks. |
| GET | `/sprints?project_id=` | member | `project_id` is **required**. |
| POST | `/sprints` | **PM** | `{project_id, name, goal?, start_date, end_date}` → `201`. |
| GET | `/sprints/{id}/stats` | member | Membership derived from the sprint's project. |

```jsonc
// ProjectOut — `my_role` is relative to the CALLING user, so the same project
// yields different values for different callers.
{ "id": 2, "name": "Apollo", "description": "", "owner_id": 3,
  "created_at": "...", "my_role": "PM", "member_count": 2 }
```

### 4.3b Membership & per-project roles

| Method | Path | Role required | Notes |
|:--|:--|:--|:--|
| GET | `/projects/{id}/members` | member | Roster with each member's role and in-project workload. |
| POST | `/projects/{id}/members` | **PM** | `{email?, user_id?, role}` → `201`. `400` if neither identifier given or already a member; `404` if the user does not exist. |
| PATCH | `/projects/{id}/members/{user_id}` | **PM** | `{role}`. `400` when demoting the **last PM**. |
| DELETE | `/projects/{id}/members/{user_id}` | **PM** | `204`. `400` when removing the **last PM**. |

```jsonc
// ProjectMemberOut
{ "user_id": 4, "project_id": 2, "role": "MEMBER",
  "full_name": "Bob", "email": "bob@demo.io", "skills": "vue",
  "avatar_url": null, "active_tasks_count": 3, "wip_points": 7 }
```

### 4.4 Tasks

| Method | Path | Notes |
|:--|:--|:--|
| GET | `/tasks?project_id=&sprint_id=&status=&assignee_id=` | `project_id` **required**; others optional. Ordered `id DESC`. |
| POST | `/tasks` | `TaskCreate` → `201` `TaskOut`. |
| GET | `/tasks/{task_id}` | `task_id` is an **integer** (see VIOLATION-01). |
| PATCH | `/tasks/{task_id}` | `TaskUpdate`; `exclude_unset` semantics — omitted fields untouched, explicit `null` clears. |
| DELETE | `/tasks/{task_id}` | `204`, empty body. |
| POST | `/tasks/{task_id}/cycle-status` | Advances one step (§3.1). No body. |
| POST | `/tasks/{task_id}/comments` | `{content}` → `201`. Author = caller. |

```jsonc
// TaskCreate — project_id required; status/priority/complexity_points defaulted
{ "project_id": 1, "sprint_id": null, "assignee_id": null,
  "title": "…", "description": "", "status": "TODO", "priority": "MEDIUM",
  "complexity_points": 2,            // int 1..8 (create only)
  "due_date": null, "blocking_reason": null,
  "dependencies": [], "acceptance_criteria": [] }   // both List[str]

// TaskOut adds: id:int, assignee:UserOut|null, created_at, updated_at, comments[]
```

**Authorisation.** Every task endpoint requires membership of the owning project. List and create
check `project_id` from the query/body; the by-id routes load the task, derive its `project_id`, and
check membership through `_get_task_for_member`. A non-member receives `404` on all of them.

### 4.5 Statistics

| Method | Path | Returns |
|:--|:--|:--|
| GET | `/stats/workload?project_id=` | **`project_id` is now required.** Per *project member*: `{user_id, full_name, email, role, skills[], active_tasks_count, total_complexity_points, is_overloaded}`. `role` is the member's role in this project. Counts only tasks in this project. Overload heuristic: `points > 10 or active > 5`. Active = TODO ∪ IN_PROGRESS ∪ BLOCKED. |
| GET | `/stats/delayed-tasks?project_id=` | `{task_id, title, status, priority, due_date, days_overdue, assignee_name}` for non-DONE tasks past `due_date`. Membership required. |

### 4.6 AI services

| Method | Path | Request | Response |
|:--|:--|:--|:--|
| POST | `/ai/weekly-summary?project_id=` | — (query param) | `{status, project_id, summary}` — `summary` is **markdown text, not structured**. |
| POST | `/ai/meeting-minutes` | `{notes}` | `{status, main_topics[], action_items[], key_decisions[]}`; `400` if notes blank. |
| POST | `/ai/recommend-assignment?project_id=` | `{title, description?}` | `{status, recommendation:{recommended_user_id, recommended_name, rationale, risk_assessment}}` |
| POST | `/ai/decompose` | `{goal}` | `{status, goal, rationale, subtasks[3]}`; `400` if goal blank. **Hardcoded — no model call.** |

```jsonc
// ActionItemOut
{ "title": "…", "assignee_name": "Unassigned", "priority": "MEDIUM", "deadline": "Next Sprint" }
// DecomposedSubtask  — note camelCase keys, unlike every other schema in the API
{ "title": "…", "description": "…", "priority": "HIGH", "complexity": "M",
  "acceptanceCriteria": ["…"], "dependsOnTitles": ["…"] }
```

> ⚠️ Naming inconsistency: `DecomposedSubtask` uses `acceptanceCriteria` / `dependsOnTitles`
> (camelCase) while `TaskCreate` uses `acceptance_criteria` (snake_case). Both are live contracts.

### 4.7 Health

`GET /api/health` → `{status:"healthy", service, version}`. Unauthenticated.

---

## 5. Frontend type contract (C3)

```ts
type TaskStatus   = 'TODO' | 'IN_PROGRESS' | 'BLOCKED' | 'DONE';
type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
type Complexity   = 'S' | 'M' | 'L' | 'XL';

interface Task {
  id: string;                    // ⚠️ string here, int on the server
  title: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  assignee?: string;             // ⚠️ a display name, not assignee_id
  dueDate?: string;              // ISO 8601 — server sends `due_date`
  blockingReason?: string;       // server sends `blocking_reason`
  createdAt: number;             // epoch ms — server sends ISO datetime
  updatedAt: number;
  dependencies?: string[];
  complexity?: Complexity;       // server stores complexity_points: int
  acceptanceCriteria?: string[];
}
```

**Every field marked ⚠️ requires transformation between C1 and C3.** No mapping layer exists —
`api.ts` returns `Promise<any[]>` from `getTasks()`, so the conversion is implicit and unchecked.
Adding a typed adapter is the recommended fix (D7 / DEC-006 follow-up).

## 6. Storage contracts

**C4 — IndexedDB.** Keys `koshi_tasks_v2_p{projectId}` (one per project) and `koshi_tasks_v2_guest`
(the unauthenticated sample board), via `idb-keyval`. Value is `Task[]` in C3 shape.

The version segment is the migration mechanism: **any breaking change to `Task` must bump it**,
since no migration code exists and stale values are read back unvalidated. `v1` used a single
shared key and was superseded when projects became first-class — a shared key would let one
project's cache be read back as another's, and an offline edit could then sync to the wrong
project. `v1` values are ignored, not migrated.

**C5 — JWT.** `{"sub": "<user_id as string>", "role": "PM|MEMBER", "exp": <unix>}`. HS256.
Default lifetime 7 days. `get_current_user` reads only `sub`; `role` is informational and is
re-read from the database on every request.

## 7. Environment contract (C7)

| Variable | Default | Notes |
|:--|:--|:--|
| `DATABASE_URL` | `sqlite:///./data/koshi.db` | Directory must exist. |
| `ENVIRONMENT` | `development` | Anything else triggers the startup safety **and migration** checks in `main.py`. |
| `JWT_SECRET` | dev placeholder | Startup **fails** outside development if left at the default. |
| `ALLOW_UNVERIFIED_GOOGLE_TOKENS` | `false` | Accepts Google tokens whose signature failed verification. Required by the test suite; blocked outside development. |
| `CORS_ORIGINS` | `*` | Comma-separated. `*` is rejected outside development, and disables `allow_credentials` when set. |
| `SEED_DEMO_DATA` | `true` | Seeds demo accounts with known passwords. Blocked outside development. |
| `AI_API_URL` | `https://api.openai.com/v1/chat/completions` | Tier 1 fires **only if** this contains `"openai"` **and** `AI_API_KEY` is set. |
| `AI_API_KEY` | `""` | Empty disables Tier 1. |
| `AI_MODEL_NAME` | `gpt-4o-mini` | |
| `OLLAMA_URL` | `http://localhost:11434/v1/chat/completions` | Compose overrides to `host.docker.internal`. |
| `OLLAMA_MODEL` | `qwen2.5:7b` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | |

> The `"openai" in AI_API_URL` substring test means pointing `AI_API_URL` at any other
> OpenAI-compatible vendor **silently disables Tier 1** even with a valid key. Non-obvious; document
> any change here.
