# D7 — Development Book & Decision Log

**Purpose:** what was tried, what failed, and why the code is the way it is — so nobody re-litigates
a settled question or "fixes" something that is deliberate.

**Format.** Decisions are append-only. To reverse one, add a new entry that supersedes it; never
edit history. Findings record observed facts about the codebase.

---

## Part I — Decision Log

### DEC-001 — Repository split into `source/` and `documentation/`
**Date:** 2026-08-28 · **Status:** Active · **Zone:** infrastructure

**Context.** Code and docs were interleaved at the repo root: `src/`, `backend/`, `docs/`,
`index.html`, plus build config, all as siblings. An agent grepping for "where does X live" had no
structural signal.

**Decision.** Two top-level homes: `source/{frontend,backend}` for all executable code,
`documentation/` for all documentation. Build configuration stays at the root, where the toolchain
expects it.

**Alternatives considered.**
- *Move `package.json` and `vite.config.ts` into `source/frontend/` too.* Rejected — it would have
  forced a pnpm workspace restructure and changed every documented command. Higher risk than the
  ask warranted.
- *Leave `index.html` at the root* so Vite's default root keeps working. Rejected — `index.html` is
  source, and leaving it out would have defeated the point.

**Implementation.**
| File | Change |
|:--|:--|
| `vite.config.ts` | added `root: 'source/frontend'`, `build.outDir: '../../dist'`, `emptyOutDir: true` |
| `tsconfig.json` | `include` now `source/frontend/**` |
| `source/frontend/index.html` | script src `/src/main.ts` → `/main.ts` |
| `docker-compose.yml` | backend build context `./backend` → `./source/backend` |
| `.gitignore` | added `.venv/` |

`git mv` was used throughout, so history is preserved (git reports every move as `R`).

**Verification.** `npx vue-tsc -b` — no errors. `npx vite build` — 1610 modules, built to `dist/`.
`pytest -q` in `source/backend` — 6 passed.

**Consequences.** The frontend Dockerfile still uses build context `.` and works unchanged.
`nginx.conf` unaffected. `submission/` retains the old layout by design (D6 §3).

---

### DEC-002 — Cycle detection degrades gracefully instead of throwing
**Date:** pre-existing, documented 2026-08-28 · **Status:** Active

**Context.** The SRS (retired in DEC-008) specified in §3.3 / SRS-FR-08 that Kahn's algorithm should
raise `CycleDetectedException` when `|L| < |V|`.

**What the code does.** `dagSorter.ts::topologicalSort` detects the same condition
(`result.length < tasks.length`) but appends the unsorted remainder rather than throwing. No
exception type exists anywhere in the codebase.

**Rationale for keeping it.** The sort feeds the primary render path. Throwing would blank the
board over a data problem the user cannot see or fix from the error. Silent degradation keeps every
task visible; cyclic members simply lose their ordering guarantee.

**Cost.** Cycles are invisible to the user. There is no warning badge and no console message.

**Follow-up.** Surface a non-blocking cycle warning in `DAGVisualizerModal.vue`. The SRS was wrong
here and the code was right, which is why D1 FR-GRAPH-03 now codifies the implemented behaviour.

**Related.** The two complexity scales (D4 §3.2) are deliberate for the same reason — CPM
exaggerates large tasks (S1/M3/L5/XL8) to surface bottlenecks, while workload accounting uses the
linear storage scale (S1/M2/L3/XL5). Harmonising them would flatten the critical path.

---

### DEC-003 — `/ai/decompose` is deterministic, not model-backed
**Date:** pre-existing, documented 2026-08-28 · **Status:** Active, **open question**

**Context.** FR-AI-04 promises goal decomposition. Three of the four AI endpoints route through
`AIService` and the full three-tier cascade.

**What the code does.** `routers/ai.py::decompose_goal` never touches `AIService`. It returns three
hardcoded Vietnamese subtasks with the goal string interpolated into their titles (truncated to 30
chars), with a fixed linear dependency chain: analysis → backend → frontend.

**Why it is probably deliberate.** It guarantees a valid `AIDecomposeResponse` with zero latency and
zero cost, and `test_mandated_ai_features` asserts exactly three subtasks — the behaviour is
pinned by a test.

**Why it is a problem.** It is indistinguishable from a real feature at the API boundary. FR-AI-04
is marked "Stub" in D1 for this reason.

