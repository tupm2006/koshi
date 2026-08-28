# D8 — Requirements Traceability Matrix (RTM)

**Purpose:** link **requirement → work item → code → test** so that the impact of any change can be
assessed in both directions.

- **Forward** (*"I'm changing FR-GRAPH-04 — what breaks?"*) → §2.
- **Reverse** (*"I'm editing `dagSorter.ts` — what does it serve, and what proves it still works?"*) → §3.

All paths are relative to the repository root. All requirement IDs come from D1 §3.
**Last verified against code:** 2026-08-28.

---

## 1. Legend

| Symbol | Verification status |
|:--:|:--|
| ✅ | Automated test exists and passes |
| 🟡 | Manually verified only |
| ❌ | **Unverified** — no test, no documented manual check |
| ⚠️ | Implementation diverges from a requirement or another document |

---

## 2. Forward trace — requirement → implementation → verification

### 2.1 Interaction

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-INT-01 | View toggle | `source/frontend/lib/keyboard.ts` (`b`), `App.vue`, `taskStore.ts::viewMode` | manual | 🟡 |
| FR-INT-02 | Table traversal | `lib/keyboard.ts` (`j`/`k`/`↓`/`↑`), `taskStore.ts::selectedIndex` | manual | 🟡 |
| FR-INT-03 | Kanban 2D traversal | `lib/keyboard.ts` (`h`/`l`), `taskStore.ts::kanbanColIndex`/`kanbanRowIndex`, `KanbanBoard.vue` | manual | 🟡 |
| FR-INT-04 | Status cycle | `taskStore.ts::STATUS_ORDER` + `lib/keyboard.ts` (`Space`) | server twin ✅ `test_tasks.py` | 🟡 |
| FR-INT-05 | Lateral shift | `lib/keyboard.ts` (`H`/`L`), `taskStore.ts::syncKanbanFocusToTask` | manual | 🟡 |
| FR-INT-06 | Priority hotkeys | `lib/keyboard.ts` (`1`–`4`) | manual | 🟡 |
| FR-INT-07 | Create / edit / inspect | `lib/keyboard.ts` (`n`/`i`/`Enter`), `CreateTaskModal.vue`, `TaskDetailModal.vue` | manual | ⚠️🟡 README says `c`/`Enter` — D7 DEC-005 |
| FR-INT-08 | Delete | `lib/keyboard.ts` (`d`/`Backspace`), `taskStore.ts::deleteTask` | manual | 🟡 |
| FR-INT-09 | Search focus | `lib/keyboard.ts` (`/`), `taskStore.ts::filter.searchQuery` | manual | 🟡 |
| FR-INT-10 | Input guards | `lib/keyboard.ts::isInputActive` | — | ❌ |
| FR-INT-11 | Capture-phase Escape | `App.vue` (`addEventListener('keydown', h, true)`) | manual | 🟡 |
| FR-INT-12 | Theme toggle | `lib/keyboard.ts` (`t`), `stores/themeStore.ts` | manual | 🟡 |
| FR-INT-13 | Help modal | `lib/keyboard.ts` (`?`), `ShortcutsHelpModal.vue` | manual | 🟡 |
| FR-INT-14 | Mobile nav | `MobileBottomNav.vue`, `TaskTable.vue` swipe handlers | manual | 🟡 |

### 2.2 Domain model

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-DOM-01 | Status enum | `types/task.ts::TaskStatus`, `entities.py::TaskStatusEnum`, `db/schema.sql` CHECK | ✅ `test_tasks.py` | ✅ |
| FR-DOM-02 | Cycle invariant | `taskStore.ts::STATUS_ORDER` **and** `routers/tasks.py::cycle_task_status` | ✅ `test_task_lifecycle_and_comments` | ⚠️✅ duplicated logic — RISK-04 |
| FR-DOM-03 | Priority enum | `types/task.ts`, `entities.py::TaskPriorityEnum` | ✅ `test_tasks.py` | ✅ |
| FR-DOM-04 | Complexity | `entities.py::complexity_points`, `schemas/task.py` (`ge=1,le=8`) | ✅ create path | ⚠️✅ no bound on update — F-08 |
| FR-DOM-05 | Dependencies | `entities.py::dependencies` property over `dependencies_json`, `types/task.ts::dependencies` | ✅ round-trip only | ⚠️❌ unresolvable server-side — F-01 |
| FR-DOM-06 | Acceptance criteria | `entities.py::acceptance_criteria`, `TaskDetailModal.vue` | ✅ round-trip | ✅ |
| FR-DOM-07 | Blocking reason | `entities.py::blocking_reason` | — | ⚠️❌ not enforced — F-09 |
| FR-DOM-08 | Project/sprint/assignee | `entities.py` relationships, `routers/projects.py`, `routers/sprints.py` | ✅ `test_tasks.py` | ✅ |
| FR-DOM-09 | Comments | `entities.py::Comment`, `routers/tasks.py::add_comment` | ✅ `test_tasks.py` | ✅ |

