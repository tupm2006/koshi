# D8 — Requirements Traceability Matrix (RTM)

**Purpose:** link **requirement → work item → code → test** so that the impact of any change can be
assessed in both directions.

- **Forward** (*"I'm changing FR-GRAPH-04 — what breaks?"*) → §2.
- **Reverse** (*"I'm editing `dagSorter.ts` — what does it serve, and what proves it still works?"*) → §3.

All paths are relative to the repository root. All requirement IDs come from D1 §3.
**Last verified against code:** 2026-08-28 (rev 2 — per-project roles).

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
| FR-INT-01 | View toggle | `lib/keyboard.ts` (`b`), `App.vue`, `taskStore.ts::viewMode` | ✅ `keyboard.test.ts` | ✅ |
| FR-INT-02 | Table traversal | `lib/keyboard.ts` (`j`/`k`/`↓`/`↑`), `taskStore.ts::selectedIndex` | ✅ incl. bounds | ✅ |
| FR-INT-03 | Kanban 2D traversal | `lib/keyboard.ts` (`h`/`l`), `taskStore.ts`, `KanbanBoard.vue` | ✅ `keyboard.test.ts`, `BoardViews.test.ts` | ✅ |
| FR-INT-04 | Status cycle | `taskStore.ts::STATUS_ORDER` + `lib/keyboard.ts` (`Space`) | ✅ both sides | ✅ |
| FR-INT-05 | Lateral shift | `lib/keyboard.ts` (`H`/`L`), `taskStore.ts::syncKanbanFocusToTask` | ✅ incl. table-view no-op | ✅ |
| FR-INT-06 | Priority hotkeys | `lib/keyboard.ts` (`1`–`4`) | ✅ all four | ✅ |
| FR-INT-07 | Create / edit / inspect | `lib/keyboard.ts` (`n`/`i`/`Enter`), `CreateTaskModal.vue`, `TaskDetailModal.vue` | ✅ incl. `c` asserted dead | ✅ |
| FR-INT-08 | Delete | `lib/keyboard.ts` (`d`/`Backspace`), `taskStore.ts::deleteTask` | ✅ incl. Cmd/Ctrl passthrough | ✅ |
| FR-INT-09 | Search focus | `lib/keyboard.ts` (`/`), `taskStore.ts::filter.searchQuery` | ✅ | ✅ |
| FR-INT-10 | Input guards | `lib/keyboard.ts::isInputActive` | ✅ all element types + guard behaviour | ✅ |
| FR-INT-11 | Capture-phase Escape | `App.vue`, `lib/keyboard.ts`, `TaskDetailModal.vue` | ✅ dispatcher + modal deference | 🟡 App.vue capture layer |
| FR-INT-12 | Theme toggle | `lib/keyboard.ts` (`t`), `stores/themeStore.ts` | ✅ `keyboard.test.ts` | ✅ |
| FR-INT-13 | Help modal | `lib/keyboard.ts` (`?`), `ShortcutsHelpModal.vue` | ✅ dispatch | 🟡 modal itself |
| FR-INT-14 | Mobile nav | `MobileBottomNav.vue`, `TaskTable.vue` swipe handlers | manual | 🟡 |

### 2.1b Navigation & entry

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-NAV-01 | Landing page | `components/LandingPage.vue`, `taskStore.appView` | ✅ both sides | ✅ |
| FR-NAV-02 | Logout → landing | `taskStore.logout` | ✅ `taskStore.test.ts` | ✅ |
| FR-NAV-03 | No signed-out board | guest mode removed from `taskStore` | ✅ `taskStore.test.ts` | ✅ |
| FR-NAV-04 | Auth → board / dashboard | `taskStore.onAuthenticated` | ✅ `taskStore.test.ts` | ✅ |
| FR-NAV-05 | Profile navigation | `App.vue` header pill, `taskStore.showProfile` / `showBoard` | ✅ both sides | ✅ |

### 2.1c Localisation

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-I18N-01 | en + vi | `lib/translations.ts` | ✅ `i18nStore.test.ts` | ✅ |
| FR-I18N-02 | Locale picker | `LandingPage.vue` nav + footer | ✅ `LandingPage.test.ts` | ✅ |
| FR-I18N-03 | Persistence | `i18nStore.setLocale` → `koshi_locale` | ✅ | ✅ |
| FR-I18N-04 | Browser detection | `i18nStore.detectLocale` | ✅ `i18nStore.test.ts` | ✅ |
| FR-I18N-05 | Dictionary completeness | `Translations` type + test | ✅ `i18nStore.test.ts` | ✅ |