**Do not change this unilaterally** — RED zone (D6 §1). Tracked as OQ-04. If it is ever made
model-backed, `test_mandated_ai_features` will fail correctly; fix the endpoint, not the assertion
(D5 §5).

---

### DEC-004 — Restored the missing `require_role` in `security.py`
**Date:** 2026-08-28 · **Status:** Active · **Zone:** 🔴 RED (auth) — done deliberately, flagged

**Problem found.** On a clean clone of `main`, the backend test suite could not be collected:

```
tests/conftest.py:11: from app.main import app, seed_initial_data
app/routers/users.py:7: from app.security import get_current_user, require_role
E   ImportError: cannot import name 'require_role' from 'app.security'
```

`routers/users.py` used `Depends(require_role(RoleEnum.PM))` to guard `PATCH /users/{user_id}`, but
`security.py` never defined `require_role`. **This was pre-existing upstream, not caused by the
restructure** — `git status` records `security.py` as a pure rename (`R`) with no content change
prior to this fix. The consequence was total: FastAPI failed at import, so all 6 tests, `uvicorn`,
and the Docker backend image were all non-functional on a clean checkout.

**What was tried first.** Confirmed the blast radius by adding the function temporarily and running
the suite: **6 passed**. So a single missing 6-line dependency factory was the only thing standing
between a broken repo and a fully green suite.

**Decision.** Restore `require_role` as a dependency factory in `security.py`, mirroring the
existing `get_current_pm_user` guard:

```python
def require_role(role: RoleEnum):
    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user
    return _guard
```

**Alternatives considered.**
- *Leave it broken and only document it.* Rejected — D5 would have had nothing to verify, and the
  restructure could not be validated against a suite that cannot run.
- *Rewrite `users.py` to use the existing `get_current_pm_user`.* Rejected — that changes a caller
  to work around a missing definition, and discards the more general factory the author clearly
  intended (it takes a role parameter).

**Honest disclosure.** This is auth code, a RED zone under D6 §1, and it exceeds a pure restructure
brief. It was done because the repository was non-functional without it and the fix is the minimal
restoration of clearly-intended behaviour. **It warrants human review.** Note that the negative case
(a `MEMBER` receiving `403`) remains untested — D5 GAP-02.

**Verification.** `pytest -q` → 6 passed, 47 warnings, 5.20s.

---

### DEC-005 — The documentation/code conflict ledger
**Date:** documented 2026-08-28 · **Status:** Active (source documents retired in DEC-008)

**Why this record survives its sources.** The documents listed below were deleted in DEC-008. This
entry is kept deliberately: it is the evidence that motivated the whole D1–D8 exercise, and without
it a future reader has no way to know *why* the old specs were discarded rather than merged.

**The keyboard case, in detail.** The retired `README.md` §4.1 and `CLAUDE.md` documented `c` =
create task and `Enter` = inline title edit. `lib/keyboard.ts` implements `n` = create, `i` = inline
edit, and `Enter` = open the task detail inspector. Git confirms this was intentional: commit
`ea46cc2` — *"feat(inspector): add TaskDetailModal, overhaul keyboard schema (n/Enter/i/Esc), and
circular Kanban nav"* — changed the bindings, and the source comment still reads *"'n': Create task
(overhauls 'c')"*. **The docs were simply never updated after a deliberate refactor.**

**Why this matters more than it looks.** An agent asked to "fix the create-task shortcut" while
trusting the README would have changed working code to match wrong documentation — reverting a
deliberate design decision on the authority of a stale sentence. This is RISK-07, and it is the
reason D6 §5 fixes a precedence order.

**All confirmed conflicts (7), as found on 2026-08-28:**

| Claim | Source of claim | Reality |
|:--|:--|:--|
| Status order `TODO→IN_PROGRESS→DONE→BLOCKED` | `README.md`, `URD.md` | Code: `TODO→IN_PROGRESS→BLOCKED→DONE` |
| Status order stated a third, different way | `CLAUDE.md` | same as above |
| `c` = create, `Enter` = inline edit | `README.md`, `CLAUDE.md` | `n` = create, `i` = inline edit, `Enter` = inspector |
| Endpoints at `/api/v1/...` | `SRS.md` §3.4 | `/api/...` — no `/v1` segment exists anywhere |
| `gitParser.test.ts` verifies URD-FR-10 | `SRS.md` §5 RTM | The file does not exist; **no** frontend tests exist |
| "Gemini 1.5 Flash" is the LLM | `README.md`, `CLAUDE.md` | OpenAI-compatible (`gpt-4o-mini`) + Ollama. No Gemini client anywhere. |
| `< 15MB` idle RAM | `README.md` badge | Never measured (D1 NFR-03) |