### 2.3 Graph engine — **the least-verified, highest-complexity area**

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-GRAPH-01 | Topological sort | `lib/dagSorter.ts::topologicalSort` | — | ❌ **GAP-01** |
| FR-GRAPH-02 | Deterministic tie-break | `dagSorter.ts` queue sort (priority → dueDate → createdAt) | — | ❌ **GAP-01** |
| FR-GRAPH-03 | Cycle tolerance | `dagSorter.ts` tail block (`result.length < tasks.length`) | — | ❌ ⚠️ diverges from SRS — D7 DEC-002 |
| FR-GRAPH-04 | Critical path | `dagSorter.ts::computeCriticalPath` (memoised longest weighted path) | — | ❌ **GAP-01** |
| FR-GRAPH-05 | DAG visualiser | `DAGVisualizerModal.vue`, `lib/keyboard.ts` (`v`) | manual | 🟡 |

### 2.4 Persistence & sync

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-PERS-01 | IndexedDB write | `taskStore.ts` `set('koshi_tasks_v1', …)` via `idb-keyval` | — | 🟡 |
| FR-PERS-02 | Offline operation | `taskStore.ts` local-first ordering (INV-03) | — | 🟡 |
| FR-PERS-03 | Passive offline badge | `taskStore.ts::isBackendConnected`, `App.vue` | — | 🟡 |
| FR-PERS-04 | Token persistence | `services/api.ts::setToken` → `localStorage['koshi_jwt_token']` | — | 🟡 |
| FR-PERS-05 | JSON export/import | `taskStore.ts` | — | ❌ |

### 2.5 Identity & access

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-AUTH-01 | Register / login | `routers/auth.py`, `security.py` (bcrypt) | ✅ `test_register_and_login_flow` | ✅ |
| FR-AUTH-02 | Google OAuth | `routers/auth.py::google_auth` | ✅ `test_google_oauth_and_user_management_flow` | ⚠️✅ test exercises the **unverified** fallback path — RISK-01 |
| FR-AUTH-03 | Bearer required | `security.py::get_current_user`, `Depends` on every router | ✅ `test_unauthenticated_request_rejected` | ✅ |
| FR-AUTH-04 | PM role gate | `security.py::require_role`, `routers/users.py::update_user_profile` | ✅ positive case only | ⚠️✅ negative case untested — GAP-02; function restored in DEC-004 |
| FR-AUTH-05 | First user → PM | `routers/auth.py::google_auth` | — | ❌ |
| *(implicit)* | Project-scoped authz | **absent** | — | ❌ **RISK-03** |

### 2.6 AI workflows

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-AI-01 | Weekly summary | `routers/ai.py::generate_weekly_summary`, `ai_service.py::generate_weekly_summary`, `WeeklySummaryModal.vue` | ✅ `test_mandated_ai_features` | ✅ shape only |
| FR-AI-02 | Meeting minutes | `routers/ai.py::extract_meeting_minutes`, `ai_service.py::extract_meeting_minutes`, `MeetingMinutesModal.vue` | ✅ same | ✅ shape only |
| FR-AI-03 | Assignment recommendation | `routers/ai.py::recommend_assignment`, `ai_service.py::recommend_task_assignment`, `WorkloadAssignModal.vue` | ✅ same | ✅ shape only |
| FR-AI-04 | Goal decomposition | `routers/ai.py::decompose_goal` (hardcoded), `lib/aiDecomposer.ts`, `AIDecomposerModal.vue` | ✅ asserts `len == 3` | ⚠️✅ **test pins the stub** — D5 §5, DEC-003 |
| FR-AI-05 | Git diff analysis | `lib/gitParser.ts` (real, orphaned) vs `services/api.ts::analyzeGitDiff` (stub, live), `GitDiffModal.vue` | — | ⚠️❌ **DEC-006**; SRS claims a test that does not exist |
| FR-AI-06 | 3-tier cascade | `ai_service.py::_call_llm`, `_deterministic_fallback` | ✅ implicitly — CI runs with no key and no Ollama | ✅ |
| FR-AI-07 | Workload stats | `routers/stats.py::get_member_workloads` | ✅ `test_workload_and_delayed_tasks_stats` | ✅ |
| FR-AI-08 | Delayed tasks | `routers/stats.py::get_delayed_tasks` | ✅ same | 🟡 no overdue fixture |