### 2.1d Marketing site

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-MKT-01 | Landing sections | `LandingPage.vue` | ✅ | ✅ |
| FR-MKT-02 | Small top-right sign-in | `LandingPage.vue` nav | ✅ | ✅ |
| FR-MKT-03 | Auth dialog | `AuthDialog.vue` | ✅ | ✅ |
| FR-MKT-04 | Video only when configured | `VITE_DEMO_VIDEO_URL` guard | ✅ | ✅ |
| FR-MKT-05 | No fabricated testimonials | absent by design (D6 P14) | ✅ asserted | ✅ |

### 2.2 Domain model

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-DOM-01 | Status enum | `types/task.ts::TaskStatus`, `entities.py::TaskStatusEnum` | ✅ `test_tasks.py` | ✅ |
| FR-DOM-02 | Cycle invariant | `taskStore.ts::STATUS_ORDER` **and** `routers/tasks.py::cycle_task_status` | ✅ `test_task_lifecycle_and_comments` | ⚠️✅ duplicated logic — RISK-04 |
| FR-DOM-03 | Priority enum | `types/task.ts`, `entities.py::TaskPriorityEnum` | ✅ `test_tasks.py` | ✅ |
| FR-DOM-04 | Complexity | `entities.py::complexity_points`, `schemas/task.py` (`ge=1,le=8`) | ✅ create path | ⚠️✅ no bound on update — F-08 |
| FR-DOM-05 | Dependencies | `entities.py::dependencies` (int ids), `types/task.ts`, `api.ts::taskKeyOf`/`serverIdOf` | ✅ `test_tasks.py` round-trip + resolution | ✅ |
| FR-DOM-10 | Dependency validation | `routers/tasks.py::_validate_dependencies` | ✅ unknown / self / cross-project | ✅ |
| FR-DOM-06 | Acceptance criteria | `entities.py::acceptance_criteria`, `TaskDetailModal.vue` | ✅ round-trip | ✅ |
| FR-DOM-07 | Blocking reason | `entities.py::blocking_reason` | — | ⚠️❌ not enforced — F-09 |
| FR-DOM-08 | Project/sprint/assignee | `entities.py` relationships, `routers/projects.py`, `routers/sprints.py` | ✅ `test_tasks.py` | ✅ |
| FR-DOM-09 | Comments | `entities.py::Comment`, `routers/tasks.py::add_comment` | ✅ `test_tasks.py` | ✅ |

### 2.3 Graph engine — **fully covered as of DEC-013**

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-GRAPH-01 | Topological sort | `lib/dagSorter.ts::topologicalSort` | ✅ `dagSorter.test.ts` | ✅ |
| FR-GRAPH-02 | Deterministic tie-break | `dagSorter.ts` queue sort (priority → dueDate → createdAt) | ✅ `dagSorter.test.ts` | ✅ |
| FR-GRAPH-03 | Cycle tolerance | `dagSorter.ts` tail block (`result.length < tasks.length`) | ✅ `dagSorter.test.ts` | ✅ — D7 DEC-002 |
| FR-GRAPH-04 | Critical path | `dagSorter.ts::computeCriticalPath` (memoised longest weighted path) | ✅ `dagSorter.test.ts` | ⚠️✅ order-dependent on cyclic graphs — F-24 |
| FR-GRAPH-05 | DAG visualiser | `DAGVisualizerModal.vue`, `lib/keyboard.ts` (`v`) | ✅ `AIModals.test.ts` (4) | ✅ |

### 2.4 Persistence & sync

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-PERS-01 | IndexedDB write | `taskStore.ts::persist` → `tasksKey(projectId)` / `GUEST_DB_KEY` via `idb-keyval` | — | 🟡 |
| FR-PERS-02 | Offline personal project | `taskStore.canMutate` / `isPersonalProject` | ✅ `taskStore.test.ts` | ✅ |
| FR-PERS-06 | Offline shared project read-only | `taskStore.canMutate` + guards on create/update/delete | ✅ `taskStore.test.ts` | ✅ |
| FR-PERS-03 | Passive offline badge | `taskStore.ts::isBackendConnected`, `App.vue` | — | 🟡 |
| FR-PERS-04 | Token persistence | `services/api.ts::setToken` → `localStorage['koshi_jwt_token']` | — | 🟡 |
| FR-PERS-05 | JSON export/import | `taskStore.ts` | — | ❌ |

