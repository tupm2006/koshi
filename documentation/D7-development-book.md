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

### DEC-013 — Vitest adopted; `dagSorter.ts` characterised
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

**Context.** D5 GAP-01 / RISK-06 had been the top-ranked gap since the first audit: the dependency
graph engine held the most intricate logic in the repository with zero automated coverage, and no
frontend test runner existed at all.

**Decision.** Add Vitest (config lives in `vite.config.ts`, `environment: 'node'` since `lib/` is
framework-free) and write **characterisation** tests — pinning what the code does today rather than
what an idealised spec says, per D6 P4/P5.

That distinction produced three assertions that would otherwise have looked like bugs to fix:

- **Cycle tolerance** rather than throwing (DEC-002) is asserted as correct behaviour.
- **The CPM weight scale** (S1/M3/L5/XL8) is pinned specifically, using a fixture where the storage
  scale (S1/M2/L3/XL5) would select a *different* winner. Harmonising the two scales — an obvious
  looking "cleanup" — now fails a test that explains why they differ (D4 §3.2).
- **A due date only breaks ties when both tasks have one**; a dated task does not sort ahead of an
  undated one. Labelled `QUIRK` so it reads as observed, not endorsed.

**Validating the tests.** All 28 passed on the first run, which for previously-untested code is a
warning sign rather than a success: a test that cannot fail proves nothing. Seven defects were
seeded into `dagSorter.ts` one at a time — removing the priority tie-break, inverting edge
direction, dropping the cycle remainder, including DONE tasks, swapping in the storage scale,
returning only the chain endpoint, ignoring the due-date tie-break — and every one was caught
(1–3 failures each). The source was then restored and confirmed byte-identical. This is now D6 P13.

**Found in the process — F-24.** `computeCriticalPath` memoises by task id alone, but
`getPathWeight`'s result also depends on the `visited` set that truncated the walk. On a **cyclic**
graph a node can be memoised from a truncated traversal and reused where the truncation would not
apply, so the same graph returns different answers depending on array order:

```
B <-> C  (cycle),  E depends on C
computeCriticalPath([B, C, E]) -> {B, C}
computeCriticalPath([E, B, C]) -> {B, C, E}
```

**Not fixed, deliberately.** The brief was to add tests; changing engine behaviour is a separate
decision (D6 P2), and the defect only manifests on graphs that are already invalid and already
degraded by DEC-002. It is pinned by a `KNOWN LIMITATION` test asserting both orders, so a future
fix fails loudly and forces the documentation to be updated rather than silently diverging.

The likely fix is to skip memoisation on any traversal that truncated at a visited node, at some
cost to the memo hit rate. That is a judgement call for the maintainer.

**Verification.** `pnpm test` → 28 passed. `pnpm test` is now part of the Definition of Done
(D5 §4).

**Gap unchanged in shape.** This covers one file. `taskStore.ts` — the widest-blast-radius module in
the repo, and where all three DEC-012 auth defects lived — is still untested (GAP-05, RISK-16). The
runner now exists, so it is unblocked.

---

### DEC-014 — Outstanding defects cleared; landing and profile pages added
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

Three separate asks: clear the open findings, add a landing page, and replace the
account popover with a real profile page.

#### Task identity unified (F-01, VIOLATION-01, RISK-08)

The longest-standing defect. `dependencies` was `List[str]` while `Task.id` was an integer, so a
dependency could never match a task: data round-tripped through the API and resolved to nothing.

**Decision.** The integer id is canonical everywhere. `dependencies` becomes `List[int]`;
`TaskOut` gains a derived `key` (`"TSK-12"`) as the display label. The server now **rejects**
dependency ids that do not resolve inside the same project, self-dependencies, and cross-project
references — silently storing junk is what let the defect survive this long. Legacy `"TSK-n"`
strings already in `dependencies_json` are coerced on read rather than left to poison the graph.

*Alternative rejected:* making the primary key a `TSK-n` string, matching `db/schema.sql`. That
would have required a table rebuild and a migration of every foreign key, to gain nothing the
derived `key` does not already provide.

On the client, conversion happens in exactly two functions — `taskKeyOf` / `serverIdOf` in
`services/api.ts` (INV-14). Scattering that translation is how the representations drifted apart.

