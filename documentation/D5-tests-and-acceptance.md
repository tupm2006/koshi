# D5 — Tests & Acceptance Criteria

**Purpose:** define what "correct" means, and record honestly what is currently verified.
**Last verified by execution:** 2026-08-28 — backend `38 passed`, frontend `28 passed`.

---

## 1. How to run the suites

### Backend (the only automated suite that exists)

```bash
cd source/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```
Expected: **38 passed**. (`app/database.py` creates the sqlite directory itself, so no `mkdir` is needed.) Config in `pytest.ini` (`pythonpath=.`, `testpaths=tests`, `asyncio_mode=auto`).

### Database migrations

```bash
cd source/backend
alembic upgrade head          # build or update the schema
alembic current               # what revision is this database at?
alembic history --verbose     # the full chain

# An existing database created before Alembic existed:
alembic stamp 0001_initial_schema && alembic upgrade head
```

In development the app still calls `create_all` on boot for convenience. Outside development it
creates nothing and **refuses to start** unless the database is at head (D3 §5c).

### Frontend

```bash
pnpm install
pnpm test                     # vitest run — 28 tests
pnpm run test:watch           # vitest, watch mode
pnpm run build                # vue-tsc -b && vite build
pnpm run dev                  # manual verification at :5173
```

Vitest covers `lib/dagSorter.ts` only. Everything else in the frontend — the store, the keyboard
dispatcher, `gitParser.ts`, every component — remains **manually verified only**; treat the
acceptance criteria below accordingly unless a test is named.

---

## 2. Current verification state — the honest picture

| Area | Automated coverage | Verdict |
|:--|:--|:--|
| Auth: register, duplicate, login, `/me`, 401 | ✅ `test_auth.py` | Good |
| Google OAuth happy path | ✅ `test_auth.py` | Good |
| Google OAuth **rejects unverifiable signatures** | ✅ `test_auth.py` | Good — closes RISK-01 |
| Registration takes no role / ignores a posted one | ✅ `test_projects_and_roles.py` | Good |
| Project creation grants PM; dashboard scoping | ✅ `test_projects_and_roles.py` | Good |
| Per-project role assignment (PM path) | ✅ `test_projects_and_roles.py` | Good |
| **Negative authorisation**: MEMBER blocked from role/member/sprint changes | ✅ `test_projects_and_roles.py` | Good — closes GAP-02 |
| **Cross-project isolation**: non-member blocked from project, tasks, AI, stats | ✅ `test_projects_and_roles.py` | Good — closes RISK-03 |
| Last-PM protection | ✅ `test_projects_and_roles.py` | Good |
| Same user holding different roles in different projects | ✅ `test_projects_and_roles.py` | Good |
| Profile edit is self-only | ✅ `test_projects_and_roles.py` | Good |
| Task lifecycle, cycle-status, comments, sprint stats | ✅ `test_tasks.py` | Good |
| Dependency validation: resolves in-project, rejects unknown / self / cross-project | ✅ `test_tasks.py` | Good — closes F-01 |
| `complexity_points` bounds on update | ✅ `test_tasks.py` | Good — closes F-08 |
| AI endpoints A–D respond with valid schemas | ✅ `test_ai_and_stats.py` | Shape only — never asserts semantic quality |
| Workload & delayed-task stats | ✅ `test_ai_and_stats.py` | Smoke-level |
| Production boot guard (all four insecure defaults) | ✅ `test_startup_safety.py` | Good — closes GAP-08 |
| Migrations: fresh upgrade, legacy upgrade + backfill, downgrade | ✅ `test_migrations.py` | Good — covers the un-recoverable case |
| `dagSorter.ts` — topological sort, cycles, critical path | ✅ `dagSorter.test.ts` (28) | Good — closes GAP-01. Mutation-tested: 7 seeded defects, all caught. |
| `gitParser.ts` — diff parsing, secret detection | ❌ **none** | The retired SRS claimed a `gitParser.test.ts`; it never existed. |
| `keyboard.ts` — 24 bindings, input guards | ❌ **none** | Manual only |
| `taskStore.ts` — mutations, filters, persistence | ❌ **none** | Manual only |
| Any Vue component | ❌ **none** | Manual only |
| Offline / IndexedDB behaviour | ❌ **none** | Manual only |
| Performance (NFR-01, NFR-03) | ❌ **none** | Claims are unmeasured |
| Accessibility (NFR-04) | ❌ **none** | Claims are unmeasured |