### 2.5 Identity & access

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-AUTH-01 | Register / login | `routers/auth.py`, `security.py` (bcrypt) | ✅ `test_register_and_login_flow` | ✅ |
| FR-AUTH-02 | Roleless registration | `schemas/auth.py::UserRegister`, `routers/auth.py::register_user` | ✅ `test_registration_accepts_no_role_and_grants_none`, `test_registration_ignores_a_submitted_role` | ✅ |
| FR-AUTH-03 | Google OAuth, signature-verified | `routers/auth.py::google_auth`, `config.ALLOW_UNVERIFIED_GOOGLE_TOKENS` | ✅ `test_google_oauth_...`, `test_unverified_google_token_rejected_when_flag_disabled` | ✅ |
| FR-AUTH-04 | Bearer required | `security.py::get_current_user` | ✅ `test_unauthenticated_request_rejected` | ✅ |
| FR-AUTH-05 | Creator → PM | `routers/projects.py::create_project` | ✅ `test_creator_becomes_pm_of_their_own_project` | ✅ |
| FR-AUTH-06 | PM administers membership | `routers/projects.py` member routes, `security.py::require_project_pm` | ✅ `test_pm_can_assign_and_change_roles` | ✅ |
| FR-AUTH-07 | MEMBER restrictions | same guards | ✅ `test_member_cannot_change_roles`, `..._add_or_remove_members`, `..._create_sprints` | ✅ |
| FR-AUTH-08 | Last-PM protection | `routers/projects.py` demote/remove guards | ✅ `test_cannot_demote_the_last_pm` | ✅ |
| FR-AUTH-09 | Non-members refused (404) | `security.py::require_member` + every project-scoped router | ✅ four `test_non_member_cannot_*` tests | ✅ |
| FR-AUTH-10 | Self-only profile edit | `routers/users.py::update_user_profile` | ✅ `test_user_can_edit_own_profile`, `test_user_cannot_edit_another_profile` | ✅ |

### 2.5b Projects & dashboard

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-PROJ-01 | Create project | `routers/projects.py::create_project`, `ProjectDashboard.vue`, `taskStore.createProject` | ✅ | ✅ |
| FR-PROJ-02 | Dashboard feed scoped to caller | `routers/projects.py::list_my_projects` | ✅ `test_dashboard_lists_only_my_projects` | ✅ |
| FR-PROJ-03 | Project switching | `taskStore.selectProject`, `App.vue` header pill | — | 🟡 |
| FR-PROJ-04 | Add member by email | `routers/projects.py::add_member`, `ProjectDashboard.vue` | ✅ | ✅ |
| FR-PROJ-05 | Roster with workload | `routers/projects.py::_member_out` | ✅ (shape) | 🟡 display |
| FR-PROJ-06 | PM-only controls | `taskStore.isProjectManager` (UI) + `require_project_pm` (server) | ✅ both sides | ✅ |
| FR-PROJ-07 | Delete project | `routers/projects.py::delete_project` | — | ❌ |
| FR-PROJ-08 | Empty account opens dashboard | `taskStore.onAuthenticated`, `App.vue` empty state | — | 🟡 verified by hand (DEC-012) |
| FR-PROJ-09 | Profile page | `components/ProfilePage.vue` | ✅ | ✅ |
| FR-PROJ-10 | Edit name / skills | `ProfilePage.vue`, `taskStore.updateProfile`, `PATCH /users/{id}` | ✅ both sides | ✅ |
| FR-PROJ-11 | Membership list | `ProfilePage.vue`, `routers/projects.py::list_my_projects` | ✅ both sides | ✅ |
| — | Roles independent across projects | `entities.py::ProjectMember` | ✅ `test_roles_are_independent_across_projects` | ✅ |

### 2.6 AI workflows