### 2.7 Non-functional

| Req | Implementation | Verification | St |
|:--|:--|:--|:--:|
| NFR-01 | Local-first ordering, `taskStore.ts` | — | ❌ unmeasured |
| NFR-02 | `themeStore.ts` transition-freeze injection, `app.css` | manual | 🟡 |
| NFR-03 | — | — | ❌ **claim unsupported** |
| NFR-04 | Tailwind slate palette, `TaskTable.vue` DONE styling | — | ❌ |
| NFR-05 | `index.html` synchronous head script | manual | 🟡 |
| NFR-06 | `ai_service.py` httpx timeouts (10 s / 4 s) | — | 🟡 |
| NFR-07 | whole backend | ✅ `pytest -q` → 6 passed | ✅ |
| NFR-08 | — | — | ❌ **no frontend tests exist** |

---

## 3. Reverse trace — file → requirements → tests

Use this before editing. "Zone" is the D6 §1 autonomy level.

### 3.1 Frontend

| File | Serves | Verified by | Zone |
|:--|:--|:--|:--:|
| `lib/keyboard.ts` | FR-INT-01…13 | none | 🟡 |
| `lib/dagSorter.ts` | FR-GRAPH-01…04 | **none** | 🟡 ⚠️ test first (P4) |
| `lib/gitParser.ts` | FR-AI-05 | **none** | 🟡 |
| `lib/aiDecomposer.ts` | FR-AI-04 (tier 1) | none | 🟡 |
| `stores/taskStore.ts` | FR-INT-02…09, FR-DOM-02, FR-PERS-01…03, FR-PERS-05 | none | 🟡 **widest blast radius** |
| `stores/themeStore.ts` | FR-INT-12, NFR-02, NFR-05 | none | 🟢 |
| `services/api.ts` | FR-AUTH-01…04, FR-PERS-04, FR-AI-01…05 · **contract C1↔C3** | backend side only | 🔴 for shapes |
| `types/task.ts` | **contract C3** — every component | `pnpm run build` | 🔴 |
| `index.html` | NFR-05 | manual | 🟡 |
| `App.vue` | FR-INT-01, FR-INT-11, FR-PERS-03 | none | 🟡 |
| `components/TaskTable.vue` | FR-INT-02, FR-INT-14, NFR-04 | none | 🟢 styling / 🟡 logic |
| `components/KanbanBoard.vue` | FR-INT-03, FR-INT-05, INV-01 | none | 🟢 styling / 🟡 logic |
| `components/TaskDetailModal.vue` | FR-DOM-06, FR-DOM-09, FR-INT-07 | none | 🟡 |
| `components/*Modal.vue` (AI) | FR-AI-01…05 | none | 🟢 styling / 🟡 logic |

### 3.2 Backend