`test_tasks.py` now asserts a dependency round-trips as a resolvable id, and covers the three
rejection cases. The pre-existing test that posted `"dependencies": ["TSK-1"]` was asserting the
broken contract; it was rewritten to create a real prerequisite (D6 P5 — the test encoded the bug).

#### Other findings closed

| Finding | Fix |
|:--|:--|
| **F-24** | `computeCriticalPath` cached results from truncated walks. Truncated results are now returned but never memoised, so cyclic graphs are order-independent. Its `KNOWN LIMITATION` test became a regression test. |
| **F-25** | `ApiClient.analyzeGitDiff` fabricated results and shadowed the real `parseGitDiff`. Deleted; `GitDiffModal` calls the parser directly, so secret/TODO detection actually runs. |
| **F-08** | `complexity_points` bounds now enforced on update, not only create. |
| **F-10** | The deterministic AI fallback selected its response by substring-matching the prompt, so rewording a prompt silently changed the fallback. It now takes an explicit `AIFeature` enum. |
| **F-11** | Tier 1 required `"openai"` in the URL, silently disabling it for every other compatible vendor even with a valid key. It now fires whenever a key is configured. |
| **F-16** | `acceptanceCriteria` / `dependsOnTitles` → snake_case, matching every other schema. |
| **F-18** | `datetime.utcnow()` replaced with a `utcnow()` helper returning naive UTC — aware datetimes would have broken comparisons against the naive columns. Warnings: 175 → 8. |
| **F-06, F-14, F-15** | Stale `db/schema.sql` and dead `svelte.config.js` deleted; the committed SQLite binary and build cache untracked. |
| **F-20** | UI labels corrected `c` → `n`. |
| **F-26 (DEC-007)** | `package-lock.json` removed; the Dockerfile now runs `pnpm install --frozen-lockfile` instead of `npm install` with no lockfile at all. |

**Two findings deliberately left open**, because they are decisions rather than defects:

- **F-09** — requiring `blocking_reason` when a task is `BLOCKED` conflicts directly with
  `POST /tasks/{id}/cycle-status`, which cycles *into* `BLOCKED` with no reason available.
  Enforcing it breaks that endpoint. Tracked as OQ-07.
- **FR-AI-04** — whether `/ai/decompose` should call a real model is a product question (OQ-04).

#### Landing page (FR-NAV-01..04)

An unauthenticated visitor previously landed on a board full of sample tasks with a small sign-in
popover, which implied the data was theirs and gave no sense of what the product was. `LandingPage.vue`
is now the default screen and where `logout()` returns.

**Tension resolved deliberately.** FR-PERS-02 promises the app is usable with the backend
unreachable. Forcing everyone through authentication would have quietly broken that, so the landing
page carries an explicit *"Explore the demo board without an account"* option (FR-NAV-03). Guest
mode survives, but as a choice rather than the accidental default.

#### Profile page (FR-PROJ-09..11)

`ProfilePage.vue` replaces the popover: identity with avatar/initials and member-since, stat tiles,
**editable name and skills** with dirty-state save/discard, project memberships with the caller's
role in each (selecting one opens its board), and sign-out. `AuthModal.vue` is deleted — its login
half moved to the landing page and its account half became this page.

#### Navigation

Three screens driven by `taskStore.appView` (`LANDING | BOARD | PROFILE`). A router was rejected:
three screens, no deep links to preserve, and it would add a dependency plus URL state to keep in
sync with a store that already owns the session (D3 §5a). The cost is that screens are not
addressable — the reason to revisit if deep-linking is ever wanted.

**Verification.** Backend 34 → 38 tests; frontend 28; type-check and build clean. Verified live:
a dependency round-trips as `[6]` and resolves, bogus and self-referential ids are rejected, the
landing page renders for a signed-out visitor, sign-in reaches the board, the profile page shows
identity and memberships, and sign-out returns to the landing page.

**Gap.** The landing and profile pages are auth-adjacent and have **no automated tests** (GAP-10),
and `taskStore.ts` — which now also owns `appView`, guest mode and profile updates — is still
untested (GAP-05, RISK-16). That remains the largest gap in the project.

---

### DEC-015 — Guest mode dropped, offline narrowed, marketing site, localisation, store tests
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

#### Guest mode removed