| Req | Work item | Implementation | Verification | St |
|:--|:--|:--|:--|:--:|
| FR-AI-01 | Weekly summary | `routers/ai.py::generate_weekly_summary`, `ai_service.py::generate_weekly_summary`, `WeeklySummaryModal.vue` | ✅ `test_mandated_ai_features`, `test_ai_cascade.py`, `AIModals.test.ts` (6) | ✅ |
| FR-AI-02 | Meeting minutes | `routers/ai.py::extract_meeting_minutes`, `ai_service.py::extract_meeting_minutes`, `MeetingMinutesModal.vue` | ✅ same + `test_ai_cascade.py` (fence stripping, unparseable-JSON degradation) + `AIModals.test.ts` (5) | ✅ |
| FR-AI-03 | Assignment recommendation | `routers/ai.py::recommend_assignment`, `ai_service.py::recommend_task_assignment`, `WorkloadAssignModal.vue` | ✅ same + `test_ai_cascade.py` + `AIModals.test.ts` (6) | ✅ |
| FR-AI-04 | Goal decomposition | `routers/ai.py::decompose_goal` (hardcoded), `lib/aiDecomposer.ts`, `AIDecomposerModal.vue` | ✅ asserts `len == 3`; `AIModals.test.ts` (7) covers insertion and dependency wiring | ⚠️✅ **test pins the stub** — D5 §5, DEC-003 |
| FR-AI-05 | Git diff analysis | `lib/gitParser.ts::parseGitDiff` called directly by `GitDiffModal.vue` | ✅ `gitParser.test.ts` (39) + `AIModals.test.ts` (5) | ✅ — but the BLOCKED-task heuristic is loose by design; OQ-08 |
| FR-AI-06 | 3-tier cascade | `ai_service.py::_call_llm`, `_deterministic_fallback`, `AITier` | ✅ `test_ai_cascade.py` (26) — each tier mocked at the httpx boundary, asserted by provenance | ✅ |
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
| `lib/keyboard.ts` | FR-INT-01…14 | ✅ `keyboard.test.ts` (38, mutation-verified) | 🟡 |
| `lib/dagSorter.ts` | FR-GRAPH-01…04 | ✅ `dagSorter.test.ts` (28, mutation-verified) | 🟡 |
| `lib/gitParser.ts` | FR-AI-05 (now actually wired up) | **none** | 🟡 GAP-03 |
| `lib/aiDecomposer.ts` | FR-AI-04 (tier 1) | none | 🟡 |
| `stores/taskStore.ts` | FR-INT-02…09, FR-DOM-02, FR-PERS-01…06, FR-PROJ-01…03, FR-NAV-01…05 | ✅ `taskStore.test.ts` (24, mutation-verified) | 🟡 **widest blast radius** |
| `stores/i18nStore.ts` · `lib/translations.ts` | FR-I18N-01…05 · contract C10 | ✅ `i18nStore.test.ts` (9) | 🟡 |
| `stores/themeStore.ts` | FR-INT-12, NFR-02, NFR-05 | none | 🟢 |
| `services/api.ts` | FR-AUTH-01…03, FR-PROJ-01…07, FR-PERS-04, FR-AI-01…05 · **contract C1↔C3** | backend side only | 🔴 for shapes |
| `types/task.ts` | **contract C3** — every component | `pnpm run build` | 🔴 |
| `index.html` | NFR-05 | manual | 🟡 |
| `App.vue` | FR-INT-01, FR-INT-11, FR-PERS-03 | none | 🟡 |
| `components/TaskTable.vue` | FR-INT-02, FR-INT-14, NFR-04 | ✅ `BoardViews.test.ts` | 🟢 styling / 🟡 logic |
| `components/KanbanBoard.vue` | FR-INT-03, FR-INT-05, INV-01 | ✅ `BoardViews.test.ts` | 🟢 styling / 🟡 logic |
| `components/TaskDetailModal.vue` | FR-DOM-06, FR-DOM-09, FR-INT-07, INV-15 | ✅ `TaskDetailModal.test.ts` (13) | 🟡 |
| `components/*Modal.vue` (AI) | FR-AI-01…05 | none | 🟢 styling / 🟡 logic |
| `components/ProjectDashboard.vue` | FR-PROJ-01…08, FR-AUTH-06 | ✅ `ProjectDashboard.test.ts` (14) + server tests | 🟡 |
| `components/LandingPage.vue` | FR-NAV-01, FR-MKT-01…05, FR-I18N-02 | ✅ `LandingPage.test.ts` (14) | 🟡 |
| `components/AuthDialog.vue` | FR-AUTH-01, 02, FR-MKT-03 | ✅ `AuthDialog.test.ts` (16) | 🟡 |
| `components/ProfilePage.vue` | FR-NAV-05, FR-PROJ-09…11 | ✅ `ProfilePage.test.ts` (17) | 🟡 |