| File | Serves | Verified by | Zone |
|:--|:--|:--|:--:|
| `app/security.py` | FR-AUTH-01, 03, 04 · contract C5 | `test_auth.py` | 🔴 |
| `app/routers/auth.py` | FR-AUTH-01, 02, 05 | `test_auth.py` | 🔴 |
| `app/routers/users.py` | FR-AUTH-04 | `test_auth.py` (positive only) | 🔴 |
| `app/routers/tasks.py` | FR-DOM-02, 08, 09 · contract C1 | `test_tasks.py` | 🟡 logic / 🔴 shapes |
| `app/routers/projects.py` | FR-DOM-08 | `test_tasks.py` | 🟡 |
| `app/routers/sprints.py` | FR-DOM-08 | `test_tasks.py` | 🟡 |
| `app/routers/stats.py` | FR-AI-07, 08 | `test_ai_and_stats.py` | 🟡 |
| `app/routers/ai.py` | FR-AI-01…04 | `test_ai_and_stats.py` | 🟡 (🔴 for FR-AI-04) |
| `app/services/ai_service.py` | FR-AI-01…03, 06 | `test_ai_and_stats.py` (tier-3 path) | 🟡 ⚠️ prompt text drives fallback routing — F-10 |
| `app/models/entities.py` | FR-DOM-01…09 · **contract C2** | all backend tests | 🔴 |
| `app/schemas/*.py` | **contract C1** | all backend tests | 🔴 |
| `app/main.py` | seeding, CORS, mounting | `conftest.py` imports it | 🟡 (🔴 for CORS — RISK-05) |
| `app/config.py` | **contract C7** | — | 🔴 (secrets) |
| `db/schema.sql` | reference only | — | 🟢 ⚠️ stale — D4 §2.3 |

### 3.3 Build & deploy

| File | Serves | Verified by | Zone |
|:--|:--|:--|:--:|
| `vite.config.ts` | build paths, dev `/api` proxy | `pnpm run build` | 🟡 |
| `tsconfig.json` | type gate | `vue-tsc -b` | 🟡 |
| `Dockerfile` | frontend image | manual | 🟡 ⚠️ ignores lockfiles — F/DEC-007 |
| `docker-compose.yml` | topology · contract C7 | manual | 🟡 |
| `nginx.conf` | SPA fallback + `/api` proxy | manual | 🟡 |

---

## 4. Impact analysis quick reference

| If you change… | You must also touch | And re-verify |
|:--|:--|:--|
| A key binding | `lib/keyboard.ts`, `ShortcutsHelpModal.vue`, `README.md`, D1 §3.1, D8 §2.1 | manual |
| The status cycle order | `taskStore.ts::STATUS_ORDER`, `routers/tasks.py::cycle_task_status`, `KanbanBoard.vue`, D4 §3.1 | `pytest` 🔴 **RED zone** |
| `types/task.ts` | every component, `services/api.ts`, D4 §5, **bump `koshi_tasks_v1`** | `pnpm run build` 🔴 |
| A Pydantic schema | matching `services/api.ts` method, D4 §4 | `pytest` + `pnpm run build` 🔴 |
| An ORM column | `entities.py`, `db/schema.sql`, affected schemas, **migration plan** (RISK-10) | `pytest` 🔴 |
| Critical-path weights | `dagSorter.ts`, D4 §3.2 | **write GAP-01 tests first** |
| An AI prompt | `ai_service.py` only — **check `_deterministic_fallback` substring routing** (F-10) | `pytest` |
| Env var names | `config.py`, `docker-compose.yml`, D4 §7 | manual |
| Build paths | `vite.config.ts`, `tsconfig.json`, `Dockerfile`, `docker-compose.yml`, D3 §6 | `pnpm run build` + `pytest` |

## 5. Coverage roll-up

| Area | Requirements | ✅ | 🟡 | ❌ |
|:--|:--:|:--:|:--:|:--:|
| Interaction (FR-INT) | 14 | 0 | 13 | 1 |
| Domain (FR-DOM) | 9 | 7 | 0 | 2 |
| Graph (FR-GRAPH) | 5 | 0 | 1 | 4 |
| Persistence (FR-PERS) | 5 | 0 | 4 | 1 |
| Auth (FR-AUTH) | 5 | 4 | 0 | 1 |
| AI (FR-AI) | 8 | 6 | 1 | 1 |
| Non-functional (NFR) | 8 | 1 | 3 | 4 |
| **Total** | **54** | **18** | **22** | **14** |

**Reading.** 33% automated, 41% manual-only, 26% unverified. Automation is concentrated almost
entirely in the backend HTTP surface. The frontend — which carries the product's distinguishing
logic (graph engine, keyboard model, local-first store) — has **no automated verification at all**.

**Highest-leverage next work item:** D5 GAP-01 — add Vitest and test `lib/dagSorter.ts`. It converts
4 ❌ rows to ✅, requires no framework mocking (the module is pure), and protects the code most
likely to be silently broken by an AI edit.