A signed-out visitor previously got a board of sample tasks. That implied the data was theirs, and
kept a second persistence path (`koshi_tasks_v2_guest`, `INITIAL_TASKS`, `resetToDefault`) that
nothing else used. All of it is deleted: authentication is now required before any project data
loads, and `taskStore.test.ts` asserts `continueAsGuest` and `isGuestMode` no longer exist so they
cannot quietly return.

#### Offline writes narrowed to personal projects (FR-PERS-02 / FR-PERS-06)

FR-PERS-02 promised the whole app worked offline. That is only safe with one writer. There is no
reconciliation (RISK-13), so two members editing the same task offline would silently overwrite each
other on reconnect.

```
1 member  + offline -> writable   (nobody else can conflict)
2+ members + offline -> READ-ONLY
any        + online  -> writable
```

`taskStore.canMutate` is the single gate; `createTask`, `updateTask` and `deleteTask` all consult it.
The UI shows a red "read-only" badge plus an explanatory banner for a shared project, and an amber
"editing locally" badge for a personal one — the two states are genuinely different and were worth
distinguishing rather than showing one generic "offline" pill.

This narrows a published requirement rather than fixing a bug, so FR-PERS-02 was rewritten and
FR-PERS-06 added. RISK-13 drops from High to Medium: the remaining exposure is one user on two
devices, not two users on one project.

#### Landing page rebuilt as a marketing site (FR-MKT)

Sticky nav, hero, product preview, features, how-it-works, use cases, pricing, FAQ, closing CTA,
footer. Sign-in is a small control in the top-right; authentication moved into `AuthDialog.vue` so
the fold is product messaging rather than a form.

**Two things deliberately not fabricated:**

- **No testimonials.** Inventing quotes from users who do not exist is fabricated social proof. The
  "who it is for" section describes use cases instead. Now D6 P14.
- **No demo video.** No video file ships with the repo, so the player renders only when
  `VITE_DEMO_VIDEO_URL` is set. An empty frame that says so is honest; a fake play button is not.

**Pricing is placeholder.** The figures are plausible defaults, not commercial decisions, and are
flagged in D1 §3.5b and RISK-18. They must be replaced before the page is published.

#### Localisation: English + Vietnamese (FR-I18N)

Hand-rolled rather than `vue-i18n`, per D6's preference for zero-dependency solutions: two locales
and a fixed key set do not justify a runtime library.

The design point is that `Translations` is *derived from the English object*, so adding a key
without a Vietnamese counterpart is a **compile error**, not a string that silently falls back at
runtime. A test additionally asserts no locale has empty or stale keys, and that Vietnamese actually
differs from English on sampled copy — which catches a locale stubbed out by copying the English
file.

`detectLocale` resolves stored choice → browser language (primary subtag, so `vi-VN` counts) →
English, and is a pure function so it is testable without a browser.

#### Store tests (GAP-05 / RISK-16)

24 tests over `taskStore.ts`: the screen state machine, the offline write policy, project selection
and per-project cache partitioning, task id translation, the status cycle and filters. `idb-keyval`
and the API client are faked via `vi.hoisted()` — `vi.mock` factories are hoisted above the file
body, so anything they close over must be created there.

Validated the same way as DEC-013: eight defects seeded one at a time — making a shared project
writable offline, making a personal one read-only, removing each mutation guard, sending the user to
the board on logout, skipping the dashboard for a project-less account, unpartitioning the cache key,
and sending dependencies as raw display keys. **All eight were caught**, and the source was restored
byte-identical.

**Verification.** Frontend 28 → 61 tests; backend 38 unchanged; type-check and build clean. Verified
in-browser: the landing page renders with a small top-right sign-in, and switching to Vietnamese
translates the entire page including pricing and FAQ.

**Gap.** Every store and pure module is now covered, so the residual risk sits entirely in `.vue`
components, which still have no tests at all (GAP-10, RISK-17) — including `AuthDialog` and
`ProfilePage`, which handle credentials and account edits.

---

### DEC-016 — Component tests; the last untested layer
**Date:** 2026-08-28 · **Status:** Active · **Requested by the maintainer**

**Context.** With both stores and every pure module covered, `.vue` files were the only layer with
no automated verification at all (GAP-10 / RISK-17) — including the two that handle credentials and
account edits.