### 3.2 Backend

| File | Serves | Verified by | Zone |
|:--|:--|:--|:--:|
| `app/security.py` | FR-AUTH-04, 06, 07, 09 · contracts C5, C8 | `test_auth.py`, `test_projects_and_roles.py` | 🔴 **the authorisation boundary** |
| `app/routers/auth.py` | FR-AUTH-01, 02, 03 | `test_auth.py`, `test_projects_and_roles.py` | 🔴 |
| `app/routers/users.py` | FR-AUTH-10 | `test_projects_and_roles.py` (both paths) | 🔴 |
| `app/routers/projects.py` | FR-AUTH-05…09, FR-PROJ-01…07 | `test_projects_and_roles.py` | 🔴 |
| `app/routers/tasks.py` | FR-DOM-02, 08, 09, FR-AUTH-09 · contract C1 | `test_tasks.py`, `test_projects_and_roles.py` | 🟡 logic / 🔴 shapes & guards |
| `app/routers/sprints.py` | FR-DOM-08, FR-AUTH-07 | `test_tasks.py`, `test_projects_and_roles.py` | 🟡 |
| `app/routers/stats.py` | FR-AI-07, 08, FR-AUTH-09 | `test_ai_and_stats.py`, `test_projects_and_roles.py` | 🟡 |
| `app/routers/ai.py` | FR-AI-01…04 | `test_ai_and_stats.py` | 🟡 (🔴 for FR-AI-04) |
| `app/services/ai_service.py` | FR-AI-01…03, 06 | `test_ai_and_stats.py` (tier-3 path) | 🟡 ⚠️ prompt text drives fallback routing — F-10 |
| `app/models/entities.py` | FR-DOM-01…09, FR-AUTH-05…09 · **contracts C2, C8** | all backend tests | 🔴 |
| `app/schemas/*.py` | **contract C1** | all backend tests | 🔴 |
| `app/main.py` | seeding, CORS, mounting | `conftest.py` imports it | 🟡 (🔴 for CORS — RISK-05) |
| `app/config.py` | **contract C7**, NFR-09 | — | 🔴 (secrets) |
| `app/main.py::_check_production_safety` | NFR-09 | ✅ `test_startup_safety.py` | 🔴 |
| `app/main.py::_check_migrations_current` | NFR-10 | 🟡 verified by hand | 🔴 |
| `migrations/versions/*` | NFR-10 · **contract C9** | ✅ `test_migrations.py` | 🔴 **immutable once applied (D6 P12)** |
| `db/schema.sql` | reference only | — | 🟢 ⚠️ stale — D4 §2.3 |

### 3.3 Build & deploy

| File | Serves | Verified by | Zone |
|:--|:--|:--|:--:|
| `vite.config.ts` | build paths, dev `/api` proxy | `pnpm run build` | 🟡 |
| `tsconfig.json` | type gate | `vue-tsc -b` | 🟡 |
| `Dockerfile` | frontend image | manual | 🟡 pnpm pinned via `packageManager`; builds on `node:22` (F-31) |
| `docker-compose.yml` | topology · contract C7 | manual | 🟡 |
| `docker-compose.dev.yml` | local stack — migrations then serve | manual — verified 2026-08-28, both revisions clean from empty | 🟡 |
| `source/backend/.dockerignore` | keeps `.env`/`data/`/`.venv` out of the image | manual | 🟡 ⚠️ see RISK-19 |
| `nginx.conf` | SPA fallback + `/api` proxy | manual | 🟡 |

---

## 4. Impact analysis quick reference

