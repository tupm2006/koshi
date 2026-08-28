# D4 — API & Data Contracts

**Purpose:** the boundaries. Everything in this document is load-bearing: other code depends on
these shapes, so changing one without changing every consumer is a defect, not a refactor.
**Last verified against code:** 2026-08-28

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
| C4 | IndexedDB persisted shape | key `koshi_tasks_v1` | `taskStore.ts` only |
| C5 | JWT claims | `security.py` | `get_current_user` |
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

Tables are created by `Base.metadata.create_all()` from the ORM. `schema.sql` is never executed by
the application. It diverges from the ORM in at least four ways:

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
| INV-04 | A cyclic dependency graph must not drop tasks; cyclic members append after the acyclic prefix. | `dagSorter.ts::topologicalSort` tail block |
| INV-05 | Critical path considers only tasks where `status !== 'DONE'`. | `dagSorter.ts::computeCriticalPath` |
| INV-06 | An AI endpoint never returns 5xx because a model was unreachable. | `ai_service.py::_call_llm` |
| INV-07 | Passwords are truncated to 72 bytes before bcrypt (library limit). | `security.py` |

---

## 4. HTTP API reference

Base URL: `/api`. All responses JSON. All endpoints except `POST /auth/register`,
`POST /auth/login`, `POST /auth/google` and `GET /health` require `Authorization: Bearer <jwt>`.

### 4.1 Authentication

| Method | Path | Body | Success | Errors |
|:--|:--|:--|:--|:--|
| POST | `/auth/register` | `{email, password, full_name, role?, skills?}` | `201` `Token` | `400` email taken |
| POST | `/auth/login` | `{email, password}` | `200` `Token` | `401` bad credentials |
| POST | `/auth/google` | `{credential}` | `200` `Token` | `400` invalid/missing email |
| GET | `/auth/me` | — | `200` `UserOut` | `401` |

```jsonc
// Token
{ "access_token": "<jwt>", "token_type": "bearer",
  "user": { "id": 1, "email": "...", "full_name": "...", "role": "PM|MEMBER", "skills": "a,b,c" } }
```

### 4.2 Users

| Method | Path | Notes |
|:--|:--|:--|
| GET | `/users` | Returns `UserWithWIPOut[]` — adds `active_tasks_count`, `wip_points`. |
| PATCH | `/users/{user_id}` | Body `{role?, skills?, full_name?}`. **Requires `PM`** via `require_role(RoleEnum.PM)`. `404` if absent. |

### 4.3 Projects & sprints

| Method | Path | Notes |
|:--|:--|:--|
| GET | `/projects` | All projects. |
| POST | `/projects` | `{name, description?}` → `201`. Owner = caller. **Any authenticated user may create.** |
| GET | `/projects/{id}` | `404` if absent. |
| GET | `/sprints?project_id=` | `project_id` is **required**. |
| POST | `/sprints` | `{project_id, name, goal?, start_date, end_date}` → `201`. |
| GET | `/sprints/{id}/stats` | `{total_tasks, blocked_tasks, ...}`. |

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

**Authorisation gap:** none of the task endpoints check that the caller owns or belongs to the
project. Any authenticated user can read, mutate and delete any task in any project. Tracked as
RISK-03 in D6 §4.

### 4.5 Statistics

| Method | Path | Returns |
|:--|:--|:--|
| GET | `/stats/workload` | Per user: `{user_id, full_name, email, role, skills[], active_tasks_count, total_complexity_points, is_overloaded}`. Overload heuristic: `points > 10 or active > 5`. Active = TODO ∪ IN_PROGRESS ∪ BLOCKED. |
| GET | `/stats/delayed-tasks?project_id=` | `{task_id, title, status, priority, due_date, days_overdue, assignee_name}` for non-DONE tasks past `due_date`. |

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

**C4 — IndexedDB.** Key `koshi_tasks_v1` (via `idb-keyval`), value `Task[]` in C3 shape. The `_v1`
suffix is the migration mechanism: **any breaking change to `Task` must bump the key**, since no
migration code exists and stale values are read back unvalidated.

**C5 — JWT.** `{"sub": "<user_id as string>", "role": "PM|MEMBER", "exp": <unix>}`. HS256.
Default lifetime 7 days. `get_current_user` reads only `sub`; `role` is informational and is
re-read from the database on every request.

## 7. Environment contract (C7)

| Variable | Default | Notes |
|:--|:--|:--|
| `DATABASE_URL` | `sqlite:///./data/koshi.db` | Directory must exist. |
| `JWT_SECRET` | `koshi_super_secret_jwt_key_2026_academic_spec` | ⚠️ Insecure default, also hardcoded in `docker-compose.yml`. |
| `AI_API_URL` | `https://api.openai.com/v1/chat/completions` | Tier 1 fires **only if** this contains `"openai"` **and** `AI_API_KEY` is set. |
| `AI_API_KEY` | `""` | Empty disables Tier 1. |
| `AI_MODEL_NAME` | `gpt-4o-mini` | |
| `OLLAMA_URL` | `http://localhost:11434/v1/chat/completions` | Compose overrides to `host.docker.internal`. |
| `OLLAMA_MODEL` | `qwen2.5:7b` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | |

> The `"openai" in AI_API_URL` substring test means pointing `AI_API_URL` at any other
> OpenAI-compatible vendor **silently disables Tier 1** even with a valid key. Non-obvious; document
> any change here.