**Decision.** Add `@vue/test-utils` + `jsdom` and cover the four highest-risk components, in
descending order of what a defect would cost:

| Component | Tests | Focus |
|:--|--:|:--|
| `AuthDialog` | 16 | Sends exactly what was typed, no role field, failure surfaced rather than a silent non-login, password cleared on success but kept after a failure. |
| `ProfilePage` | 17 | Shows the signed-in account (not a stale one), dirty-state editing, email and role not editable, memberships, sign-out clears the session. |
| `ProjectDashboard` | 14 | PM affordances present, MEMBER restrictions absent, rejected actions surfaced. |
| `LandingPage` | 14 | Sections render, sign-in is in the nav not the hero, locale switching translates the whole page, and the two content commitments hold. |

**Environment.** Vitest stays on `node` by default; component files opt in with a
`// @vitest-environment jsdom` docblock, so the pure-module suites keep running without a DOM.
`test-setup.ts` supplies `matchMedia`, which jsdom does not implement and `themeStore` calls — a
harness gap, not something the component should have to defend against.

**Two content commitments are now asserted, not just intended.** `LandingPage.test.ts` fails if a
`<video>` element appears without `VITE_DEMO_VIDEO_URL`, and fails if the copy starts claiming
"trusted by", "loved by", "customers say" and similar. Those were decisions in DEC-015 that nothing
enforced; a future copy edit would have quietly undone them.

**Mutation testing — and two false passes.** Nine defects were seeded. Six failed immediately. The
other three needed investigation rather than being written off:

1. *Removing `v-if="isPM"` from the role select* reported "0 failed". The mutation made `v-else`
   invalid on the sibling, so the template failed to **compile** and Vitest reported "no tests" —
   which the measuring script counted as zero failures. Re-run as `v-if="true"`, it was caught.
2. *Removing the `isDirty` guard in `ProfilePage`* genuinely survived: the test only asserted the
   Save button was `disabled`, which does not exercise the handler a form can still reach via
   Enter. A test for the guard itself was added, and the mutation is now caught.
3. *Removing `.trim()` from the email* genuinely survived, and the test was **wrong rather than the
   code**: an `<input type="email">` applies the HTML value-sanitisation algorithm, so jsdom strips
   surrounding whitespace before the component ever sees it. The assertion could never have failed.
   It was rewritten to state what is actually true, with the reason in a comment, rather than left
   as a green test that verified nothing.

That third case is the point of P13. A suite that passes first time on untested code is a claim, not
evidence — and here the evidence showed one assertion was theatre. D6 P13 now also warns that a
mutation which breaks compilation reads as a false pass.

**Verification.** Frontend 61 → 122 tests; backend 38 unchanged; type-check and build clean.

**Gap.** Coverage is no longer absent anywhere, but it is uneven: the **board interaction layer** —
`lib/keyboard.ts`, `TaskTable`, `KanbanBoard`, `TaskDetailModal` — is still manual-only, and that is
all fourteen FR-INT requirements (GAP-12). `lib/keyboard.ts` is the obvious next target: a pure
function over a store that is already covered, needing no DOM.

---

## Part II — Findings ledger

Observations that are not yet decisions. Each should become a decision or a work item.