**Related.** `svelte.config.js` claims a Svelte frontend; the app is Vue 3 (F-15).

---

### DEC-006 — `analyzeGitDiff` stub shadows the real parser
**Date:** pre-existing, documented 2026-08-28 · **Status:** Active, **unresolved**

**Finding.** `lib/gitParser.ts::parseGitDiff` is a complete, careful implementation: close-keyword
regexes (`close[sd]?|fix(e[sd])?|resolve[sd]?`), added-line scanning for TODO/FIXME/HACK, empty
catch blocks, hardcoded-secret patterns, and `: any` coercions, returning a full
`GitDiffAnalysisResult`.

`services/api.ts::analyzeGitDiff` does not call it. It counts `+++ b/` lines, marks
`currentTasks[0]` resolved regardless of content, and returns an object **missing
`architecturalConcerns`** — so it does not even satisfy the `GitDiffAnalysisResult` type in C3.

**Assessment.** This looks like scaffolding that was never removed, not a decision. The good code is
orphaned; the placeholder is what ships.

**Recommended fix (not applied).** Have `GitDiffModal.vue` call `parseGitDiff` directly — it is a
pure client-side function and needs no network call — and delete `ApiClient.analyzeGitDiff`. This
was not done here because it changes feature behaviour, which is outside a restructure brief.
Requires the D5 GAP-03 tests first (P4).

---

### DEC-007 — Package manager is ambiguous
**Date:** documented 2026-08-28 · **Status:** Unresolved

**Finding.** Both `pnpm-lock.yaml` and `package-lock.json` are committed. `README.md` and
`CLAUDE.md` prescribe `pnpm install`. The production `Dockerfile` runs `npm install` — and copies
only `package.json`, **not** either lockfile, so the production image resolves dependencies fresh
and ignores both locks entirely.

**Impact.** The deployed bundle can be built from a different dependency tree than any developer
ever tested. RISK-09.

**Recommendation (not applied).** Pick pnpm, delete `package-lock.json`, and change the Dockerfile
to `COPY package.json pnpm-lock.yaml ./` + `pnpm install --frozen-lockfile`. Deferred: it changes
the production build and belongs to a human (D6 §1).

---

### DEC-008 — Retired the legacy specification set; D1–D8 is the only documentation
**Date:** 2026-08-28 · **Status:** Active · **Zone:** documentation

**Context.** After DEC-001 the `documentation/` folder held two incompatible generations: the
legacy set (`SRS.md`, `URD.md`, `architecture.md`, `codebase-map.md`, `user-stories.md`,
`BAO_CAO_KT1.md`) and the new code-verified D1–D8. The legacy documents were authored ~2026-08-24 to
an IEEE 29148 template and had drifted from the code in seven confirmed places (DEC-005). Keeping
both meant every agent had to know which to distrust — the exact failure mode the D-set exists to
prevent.

**Decision.** Delete the legacy six. D1–D8 becomes the sole documentation set. `README.md` and
`CLAUDE.md` were rewritten from scratch against the code and demoted to explicit *summaries* that
defer to D1–D8.

**Alternatives considered.**
- *Merge the legacy content into D1–D8.* Rejected — the salvageable material (personas, MoSCoW
  classification, the state-transition formalism, the traceability matrix) was already absorbed into
  D1 and D8 during authoring. What remained was the incorrect residue.
- *Keep them marked "deprecated".* Rejected — a deprecation banner does not stop an agent grepping
  the repo and finding `/api/v1` in a file that looks authoritative. Deletion is the only reliable
  signal, and git history preserves them.

**What was NOT deleted, and why.**
- `submission/nhom4/docs/` still contains copies of the retired SRS/URD. `submission/` is a frozen
  coursework artefact (D6 §3); rewriting it would falsify a point-in-time submission.
- `nhom4.docx` and `scripts/generate_docx.py` are coursework packaging, not project documentation.