**Coverage summary:** the backend HTTP surface is well covered, and authorisation now has real
negative-path coverage (23 of the 29 tests concern access control or deployment safety). The frontend —
where the product's differentiating logic lives — still has **zero** automated verification.

> **Historical note.** Before 2026-08-28 the backend suite could not even be collected:
> `routers/users.py` imported `require_role` from `security.py`, which did not define it, raising
> `ImportError` at import time. All 6 tests were unrunnable on a clean checkout (D7 / DEC-004).
> The suite then grew from 6 to 29 with the per-project roles work (D7 / DEC-009, DEC-010).

---

## 3. Acceptance criteria by requirement

Legend: **A** = automated · **M** = manual · **✗** = unverified

### 3.0b Navigation (FR-NAV)

| Req | Acceptance criteria | Method |
|:--|:--|:--|
| FR-NAV-01 | Visiting with no session shows the landing page, not a board. | M |
| FR-NAV-02 | Sign out from the profile page returns to the landing page and clears the session. | M |
| FR-NAV-03 | "Explore the demo board" enters guest mode with the local sample board. | M |
| FR-NAV-04 | Signing in moves to the board; an account with no projects opens the dashboard. | M |
| FR-NAV-05 | The header pill opens the profile page; "Back to board" returns. | M |

### 3.0c Profile (FR-PROJ-09..11)

| Req | Acceptance criteria | Method |
|:--|:--|:--|
| FR-PROJ-09 | Profile shows name, email, member-since, and project/managing/open-task counts. | M |
| FR-PROJ-10 | Editing name or skills enables Save; saving persists and survives reload. | M |
| FR-PROJ-11 | Memberships list every project with the caller's role; selecting one opens its board. | M |

### 3.1 Interaction (FR-INT)

| Req | Acceptance criteria | Method |
|:--|:--|:--|
| FR-INT-01 | `b` toggles Table ⇄ Kanban; selection survives the switch. | M |
| FR-INT-02/03 | `j`/`k` never move selection outside `[0, N-1]`; `h`/`l` wrap `(c ± 1 + 4) % 4` at column 0 and 3. | M |
| FR-INT-04 | `Space` on each of the 4 statuses yields the D4 §3.1 successor; 4 presses return to the origin. | M (server equivalent: **A**) |
| FR-INT-05 | `Shift+L` moves the card one column right **and** the focus ring stays on that card. | M |
| FR-INT-06 | `1`/`2`/`3`/`4` set LOW/MEDIUM/HIGH/CRITICAL. | M |
| FR-INT-07 | `n` opens create modal; `i` enters inline title edit; `Enter` opens the detail inspector. | M |
| FR-INT-10 | With focus in the search box, typing `d`, `n`, `b` inserts characters and triggers **no** action. | M |
| FR-INT-11 | With a modal open **and** an inline edit active, one `Escape` dismisses the topmost layer; the handler fires in capture phase so no child can swallow it. | M |
| FR-INT-12 | `t` swaps theme with no observable transition frame. | M |

### 3.2 Graph engine (FR-GRAPH) — *specification for the tests that should exist*

| Req | Acceptance criteria | Method |
|:--|:--|:--|
| FR-GRAPH-01 | Every dependency precedes its dependent; chains and diamonds resolve; unknown dependency ids are ignored; no task is dropped or duplicated. | **A** |
| FR-GRAPH-02 | Priority orders CRITICAL→LOW; equal priority falls back to earlier `dueDate`, then `createdAt`; permuted input yields an identical array. | **A** |
| FR-GRAPH-03 | Given `A→B→C→A`, `topologicalSort` returns **all three** tasks, does not throw and does not hang. Self-dependency is tolerated; the acyclic prefix sorts first and cycle members append in input order. | **A** |
| FR-GRAPH-04 | On fixture graphs `computeCriticalPath` returns exactly the expected id set, including the whole chain rather than its endpoint; `DONE` tasks are excluded and a completed dependency breaks the chain (INV-05). | **A** |
| FR-GRAPH-04 | Weighting is `priority × complexity` on the CPM scale (S1/M3/L5/XL8), **not** the storage scale; missing complexity defaults to M. | **A** |
| — | ⚠️ On **cyclic** graphs the result depends on input order (F-24), pinned by a KNOWN LIMITATION test. | **A** |

### 3.3 Persistence (FR-PERS)