| ID | Finding | Location | Severity | Status |
|:--|:--|:--|:--:|:--|
| F-01 | Task ID type differed across layers; dependencies were `List[str]` against `int` ids, so the server-side graph could never resolve. | D4 §2.1 | Critical | ✅ Closed — DEC-014 |
| F-02 | Google ID token signature verification failure fell back to **unverified** base64 payload decoding. | `routers/auth.py` | Critical | ✅ Closed — DEC-010 |
| F-03 | JWT secret hardcoded in `config.py` and `docker-compose.yml`, both public. | | Critical | ⚠️ Mitigated — DEC-010. **Rotate any deployed secret**; old tokens stay forgeable. |
| F-04 | No task endpoint verified project membership. Any user could mutate any task. | `routers/tasks.py` | High | ✅ Closed — DEC-009 |
| F-05 | `dagSorter.ts` — the most intricate logic in the repo — has zero tests. | | High | ✅ Closed — DEC-013 (28 tests, mutation-verified) |
| F-06 | `db/schema.sql` diverged from the ORM and was never executed. | | Medium | ✅ Closed — DEC-014 (deleted; Alembic owns the schema) |
| F-07 | `allow_origins=["*"]` with `allow_credentials=True` is spec-invalid. | `main.py` | Medium | ✅ Closed — DEC-010 |
| F-08 | `complexity_points` validated on create, unvalidated on update. | `schemas/task.py` | Low | ✅ Closed — DEC-014 |
| F-09 | `blocking_reason` not required when status is `BLOCKED`. | | Low | ⚠️ **Open by decision** — conflicts with `cycle-status`, which enters `BLOCKED` with no reason. OQ-07. |
| F-10 | Tier-3 AI fallback branched on substring matches in prompt text. | `ai_service.py` | Medium | ✅ Closed — DEC-014 (explicit `AIFeature` enum) |
| F-11 | Tier 1 required `"openai"` in the URL, silently disabling it for other compatible vendors. | `ai_service.py` | Medium | ✅ Closed — DEC-014 |
| F-12 | Seed data creates `pm@tupm.qzz.io` / `koshi123` whenever the users table is empty. | `main.py` | High | ✅ Closed — DEC-010 (gated by `SEED_DEMO_DATA`) |
| F-13 | No migration tooling. `create_all` never alters existing tables, so schema changes silently no-op on a deployed volume. | | High | ✅ Closed — DEC-011 (Alembic, with an upgrade path for pre-existing databases) |
| F-14 | SQLite binary and build cache were committed. | | Low | ✅ Closed — DEC-014 (untracked + gitignored) |
| F-15 | `svelte.config.js` was dead residue from a Svelte prototype. | | Low | ✅ Closed — DEC-014 (deleted) |
| F-16 | `AIDecomposeResponse` used camelCase while every other schema used snake_case. | `schemas/ai.py` | Low | ✅ Closed — DEC-014 |
| ~~F-17~~ | ~~Tests require `source/backend/data/` to exist before the first run.~~ **Incorrect when written** — `app/database.py` creates the sqlite directory itself. Corrected in D5 §1. | `database.py` | — | Withdrawn |
| F-18 | Widespread deprecated `datetime.utcnow()`. | backend | Low | ✅ Closed — DEC-014 (warnings 175 → 8) |
| F-19 | `AuthModal.vue` quick-login buttons were labelled "PM" / "Member", implying global roles. | `AuthModal.vue` | Low | ✅ Closed — DEC-012 (relabelled `pm@` / `dev@`, dev-only) |
| F-20 | UI tooltips said `c` for create task; the binding is `n`. | `App.vue`, `MobileBottomNav.vue` | Low | ✅ Closed — DEC-014 |
| F-21 | The post-auth sequence was duplicated between boot and login and drifted, leaving a signed-in user with no projects loaded. | `taskStore.ts`, `AuthModal.vue` | High | ✅ Closed — DEC-012 (single `onAuthenticated`) |
| F-22 | `App.vue` shadowed `taskStore.isDashboardOpen` with a local ref, making the store field dead state. | `App.vue` | Medium | ✅ Closed — DEC-012 |
| F-24 | `computeCriticalPath` memoised results from truncated walks, so cyclic graphs were order-dependent. | `lib/dagSorter.ts` | Medium | ✅ Closed — DEC-014 (truncated results never cached) |
| F-25 | `ApiClient.analyzeGitDiff` fabricated results and shadowed the real `parseGitDiff`. | `services/api.ts` | Medium | ✅ Closed — DEC-014 |
| F-26 | Dockerfile ran `npm install` copying neither lockfile, so the image resolved an untested dependency tree. | `Dockerfile` | Medium | ✅ Closed — DEC-014 |
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
| **2026-08-28** | Vitest adopted; `dagSorter.ts` characterised with 28 mutation-verified tests; GAP-01/RISK-06 closed, F-24 found (DEC-013). |
| **2026-08-28** | Task identity unified and 11 further findings closed; landing + profile pages added (DEC-014). Backend suite → 38. |
| **2026-08-28** | Guest mode removed; offline writes narrowed to personal projects; marketing landing page; en/vi localisation; store tests (DEC-015). Frontend suite → 61. |
| **2026-08-28** | Component tests for the four highest-risk `.vue` files; GAP-10/RISK-17 closed; two false-pass tests corrected (DEC-016). Frontend suite → 122. |