**Recovery.** `git show 575bee7:docs/SRS.md` (and siblings) retrieves any retired document.

**Consequences.** D6 §5's precedence list drops from four tiers to three. RISK-07 moves to
**Closed**. Cross-references in D1, D5, D6 and D7 were updated to describe the retired documents in
the past tense rather than as live sources.

---

### DEC-009 — Roles moved from the user to the (user, project) pair
**Date:** 2026-08-28 · **Status:** Active · **Zone:** 🔴 RED (auth) — requested by the maintainer

**Context.** `User.role` was a single global `PM | MEMBER` column chosen at registration. Three
things were wrong with it: a user had the same authority in every project; registration asked a
question a new user cannot meaningfully answer; and the column was nearly decorative, since only
`PATCH /users/{id}` ever consulted it (RISK-03 — nothing else checked anything).

**Decision.** Authorisation becomes relational. A new `project_members` join entity carries
`(project_id, user_id, role)` with a uniqueness constraint on the pair, and `User.role` is removed
entirely. Registration takes no role. Creating a project makes the creator its PM. A PM administers
membership and roles **within that project only**.

**Consequences by design:**
- The same account can be PM of one project and MEMBER of another, with nothing to reconcile.
- A brand-new account has zero authority anywhere until it creates or joins a project.
- `GET /projects` became the personal dashboard feed: it returns only the caller's projects,
  each annotated with `my_role`.
- `/stats/workload` gained a required `project_id`; workload is now per-project rather than global.
- `PATCH /users/{id}` became self-service; roles are no longer reachable through it.

**Alternatives considered.**
- *Keep `User.role` as a default and let projects override it.* Rejected — two sources of authority
  is exactly the ambiguity that made the old model useless. There would be no answer to "which one
  wins" that survives contact with a real permission check.
- *Add an Organisation tier above Project.* Rejected as premature; nothing in the requirements needs
  it, and it can be layered on later without changing the ProjectMember contract.
- *Model roles as permission flags rather than a two-value enum.* Rejected for v1 — no requirement
  distinguishes finer than "can administer" vs "can contribute" (D1 OQ-05 tracks revisiting this).

**404 rather than 403 for non-members.** A `403` confirms the resource exists. For a project the
caller has no right to know about, that is a disclosure, so unknown and forbidden are deliberately
indistinguishable. `403` is reserved for callers who *are* members but lack the PM role — at that
point there is nothing left to conceal and a precise error is more useful. This asymmetry is
asserted in the tests, so it cannot be "tidied up" into consistency by accident.

**Last-PM protection.** Demoting or removing the final PM of a project returns `400`. Without it a
project could be stranded with no one able to administer it and no recovery path short of direct DB
access.

**Schema migration.** `create_all` never alters an existing table (RISK-10), so an existing database
will **not** pick up `project_members`, nor drop `users.role`. For development the fix is to delete
`source/backend/data/koshi.db` and let it re-seed. A deployed database needs a real migration; this
is the clearest argument yet for adopting Alembic (RISK-10).

**Verification.** 17 new tests in `tests/test_projects_and_roles.py`; suite 6 → 23 passing. Verified
end to end against a running stack: a user registered with no role, created a project, became its
PM, added a second user as MEMBER, was refused a role change as that MEMBER (403), and the second
user held PM in their own project and MEMBER in the first simultaneously.

**Known gap.** Fixed during the same change: the IndexedDB cache used one shared key, which under a
multi-project model would let one project's board be read back as another's. Keys are now
partitioned per project (`koshi_tasks_v2_p{id}`) — see D4 §6 / INV-12. Divergence *within* a single
project is still unreconciled (RISK-13).

---

### DEC-010 — Insecure defaults became opt-in and boot-blocking
**Date:** 2026-08-28 · **Status:** Active · **Zone:** 🔴 RED (auth/config) — requested by the maintainer

**Context.** Four development conveniences were live in production code with no guard: an
unverified-Google-token fallback (RISK-01), a hardcoded JWT secret in both `config.py` and
`docker-compose.yml` (RISK-02), `allow_origins=["*"]` with `allow_credentials=True` (RISK-05), and
unconditional demo seeding with the known password `koshi123` (RISK-11).

**Decision.** Each becomes an explicit setting that is *off or safe by default*, and
`main.py::_check_production_safety()` refuses to start when `ENVIRONMENT` is not a development value
and any of them is still in force.