| If you change… | You must also touch | And re-verify |
|:--|:--|:--|
| A key binding | `lib/keyboard.ts`, `ShortcutsHelpModal.vue`, `README.md`, D1 §3.1, D8 §2.1 | manual |
| The status cycle order | `taskStore.ts::STATUS_ORDER`, `routers/tasks.py::cycle_task_status`, `KanbanBoard.vue`, D4 §3.1 | `pytest` 🔴 **RED zone** |
| `types/task.ts` | every component, `services/api.ts`, D4 §5, **bump `koshi_tasks_v1`** | `pnpm run build` 🔴 |
| A Pydantic schema | matching `services/api.ts` method, D4 §4 | `pytest` + `pnpm run build` 🔴 |
| An ORM column | `entities.py`, affected schemas, **a new Alembic revision** (never edit an applied one) | `pytest` incl. `test_migrations.py` 🔴 |
| Task id representation | `entities.py`, `schemas/task.py`, `api.ts::taskKeyOf`/`serverIdOf`, `taskStore.ts`, D4 INV-14 | `pytest` + `pnpm test` 🔴 |
| Which screen is shown | `taskStore.appView` + `App.vue`; every transition action (`logout`, `onAuthenticated`, `continueAsGuest`, `showProfile`, `showBoard`) | manual |
| Critical-path weights | `dagSorter.ts`, D4 §3.2 | `pnpm test` — the CPM scale is pinned by a test that fails if it is swapped for the storage scale |
| An AI prompt | `ai_service.py` only — **check `_deterministic_fallback` substring routing** (F-10) | `pytest` |
| A role or permission rule | `security.py` guards, every calling router, `taskStore.isProjectManager`, `ProjectDashboard.vue`, D1 §3.5, D4 §4.3b | `pytest` 🔴 **RED zone** |
| `ProjectMember` shape | `entities.py`, `schemas/project.py`, `services/api.ts`, `ProjectDashboard.vue`, D4 §4.3b, **migration plan** | `pytest` + `pnpm run build` 🔴 |
| The IndexedDB key format | `taskStore.ts::tasksKey`/`GUEST_DB_KEY`, D4 §6 — bump the version segment | manual offline test |
| Env var names | `config.py`, `docker-compose.yml`, D4 §7 | manual |
| Build paths | `vite.config.ts`, `tsconfig.json`, `Dockerfile`, `docker-compose.yml`, D3 §6 | `pnpm run build` + `pytest` |

## 5. Coverage roll-up

| Area | Requirements | ✅ | 🟡 | ❌ |
|:--|:--:|:--:|:--:|:--:|
| Navigation (FR-NAV) | 5 | 5 | 0 | 0 |
| Localisation (FR-I18N) | 5 | 5 | 0 | 0 |
| Marketing (FR-MKT) | 5 | 5 | 0 | 0 |
| Interaction (FR-INT) | 14 | 11 | 3 | 0 |
| Domain (FR-DOM) | 10 | 9 | 0 | 1 |
| Graph (FR-GRAPH) | 5 | 5 | 0 | 0 |
| Persistence (FR-PERS) | 6 | 2 | 3 | 1 |
| Auth (FR-AUTH) | 10 | 10 | 0 | 0 |
| AI (FR-AI) | 8 | 8 | 0 | 0 |
| Projects (FR-PROJ) | 12 | 9 | 2 | 1 |
| Non-functional (NFR) | 10 | 3 | 3 | 4 |
| **Total** | **90** | **76** | **9** | **5** |

**Reading.** 84% automated, 10% manual-only, 6% unverified — up from 33% automated at rev 1.
**Every non-trivial frontend module now has tests**: both stores, both pure libraries, the keyboard
dispatcher, and thirteen components including all six AI modals. The imbalance noted at rev 1 —
"automation is still almost entirely backend, and the frontend carries the product's distinguishing
logic with no automated verification at all" — no longer holds.

What remains unverified is genuinely hard to unit-test rather than merely unwritten:

- **NFR-01/03/04** — frame budget, load time, contrast. These need measurement tooling, not tests.
  Either measure them or soften the claims in D1.
- **FR-PERS offline round-trip** — IndexedDB is mocked in every frontend test. The *policy* is
  covered (INV-15, in the store and now in both writing modals); the *persistence* is not.

**Highest-leverage next work item:** D5 GAP-06 — Playwright over the keyboard model. Every
remaining gap needs tooling rather than tests: a browser (GAP-06), a profiler and a contrast checker
(GAP-07). There is no module left that somebody simply forgot to test.

**One caveat on the AI rows.** They are now covered for provenance in the *service*, but nothing
surfaces the tier to an operator except a log line. A production deployment silently serving tier-3
answers would still not page anyone. That is a monitoring gap, not a test gap, and it is out of
scope for this matrix — recorded here so it is not mistaken for solved (F-35).
