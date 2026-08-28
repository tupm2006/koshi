# D5 — Tests & Acceptance Criteria

**Purpose:** define what "correct" means, and record honestly what is currently verified.
**Last verified by execution:** 2026-08-28 — `6 passed` in 5.20s (`source/backend`, Python 3.11).

---

## 1. How to run the suites

### Backend (the only automated suite that exists)

```bash
cd source/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data                 # required: DATABASE_URL points at ./data/, not auto-created
pytest -q
```
Expected: **6 passed**. Config in `pytest.ini` (`pythonpath=.`, `testpaths=tests`, `asyncio_mode=auto`).

### Frontend

```bash
pnpm install
pnpm run build                # vue-tsc -b && vite build  ← the ONLY automated frontend gate
pnpm run dev                  # manual verification at :5173
```

There is **no frontend test runner**. `pnpm run build` is a type-check plus bundle; a green build
means the types agree, nothing more. Treat every frontend acceptance criterion below as
**manually verified only** unless stated otherwise.

---

## 2. Current verification state — the honest picture

| Area | Automated coverage | Verdict |
|:--|:--|:--|
| Auth: register, duplicate, login, `/me`, 401 | ✅ `test_auth.py` | Good |
| Google OAuth + PM role update | ✅ `test_auth.py` | Good |
| Task lifecycle, cycle-status, comments, sprint stats | ✅ `test_tasks.py` | Good |
| AI endpoints A–D respond with valid schemas | ✅ `test_ai_and_stats.py` | Shape only — never asserts semantic quality |
| Workload & delayed-task stats | ✅ `test_ai_and_stats.py` | Smoke-level |
| `dagSorter.ts` — topological sort, cycles, critical path | ❌ **none** | **Highest-risk gap.** Most intricate logic in the repo, zero tests. |
| `gitParser.ts` — diff parsing, secret detection | ❌ **none** | The retired SRS claimed a `gitParser.test.ts`; it never existed. |
| `keyboard.ts` — 24 bindings, input guards | ❌ **none** | Manual only |
| `taskStore.ts` — mutations, filters, persistence | ❌ **none** | Manual only |
| Any Vue component | ❌ **none** | Manual only |
| Offline / IndexedDB behaviour | ❌ **none** | Manual only |
| Performance (NFR-01, NFR-03) | ❌ **none** | Claims are unmeasured |
| Accessibility (NFR-04) | ❌ **none** | Claims are unmeasured |

**Coverage summary:** the backend HTTP surface is smoke-tested end to end. The frontend — which is
where the product's differentiating logic lives — has zero automated verification.

> **Historical note.** Before 2026-08-28 the backend suite could not even be collected:
> `routers/users.py` imported `require_role` from `security.py`, which did not define it, raising
> `ImportError` at import time. All 6 tests were unrunnable on a clean checkout. See D7 / DEC-004.

---

## 3. Acceptance criteria by requirement

Legend: **A** = automated · **M** = manual · **✗** = unverified

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
| FR-GRAPH-01 | For every task `t` and every `d ∈ t.dependencies` present in the set, `index(d) < index(t)` in the output. | ✗ |
| FR-GRAPH-02 | Two independent tasks with different priorities always emit in CRITICAL→LOW order; equal priority falls back to earlier `dueDate`, then earlier `createdAt`. Repeated runs on the same input give an identical array. | ✗ |
| FR-GRAPH-03 | Given `A→B→C→A`, `topologicalSort` returns **all three** tasks, does not throw, and does not hang. | ✗ |
| FR-GRAPH-04 | On a known fixture graph, `computeCriticalPath` returns exactly the expected ID set; `DONE` tasks are excluded (INV-05). | ✗ |
| FR-GRAPH-04 | Weighting uses `priority × complexity` with the CPM scale (S1/M3/L5/XL8), **not** the storage scale. | ✗ |

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
| FR-AUTH-02 | A Google ID token yields a session and stores `avatar_url`. | **A** `test_google_oauth_and_user_management_flow` |
| FR-AUTH-03 | `GET /api/auth/me` without a token returns `401`. | **A** `test_unauthenticated_request_rejected` |
| FR-AUTH-04 | A `PM` can `PATCH /users/{id}` role and skills. | **A** (same test) |
| FR-AUTH-04 | ⚠️ A `MEMBER` calling `PATCH /users/{id}` receives `403`. | ✗ **Negative case untested — see §6 GAP-02** |

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
| NFR-07 | `pytest` is green on a clean checkout. | **A** ✅ 6/6 |

---

## 4. Definition of Done

A change is done when **all** hold:

1. `cd source/backend && pytest -q` passes with no new failures.
2. `pnpm run build` completes with no TypeScript errors.
3. Any contract in D4 that the change touches is updated **in the same commit**, and every consumer
   listed in D4 §1 is updated with it.
4. The RTM (D8) row for the affected requirement is updated.
5. If behaviour changed, the relevant acceptance criterion in §3 is updated **and** re-verified.
6. A decision that closed off an alternative is recorded in D7.
7. No new file is added under `submission/` (D6 §3).

## 5. Tests that encode defects

`test_mandated_ai_features` asserts `len(decomp_data["subtasks"]) == 3`. `/ai/decompose` returns
three hardcoded subtasks (FR-AI-04 is a stub), so this assertion **locks in the stub**. If the
endpoint is ever given a real model, this test will fail for the right reason — do not "fix" it by
loosening the assertion without reading D7 / DEC-003.

## 6. Prioritised test gaps

| ID | Gap | Severity | Recommended action |
|:--|:--|:--|:--|
| GAP-01 | `dagSorter.ts` has zero tests | **Critical** | Add Vitest; cover FR-GRAPH-01…04 including the cycle fixture. Pure functions — cheapest coverage in the repo. |
| GAP-02 | No negative authorisation tests | **High** | Assert `MEMBER` → `403` on `PATCH /users/{id}`; assert cross-project task access (RISK-03, D6 §4). |
| GAP-03 | `gitParser.ts` untested | **High** | Add `gitParser.test.ts` — secret detection and close-keyword regexes are security-adjacent. |
| GAP-04 | No test distinguishes real LLM output from Tier-3 fallback | **Medium** | Assert cascade behaviour by mocking tiers, not just response shape. |
| GAP-05 | `taskStore` mutations and filters untested | **Medium** | Vitest with a fake `idb-keyval`. |
| GAP-06 | No E2E keyboard coverage | **Medium** | Playwright over FR-INT-01…11. |
| GAP-07 | Performance/accessibility claims unmeasured | **Low** | Either measure them or soften NFR-01/03/04 in D1. |

**Recommended first move:** add Vitest and close GAP-01. It is pure-function testing with no
framework mocking, and it protects the logic most likely to be silently broken by an AI edit.