| Setting | Default | Outside development |
|:--|:--|:--|
| `ALLOW_UNVERIFIED_GOOGLE_TOKENS` | `false` | boot fails if true |
| `JWT_SECRET` | obvious dev placeholder | boot fails if unchanged |
| `CORS_ORIGINS` | `*` | boot fails if `*`; `allow_credentials` auto-disabled while `*` |
| `SEED_DEMO_DATA` | `true` | boot fails if true |

**Why fail closed at boot rather than warn.** A warning in a log nobody reads is how these got
shipped in the first place. Refusing to start is noticed immediately and cannot be ignored.

**Why the unverified-token path was kept at all.** `tests/test_auth.py` exercises Google sign-in
without network access to Google's public keys. Deleting the path would mean deleting that coverage.
It is enabled explicitly in `conftest.py` and nowhere else.

**Not fully resolved.** RISK-02 is *mitigated, not eliminated*: the secret still has a source-code
default rather than coming from a secret store, and any database seeded under the old published
secret should be treated as compromised — existing tokens remain forgeable by anyone who read the
public repo. Rotating it is a deployment action, not a code change.

**Verification.** `test_unverified_google_token_rejected_when_flag_disabled` asserts the `401`.
`test_startup_safety.py` covers the boot guard itself: each of the four insecure defaults blocks
startup, a fully safe production config starts, and development is exempt.

---

### DEC-011 — Alembic owns the schema; the app stops creating it
**Date:** 2026-08-28 · **Status:** Active · **Zone:** infrastructure · **Requested by the maintainer**

**Context.** RISK-10 had been open since the first audit and became blocking with DEC-009: that
change added `project_members` and dropped `users.role`, but `Base.metadata.create_all()` never
alters an existing table. A deployed database would have silently kept the old shape while the code
assumed the new one — the failure would have surfaced as confusing authorisation errors, not as a
clear schema error.

**Decision.** Adopt Alembic with two revisions, and make the environment decide who owns the schema.

| Revision | Contents |
|:--|:--|
| `0001_initial_schema` | The **pre-DEC-009** schema (global `users.role`, no `project_members`). |
| `0002_per_project_roles` | Creates `project_members`, backfills it, drops `users.role`. Reversible. |

Starting the baseline at the *old* schema is the point: an already-deployed database can be stamped
at `0001` and migrated forward, instead of being rebuilt. A baseline describing the current schema
would have offered no upgrade path at all — only a fresh install.

**Environment decides schema ownership** (D3 §5c):
- development → `create_all()`, for fast local iteration.
- otherwise → the app creates nothing and `_check_migrations_current()` refuses to start unless the
  database revision equals the code's head, printing the exact command to run.

**Backfill policy, and why it is permissive.** Before DEC-009 there was no project-scoped
authorisation: any authenticated user could touch any task in any project (RISK-03). The faithful
translation is that **every existing user becomes a member of every existing project** — that is the
access they already had. Owners and former global PMs become PMs; everyone else becomes MEMBER; an
ownerless project with no global PM promotes the lowest-id user so it is never left unadministered.

A migration must not silently revoke access people depend on. Tightening a roster is a judgement
call for whoever runs the upgrade, so it is documented as a required follow-up (D6 §7.2) rather than
guessed at here.

**Alternatives considered.**
- *Baseline at the current schema.* Rejected — no upgrade path for existing data, which is the only
  case that cannot be recovered by deleting the file.
- *Keep `create_all` everywhere and hand-write ALTERs.* Rejected — unversioned and unreversible.
- *Backfill only project owners as members.* Rejected — it would lock every other user out of
  projects they could previously use, turning an upgrade into an outage.

**Implementation note.** `migrations/env.py` takes the URL and metadata from `app.config` /
`app.database` rather than `alembic.ini`, so migrations always follow the app's configuration. An
explicitly supplied `sqlalchemy.url` still wins — without that the test-suite could not point a
migration run at a scratch database, which it does five times.

**Verification.** `test_migrations.py` (5 tests): single head; fresh upgrade produces the current
schema; a **populated legacy database** upgrades with roles backfilled correctly and nobody losing
access; an ownerless project still gets a PM; downgrade restores `users.role` from memberships.
Also exercised by hand end to end, including the boot guard refusing an unmigrated database.

---