| Req | Acceptance criteria | Method |
|:--|:--|:--|
| FR-PERS-01 | After a mutation, `koshi_tasks_v1` in IndexedDB contains the new value; reload restores it. | M |
| FR-PERS-02 | With the backend stopped, create/edit/delete/cycle all succeed and survive reload. | M |
| FR-PERS-03 | Backend down ⇒ amber "Offline (Local buffer)" badge, and **no** modal, toast, or thrown error. | M |
| FR-PERS-04 | JWT persists in `localStorage`; a reload restores the session without re-login. | M |

### 3.4 Auth (FR-AUTH)

| Req | Acceptance criteria | Method |
|:--|:--|:--|
| FR-AUTH-01 | Register returns `201` + token; duplicate email returns `400`; login returns `200` + token. | **A** `test_register_and_login_flow` |
| FR-AUTH-02 | A registration response contains no `role`, and a posted `role` is ignored; a fresh account sees an empty project list. | **A** `test_registration_accepts_no_role_and_grants_none`, `test_registration_ignores_a_submitted_role` |
| FR-AUTH-03 | A valid Google token yields a session; a token with an unverifiable signature returns `401` when the override flag is off. | **A** `test_google_oauth_and_user_management_flow`, `test_unverified_google_token_rejected_when_flag_disabled` |
| FR-AUTH-04 | `GET /api/auth/me` without a token returns `401`. | **A** `test_unauthenticated_request_rejected` |
| FR-AUTH-05 | Creating a project returns `my_role == "PM"` and `member_count == 1`. | **A** `test_creator_becomes_pm_of_their_own_project` |
| FR-AUTH-06 | A PM can add a member and change their role in that project. | **A** `test_pm_can_assign_and_change_roles` |
| FR-AUTH-07 | A MEMBER receives `403` on role change, member add/remove, and sprint creation. | **A** `test_member_cannot_change_roles`, `test_member_cannot_add_or_remove_members`, `test_member_cannot_create_sprints` |
| FR-AUTH-08 | Demoting or removing the last PM returns `400`. | **A** `test_cannot_demote_the_last_pm` |
| FR-AUTH-09 | A non-member receives `404` — never `403` — from project, task, AI and stats routes, and the data is genuinely unmodified. | **A** `test_non_member_cannot_read_project`, `..._list_or_create_tasks`, `..._mutate_a_task_by_id`, `..._reach_ai_or_stats` |
| FR-AUTH-10 | A user can edit their own profile; editing another's returns `403`. | **A** `test_user_can_edit_own_profile`, `test_user_cannot_edit_another_profile` |

### 3.4b Projects & dashboard (FR-PROJ)

| Req | Acceptance criteria | Method |
|:--|:--|:--|
| FR-PROJ-01 | Any authenticated user can `POST /projects` and becomes its PM. | **A** |
| FR-PROJ-02 | `GET /projects` returns only the caller's projects, each with `my_role`. | **A** `test_dashboard_lists_only_my_projects` |
| FR-PROJ-03 | Switching project in the dashboard reloads the board for that project. | M |
| FR-PROJ-04 | A PM adds a member by email with a chosen role. | **A** |
| FR-PROJ-05 | The roster shows per-member role, active task count, and WIP points. | **A** (shape) / M (display) |
| FR-PROJ-06 | Role controls are hidden for a MEMBER **and** refused by the server. | **A** (server) / M (UI) |
| FR-PROJ-07 | A PM can delete a project. | ✗ |
| FR-PROJ-08 | An account with no projects opens on the dashboard. | M |
| — | The same account is PM of one project and MEMBER of another simultaneously. | **A** `test_roles_are_independent_across_projects` |

### 3.5 AI (FR-AI)