### DEC-012 — JWT secret rotated; auth UI corrected
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

**Secret rotation.** The published default
(`koshi_super_secret_jwt_key_2026_academic_spec`) was replaced with a fresh 256-bit value generated
via `openssl rand -hex 32`, stored in `source/backend/.env`, which is gitignored. A tracked
`.env.example` documents every setting without carrying a value. Verified: a token signed with the
old published secret is now rejected. RISK-02 is closed **for this checkout only** — any other
deployment must rotate independently, and the runbook is D6 §7.1.

**Three UI defects fixed**, reported by the maintainer after testing DEC-009:

1. **The account panel showed a stranger's email.** `AuthModal` initialised its fields to the seeded
   demo credentials (`pm@tupm.qzz.io` / `koshi123`), so a user who had just registered saw those
   instead of their own account. Fields now start empty; the demo shortcuts are reduced to two
   labelled chips and only rendered under `import.meta.env.DEV`.

2. **The dashboard never opened for a new account.** `taskStore.isDashboardOpen` was set by `init()`,
   but `App.vue` held its own local `ref` of the same name — two independent pieces of state, so the
   store's value was never read. The local ref is gone; the store is the single source of truth.

3. **Signing in loaded no projects.** `AuthModal` called `syncWithBackend()` without
   `loadProjects()`, so `currentProjectId` stayed `null` and the board rendered empty with no route
   forward. This is the "nothing was usable" report.

**Root cause of 2 and 3 is the same:** the post-authentication sequence existed in two places
(boot and login) and they drifted. Both now funnel through a single `taskStore.onAuthenticated()`,
so the sequence cannot diverge again. A matching `logout()` clears session state and restores the
guest board.

**Also added:** an empty-state panel on the board when signed in with no project selected, and a
signed-in account panel showing the user, their current project and role, and a sign-out button —
there was previously no way to sign out at all.

**Verification.** Confirmed in-browser: registered a fresh account, was taken to the dashboard,
created a project, became its PM, and reopened the account panel to see the correct email. The
rotation was visible in the same session — the pre-rotation token was rejected and the app fell
back to the guest board.

**Gap.** These are frontend defects and the frontend still has no automated tests (D5 GAP-01 /
NFR-08). Nothing would catch a regression of any of the three. That remains the largest gap in the
project.

---

## Part II — Findings ledger

Observations that are not yet decisions. Each should become a decision or a work item.

| ID | Finding | Location | Severity | Status |
|:--|:--|:--|:--:|:--|
| F-01 | Task ID type differs across ORM (`int`), frontend (`string`), and `schema.sql` (`VARCHAR`). Dependencies are `List[str]` against `int` IDs, so the server-side graph can never resolve. | D4 VIOLATION-01 | **Critical** | Open — OQ-01, RED |
| F-02 | Google ID token signature verification failure fell back to **unverified** base64 payload decoding. | `routers/auth.py` | Critical | ✅ Closed — DEC-010 |
| F-03 | JWT secret hardcoded in `config.py` and `docker-compose.yml`, both public. | | Critical | ⚠️ Mitigated — DEC-010. **Rotate any deployed secret**; old tokens stay forgeable. |
| F-04 | No task endpoint verified project membership. Any user could mutate any task. | `routers/tasks.py` | High | ✅ Closed — DEC-009 |
| F-05 | `dagSorter.ts` — the most intricate logic in the repo — has zero tests. | | High | Open — D5 GAP-01 |
| F-06 | `db/schema.sql` diverges from the ORM and is never executed. | | Medium | Superseded — Alembic is now the schema source (DEC-011). The file is stale legacy reference; **candidate for deletion**. |
| F-07 | `allow_origins=["*"]` with `allow_credentials=True` is spec-invalid. | `main.py` | Medium | ✅ Closed — DEC-010 |
| F-08 | `complexity_points` validated `ge=1, le=8` on create, unvalidated on update. | `schemas/task.py` | Low | Open |
| F-09 | `blocking_reason` not required when status is `BLOCKED`, despite FR-DOM-07. | | Low | Open — OQ-02 |
| F-10 | Tier-3 AI fallback branches on **substring matches in prompt text** (`"cuộc họp"`, `"recommended_user_id"`). Rewording a prompt silently breaks fallback routing. | `ai_service.py` | Medium | Open |
| F-11 | Tier 1 fires only if `"openai" in AI_API_URL`. Any other OpenAI-compatible vendor silently falls through to Tier 2/3 even with a valid key. | `ai_service.py` | Medium | Open |
| F-12 | Seed data creates `pm@tupm.qzz.io` / `koshi123` whenever the users table is empty. | `main.py` | High | ✅ Closed — DEC-010 (gated by `SEED_DEMO_DATA`) |
| F-13 | No migration tooling. `create_all` never alters existing tables, so schema changes silently no-op on a deployed volume. | | High | ✅ Closed — DEC-011 (Alembic, with an upgrade path for pre-existing databases) |
| F-14 | `source/backend/app/data/koshi.db` (SQLite binary) and `tsconfig.tsbuildinfo` (build cache) are committed. | | Low | Open |
| F-15 | `svelte.config.js` is dead residue from a Svelte prototype. | | Low | Open — safe to delete |
| F-16 | `AIDecomposeResponse` uses camelCase (`acceptanceCriteria`) while every other schema uses snake_case. | `schemas/ai.py` | Low | Open |
| ~~F-17~~ | ~~Tests require `source/backend/data/` to exist before the first run.~~ **Incorrect when written** — `app/database.py` creates the sqlite directory itself. Corrected in D5 §1. | `database.py` | — | Withdrawn |
| F-18 | Widespread `datetime.utcnow()` — deprecated, 47 warnings per test run. | backend | Low | Open |
| F-19 | `AuthModal.vue` quick-login buttons were labelled "PM" / "Member", implying global roles. | `AuthModal.vue` | Low | ✅ Closed — DEC-012 (relabelled `pm@` / `dev@`, dev-only) |
| F-20 | Several UI tooltips and the footer legend still say `c` for create task; the binding is `n` (DEC-005). | `App.vue`, `MobileBottomNav.vue` | Low | Open — cosmetic, but it is the same class of drift as DEC-005 |
| F-21 | The post-auth sequence was duplicated between boot and login and drifted, leaving a signed-in user with no projects loaded. | `taskStore.ts`, `AuthModal.vue` | High | ✅ Closed — DEC-012 (single `onAuthenticated`) |
| F-22 | `App.vue` shadowed `taskStore.isDashboardOpen` with a local ref, making the store field dead state. | `App.vue` | Medium | ✅ Closed — DEC-012 |
| F-23 | Deleting the SQLite file under a running uvicorn leaves it writing to a deleted inode ("attempt to write a readonly database"). Restart the process, do not just replace the file. | operational | Low | Open — documented here |

## Part III — Timeline

| Date | Event |
|:--|:--|
| ~2026-08-24 | `URD.md` / `SRS.md` v2.1.0 authored (IEEE 29148 style). Both later drift from the code. |
| 2026-08-24 | `ea46cc2` overhauls the keyboard schema to `n`/`Enter`/`i`/`Esc`; docs never updated (DEC-005). |
| pre-2026-08-28 | Svelte prototype abandoned for Vue 3; `svelte.config.js` left behind (F-15). |
| pre-2026-08-28 | `submission/nhom4` snapshot frozen for coursework. |
| pre-2026-08-28 | `require_role` lost from `security.py`; backend becomes non-importable (DEC-004). |
| **2026-08-28** | Repository restructured into `source/` + `documentation/` (DEC-001). |
| **2026-08-28** | `require_role` restored; backend suite green at 6/6 for the first time (DEC-004). |
| **2026-08-28** | D1–D8 authored against the code; 18 findings and 7 prose/code conflicts recorded. |
| **2026-08-28** | Legacy SRS/URD/architecture/codebase-map/user-stories/BAO_CAO_KT1 deleted; `README.md` and `CLAUDE.md` rewritten against the code (DEC-008). |
| **2026-08-28** | Roles moved from `User` to `ProjectMember`; personal dashboard added; RISK-03 closed (DEC-009). |
| **2026-08-28** | Insecure defaults gated and made boot-blocking; RISK-01/05/11/14 closed, RISK-02 mitigated (DEC-010). Suite 6 → 29. |
| **2026-08-28** | Alembic adopted with an upgrade path for pre-existing databases; RISK-10 closed (DEC-011). |
| **2026-08-28** | JWT secret rotated; three auth-UI defects fixed; RISK-02 closed for this checkout (DEC-012). Suite → 34. |