| Req | Acceptance criteria | Method |
|:--|:--|:--|
| FR-AI-01 | `POST /ai/weekly-summary` → `200`, `status=="success"`, `len(summary) > 20`. | **A** |
| FR-AI-02 | `POST /ai/meeting-minutes` → non-empty `main_topics`, `action_items`, `key_decisions`. | **A** |
| FR-AI-02 | Blank notes → `400`. | ✗ |
| FR-AI-03 | `POST /ai/recommend-assignment` → recommendation with `recommended_name` and `rationale`. | **A** |
| FR-AI-04 | `POST /ai/decompose` → exactly 3 subtasks. | **A** *(asserts the stub's hardcoded behaviour — see §5)* |
| FR-AI-06 | With `AI_API_KEY` unset **and** no Ollama reachable, every AI endpoint still returns `200` with a schema-valid body. | **A** implicitly — this is the path CI actually exercises |
| FR-AI-07 | `/stats/workload` returns `total_complexity_points` per member. | **A** |
| FR-AI-08 | `/stats/delayed-tasks` returns a list. | **A** (shape only; no overdue fixture) |

### 3.6 Non-functional

| Req | Acceptance criteria | Method |
|:--|:--|:--|
| NFR-01 | Mutation → paint under 16 ms (Performance panel). | ✗ |
| NFR-02 | Computed style shows `transition-duration: 0s` on task surfaces. | M |
| NFR-03 | Idle heap < 15 MB. | ✗ **Claim currently unsupported** |
| NFR-04 | Contrast ≥ 4.5:1, including `DONE` rows (`line-through text-slate-500`). | ✗ |
| NFR-05 | Hard reload in dark mode produces no light flash. | M |
| NFR-07 | `pytest` is green on a clean checkout. | **A** ✅ 38/38 |
| NFR-10 | `alembic upgrade head` builds the current schema from empty; a populated pre-roles DB upgrades with roles backfilled and no user losing access; downgrade restores the old shape. | **A** `test_migrations.py` |
| NFR-09 | Startup aborts with dev defaults when `ENVIRONMENT` is not development; development is exempt. | **A** `test_startup_safety.py` |

---

## 4. Definition of Done

A change is done when **all** hold:

1. `cd source/backend && pytest -q` passes with no new failures.
2. `pnpm test` passes with no new failures.
3. `pnpm run build` completes with no TypeScript errors.
4. Any contract in D4 that the change touches is updated **in the same commit**, and every consumer
   listed in D4 §1 is updated with it.
5. The RTM (D8) row for the affected requirement is updated.
6. If behaviour changed, the relevant acceptance criterion in §3 is updated **and** re-verified.
7. A decision that closed off an alternative is recorded in D7.
8. No new file is added under `submission/` (D6 §3).

## 5. Tests that encode defects

`test_mandated_ai_features` asserts `len(decomp_data["subtasks"]) == 3`. `/ai/decompose` returns
three hardcoded subtasks (FR-AI-04 is a stub), so this assertion **locks in the stub**. If the
endpoint is ever given a real model, this test will fail for the right reason — do not "fix" it by
loosening the assertion without reading D7 / DEC-003.

## 6. Prioritised test gaps

| ID | Gap | Severity | Recommended action |
|:--|:--|:--|:--|
| ~~GAP-01~~ | ~~`dagSorter.ts` has zero tests~~ | — | ✅ **Closed 2026-08-28.** Vitest added; 28 tests over FR-GRAPH-01…04, tie-breaking, cycles and both weight scales. Surfaced F-24 in the process. |
| ~~GAP-02~~ | ~~No negative authorisation tests~~ | — | ✅ **Closed 2026-08-28.** `test_projects_and_roles.py` covers MEMBER→403 on every PM action and non-member→404 across project, task, AI and stats routes. |
| GAP-03 | `gitParser.ts` untested | **High** | Add `gitParser.test.ts` — secret detection and close-keyword regexes are security-adjacent. |
| GAP-04 | No test distinguishes real LLM output from Tier-3 fallback | **Medium** | Assert cascade behaviour by mocking tiers, not just response shape. |
| GAP-05 | `taskStore` mutations and filters untested — the largest gap. Now also owns `appView`, guest mode and profile updates, all unverified. | **High** | Vitest with a fake `idb-keyval`. The runner exists, so this is unblocked. |
| GAP-10 | `LandingPage.vue` and `ProfilePage.vue` have no tests; both are auth-adjacent and manually verified only. | **Medium** | Component tests once a DOM environment is configured. |
| GAP-06 | No E2E keyboard coverage | **Medium** | Playwright over FR-INT-01…11. |
| ~~GAP-08~~ | ~~`_check_production_safety` untested~~ | — | ✅ **Closed 2026-08-28.** `test_startup_safety.py` parametrises all four insecure defaults plus the safe and development cases. |
| GAP-09 | No frontend test asserts that PM-only controls are hidden from a MEMBER | **Low** | Component test once a runner exists; the server-side refusal is already covered. |
| GAP-07 | Performance/accessibility claims unmeasured | **Low** | Either measure them or soften NFR-01/03/04 in D1. |

**Recommended next move:** GAP-05 — `taskStore.ts`. It is now the largest untested surface, has the
widest blast radius in the repo, and is where the three DEC-012 auth defects lived. The runner
exists, so the only remaining cost is faking `idb-keyval` and the API client.
